const statusEl = document.getElementById("status");

async function check() {
  try {
    const r = await fetch("http://127.0.0.1:8765/health", { cache: "no-store" });
    const j = await r.json();
    statusEl.textContent = `服务在线 · 队列 ${j.queued ?? 0}`;
  } catch (e) {
    statusEl.textContent = "服务未启动 (运行 bm.py serve)";
  }
}

document.getElementById("drain").addEventListener("click", () => {
  chrome.runtime.sendMessage("drain", () => {
    statusEl.textContent = "已触发拉取";
    setTimeout(check, 500);
  });
});

check();
