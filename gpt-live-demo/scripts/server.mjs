import express from "express";
import OpenAI from "openai";
import { readFile, writeFile, mkdir, readdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const app = express();
const client = new OpenAI({ maxRetries: 0, apiKey: process.env.OPENAI_API_KEY });
const port = process.env.PORT || 3000;
const indexPath = resolve("index.html");
const DATA_DIR = resolve("data");

const LIVE_PROMPT = `You are Starchild's voice interface. The user talks to you by voice; you ARE Starchild itself. Never describe yourself as an "operator", "relay", or say you will "ask the backend" — you are the agent.

LANGUAGE: Always reply in the same language the user is currently speaking. Detect it from their speech every turn (they speak Chinese, you reply in Chinese; they switch to English, you switch too). If genuinely unclear, default to Simplified Chinese.

SPEAKING STYLE: concise, natural, conversational — like phoning a knowledgeable assistant. One or two sentences per answer unless the user asks you to expand.

You have these tools (the backend routes them automatically from your request):
- memory_lookup: recall past conversations and context with the user. Use when they say "before / last time / remember / we talked about".
- ask_starchild: hand complex reasoning, multi-step work, execution requests, or anything needing real-time information to the background brain (async — you must wait for it). Your most-used tool.
- check_task: report progress of a task already sent to the brain. Use when the user asks "how is it going / is it done yet".
- cancel_task: abort a background task. Use when the user says "never mind / cancel it".
- list_tasks: list all background tasks currently tracked.

POLICY:
- Greetings and small talk: answer directly. Anything that needs thinking, looking up, or doing: hand to ask_starchild.
- memory_lookup is ONLY for recalling past conversations. Never use it to answer real-time questions — news, prices, tweets, or any live lookup belongs to ask_starchild.
- Once a request is handed to ask_starchild: say "Sure, Starchild is on it — one moment", then stop talking and wait for the result. Do not add anything else.
- Before the brain has returned, it is FORBIDDEN to say "nothing found", "couldn't find it", "no results" or similar. You have no answer until the brain replies — only wait. If the user presses for progress, use check_task and relay what it says.
- Only tell the user something failed when the brain explicitly returned an error or the task was cancelled.
- If the user changes topic mid-task, leave the old task running unless they explicitly ask to cancel it.`;

app.use(express.json({ limit: "256kb" }));

// Preview reverse-proxy tolerance: if the proxy forwards the full
// /preview/<id>/... path instead of stripping the prefix, normalize it
// back to a root-relative URL so /api/* routes keep working.
app.use((req, _res, next) => {
  if (req.url.startsWith("/preview/")) {
    req.url = req.url.replace(/^\/preview\/[^/?#]+\/?/, "/") || "/";
  }
  next();
});

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
// tasks restored from disk have no live process — a "running" status here is stale
for (const t of tasks.values()) {
  if (t.status === "running") t.status = "cancelled";
}
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
            else if (ev.type === "turn_start") push("turn", `Turn ${ev.data?.turn ?? "?"} thinking started`);
            else if (ev.type === "tool_start") push("tool", `Calling tool ${ev.data?.tool_name || ""}`);
            else if (ev.type === "tool_complete") push("tool_done", `Tool ${ev.data?.tool_name || ""} returned`);
            else if (ev.type === "agent_complete") { buf = ""; break; }
          } catch (_) {}
        }
      }
      if (tasks.get(taskId)?.status === "cancelled") return;
      reply = reply.trim() || "(brain returned nothing yet)";
      histArr().push({ role: "agent", text: reply, t: Date.now() });
      saveHistory();
      tasks.set(taskId, { ...tasks.get(taskId), status: "done", reply });
    } catch (err) {
      if (err.name === "AbortError" || tasks.get(taskId)?.status === "cancelled") return;
      console.error("agent call failed", err.message);
      tasks.set(taskId, { ...tasks.get(taskId), status: "error", error: `Brain call failed: ${err.message}` });
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

// cancel all running tasks (used when the page closes without hanging up)
// NOTE: must be registered BEFORE "/api/tasks/:id/cancel" or Express matches "all" as an id
function abortTask(t) {
  if (t.controller && typeof t.controller.abort === "function") t.controller.abort();
  delete t.controller;
}
app.post("/api/tasks/all/cancel", (_req, res) => {
  let n = 0;
  for (const t of tasks.values()) {
    if (t.status === "running") { t.status = "cancelled"; abortTask(t); n++; }
  }
  if (n) saveTasks();
  res.json({ ok: true, cancelled: n });
});

app.post("/api/tasks/:id/cancel", (req, res) => {
  const t = tasks.get(req.params.id);
  if (!t) return res.status(404).json({ error: "task not found" });
  if (t.status !== "running") return res.json({ ok: false, status: t.status });
  t.status = "cancelled";
  abortTask(t);
  saveTasks();
  res.json({ ok: true, status: "cancelled" });
});


// ---- memory_lookup: search Starchild's REAL persistent memory files ----
// Reads the same store the main agent uses: memory/MEMORY.md, PROFILE.md,
// prompt/USER.md and memory/topics/*.md — not just the local voice history.
const WS_ROOT = resolve(DATA_DIR, "..", "..", "..", ".."); // scripts/data -> scripts -> gpt-live-demo -> skills -> workspace
const MEMORY_FILES = [
  resolve(WS_ROOT, "memory", "MEMORY.md"),
  resolve(WS_ROOT, "memory", "PROFILE.md"),
  resolve(WS_ROOT, "prompt", "USER.md"),
];
async function memoryFiles() {
  const chunks = [];
  for (const f of MEMORY_FILES) {
    try { chunks.push({ src: f.split("/").pop(), text: await readFile(f, "utf8") }); } catch (_) {}
  }
  // Recursively read memory/topics/**/*.md — topic bodies live in subdirectories.
  try {
    const dir = resolve(WS_ROOT, "memory", "topics");
    const walk = async (d) => {
      for (const e of await readdir(d, { withFileTypes: true })) {
        const p = resolve(d, e.name);
        if (e.isDirectory()) await walk(p);
        else if (e.name.endsWith(".md")) chunks.push({ src: `topics/${p.slice(dir.length + 1)}`, text: await readFile(p, "utf8") });
      }
    };
    await walk(dir);
  } catch (_) {}
  return chunks;
}
function extractMatches(text, kw) {
  // return lines containing the keyword, with one line of context after
  const lines = text.split("\n");
  const hits = [];
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].toLowerCase().includes(kw)) {
      hits.push(lines[i].trim() + (lines[i + 1] && lines[i + 1].trim() ? "\n  " + lines[i + 1].trim() : ""));
      if (hits.length >= 5) break;
    }
  }
  return hits;
}
// Split a Chinese/English question into searchable keywords (drop stopwords).
function tokenize(q) {
  const spaced = q.toLowerCase()
    .replace(/([a-z0-9])([\u4e00-\u9fff])/g, "$1 $2")
    .replace(/([\u4e00-\u9fff])([a-z0-9])/g, "$1 $2");
  const cleaned = spaced.replace(/(请|帮我|你|我|他|她|它|有|什么|哪些|那个|这个|一下|能否|是否|可以|看看|查询|告诉我|说说|讲讲|聊聊|回顾|之前|上次|记得吗|我们说过|历史|记忆|内容|事情|对话|聊天|记录|关于|有关|方面|情况|最近|现在|怎么|怎样|如何|是|的|了|着|过|和|跟|与|在|吗|呢|吧|啊|呀|what|which|the|about|memory|memories|history|remember|recall|tell|show|list|all|any)/g, " ");
  return [...new Set(cleaned.split(/[\s,，。？?！!；;：:、…—\-_\/\\|()（）\[\]【】"'“”‘’·]+/).filter((w) => w.length >= 2))];
}
// "你有什么记忆 / 有哪些历史" style questions want an overview, not a keyword hit.
const OVERVIEW_RE = /(有什么|有哪些|有啥|所有|全部|列出|总结|概览|盘点).*(记忆|历史|记得)|^(记忆|历史|memory)/i;
function overviewChunks(files) {
  const out = [];
  for (const { src, text } of files) {
    if (src === "_index.md") continue;
    const t = text.trim();
    if (!t) continue;
    const head = t.split("\n").filter((l) => l.trim()).slice(0, 6).join("\n").slice(0, 400);
    if (head) out.push({ source: src, text: head });
    if (out.length >= 8) break;
  }
  out.push({ source: "voice-history", text: `Local voice history holds ${histArr().length} message(s) from recent calls.` });
  return out;
}
app.get("/api/memory", async (req, res) => {
  const q = String(req.query.q || "").trim();
  const files = await memoryFiles();
  const kws = tokenize(q);
  if (!kws.length || OVERVIEW_RE.test(q)) {
    const results = overviewChunks(files);
    return res.json({ query: q, mode: "overview", total_results: results.length, results: results.slice(0, 12) });
  }
  const scored = [];
  for (const { src, text } of files) {
    const hits = [];
    for (const kw of kws) {
      for (const h of extractMatches(text, kw)) hits.push({ kw, h });
    }
    if (hits.length) scored.push({ src, hits });
  }
  // rank chunks by number of distinct keywords matched
  scored.sort((a, b) => new Set(b.hits.map((h) => h.kw)).size - new Set(a.hits.map((h) => h.kw)).size);
  let results = [];
  for (const { src, hits } of scored) {
    for (const { h } of hits) {
      results.push({ source: src, text: h.slice(0, 400) });
      if (results.length >= 12) break;
    }
    if (results.length >= 12) break;
  }
  if (!results.length) {
    // fall back to local voice conversation history (keyword OR-match)
    results = histArr()
      .filter((m) => kws.some((kw) => m.text.toLowerCase().includes(kw)))
      .slice(-10)
      .map((m) => ({ source: "voice-history", text: `${m.role === "user" ? "User" : "You"} said: ${m.text}` }));
  }
  res.json({ query: q, mode: "search", total_results: results.length, results: results.slice(0, 12) });
});

app.get("/api/health", (_req, res) => {
  res.json({ ok: true, key: !!process.env.OPENAI_API_KEY, tasks: tasks.size, history: histArr().length });
});

// Expose the live voice agent's system prompt + tool list for the UI panel.
app.get("/api/config", (_req, res) => {
  res.json({
    system_prompt: LIVE_PROMPT,
    tools: [
      { name: "memory_lookup", desc: "Recall past conversations and context (Starchild memory files + local voice history). Asking what is remembered returns an overview; specific words do a keyword search." },
      { name: "ask_starchild", desc: "Hand complex reasoning, multi-step work, or real-time lookups to the background brain (async task)." },
      { name: "check_task", desc: "Report progress of a background task." },
      { name: "cancel_task", desc: "Abort a background task." },
      { name: "list_tasks", desc: "List all tracked background tasks." },
    ],
  });
});

// Unknown /api/* routes must return JSON (not Express HTML) so the
// frontend api() helper never throws "Unexpected token '<'".
app.use("/api", (_req, res) => {
  res.status(404).json({ error: "not found" });
});

// Global error handler: always JSON.
app.use((err, _req, res, _next) => {
  console.error("unhandled", err?.message || err);
  res.status(500).json({ error: "internal error" });
});

app.listen(port, "0.0.0.0", () => {
  console.log(`gpt-live demo listening on :${port}`);
});
