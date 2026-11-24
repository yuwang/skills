---
name: organizing-bookmarks
description: 当用户要求整理、合并、同步、去重浏览器书签，或按规则归类、清理书签标题、给多环境入口（测试/开发/预发/生产等）标注环境时使用。适用于 macOS / Windows / Linux 上的 Chrome、Edge、Chromium、Brave 等 Chromium 系浏览器。
---

# Bookmark Organizer

跨平台浏览器书签工具。脚本负责机械操作（路径发现、读写、去重、合并、规则匹配），Claude 负责语义判断（制定分类规则、审阅不匹配条目、生成补丁）。

支持浏览器（Chromium 系，共享 Bookmarks JSON 格式）：Chrome、Edge、Chromium、Brave、Vivaldi、Yandex。

## 何时使用

- 用户要**整理/重组**浏览器书签的目录结构
- 用户要**合并两个浏览器**的书签（如 Chrome + Edge）
- 用户要**同步**两边书签、**去重**、**删空文件夹**
- 用户要**按规则分类**书签（域名/URL/关键词 → 分类）
- 用户要**标注环境**（test/dev/uat/sit/stg/pre/staging/prod 等多环境入口区分）
- 用户不了解书签文件在哪、想先分析现状

## 何时不要使用

- 只是想打开/查看某个书签
- 用户要求操作 Firefox / Safari 书签（格式不同，不适用）
- 浏览器正在运行且用户不愿退出

## 安全铁律（必须遵守）

1. **写入前必须完全退出浏览器**：Chrome/Edge 运行时会在退出时用内存数据覆盖文件。脚本会检测进程并拒绝写入，除非用户明确要求 `--force`。
2. **每次写入自动备份**到系统临时目录（`tempfile.gettempdir()/bookmark-organizer-backups`，macOS/Linux/Windows 通用），同名文件最多保留 20 份自动轮转。**每次写入后，必须把备份文件的完整路径告诉用户**（脚本会打印 `[备份] <路径>`），用户需要时自行转存。
3. **先预览后写入**：任何分类操作先 `--dry-run` + `--export preview.html`，让用户导入 HTML 预览确认，再实际写入。
4. **保护文件夹**：用户在规则中列入 `protected` 的文件夹（如「固定导航」）永远不动。
5. 写入后提醒用户重启浏览器验证，并告知备份文件的完整路径。

## 快速开始

```bash
# 1) 发现本机浏览器与 profile
python3 scripts/bm.py browsers

# 2) 分析现状（结构、重复、域名分布）
python3 scripts/bm.py analyze --src chrome
python3 scripts/bm.py analyze --src "edge:Profile 1"

# 3) 备份
python3 scripts/bm.py backup --src chrome

# 4) 导出预览 HTML（可导入任意浏览器查看）
python3 scripts/bm.py export --src chrome --out /tmp/preview.html

# 5) 双向合并同步（两边取并集、按归一化 URL 去重）
python3 scripts/bm.py sync --src chrome --dst edge --dry-run
python3 scripts/bm.py sync --src chrome --dst edge

# 6) 按规则分类
python3 scripts/bm.py organize --src chrome --rules rules.json --dry-run --export /tmp/preview.html
python3 scripts/bm.py organize --src chrome --rules rules.json

# 7) 用补丁精修个别条目（URL -> 分类路径）
python3 scripts/bm.py apply --src chrome --patch patch.json

# 8) 删除重复书签（--normalized 忽略 www/追踪参数/尾斜杠差异）
python3 scripts/bm.py dedupe --src chrome --dry-run
python3 scripts/bm.py dedupe --src chrome --normalized --dry-run

# 9) 标题批量清理（不可见字符/噪音后缀/超长截断/环境标注）
python3 scripts/bm.py clean --src chrome --rules clean-rules.json --dry-run
python3 scripts/bm.py clean --src chrome --rules clean-rules.json

# 10) 按 URL 精确重命名（补丁由 Claude 逐条审阅生成）
python3 scripts/bm.py rename --src chrome --patch rename.json --dry-run

# 11) 添加单条书签（无同步时才可用，路径不存在会自动新建子树）
python3 scripts/bm.py add --src chrome --url "https://..." --path "AI/模型与平台/云控制台"

# 12) 免退出浏览器（需已安装 extension/ 目录的扩展）
#    serve 会自动拉起, 空闲 120 秒自动退出, 无需常驻
python3 scripts/bm.py organize --src chrome --rules rules.json --remote --dry-run
python3 scripts/bm.py organize --src chrome --rules rules.json --remote
python3 scripts/bm.py clean --src chrome --rules clean-rules.json --remote
python3 scripts/bm.py dedupe --src chrome --normalized --remote
python3 scripts/bm.py push --url "https://..." --path "AI/模型与平台/云控制台" --name "标题"
```

`--src` 格式：`chrome`、`edge`、`chrome:Profile 1`（多 profile 时必须指定）。

## 云同步浏览器（重要限制）

Chromium 系浏览器登录账号并开启同步时（Chrome→Google 账号，Edge→Microsoft 账号），**直接修改本地 Bookmarks 文件会在浏览器启动时被云端数据覆盖**：浏览器视本地文件为"外部修改"，丢弃其同步元数据，随后以云端为准做初始同步，写入丢失。

脚本在写入前自动检测（Preferences 中的 `account_info` / `sync` 字段）：
- **检测到同步 → 中止并给出指引**，不会盲目写入；`--dry-run` 不受影响
- 需要写入时二选一：
  1. 引导用户在浏览器设置里**暂停同步** → 重新运行命令 → 验证后恢复同步（恢复时本地数据会上传）
  2. 用 `export` 生成 HTML，让用户在浏览器里**手动导入**（`chrome://bookmarks` → 导入书签 → 拖到书签栏）——推荐，最可靠，同步会正常处理导入操作
- `--force` 仅在确认云端已清空或该浏览器无同步时使用

云同步清除入口（让云端变空后再写本地或导入）：
- Chrome: https://myaccount.google.com/sync → 清除数据
- Edge: https://account.microsoft.com/privacy → 清除浏览数据

## 标准工作流（整理类任务）

**默认路径：整理 → 导出 HTML → 每个浏览器分别导入。** 一份 HTML 可导入任意多个 Chromium 系浏览器；导入操作会被云同步正常处理，也不依赖另一个浏览器存在。

1. **发现与分析**：`browsers` → `analyze --src <browser>`。把结构和重复情况汇报给用户。
2. **确认范围**：整理哪个浏览器/profile？哪些文件夹不动？顶层保留几个？
3. **制定规则**：参考 `scripts/rules.example.json`，根据 `analyze` 的域名分布和用户实际目录写一份 `rules.json`。规则覆盖不了的条目，Claude 逐条阅读后生成 `patch.json`（键为 URL，值为分类路径数组）。
4. **预览**：`organize --dry-run --export preview.html`，让用户导入浏览器确认。
5. **交付**：
   - 推荐：直接用 `export` 的 HTML，用户在每个浏览器里导入（`chrome://bookmarks` / `edge://favorites` → 导入 → 把「已导入」里的顶层文件夹拖到书签栏 → 删除旧书签）。
   - 仅当浏览器**无账号同步**时才直接写入：退出浏览器 → `organize`（不带 dry-run）→ 输出报告。有同步的浏览器直接写文件会被云端回滚（见下节）。
6. **验证**：提醒用户重启浏览器检查；出问题用备份恢复。

**单浏览器场景**（只有 Edge 没有 Chrome，或反之）：`browsers` → `analyze --src edge` → `organize --dry-run --export preview.html` → 用户导入。不需要第二个浏览器。

**多浏览器场景**：导出**一份** HTML，在每个浏览器分别导入即可，不需要脚本逐个改文件。

## 规则文件（rules.json）

```json
{
  "protected": ["固定导航"],
  "categories": [
    {"path": ["xx系统", "xx模块"], "domains": ["internal.example.com"], "keywords": ["xx功能"]},
    {"path": ["开发", "编程语言"], "keywords": ["java", "python"]},
    {"path": ["学习", "技术博客"], "domains": ["medium.com"]}
  ],
  "environment": {"suffix": "-{label}", "map": {"test": "测试", "dev": "开发", "uat": "预发", "sit": "预发", "stg": "预发", "prod": "生产"}}
}
```

匹配优先级：`domains`（主机名精确/后缀匹配）→ `url_patterns`（正则）→ `keywords`（标题或 URL 包含）。按 `categories` 顺序取第一条命中；未命中保持原位。

## 补丁文件（patch.json）

```json
{
  "https://example.com/doc/123": ["开发", "编程语言", "Java"],
  "https://other.com/page": ["学习", "技术栈"]
}
```

键是 URL（匹配时自动归一化：忽略 www、追踪参数、尾斜杠），值是目标分类路径。

## 去重（dedupe）

```bash
python3 scripts/bm.py dedupe --src chrome --dry-run          # 精确 URL 比较
python3 scripts/bm.py dedupe --src chrome --normalized       # 归一化比较
python3 scripts/bm.py dedupe --src chrome --protect "固定导航"
```

- 同一 URL 只保留**树中第一次出现**的副本（书签栏靠前的优先），报告里会列出每条被删副本的位置和保留位置
- `--normalized` 识别 `http/https` 差异、`www.` 前缀、`utm_*`/`fbclid` 等追踪参数、尾斜杠差异；**保留 `#fragment`**（SPA 路由如 `#/backlog` 不会被误判为重复）
- `--protect` 跳过指定文件夹（逗号分隔）
- 有云同步的浏览器同样适用 HTML 导入流程

## 标题清理（clean）

规则文件参考 `scripts/clean-rules.example.json`：

- `strip_invisible`：清除不可见 Unicode 字符（零宽空格、方向控制符等，常见于从网页/文档复制标题）
- `strip_suffixes`：去尾部噪音后缀（站点名、文档平台名之类，按实际配置），只去一个
- `max_length`：超长标题截断，加 `…`
- `env`：host 中**明确出现**环境词（test/dev/uat/sit/stg/pre/prod）时，把标题已有环境表示统一为 `-环境` 后缀；host 无环境词的条目不处理（避免误伤标题里本来就有的"测试/生产"等词）

## 精确重命名（rename）

补丁格式 `{"<url>": "<新标题>"}`，URL 匹配时自动归一化。适用于规则无法覆盖的条目——Claude 逐条阅读标题+URL 后生成补丁，例如把无意义的 "Sheet"/"Docs" 改成见名知义的名字。

## 添加单条书签（add）

```bash
python3 scripts/bm.py add --src chrome --url "https://..." --path "AI/模型与平台/云控制台"
```

- 目标路径不存在时**自动创建**缺失的文件夹（新建分类/子树）
- 自动抓取网页 `<title>` 作为名称；抓不到时用域名
- 已存在的 URL（归一化比较）自动跳过
- **有云同步的浏览器同样会被拦截**：实测证明单条新增也会在启动时被云端覆盖（checksum 不匹配时浏览器丢弃整个本地文件，不区分新增/删除）。必须先在浏览器设置中暂停同步，写入后再恢复

**Claude 使用方式（用户贴链接时）**：
1. 判断 URL 所属分类：优先匹配现有文件夹；现有分类都不合适时，提出一个合理的新分类路径
2. 告知用户将放置的位置（现有路径或新建路径）
3. 请用户退出浏览器 → 执行 `add` → 用户启动验证

## 浏览器扩展（免退出浏览器添加书签）

浏览器有云同步时，直接改文件会被回滚。官方唯一的程序化写入通道是**扩展的 `chrome.bookmarks` API**。`extension/` 目录提供了一个极简桥接扩展（无需上架、无需下载，本地加载即可）。

**一次性安装**（每个浏览器各一次）：
1. Chrome 打开 `chrome://extensions`（Edge 用 `edge://extensions`）
2. 打开右上角「开发者模式」
3. 点「加载已解压的扩展程序」，选择 `extension/` 目录

**支持的操作**（全部走 `chrome.bookmarks` 官方 API，云同步正常处理）：
`create` 新增 / `move` 移动 / `update` 改名 / `remove` 删除 / `removeTree` 删除文件夹 / `createFolder` 建文件夹

**使用**（所有整理命令加 `--remote` 即可免退出浏览器）：
```bash
bm.py organize --src chrome --rules rules.json --remote   # 分类（move）
bm.py clean    --src chrome --rules clean.json --remote   # 标题清理（update）
bm.py dedupe   --src chrome --normalized --remote         # 去重（remove）
bm.py rename   --src chrome --patch rename.json --remote  # 精确改名（update）
bm.py push     --url "https://..." --path "A/B/C"         # 单条新增
```

- **serve 按需自动启停**：命令会自动拉起本地服务，任务完成后自动退出（空闲 120 秒兜底），不需要常驻
- 每个已安装扩展的浏览器（Chrome/Edge）**各自执行每个任务一次**；扩展用本地存储记录已执行任务，不会重复
- 延迟：扩展每 30 秒轮询一次（浏览器限制）；点扩展图标 →「立即拉取」可立即执行
- `--remote --dry-run` 可以先看操作计划再执行

**执行结果解读（重要，避免误判）**：
- `{"complete": true, "done_by": ["chrome","edge"]}` → 成功，各浏览器均已执行
- 命令会**阻塞等待**扩展执行（最长约 30 秒 + 执行时间），返回前不要判定"没效果"
- `{"complete": false, "done_by": []}` → 超时（默认等 120 秒），说明没有扩展在线轮询。排查：
  1. `curl -s http://127.0.0.1:8765/health` 看 `active_clients`
  2. 为空或缺少某浏览器 → 浏览器没开、扩展未加载/未启用，或 service worker 报错（`chrome://extensions` 页面看「错误」）
  3. 修复后重试
- 返回 `failed: [...]` → 扩展执行报错，按条目里的 `error` 内容排查
- **不要因为"没立刻看到书签"而重复推送**——扩展有已执行记录会去重，但会多等一轮；先看命令返回值

**首次使用引导（Claude 必须执行）**：
用户第一次要求"贴链接自动加书签"时，按以下流程检查并引导：
1. 确保 `serve` 在运行，然后检查在线客户端：
   ```bash
   curl -s http://127.0.0.1:8765/health   # 看 active_clients
   ```
2. `active_clients` 含 chrome/edge → 已安装且在线，直接 `push`
3. 为空或缺某个浏览器 → **主动引导安装**，不要假设用户已装：
   - 告诉用户：扩展无需下载，是本地文件，一次性加载即可
   - 给出步骤（按浏览器）：`chrome://extensions` / `edge://extensions` → 打开「开发者模式」→「加载已解压的扩展程序」→ 选择 `extension/` 目录
   - 安装后让用户等 30 秒（或点扩展图标 →「立即拉取」），再查一次 `/health` 确认 `active_clients`
4. 扩展文件更新过（如版本号变化）→ 提醒用户在扩展页面点**刷新按钮**重新加载

注意：`serve` 与 `add` 的取舍——有云同步的浏览器用 `serve + push`；无同步的浏览器用 `add`（直接写文件，更快）。

## 环境标注

- 环境命名**完全由 `environment.map` 配置**，不限于固定几种。常见命名参考：test→测试、dev→开发、uat/sit/stg/pre/staging→预发、prod→生产、灰度/gray→灰度。按团队实际约定修改。
- 只对 URL 的 host 判断环境（避免路径/参数里的随机字符误判）。
- host 没有环境标识不等于生产——正常域名可能是唯一环境，也可能是默认生产，**不要臆断，交给用户确认**。

## 限制与注意事项

- 只支持 Chromium 系浏览器的原生 JSON 格式；Firefox（places.sqlite）/Safari 不支持。
- 备份在系统临时目录，系统可能自动清理；写入后把备份文件路径告诉用户即可。
- 不支持 Chrome 的 checksum 校验更新；Chrome 检测到外部修改会自动重新读取，通常正常。若浏览器有 Google/Microsoft 云同步，写入后启动可能触发一次重新上传，属预期行为。
- `sync` 是双向并集合并（新条目放入「同步自 <浏览器>」文件夹），不是实时同步；若要持续自动同步，建议用户使用 Floccus 等扩展。
- 写入后 guid/id 会重新生成（脚本保证唯一），不影响功能。
