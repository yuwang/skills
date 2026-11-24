// Bookmark Bridge v2 — 轮询本地服务(127.0.0.1:8765), 执行书签操作计划。
// 支持: create / move / rename / remove / removeTree / createFolder
// 每个浏览器独立执行每个任务一次(用 chrome.storage.local 记录已执行的 job id)。

const BASE = "http://127.0.0.1:8765";
const WHO = navigator.userAgent.includes("Edg/") ? "edge" : "chrome";

async function getDone() {
  const r = await chrome.storage.local.get("done");
  return new Set(r.done || []);
}

async function markDone(id) {
  const s = await getDone();
  s.add(id);
  const arr = [...s].slice(-800);
  await chrome.storage.local.set({ done: arr });
}

async function fetchJobs() {
  const r = await fetch(`${BASE}/next?who=${WHO}`, { cache: "no-store" });
  if (!r.ok) return [];
  const j = await r.json();
  return Array.isArray(j) ? j : [];
}

async function report(id, results) {
  try {
    await fetch(`${BASE}/done`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, who: WHO, results }),
    });
  } catch (e) { /* server down */ }
}

async function findOrCreateFolder(segments) {
  const roots = await chrome.bookmarks.getTree();
  const bar = roots[0].children.find((c) => c.id === "1");
  let parentId = bar ? bar.id : roots[0].children[0].id;
  for (const seg of segments || []) {
    const children = await chrome.bookmarks.getChildren(parentId);
    let found = children.find((c) => !c.url && c.title === seg);
    if (!found) found = await chrome.bookmarks.create({ parentId, title: seg });
    parentId = found.id;
  }
  return parentId;
}

async function execOp(op) {
  switch (op.op) {
    case "create": {
      const parentId = await findOrCreateFolder(op.path || []);
      await chrome.bookmarks.create({
        parentId,
        title: op.title || op.name || op.url,
        url: op.url,
      });
      return true;
    }
    case "createFolder": {
      await findOrCreateFolder(op.path || []);
      return true;
    }
    case "move": {
      const parentId = await findOrCreateFolder(op.path || []);
      await chrome.bookmarks.move(op.id, { parentId });
      return true;
    }
    case "rename": {
      await chrome.bookmarks.update(op.id, { title: op.title });
      return true;
    }
    case "remove": {
      await chrome.bookmarks.remove(op.id);
      return true;
    }
    case "removeTree": {
      await chrome.bookmarks.removeTree(op.id);
      return true;
    }
    default:
      throw new Error(`unknown op: ${op.op}`);
  }
}

async function processJob(job) {
  // 兼容旧格式: {url, path, name} -> create
  const ops = job.ops && job.ops.length ? job.ops : [{ op: "create", url: job.url, path: job.path, name: job.name }];
  const results = [];
  for (const op of ops) {
    try {
      await execOp(op);
      results.push({ op: op.op, id: op.id || null, ok: true });
    } catch (e) {
      results.push({ op: op.op, id: op.id || null, ok: false, error: String(e) });
    }
  }
  await report(job.id, results);
  return results.every((r) => r.ok);
}

async function drain() {
  const jobs = await fetchJobs();
  if (!jobs.length) return 0;
  const done = await getDone();
  let n = 0;
  for (const job of jobs) {
    if (!job.id || done.has(job.id)) continue;
    const ok = await processJob(job);
    await markDone(job.id);
    n += ok ? 1 : 0;
  }
  return n;
}

drain().catch(() => {});

chrome.alarms.create("poll", { periodInMinutes: 0.5 });
chrome.alarms.onAlarm.addListener((a) => {
  if (a.name === "poll") drain().catch(() => {});
});
chrome.runtime.onStartup.addListener(() => drain().catch(() => {}));
chrome.runtime.onInstalled.addListener(() => drain().catch(() => {}));

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg === "drain") {
    drain()
      .then((n) => sendResponse({ ok: true, added: n }))
      .catch((e) => sendResponse({ ok: false, error: String(e) }));
    return true;
  }
});
