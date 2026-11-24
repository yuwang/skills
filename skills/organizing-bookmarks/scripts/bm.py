#!/usr/bin/env python3
"""
organizing-bookmarks: 跨平台浏览器书签分析 / 合并 / 同步 / 规则分类工具。

支持: Chrome, Edge, Chromium, Brave (Chromium 系)
平台: macOS / Windows / Linux

子命令:
  browsers                          列出发现的浏览器与 profile
  analyze   --src <b>               分析书签结构、重复、域名分布
  backup    --src <b>               备份当前书签
  export    --src <b> --out f.html  导出为可导入的 Netscape HTML (预览)
  sync      --src <b> --dst <b>     双向合并同步 (取并集, 按 URL 去重)
  mirror    --src <b> --dst <b>     单向镜像 (dst 完全变成 src)
  organize  --src <b> --rules r.json [--dry-run]  按规则分类
  apply     --src <b> --patch p.json [--dry-run]  按 URL 应用分类补丁
  dedupe    --src <b> [--normalized] [--dry-run]  删除重复书签
  add       --src <b> --url U --path P          追加一条书签到指定分类(需退出浏览器)
  serve                                          启动本地服务(配合浏览器扩展, 免退出)
  push      --url U --path P                    通过扩展实时添加书签(免退出浏览器)
  clean     --src <b> --rules r.json [--dry-run]  规则化标题清理(字符/后缀/截断/环境)
  rename    --src <b> --patch p.json [--dry-run]  按 URL 精确重命名

<b> 格式: "chrome" 或 "chrome:Profile 1"

安全: 写入前必须完全退出浏览器; 所有写入自动备份到 --backup-dir (默认 ~/bookmarks-backup)。
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse

# ---------------- 跨平台浏览器发现 ----------------

HOME = Path.home()
SYSTEM = platform.system()  # Darwin / Windows / Linux

# 默认备份到系统临时目录(跨平台自动清理), 可用 --backup-dir 指定持久位置
DEFAULT_BACKUP_DIR = Path(tempfile.gettempdir()) / "bookmark-organizer-backups"
MAX_BACKUPS_PER_FILE = 20  # 轮转: 同名文件最多保留份数


def _win_local_appdata() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(HOME / "AppData" / "Local")))


def browser_bases() -> dict[str, Path]:
    """各浏览器的 User Data 根目录。"""
    if SYSTEM == "Darwin":
        app = HOME / "Library" / "Application Support"
        return {
            "chrome": app / "Google" / "Chrome",
            "edge": app / "Microsoft Edge",
            "chromium": app / "Chromium",
            "brave": app / "BraveSoftware" / "Brave-Browser",
            "vivaldi": app / "Vivaldi",
            "yandex": app / "Yandex" / "YandexBrowser",
        }
    if SYSTEM == "Windows":
        la = _win_local_appdata()
        return {
            "chrome": la / "Google" / "Chrome" / "User Data",
            "edge": la / "Microsoft" / "Edge" / "User Data",
            "chromium": la / "Chromium" / "User Data",
            "brave": la / "BraveSoftware" / "Brave-Browser" / "User Data",
            "vivaldi": la / "Vivaldi" / "User Data",
            "yandex": la / "Yandex" / "YandexBrowser" / "User Data",
        }
    # Linux
    cfg = HOME / ".config"
    return {
        "chrome": cfg / "google-chrome",
        "edge": cfg / "microsoft-edge",
        "chromium": cfg / "chromium",
        "brave": cfg / "BraveSoftware" / "Brave-Browser",
        "vivaldi": cfg / "vivaldi",
        "yandex": cfg / "yandex-browser",
    }


PROCESS_NAMES = {
    "chrome": ["Google Chrome", "chrome.exe", "google-chrome", "google-chrome-stable"],
    "edge": ["Microsoft Edge", "msedge.exe", "microsoft-edge", "microsoft-edge-stable"],
    "chromium": ["Chromium", "chromium.exe", "chromium"],
    "brave": ["Brave Browser", "brave.exe", "brave-browser"],
    "vivaldi": ["Vivaldi", "vivaldi.exe", "vivaldi"],
    "yandex": ["Yandex", "browser.exe", "yandex-browser"],
}


def find_profiles(browser: str) -> list[tuple[str, Path]]:
    """返回 [(profile_name, Bookmarks 路径)]。"""
    base = browser_bases().get(browser)
    if base is None or not base.exists():
        return []
    out = []
    for entry in sorted(base.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name != "Default" and not entry.name.startswith("Profile "):
            continue
        bm = entry / "Bookmarks"
        if bm.exists():
            out.append((entry.name, bm))
    return out


DEFAULT_DATA_MARKERS = ("application support", ".config", "appdata", "user data")


def is_running(browser: str) -> bool:
    """检测该浏览器是否在运行。排除:
    - Helper/crashpad 子进程
    - 使用自定义 --user-data-dir 的自动化/测试实例(不影响默认 profile 的书签文件)
    """
    names = PROCESS_NAMES.get(browser, [])
    try:
        if SYSTEM == "Windows":
            out = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=10).stdout.lower()
            return any(n.lower() in out for n in names)
        out = subprocess.run(["ps", "-axo", "command"], capture_output=True, text=True, timeout=10)
        for line in out.stdout.splitlines():
            low = line.lower()
            if not any(n.lower() in low for n in names):
                continue
            if "helper" in low or "crashpad" in low:
                continue
            m = re.search(r"--user-data-dir=(\S+)", line)
            if m:
                d = m.group(1).lower()
                if not any(marker in d for marker in DEFAULT_DATA_MARKERS):
                    continue  # 自定义数据目录(自动化实例), 不影响默认书签
            return True
        return False
    except Exception:
        return False  # 无法判断时按未运行处理, 但写入前会再次提示


def parse_src(spec: str) -> tuple[str, str, Path]:
    """'chrome' / 'chrome:Profile 1' -> (browser, profile, path)"""
    browser, _, profile = spec.partition(":")
    browser = browser.strip().lower()
    profile = profile.strip()
    profiles = find_profiles(browser)
    if not profiles:
        sys.exit(f"[错误] 未找到 {browser} 的书签。请确认浏览器已安装且至少打开过一次。")
    if profile:
        for name, path in profiles:
            if name.lower() == profile.lower():
                return browser, name, path
        sys.exit(f"[错误] {browser} 下没有 profile '{profile}'。可用: {', '.join(n for n, _ in profiles)}")
    # 多个 profile 时取 Default, 否则第一个并提示
    for name, path in profiles:
        if name == "Default":
            return browser, name, path
    if len(profiles) > 1:
        print(f"[提示] {browser} 有多个 profile: {', '.join(n for n, _ in profiles)}; 默认使用 {profiles[0][0]}")
    return browser, profiles[0][0], profiles[0][1]


def has_account_sync(browser: str, profile: str) -> bool:
    """检测该 profile 是否登录账号并可能开启书签同步(Chromium 系)。
    登录了账号且存在 sync.preferences 即视为可能同步。"""
    base = browser_bases().get(browser)
    if base is None:
        return False
    pref = base / profile / "Preferences"
    if not pref.exists():
        return False
    try:
        d = json.load(open(pref, encoding="utf-8"))
    except Exception:
        return False
    if d.get("account_info"):
        return True
    sync = d.get("sync")
    if isinstance(sync, dict):
        # 只有明确的书签同步痕迹才算(新 profile 的 sync 里只有默认配置)
        if "bookmarks" in sync or sync.get("transport_data_per_account"):
            return True
    return False


def guard_sync(browser: str, profile: str, force: bool) -> None:
    """写入前保护: 检测到账号同步则中止, 除非 --force。"""
    if force:
        return
    if has_account_sync(browser, profile):
        print(f"[!] 检测到 {browser}:{profile} 已登录账号, 书签可能开启云同步。")
        print("    直接改本地文件会在浏览器启动时被云端数据覆盖(以云端为准)。")
        print("    请选择其一:")
        print("      (1) 浏览器设置中'暂停同步'后重试本命令;")
        print("      (2) 用 export 生成 HTML, 在浏览器里手动导入(推荐, 同步会正常处理);")
        print("      (3) 确认云端已清空或无同步时, 加 --force 强制写入。")
        sys.exit(2)


# ---------------- 书签模型 ----------------

INVIS = re.compile(r'[​-‏‪-‮⁠-⁤⁪-⁯﻿︀-️\U000e0000-\U000e007f]')
_TRACK = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"}


def norm_url(u: str) -> str:
    try:
        p = urlparse(u.strip())
    except Exception:
        return u.strip()
    host = (p.hostname or "").lower().removeprefix("www.")
    path = p.path.rstrip("/")
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k.lower() not in _TRACK]
    qs = urlencode(sorted(q))
    frag = p.fragment
    return f"{host}{path}" + (f"?{qs}" if qs else "") + (f"#{frag}" if frag else "")


def clean_name(name: str) -> str:
    return INVIS.sub("", name).strip()


def is_folder(n: dict) -> bool:
    return n.get("type") == "folder" or "children" in n


def chrome_time() -> str:
    return str(int((time.time() + 11644473600) * 1_000_000))


def iter_links(node: dict, path: tuple = ()):
    """产出 (link_node, parent_node, path_tuple)。"""
    for c in node.get("children", []):
        if is_folder(c):
            yield from iter_links(c, path + (clean_name(c.get("name", "")),))
        else:
            yield c, node, path


def iter_folders(node: dict, path: tuple = ()):
    for c in node.get("children", []):
        if is_folder(c):
            yield c, path + (clean_name(c.get("name", "")),)
            yield from iter_folders(c, path + (clean_name(c.get("name", "")),))


def count_links(node: dict) -> int:
    t = 0
    for c in node.get("children", []):
        t += 1 if not is_folder(c) else count_links(c)
    return t


def all_urls(data: dict) -> list[str]:
    out = []
    for root in ("bookmark_bar", "other", "synced"):
        r = data.get("roots", {}).get(root)
        if isinstance(r, dict):
            out.extend(n.get("url", "") for n, _, _ in iter_links(r) if n.get("url"))
    return out


def load_bookmarks(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def backup_dir_for(args) -> Path:
    v = getattr(args, "backup_dir", None)
    return Path(v).expanduser() if v else DEFAULT_BACKUP_DIR


def backup_file(path: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    import hashlib
    # 不同浏览器路径末段都叫 Default/Bookmarks, 必须用完整路径指纹区分
    tag = hashlib.md5(str(path).encode()).hexdigest()[:8]
    label = path.parent.parent.name or path.parent.name
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    dst = backup_dir / f"{label}-{tag}-{stamp}.json"
    shutil.copy2(path, dst)
    # 轮转: 同一书签文件的备份最多保留 MAX_BACKUPS_PER_FILE 份
    prefix = f"{label}-{tag}-"
    olds = sorted(f for f in backup_dir.glob("*.json") if f.name.startswith(prefix))
    for f in olds[:-MAX_BACKUPS_PER_FILE]:
        try:
            f.unlink()
        except OSError:
            pass
    return dst


def save_bookmarks(path: Path, data: dict, backup_dir: Path, force: bool = False) -> None:
    bak = backup_file(path, backup_dir)
    print(f"[备份] {bak}")
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    print(f"[写入] {path}")


def next_id_counter(data: dict) -> None:
    """确保新节点 id 不与现有冲突: 用 uuid 派生数字。"""
    pass


def new_folder(name: str) -> dict:
    return {
        "children": [], "date_added": chrome_time(), "date_last_used": "0",
        "date_modified": chrome_time(), "guid": str(uuid.uuid4()),
        "id": str(abs(hash(str(uuid.uuid4()))) % 10**12),
        "name": name, "type": "folder",
    }


def clone_link(n: dict, keep_meta: bool = True) -> dict:
    out = {k: n[k] for k in ("date_added", "date_last_used", "name", "type", "url") if k in n}
    out.setdefault("date_added", chrome_time())
    out.setdefault("date_last_used", "0")
    out["guid"] = str(uuid.uuid4())
    out["id"] = str(abs(hash(str(uuid.uuid4()))) % 10**12)
    if keep_meta and "meta_info" in n:
        out["meta_info"] = copy.deepcopy(n["meta_info"])
    return out


def ensure_path(parent: dict, names: list[str]) -> dict:
    node = parent
    for nm in names:
        found = None
        for c in node.get("children", []):
            if is_folder(c) and clean_name(c.get("name", "")) == nm:
                found = c
                break
        if found is None:
            found = new_folder(nm)
            node.setdefault("children", []).append(found)
        node = found
    return node


def to_netscape(root: dict) -> str:
    lines = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        "<!-- This is an automatically generated file. -->",
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        "<TITLE>Bookmarks</TITLE>", "<H1>Bookmarks</H1>", "<DL><p>",
    ]

    def esc(s):
        return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))

    def emit(node, ind):
        sp = " " * ind
        for c in node.get("children", []):
            if is_folder(c):
                lines.append(f'{sp}<DT><H3>{esc(clean_name(c.get("name","")))}</H3>')
                lines.append(f"{sp}<DL><p>")
                emit(c, ind + 4)
                lines.append(f"{sp}</DL><p>")
            else:
                lines.append(f'{sp}<DT><A HREF="{esc(c.get("url",""))}">{esc(clean_name(c.get("name","")))}</A>')

    emit(root, 4)
    lines.append("</DL><p>")
    return "\n".join(lines) + "\n"


# ---------------- 子命令 ----------------

def cmd_browsers(_args):
    any_found = False
    for b in browser_bases():
        profiles = find_profiles(b)
        if not profiles:
            continue
        any_found = True
        running = "  (运行中)" if is_running(b) else ""
        print(f"{b}{running}")
        for name, path in profiles:
            data = load_bookmarks(path)
            n = sum(count_links(data["roots"].get(r, {})) for r in ("bookmark_bar", "other"))
            print(f"    {name:12} {n:6d} 条  {path}")
    if not any_found:
        print("未发现受支持的 Chromium 系浏览器书签。")


def cmd_analyze(args):
    browser, profile, path = parse_src(args.src)
    data = load_bookmarks(path)
    print(f"== {browser} / {profile} ==\n")
    for root in ("bookmark_bar", "other"):
        r = data["roots"].get(root)
        if not isinstance(r, dict) or count_links(r) == 0:
            continue
        links = list(iter_links(r))
        urls = [n.get("url", "") for n, _, _ in links if n.get("url")]
        norm = Counter(norm_url(u) for u in urls)
        exact = Counter(urls)
        print(f"[{root}] {len(urls)} 条 | 精确重复 {sum(v-1 for v in exact.values() if v>1)} | 归一化重复 {sum(v-1 for v in norm.values() if v>1)}")
        print("  顶层:")
        for c in r.get("children", []):
            if is_folder(c):
                print(f"    📁 {clean_name(c.get('name',''))} ({count_links(c)})")
            else:
                print(f"    🔗 {clean_name(c.get('name',''))[:50]}")
        domains = Counter((urlparse(u).hostname or "").lower().removeprefix("www.") for u in urls if u)
        print("  域名 Top10:")
        for h, n in domains.most_common(10):
            print(f"    {n:5d}  {h}")
        print()


def cmd_backup(args):
    browser, profile, path = parse_src(args.src)
    backup_dir = backup_dir_for(args)
    bak = backup_file(path, backup_dir)
    print(f"已备份 {browser}:{profile} -> {bak}")


def cmd_export(args):
    browser, profile, path = parse_src(args.src)
    data = load_bookmarks(path)
    out = Path(args.out).expanduser()
    out.write_text(to_netscape(data["roots"]["bookmark_bar"]), encoding="utf-8")
    print(f"已导出 {browser}:{profile} -> {out}")


def _merge_into(target_root: dict, source_root: dict, known: set[str], synced_folder_name: str) -> int:
    """把 source 中 target 没有的链接并入 target。返回新增数。"""
    added = 0
    holder = ensure_path(target_root, [synced_folder_name])
    for link, _, src_path in iter_links(source_root):
        u = link.get("url", "")
        if not u:
            continue
        k = norm_url(u)
        if k in known:
            continue
        # 尽量保持 source 的相对路径 (去掉 source 顶层名)
        rel = list(src_path[1:]) if src_path else []
        target = ensure_path(holder, rel) if rel else holder
        target.setdefault("children", []).append(clone_link(link))
        known.add(k)
        added += 1
    return added


def cmd_sync(args):
    ab, ap, apath = parse_src(args.src)
    bb, bp, bpath = parse_src(args.dst)
    if ab == bb and ap == bp:
        sys.exit("[错误] src 与 dst 相同。")
    for b in {ab, bb}:
        if is_running(b) and not args.force and not args.dry_run:
            sys.exit(f"[错误] {b} 正在运行。请完全退出后重试, 或加 --force 强制(不推荐)。")

    if not args.dry_run:
        guard_sync(ab, ap, args.force)
        guard_sync(bb, bp, args.force)
    a = load_bookmarks(apath)
    b = load_bookmarks(bpath)
    ua = {norm_url(u) for u in all_urls(a)}
    ub = {norm_url(u) for u in all_urls(b)}

    ba = a["roots"].get("bookmark_bar", {})
    bb_bar = b["roots"].get("bookmark_bar", {})

    added_to_a = _merge_into(ba, bb_bar, ua, f"同步自 {bb}")
    added_to_b = _merge_into(bb_bar, ba, ub, f"同步自 {ab}")

    print(f"{ab} 新增 {added_to_a} 条 | {bb} 新增 {added_to_b} 条")
    if args.dry_run:
        print("[dry-run] 未写入。")
        return
    backup_dir = backup_dir_for(args)
    save_bookmarks(apath, a, backup_dir)
    save_bookmarks(bpath, b, backup_dir)
    print("同步完成。重启浏览器查看。")


def cmd_mirror(args):
    ab, ap, apath = parse_src(args.src)
    bb, bp, bpath = parse_src(args.dst)
    if is_running(bb) and not args.force and not args.dry_run:
        sys.exit(f"[错误] {bb} 正在运行。请完全退出后重试（--dry-run 可在运行时执行）。")
    if not args.dry_run:
        guard_sync(bb, bp, args.force)
    a = load_bookmarks(apath)
    b = load_bookmarks(bpath)
    b["roots"]["bookmark_bar"] = copy.deepcopy(a["roots"]["bookmark_bar"])
    if args.dry_run:
        print(f"[dry-run] 将把 {ab} 的书签栏镜像到 {bb} (共 {count_links(a['roots']['bookmark_bar'])} 条)。")
        return
    backup_dir = backup_dir_for(args)
    save_bookmarks(bpath, b, backup_dir)
    print("镜像完成。")


def _match_rule(link: dict, rule: dict) -> bool:
    url = link.get("url", "")
    name = clean_name(link.get("name", ""))
    host = (urlparse(url).hostname or "").lower()
    for d in rule.get("domains", []):
        d = d.lower().strip()
        if host == d or host.endswith("." + d):
            return True
    for pat in rule.get("url_patterns", []):
        try:
            if re.search(pat, url, re.I):
                return True
        except re.error:
            pass
    for kw in rule.get("keywords", []):
        if kw.lower() in name.lower() or kw.lower() in url.lower():
            return True
    return False


def cmd_organize(args):
    browser, profile, path = parse_src(args.src)
    rules = json.loads(Path(args.rules).read_text(encoding="utf-8"))
    protected = set(rules.get("protected", []))
    categories = rules.get("categories", [])
    if not categories:
        sys.exit("[错误] 规则文件缺少 categories。")
    if is_running(browser) and not args.force and not args.dry_run:
        sys.exit(f"[错误] {browser} 正在运行。请完全退出后重试（--dry-run 可在运行时执行）。")

    if not args.dry_run:
        guard_sync(browser, profile, args.force)
    data = load_bookmarks(path)
    bar = data["roots"]["bookmark_bar"]
    links = [(n, p, path_) for n, p, path_ in iter_links(bar) if not (path_ and path_[0] in protected)]
    by = {}
    for n, p, path_ in links:
        by[id(n)] = (n, p, path_)

    moved = 0
    unmatched = []
    for n, parent, path_ in links:
        target_path = None
        for rule in categories:
            if _match_rule(n, rule):
                target_path = rule["path"]
                break
        if target_path is None:
            unmatched.append((clean_name(n.get("name", "")), n.get("url", ""), path_))
            continue
        parent["children"] = [x for x in parent.get("children", []) if x is not n]
        target = ensure_path(bar, target_path)
        target.setdefault("children", []).append(n)
        moved += 1

    # 清理空文件夹(保护名单除外)
    def prune(node, path_):
        kept = []
        for c in node.get("children", []):
            if is_folder(c):
                if path_ and path_[0] in protected:
                    kept.append(c)
                    continue
                prune(c, path_ + (clean_name(c.get("name", "")),))
                if not c.get("children"):
                    continue
            kept.append(c)
        node["children"] = kept
    prune(bar, ())
    bar["children"] = [c for c in bar.get("children", [])
                       if not (is_folder(c) and not c.get("children"))
                       or clean_name(c.get("name", "")) in protected]

    print(f"已分类 {moved} 条, 未匹配 {len(unmatched)} 条(保持原位)")
    if unmatched:
        print("\n未匹配样例(可用 apply 补丁或补充规则):")
        for nm, u, p in unmatched[:20]:
            print(f"  {nm[:40]:42.42} {u[:60]}")
    if args.dry_run:
        print("\n[dry-run] 未写入。")
        return
    backup_dir = backup_dir_for(args)
    save_bookmarks(path, data, backup_dir)

    if args.export:
        Path(args.export).write_text(to_netscape(bar), encoding="utf-8")
        print(f"预览: {args.export}")


def cmd_serve(args):
    """启动本地 Bookmark Bridge 服务。每个浏览器扩展独立执行每个任务一次：
    GET /next?who=<chrome|edge> 返回全部 pending 任务(数组, 10 分钟过期);
    扩展自行记录已执行的 id 并跳过。"""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import threading
    import time as _t
    from urllib.parse import parse_qs, urlparse as _up
    jobs = {}
    clients = {}
    lock = threading.Lock()
    TTL = 600
    ACTIVE_WINDOW = 120
    last_activity = [__import__("time").time()]

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, obj, code=200):
            data = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            u = _up(self.path)
            qs = parse_qs(u.query)
            who = (qs.get("who", [""])[0] or "").strip().lower()
            now = _t.time()
            if who:
                last_activity[0] = now
            if who:
                with lock:
                    clients[who] = now
            if u.path == "/next":
                with lock:
                    for k in [k for k, v in jobs.items() if now - v["created"] > TTL]:
                        del jobs[k]
                    if who:
                        pending = [{"id": k, **v["job"]} for k, v in jobs.items()
                                   if not v["job"].get("target") or v["job"]["target"] == who]
                    else:
                        # 旧版扩展(不带 who): 取一个即弹出
                        k = next(iter(jobs), None)
                        pending = [{"id": k, **jobs[k]["job"]}] if k else []
                        if k:
                            del jobs[k]
                self._json(pending if who else (pending[0] if pending else {}))
            elif u.path == "/health":
                with lock:
                    active = [w for w, t in clients.items() if now - t < ACTIVE_WINDOW]
                    queued = len(jobs)
                self._json({"ok": True, "queued": queued, "active_clients": active})
            elif u.path == "/results":
                with lock:
                    self._json({k: {"done_by": sorted(v["done_by"]),
                                    "results": v.get("results", [])}
                                for k, v in jobs.items() if v["done_by"]})
            else:
                self._json({"error": "not found"}, 404)

        def do_POST(self):
            u = _up(self.path)
            ln = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(ln) or b"{}")
            except Exception:
                body = {}
            if u.path == "/add":
                last_activity[0] = __import__("time").time()
                body["id"] = str(uuid.uuid4())
                with lock:
                    jobs[body["id"]] = {"job": body, "created": _t.time(), "done_by": set()}
                    n = len(jobs)
                self._json({"ok": True, "id": body["id"], "queued": n})
            elif u.path == "/done":
                with lock:
                    j = jobs.get(body.get("id"))
                    if j:
                        j["done_by"].add(body.get("who") or "?")
                        j.setdefault("results", []).extend(body.get("results") or [])
                self._json({"ok": True})
            else:
                self._json({"error": "not found"}, 404)

    srv = ThreadingHTTPServer((args.host, args.port), H)
    print(f"Bookmark Bridge 服务已启动: http://{args.host}:{args.port}")
    print(f"扩展轮询: http://{args.host}:{args.port}/next?who=<chrome|edge>")
    if args.idle_timeout:
        def watchdog():
            while True:
                __import__("time").sleep(5)
                if __import__("time").time() - last_activity[0] > args.idle_timeout:
                    print(f"空闲 {args.idle_timeout}s, 自动退出")
                    srv.shutdown()
                    return
        threading.Thread(target=watchdog, daemon=True).start()
    print("Ctrl+C 退出")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


def _http_json(url, data=None, timeout=5):
    import urllib.request
    if data is not None:
        req = urllib.request.Request(url, data=json.dumps(data, ensure_ascii=False).encode(),
                                     headers={"Content-Type": "application/json"})
    else:
        req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


def ensure_serve(port):
    """确保本地服务在运行。返回 (already_running, proc_or_None)。"""
    try:
        _http_json(f"http://127.0.0.1:{port}/health", timeout=1)
        return True, None
    except Exception:
        pass
    proc = subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "serve", "--port", str(port),
         "--idle-timeout", "120"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(25):
        try:
            _http_json(f"http://127.0.0.1:{port}/health", timeout=1)
            return False, proc
        except Exception:
            time.sleep(0.2)
    proc.terminate()
    sys.exit("[错误] 本地服务启动失败")


def push_ops(port, ops, timeout=120, wait=True, target=""):
    """下发操作计划, 等待所有在线客户端执行完成。target 可定向单个浏览器。"""
    payload = {"ops": ops}
    if target:
        payload["target"] = target
    r = _http_json(f"http://127.0.0.1:{port}/add", payload)
    jid = r.get("id")
    if not wait:
        return {"job": jid, "done_by": [], "complete": False}
    deadline = time.time() + timeout
    done_by = []
    while time.time() < deadline:
        try:
            res = _http_json(f"http://127.0.0.1:{port}/results")
            if jid in res:
                done_by = res[jid].get("done_by") or []
                results = res[jid].get("results") or []
                failed = [r for r in results if not r.get("ok")]
                if failed:
                    return {"job": jid, "done_by": done_by, "complete": True, "failed": failed[:10]}
                h = _http_json(f"http://127.0.0.1:{port}/health")
                active = set(h.get("active_clients") or [])
                expected = {target} if target else active
                if done_by and expected and set(done_by) >= expected:
                    return {"job": jid, "done_by": done_by, "complete": True}
        except Exception:
            pass
        time.sleep(1)
    return {"job": jid, "done_by": done_by, "complete": False}


def cmd_push(args):
    """向运行中的 Bookmark Bridge 服务推送一条书签任务(由浏览器扩展执行)。"""
    import urllib.error
    import urllib.request
    payload = json.dumps({
        "url": args.url,
        "path": [x.strip() for x in args.path.split("/") if x.strip()],
        "name": args.name or "",
    }).encode()
    already, proc = ensure_serve(args.port)
    try:
        res = push_ops(args.port, [{"op": "create", "url": args.url,
                                    "path": [x.strip() for x in args.path.split("/") if x.strip()],
                                    "title": args.name or ""}],
                       target=getattr(args, "target", ""))
        print(res)
    finally:
        if proc:
            proc.terminate()


def fetch_page_title(url: str) -> str:
    """尽力抓取网页 <title>(内网/无法访问时返回空)。"""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            raw = r.read(300000)
        text = raw.decode("utf-8", "ignore")
        m = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()[:100]
    except Exception:
        pass
    return ""


def cmd_add(args):
    """向指定分类路径追加一条书签。注意: 有云同步时必须先暂停同步, 否则启动后会被云端覆盖。"""
    browser, profile, path = parse_src(args.src)
    url = args.url.strip()
    target = [x.strip() for x in args.path.split("/") if x.strip()]
    if not url or not target:
        sys.exit("[错误] 需要 --url 和 --path(如 'AI/模型与平台/云控制台')")
    if is_running(browser) and not args.dry_run:
        print(f"[!] {browser} 正在运行。新增单条书签也需要先完全退出浏览器(Cmd+Q), 否则会被内存数据覆盖。")
        print("    退出后重新运行本命令。")
        sys.exit(2)
    if not args.dry_run:
        guard_sync(browser, profile, args.force)
    data = load_bookmarks(path)
    bar = data["roots"]["bookmark_bar"]
    key = norm_url(url)
    for link, _, _ in iter_links(bar):
        if norm_url(link.get("url", "")) == key:
            p_ = None
            print(f"[跳过] 已存在: {clean_name(link.get('name',''))} | {url}")
            return
    name = args.name or fetch_page_title(url) or (urlparse(url).hostname or url)
    folder = ensure_path(bar, target)
    link = {
        "date_added": chrome_time(), "date_last_used": "0", "guid": str(uuid.uuid4()),
        "id": str(abs(hash(str(uuid.uuid4()))) % 10**12),
        "name": clean_name(name), "type": "url", "url": url,
    }
    folder.setdefault("children", []).append(link)
    print(f"新增: {link['name']} | {url}")
    print(f"位置: {' / '.join(target)}")
    if args.dry_run:
        print("[dry-run] 未写入。")
        return
    save_bookmarks(path, data, backup_dir_for(args))


def cmd_dedupe(args):
    """删除重复书签。默认按精确 URL; --normalized 按归一化 URL(忽略 www/追踪参数/尾斜杠)。
    保留策略: 树中第一次出现的副本(书签栏靠前的优先)。"""
    browser, profile, path = parse_src(args.src)
    protected = {x.strip() for x in (args.protect or "").split(",") if x.strip()}
    if getattr(args, "remote", False):
        data = load_bookmarks(path)
        bar = data["roots"]["bookmark_bar"]
        seen = {}
        ops = []
        for n, parent, path_ in iter_links(bar):
            if path_ and path_[0] in protected:
                continue
            url = n.get("url", "")
            if not url:
                continue
            key = norm_url(url) if args.normalized else url
            if key in seen:
                ops.append({"op": "remove", "id": n.get("id")})
            else:
                seen[key] = n
        print(f"[remote] 计划删除重复 {len(ops)} 条")
        if args.dry_run:
            for o in ops[:20]:
                print(" ", o)
            print("[dry-run] 未下发。")
            return
        already, proc = ensure_serve(getattr(args, "port", 8765))
        res = push_ops(getattr(args, "port", 8765), ops)
        print(f"[remote] 执行结果: {res}")
        if proc:
            proc.terminate()
        return
    if not args.dry_run:
        guard_sync(browser, profile, args.force)
    data = load_bookmarks(path)
    bar = data["roots"]["bookmark_bar"]
    seen = {}
    removed = []

    def walk(node, path_):
        kept = []
        for c in node.get("children", []):
            if is_folder(c):
                nm = clean_name(c.get("name", ""))
                if nm in protected:
                    kept.append(c)
                    continue
                walk(c, path_ + [nm])
                kept.append(c)
                continue
            url = c.get("url", "")
            if not url:
                kept.append(c)
                continue
            key = norm_url(url) if args.normalized else url
            if key in seen:
                removed.append((clean_name(c.get("name", "")), url, path_, seen[key][1]))
                continue
            seen[key] = (c, path_)
            kept.append(c)
        node["children"] = kept

    walk(bar, [])
    print(f"删除重复 {len(removed)} 条 (模式: {'归一化 URL' if args.normalized else '精确 URL'})")
    for name, url, p1, p2 in removed[:20]:
        print(f"  {name[:36]:38.38} {url[:45]}")
        print(f"      删除于: {' / '.join(p1) or '(根)'}  | 保留: {' / '.join(p2) or '(根)'}")
    if len(removed) > 20:
        print(f"  ...还有 {len(removed) - 20} 条")
    if args.dry_run:
        print("[dry-run] 未写入。")
        return
    save_bookmarks(path, data, backup_dir_for(args))


def cmd_clean(args):
    """规则化标题清理: 不可见字符/噪音后缀/超长截断/环境标注。"""
    browser, profile, path = parse_src(args.src)
    rules = json.loads(Path(args.rules).read_text(encoding="utf-8"))
    protected = set(rules.get("protected", []))
    suffixes = rules.get("strip_suffixes", [])
    maxlen = int(rules.get("max_length") or 0)
    env_cfg = rules.get("env") or {}
    env_map = {k.lower(): v for k, v in (env_cfg.get("map") or {}).items()}
    env_suffix = env_cfg.get("suffix", "-{label}")
    host_env_re = re.compile(r'(^|[-._])(test|dev|uat|sit|pre|staging|stg|prod)(?=[-._]|$)', re.I)
    tail_env_re = re.compile(r'[-_\s]*[\[\(【]?(测试|开发|生产|预发|UAT|SIT)[\]\)】]?\s*$', re.I)
    tail_en_re = re.compile(r'[-_\s]*(test|dev|uat|sit|pre|prod|stg|staging|开发|测试|生产|预发)\s*$', re.I)

    if getattr(args, "remote", False):
        data = load_bookmarks(path)
        bar = data["roots"]["bookmark_bar"]
        ops = []
        for n, parent, path_ in iter_links(bar):
            if path_ and path_[0] in protected:
                continue
            old = n.get("name", "")
            new = old
            if rules.get("strip_invisible", True):
                new = INVIS.sub("", new).strip()
            for suf in suffixes:
                if new.endswith(suf) and len(new) > len(suf):
                    new = new[: -len(suf)].rstrip()
                    break
            if maxlen and len(new) > maxlen:
                new = new[: maxlen - 1] + "…"
            if env_map:
                host = (urlparse(n.get("url", "")).hostname or "").lower()
                m = host_env_re.search(host)
                if m:
                    label = env_map.get(m.group(2).lower())
                    if label:
                        b = tail_env_re.sub("", new).rstrip()
                        b = tail_en_re.sub("", b).rstrip() or b
                        new = f"{b}{env_suffix.format(label=label)}"
            if new != old:
                ops.append({"op": "update", "id": n.get("id"), "title": new})
        print(f"[remote] 计划重命名 {len(ops)} 条")
        if args.dry_run:
            for o in ops[:10]:
                print(" ", o)
            print("[dry-run] 未下发。")
            return
        already, proc = ensure_serve(getattr(args, "port", 8765))
        res = push_ops(getattr(args, "port", 8765), ops)
        print(f"[remote] 执行结果: {res}")
        if proc:
            proc.terminate()
        return
    if not args.dry_run:
        guard_sync(browser, profile, args.force)
    data = load_bookmarks(path)
    bar = data["roots"]["bookmark_bar"]
    changes = []

    def walk(node):
        for c in node.get("children", []):
            if is_folder(c):
                if clean_name(c.get("name", "")) in protected:
                    continue
                walk(c)
                continue
            old = c.get("name", "")
            new = old
            if rules.get("strip_invisible", True):
                new = INVIS.sub("", new).strip()
            for suf in suffixes:
                if new.endswith(suf) and len(new) > len(suf):
                    new = new[: -len(suf)].rstrip()
                    break
            if maxlen and len(new) > maxlen:
                new = new[: maxlen - 1] + "…"
            if env_map:
                host = (urlparse(c.get("url", "")).hostname or "").lower()
                m = host_env_re.search(host)
                if m:
                    label = env_map.get(m.group(2).lower())
                    if label:
                        # host 明确带环境词时才处理, 避免误伤文档名
                        base = tail_env_re.sub("", new).rstrip()
                        base = tail_en_re.sub("", base).rstrip() or base
                        new = f"{base}{env_suffix.format(label=label)}"
            if new != old:
                c["name"] = new
                changes.append((old, new))

    walk(bar)
    print(f"重命名 {len(changes)} 条")
    for a, b in changes[:20]:
        print(f"  {a[:45]:47.47} -> {b[:45]}")
    if len(changes) > 20:
        print(f"  ...还有 {len(changes) - 20} 条")
    if args.dry_run:
        print("[dry-run] 未写入。")
        return
    save_bookmarks(path, data, backup_dir_for(args))


def cmd_rename(args):
    """按 URL 补丁精确重命名: {"<url>": "<新标题>"}"""
    browser, profile, path = parse_src(args.src)
    patch = json.loads(Path(args.patch).read_text(encoding="utf-8"))
    norm_patch = {norm_url(k): v for k, v in patch.items()}
    if getattr(args, "remote", False):
        data = load_bookmarks(path)
        bar = data["roots"]["bookmark_bar"]
        ops = []
        for link, _, _ in iter_links(bar):
            k = norm_url(link.get("url", ""))
            if k in norm_patch:
                ops.append({"op": "update", "id": link.get("id"), "title": norm_patch[k]})
        print(f"[remote] 计划重命名 {len(ops)} 条")
        if args.dry_run:
            for o in ops[:10]:
                print(" ", o)
            print("[dry-run] 未下发。")
            return
        already, proc = ensure_serve(getattr(args, "port", 8765))
        res = push_ops(getattr(args, "port", 8765), ops)
        print(f"[remote] 执行结果: {res}")
        if proc:
            proc.terminate()
        return
    if not args.dry_run:
        guard_sync(browser, profile, args.force)
    data = load_bookmarks(path)
    bar = data["roots"]["bookmark_bar"]
    n = 0
    applied = []
    for link, _, _ in iter_links(bar):
        k = norm_url(link.get("url", ""))
        if k in norm_patch:
            applied.append((link.get("name", ""), norm_patch[k]))
            link["name"] = norm_patch[k]
            n += 1
    print(f"重命名 {n} 条")
    for a, b in applied[:20]:
        print(f"  {a[:45]:47.47} -> {b[:45]}")
    if args.dry_run:
        print("[dry-run] 未写入。")
        return
    save_bookmarks(path, data, backup_dir_for(args))


def cmd_apply(args):
    browser, profile, path = parse_src(args.src)
    patch = json.loads(Path(args.patch).read_text(encoding="utf-8"))
    # patch: {"<norm_url>": ["路径","子路径"]}
    norm_patch = {norm_url(k): v for k, v in patch.items()}
    if is_running(browser) and not args.force and not args.dry_run:
        sys.exit(f"[错误] {browser} 正在运行。请完全退出后重试（--dry-run 可在运行时执行）。")
    if not args.dry_run:
        guard_sync(browser, profile, args.force)
    data = load_bookmarks(path)
    bar = data["roots"]["bookmark_bar"]
    applied = 0
    for n, parent, _ in list(iter_links(bar)):
        k = norm_url(n.get("url", ""))
        if k in norm_patch:
            parent["children"] = [x for x in parent.get("children", []) if x is not n]
            target = ensure_path(bar, norm_patch[k])
            target.setdefault("children", []).append(n)
            applied += 1
    print(f"应用补丁 {applied} 条")
    if args.dry_run:
        print("[dry-run] 未写入。")
        return
    save_bookmarks(path, data, backup_dir_for(args))


# ---------------- CLI ----------------

def main():
    p = argparse.ArgumentParser(description="跨平台浏览器书签整理工具")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("browsers", help="列出发现的浏览器")
    sp.set_defaults(fn=cmd_browsers)

    for name, fn, needs_src, extra in [
        ("analyze", cmd_analyze, True, []),
        ("backup", cmd_backup, True, []),
        ("export", cmd_export, True, ["--out"]),
        ("sync", cmd_sync, True, ["--dst"]),
        ("mirror", cmd_mirror, True, ["--dst"]),
        ("organize", cmd_organize, True, ["--rules"]),
        ("apply", cmd_apply, True, ["--patch"]),
        ("clean", cmd_clean, True, ["--rules"]),
        ("dedupe", cmd_dedupe, True, []),
        ("add", cmd_add, True, []),
        ("serve", cmd_serve, False, []),
        ("push", cmd_push, False, []),
        ("rename", cmd_rename, True, ["--patch"]),
    ]:
        sp = sub.add_parser(name)
        if needs_src:
            sp.add_argument("--src", required=True, help="chrome / edge / chrome:Profile 1")
        for e in extra:
            if e == "--out":
                sp.add_argument("--out", required=True)
            elif e == "--dst":
                sp.add_argument("--dst", required=True)
            elif e == "--rules":
                sp.add_argument("--rules", required=True)
            elif e == "--patch":
                sp.add_argument("--patch", required=True)
        sp.add_argument("--backup-dir", default=None, help="备份目录(默认系统临时目录, 自动轮转)")
        sp.add_argument("--dry-run", action="store_true")
        sp.add_argument("--force", action="store_true")
        if name == "organize":
            sp.add_argument("--export", help="同时导出预览 HTML")
        if name in ("organize", "clean", "dedupe", "rename"):
            sp.add_argument("--remote", action="store_true",
                            help="通过浏览器扩展执行, 免退出浏览器(需已安装 extension/)")
            sp.add_argument("--port", type=int, default=8765)
        if name == "dedupe":
            sp.add_argument("--normalized", action="store_true",
                            help="按归一化 URL 比较(忽略 www/追踪参数/尾斜杠)")
            sp.add_argument("--protect", default="", help="额外保护的文件夹名, 逗号分隔")
        if name == "add":
            sp.add_argument("--url", required=True, help="要添加的书签 URL")
            sp.add_argument("--path", required=True, help="目标分类路径, 如 'AI/模型与平台/云控制台'")
            sp.add_argument("--name", default="", help="标题(默认自动抓取网页标题)")
        if name == "serve":
            sp.add_argument("--host", default="127.0.0.1")
            sp.add_argument("--port", type=int, default=8765)
            sp.add_argument("--idle-timeout", type=int, default=300,
                            help="无活动多少秒后自动退出(0=常驻)")
        if name == "push":
            sp.add_argument("--url", required=True)
            sp.add_argument("--path", required=True, help="目标分类路径")
            sp.add_argument("--name", default="")
            sp.add_argument("--port", type=int, default=8765)
            sp.add_argument("--target", default="", help="只推给指定浏览器: chrome / edge")
        sp.set_defaults(fn=fn)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
