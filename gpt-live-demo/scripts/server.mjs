// Starchild Live bridge — thin HTTP shell. Protocol lives in core/, scenario logic in bindings/.
import express from "express";
import { WebSocket as WS } from "ws";
import OpenAI from "openai";
import { readFile } from "node:fs/promises";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { LiveSession } from "./core/live-session.mjs";
import { Transcripts } from "./core/transcripts.mjs";
import { Delegator } from "./core/delegator.mjs";
import { BINDINGS } from "./bindings/index.mjs";
import { runtime } from "./adapters/starchild-runtime.mjs";

const app = express();
const apiKey = process.env.OPENAI_REALTIME_API_KEY || process.env.OPENAI_API_KEY;
const client = new OpenAI({ maxRetries: 0, apiKey });
const port = process.env.PORT || 3000;
await mkdir(resolve("data"), { recursive: true });

// Short prompt: style + when to delegate. Business rules and tools stay in Starchild (OpenAI guidance).
const LIVE_PROMPT = [
  "You are the user's voice agent, continuing an existing Starchild conversation. Speak naturally, briefly, and follow the user's language.",
  "Answer directly when the context already has the answer: what we were doing, repeating something, small talk.",
  "Delegate anything that needs facts, tools, files, writing, or a decision to record.",
  "Progress or status questions about work (到哪了 / 合了吗 / 部署了吗 / 好了没 / did it land / is it done): ALWAYS delegate. Never answer them from your context — anything you know about a task's state is a snapshot from earlier and may already be wrong.",
  "While a delegation runs: acknowledge ONCE in a few words (e.g. 'on it'), then stay silent until commentary arrives or the user speaks. Never narrate progress, never fill silence, never say again that you are checking. Thinking updates are for your awareness only — they are not a cue to speak.",
  "When commentary arrives, say it in your own words, once. If interrupted, stop, listen, and do not repeat what you already said.",
].join(" ");

app.use(express.json({ limit: "1mb" }));
app.get("/", async (_req, res) => res.type("html").send(await readFile(resolve("index.html"), "utf8")));

// One bridge per Live session: LiveSession (out) + Transcripts/Delegator (in) + Binding + event pump.

// ── Sideband WebSocket ────────────────────────────────────────────────────────────────────────
// Official: wss://api.openai.com/v1/live/sessions/{session_id}/attach (Bearer = the key that created the
// session). Audio stays on the browser's WebRTC track; the server receives transcript / delegation /
// usage events directly and sends context appends directly. This removes the browser from the control
// plane: tab in background, laptop asleep, or a bridge restart no longer silence the agent.
// Ownership rule (docs): when both browser and sideband see an event, act ONCE — while the sideband is
// open the bridge ignores browser-forwarded events and only mirrors outbound appends to the UI.
const SIDEBAND_DISABLED = process.env.LIVE_SIDEBAND === "0";
function attachSideband({ sessionId, onEvent, onState, log }) {
  const url = `${(process.env.OPENAI_BASE_URL || "https://api.openai.com/v1").replace(/^http/, "ws").replace(/\/$/, "")}/live/sessions/${sessionId}/attach`;
  const st = { ws: null, open: false, closedBySession: false, attempts: 0, sent: 0, received: 0, connectedAt: null };
  const connect = () => {
    st.attempts += 1;
    const ws = new WS(url, { headers: { Authorization: `Bearer ${apiKey}` }, followRedirects: false });
    st.ws = ws;
    ws.on("open", () => { st.open = true; st.connectedAt = Date.now(); log("sideband attached", url); onState({ ...st }); });
    ws.on("message", (buf) => {
      let ev; try { ev = JSON.parse(buf.toString()); } catch { return; }
      // Reflected audio (input_audio.append / output_audio.delta, ~12.8 KB each, ~4/s) is for recording use-cases;
      // the browser already plays audio over WebRTC. Drop it here so it never hits the journal or the delegator.
      if (ev.type === "session.input_audio.append" || ev.type === "session.output_audio.delta") { st.audioDropped = (st.audioDropped || 0) + 1; return; }
      st.received += 1;
      if (ev.type === "session.closed") st.closedBySession = true;
      onEvent(ev);
    });
    ws.on("error", (e) => log("sideband error", e.message));
    ws.on("close", (code, reason) => {
      const lived = st.connectedAt ? Date.now() - st.connectedAt : 0;
      st.open = false; st.ws = null; st.lastClose = { code, reason: String(reason || ""), lived_ms: lived, at: new Date().toISOString() };
      onState({ ...st }); onEvent({ type: "bridge.sideband.closed", ...st.lastClose });
      log("sideband closed", code, String(reason || ""), `after ${lived}ms`);
      if (st.closedBySession || st.stopped) return;
      if (lived > 60000) st.attempts = 0; // a stable connection that dropped is not a failing one
      if (st.attempts >= 6) return log("sideband gave up after", st.attempts, "attempts");
      const delay = Math.min(15000, 500 * 2 ** st.attempts);
      setTimeout(() => { if (!st.stopped) connect(); }, delay);
    });
  };
  connect();
  return {
    state: () => ({ open: st.open, attempts: st.attempts, sent: st.sent, received: st.received, audioDropped: st.audioDropped || 0, lastClose: st.lastClose || null, connectedAt: st.connectedAt, url }),
    send: (msg) => { if (!st.open || !st.ws) return false; st.ws.send(JSON.stringify(msg)); st.sent += 1; return true; },
    close: () => { st.stopped = true; try { st.ws?.close(); } catch {} },
  };
}

const bridges = new Map();
// Debug journal: full content of every inbound DataChannel event and every outbound append, per bridge.
// In-memory ring (last 400) + append-only file data/journal.jsonl. GET /api/bridge/:id/journal?since=<ms>
import { appendFile } from "node:fs/promises";
const JOURNAL_FILE = new URL("./data/journal.jsonl", import.meta.url);
await mkdir(new URL("./data/", import.meta.url), { recursive: true }).catch(() => {});
const journals = new Map();
function journal(id, dir, ev) {
  const rec = { t: Date.now(), iso: new Date().toISOString(), bridge: id, dir, type: ev.type || "?", ev };
  const j = journals.get(id) || []; j.push(rec); if (j.length > 400) j.splice(0, j.length - 400); journals.set(id, j);
  appendFile(JOURNAL_FILE, JSON.stringify(rec) + "\n").catch(() => {});
}


app.post("/api/session", async (req, res) => {
  const { sdp, binding: kind = "thread", ...params } = req.body || {};
  // Browser forwards the signed-in user's token so delegated turns count as real user turns.
  if (req.headers.authorization) params.auth = req.headers.authorization;
  if (typeof sdp !== "string" || !sdp.trim()) return res.status(400).json({ error: "sdp is required" });
  const Binding = BINDINGS[kind];
  if (!Binding) return res.status(400).json({ error: `unknown binding: ${kind}` });

  let binding, seed;
  try { binding = await Binding.create(params); seed = await binding.seed(); }
  catch (e) { return res.status(e.status || 502).json({ error: e.message }); }

  try {
    // Shape verified against 0.3.0 (worked end-to-end): session-level fields live under `session`.
    const result = await client.live.create({
      session: {
        model: process.env.GPT_LIVE_MODEL || "gpt-live-1",
        instructions: LIVE_PROMPT,
        delegation: { type: "client" },
        input: [{ role: "developer", content: [{ type: "input_text", text: seed }] }],
      },
      transport: { type: "webrtc", sdp },
    });
    const id = `b${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const sessionId = result?.session?.id || result?.id || result?.session_id || null;
    const outbox = []; let sseRes = null; let sideband = null;
    // Outbound append: via sideband when attached (browser gets a display-only mirror), else via the browser's DataChannel.
    const send = (msg) => {
      journal(id, "out", msg);
      const viaSideband = sideband?.send(msg) === true;
      outbox.push(viaSideband ? { ...msg, mirror: true } : msg); flush();
    };
    const flush = () => { if (!sseRes) return; while (outbox.length) sseRes.write(`data: ${JSON.stringify(outbox.shift())}\n\n`); };
    const log = (...a) => console.log(`[${id}]`, ...a);
    const live = new LiveSession(send, log);
    const delegator = new Delegator({ live, transcripts: new Transcripts(), binding, log });
    const eventsAbort = new AbortController();
    (async () => { try { for await (const ev of binding.events(eventsAbort.signal)) live.think(`[Update from the conversation thread — for awareness, do not read aloud unless relevant] [${ev.kind}] ${ev.text}`, null); } catch {} })();
    const bridge = { live, delegator, binding, eventsAbort, sessionId, sideband: null, attach: (r) => { sseRes = r; flush(); }, detach: () => { sseRes = null; } };
    if (sessionId && !SIDEBAND_DISABLED) {
      sideband = attachSideband({
        sessionId, log,
        onEvent: (ev) => { journal(id, "sb", ev); if (ev.type.startsWith("bridge.")) return; delegator.onEvent(ev).catch((e) => console.error("sideband event", e.message)); },
        onState: (st) => { outbox.push({ type: "bridge.sideband", open: st.open, attempts: st.attempts, mirror: true }); flush(); },
      });
      bridge.sideband = sideband;
    } else log("sideband not attached", sessionId ? "disabled" : "no session id in create response", Object.keys(result || {}));
    bridges.set(id, bridge);
    log("session created", Binding.kind, binding.info || "", "session", sessionId);
    res.status(201).json({ ...result, bridge_id: id, session_id: sessionId, sideband: !!sideband, binding: binding.info || { kind } });
  } catch (error) {
    if (!(error instanceof OpenAI.APIError)) throw error;
    console.error("Live session creation failed", error.status, error.message);
    res.status(error.status || 502).json({ error: error.message });
  }
});

// Browser → bridge: every DataChannel event, verbatim.
app.post("/api/bridge/:id/event", (req, res) => {
  const b = bridges.get(req.params.id); if (!b) return res.status(404).json({ error: "no such bridge" });
  if (b.sideband?.state().open) { return res.json({ ok: true, ignored: "sideband-owns-control-plane" }); }
  journal(req.params.id, "in", req.body || {});
  b.delegator.onEvent(req.body || {}).catch((e) => console.error("event", e.message));
  res.json({ ok: true });
});
// Bridge → browser: messages to dc.send(), as SSE.
app.get("/api/bridge/:id/out", (req, res) => {
  const b = bridges.get(req.params.id); if (!b) return res.status(404).end();
  res.set({ "Content-Type": "text/event-stream", "Cache-Control": "no-cache", Connection: "keep-alive" }); res.flushHeaders();
  b.attach(res); const ka = setInterval(() => res.write(": ka\n\n"), 15000);
  req.on("close", () => { clearInterval(ka); b.detach(); });
});
app.get("/api/bridge/:id/journal", (req, res) => {
  const since = Number(req.query.since || 0); const type = req.query.type ? String(req.query.type) : null;
  const j = (journals.get(req.params.id) || []).filter((r) => r.t >= since && (!type || r.type.includes(type)));
  res.json({ bridge: req.params.id, count: j.length, events: j });
});
app.get("/api/journal", (_req, res) => { const all = [...journals.values()].flat().sort((a, b) => a.t - b.t); res.json({ count: all.length, events: all.slice(-200) }); });
app.delete("/api/bridge/:id", (req, res) => {
  const b = bridges.get(req.params.id); if (b) { b.delegator.close(); b.eventsAbort.abort(); b.sideband?.close(); bridges.delete(req.params.id); }
  res.json({ ok: true });
});

// Debug: what a binding would seed with.
app.get("/api/seed", async (req, res) => {
  try { const B = BINDINGS[req.query.binding || "thread"]; const b = await B.create(req.query); const text = await b.seed(); res.json({ ...b.info, text }); }
  catch (e) { res.status(e.status || 502).json({ error: e.message }); }
});
app.get("/api/bridge/:id/status", (req, res) => { const b = bridges.get(req.params.id); if (!b) return res.status(404).json({ error: "no such bridge" }); res.json({ bridge: req.params.id, session_id: b.sessionId, sideband: b.sideband ? b.sideband.state() : null, active_delegations: b.delegator.active.size }); });
app.get("/api/health", (_req, res) => res.json({ ok: true, key: !!apiKey, runtime: runtime.base, bindings: Object.keys(BINDINGS), active: bridges.size, sideband: !SIDEBAND_DISABLED, bridges: [...bridges.entries()].map(([id, b]) => ({ id, session_id: b.sessionId, sideband_open: !!b.sideband?.state().open })) }));
app.get("/api/config", (_req, res) => res.json({ bindings: Object.keys(BINDINGS) }));

app.use((err, _req, res, _next) => { console.error(err); res.status(500).json({ error: "internal error" }); });
app.listen(port, "0.0.0.0", () => console.log(`starchild-live bridge listening on :${port}`));
