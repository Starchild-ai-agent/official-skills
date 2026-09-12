import express from "express";
import OpenAI from "openai";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const app = express();
const client = new OpenAI({ maxRetries: 0, apiKey: process.env.OPENAI_API_KEY });
const port = process.env.PORT || 3000;
const indexPath = resolve("index.html");
const DATA_DIR = resolve("data");

const LIVE_PROMPT = `你是 Starchild 的语音界面。用户通过语音和你对话，你就是 Starchild 本身——不要把自己描述成"接线员"或"转接员"，也不要说"让我帮你问问后台"。

说话风格：简洁、自然、口语化，像打电话给一位懂技术的助理。每次回答一两句话就好，除非用户要求展开。用用户的语言（默认简体中文）回答。

你可以使用这些工具（后台会按你的请求自动路由）：
- memory_lookup：查询与用户的过往对话记忆和上下文。当用户提到"之前/上次/记得吗/我们说过"或需要历史信息时使用。
- ask_starchild：把复杂推理、多步任务、执行类请求或需要实时信息的问题交给后台大脑处理（异步，需要等待）。这是最常用的工具。
- check_task：查询已交给后台的任务进展。用户问"怎么样了/好了吗/进度"时使用。
- cancel_task：终止某个后台任务。用户说"别查了/取消那个任务"时使用。
- list_tasks：列出当前所有后台任务。

策略：
- 打招呼闲聊直接答；需要动脑、查资料、执行的事交给 ask_starchild。
- 等待大脑结果期间不要猜答案；用户催问进展时用 check_task。
- 用户中途改变话题不需要取消旧任务，除非明确要求。`;

app.use(express.json({ limit: "256kb" }));

// ---------------- persistence ----------------
if (!existsSync(DATA_DIR)) await mkdir(DATA_DIR, { recursive: true });
const TASKS_FILE = resolve(DATA_DIR, "tasks.json");
const HISTORY_FILE = resolve(DATA_DIR, "voice-history.json");

async function loadJson(file, fallback) {
  try { return JSON.parse(await readFile(file, "utf8")); } catch { return fallback; }
}
const saveTasks = (() => {
  let timer = null;
  return () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      const obj = {};
      for (const [k, v] of tasks) obj[k] = v;
      writeFile(TASKS_FILE, JSON.stringify(obj)).catch(() => {});
    }, 300);
  };
})();
const saveHistory = (() => {
  let timer = null;
  return () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      const obj = {};
      for (const [k, v] of voiceHistory) obj[k] = v;
      writeFile(HISTORY_FILE, JSON.stringify(obj)).catch(() => {});
    }, 300);
  };
})();

// tasks: id -> {status, reply?, error?, progress[], createdAt, userText, controller?}
const tasks = new Map(Object.entries(await loadJson(TASKS_FILE, {})));
// voiceHistory: sessionKey -> [{role:'user'|'agent', text, t}]  (global "voice" key shared)
const voiceHistory = new Map(Object.entries(await loadJson(HISTORY_FILE, {})));
const VOICE_KEY = "voice"; // all voice sessions share one short-term memory stream
const MAX_HISTORY = 40;

function histArr() {
  if (!voiceHistory.has(VOICE_KEY)) voiceHistory.set(VOICE_KEY, []);
  return voiceHistory.get(VOICE_KEY);
}
function histText(entries, n = MAX_HISTORY) {
  return entries.slice(-n)
    .map((m) => (m.role === "user" ? `用户: ${m.text}` : `Starchild: ${m.text}`))
    .join("\n");
}

// ---------------- routes ----------------
app.get("/", async (_req, res) => {
  res.type("html").send(await readFile(indexPath, "utf8"));
});

// Local-only demo. Add auth before exposing publicly.
app.post("/api/session", async (req, res) => {
  if (typeof req.body?.sdp !== "string" || !req.body.sdp.trim()) {
    return res.status(400).json({ error: "An SDP offer is required" });
  }
  if (!process.env.OPENAI_API_KEY) {
    return res.status(503).json({ error: "OPENAI_API_KEY not set" });
  }
  // Inject recent voice conversation history as initial context (§5 记忆回灌).
  const entries = histArr();
  const input = entries.length
    ? [{
        role: "developer",
        content: [{ type: "input_text", text:
          `以下是用户与本语音助手近期的对话历史（供上下文衔接，不要主动复述）：\n${histText(entries, 12)}` }],
      }]
    : undefined;
  try {
    const result = await client.live.create({
      session: {
        model: "gpt-live-1",
        instructions: LIVE_PROMPT,
        delegation: { type: "client" },
        ...(input ? { input } : {}),
      },
      transport: { type: "webrtc", sdp: req.body.sdp },
    });
    res.status(201).json(result);
  } catch (error) {
    if (!(error instanceof OpenAI.APIError)) throw error;
    console.error("Live session creation failed", error.status, error.message);
    res.status(error.status || 500).json({ error: error.message });
  }
});

// ---- ask_starchild: async task ----
// Frontend POSTs to start, then polls GET /api/agent/:id.
let taskSeq = 0;

app.post("/api/agent", async (req, res) => {
  const { session_id: sessionId, text } = req.body || {};
  if (typeof text !== "string" || !text.trim()) {
    return res.status(400).json({ error: "text is required" });
  }
  const h = histArr();
  h.push({ role: "user", text: text.trim(), t: Date.now() });
  if (h.length > MAX_HISTORY) h.splice(0, h.length - MAX_HISTORY);
  saveHistory();

  const message =
    (h.length > 1
      ? `以下是近期对话历史（供上下文参考）：\n${histText(h, 10).slice(0, 4000)}\n\n`
      : "") + `用户现在说：${text.trim()}\n\n请简洁口语化地回答（1-2句话，适合语音播报），默认简体中文。`;

  const taskId = `t${Date.now()}_${++taskSeq}`;
  tasks.set(taskId, { status: "running", progress: [], userText: text.trim(), createdAt: Date.now() });
  saveTasks();
  res.json({ task_id: taskId });

  const controller = new AbortController();
  tasks.get(taskId).controller = controller;
  (async () => {
    const prog = tasks.get(taskId).progress;
    const push = (kind, detail) => {
      prog.push({ t: Date.now(), kind, detail: String(detail).slice(0, 200) });
      if (prog.length > 50) prog.shift();
      saveTasks();
    };
    try {
      const r = await fetch("http://localhost:8000/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, call_source: "internal" }),
        signal: controller.signal,
      });
      if (!r.ok || !r.body) throw new Error(`agent HTTP ${r.status}`);
      const reader = r.body.getReader();
      const dec = new TextDecoder();
      let buf = "", reply = "";
      for (;;) {
        const { value, done: eof } = await reader.read();
        if (eof) break;
        buf += dec.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop();
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const ev = JSON.parse(line.slice(6));
            if (ev.type === "text_delta") reply += ev.data?.text || "";
            else if (ev.type === "turn_start") push("turn", `开始第 ${ev.data?.turn ?? "?"} 轮思考`);
            else if (ev.type === "tool_start") push("tool", `调用工具 ${ev.data?.tool_name || ""}`);
            else if (ev.type === "tool_complete") push("tool_done", `工具 ${ev.data?.tool_name || ""} 返回`);
            else if (ev.type === "agent_complete") { buf = ""; break; }
          } catch (_) {}
        }
      }
      if (tasks.get(taskId)?.status === "cancelled") return;
      reply = reply.trim() || "（大脑暂时没有返回）";
      histArr().push({ role: "agent", text: reply, t: Date.now() });
      saveHistory();
      tasks.set(taskId, { ...tasks.get(taskId), status: "done", reply });
    } catch (err) {
      if (err.name === "AbortError" || tasks.get(taskId)?.status === "cancelled") return;
      console.error("agent call failed", err.message);
      tasks.set(taskId, { ...tasks.get(taskId), status: "error", error: `大脑调用失败: ${err.message}` });
    }
    delete tasks.get(taskId)?.controller;
    saveTasks();
    setTimeout(() => { tasks.delete(taskId); saveTasks(); }, 3600000); // keep done tasks 1h
  })();
});

app.get("/api/agent/:id", (req, res) => {
  const t = tasks.get(req.params.id);
  if (!t) return res.status(404).json({ error: "task not found" });
  const { status, reply, error, progress, userText } = t;
  res.json({ status, reply, error, progress, userText });
});

// ---- task management tools ----
app.get("/api/tasks", (_req, res) => {
  const list = [...tasks.entries()].map(([id, t]) => ({
    id, status: t.status, userText: t.userText,
    progress: t.progress?.slice(-3) || [],
    createdAt: t.createdAt,
    ...(t.reply ? { reply: t.reply.slice(0, 300) } : {}),
    ...(t.error ? { error: t.error } : {}),
  }));
  res.json({ tasks: list });
});

app.post("/api/tasks/:id/cancel", (req, res) => {
  const t = tasks.get(req.params.id);
  if (!t) return res.status(404).json({ error: "task not found" });
  if (t.status !== "running") return res.json({ ok: false, status: t.status });
  t.status = "cancelled";
  t.controller?.abort();
  saveTasks();
  res.json({ ok: true, status: "cancelled" });
});

// ---- memory_lookup: search persisted voice history + task results ----
app.get("/api/memory", (req, res) => {
  const q = String(req.query.q || "").trim();
  const entries = histArr();
  let results;
  if (!q) {
    results = entries.slice(-10);
  } else {
    const kw = q.toLowerCase();
    results = entries.filter((m) => m.text.toLowerCase().includes(kw)).slice(-10);
  }
  res.json({
    query: q,
    total_entries: entries.length,
    results: results.map((m) => ({ role: m.role, text: m.text, t: m.t })),
  });
});

app.get("/api/health", (_req, res) => {
  res.json({ ok: true, key: !!process.env.OPENAI_API_KEY, tasks: tasks.size, history: histArr().length });
});

app.listen(port, "0.0.0.0", () => {
  console.log(`gpt-live demo listening on :${port}`);
});
