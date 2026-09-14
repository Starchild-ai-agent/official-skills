// Starchild Live bridge — thin HTTP shell. Protocol lives in core/, scenario logic in bindings/.
import express from "express";
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
const client = new OpenAI({ maxRetries: 0, apiKey: process.env.OPENAI_API_KEY });
const port = process.env.PORT || 3000;
await mkdir(resolve("data"), { recursive: true });

// Short prompt: style + when to delegate. Business rules and tools stay in Starchild (OpenAI guidance).
const LIVE_PROMPT = [
  "You are the user's voice agent, continuing an existing Starchild conversation. Speak naturally, briefly, and follow the user's language.",
  "Answer directly when the context already has the answer: what we were doing, repeating something, progress on a task, small talk.",
  "Delegate anything that needs facts, tools, files, writing, or a decision to record. While a delegation runs, keep talking; when commentary arrives, say it in your own words, never verbatim.",
  "If interrupted, stop, listen, and do not repeat what you already said.",
].join(" ");

app.use(express.json({ limit: "1mb" }));
app.get("/", async (_req, res) => res.type("html").send(await readFile(resolve("index.html"), "utf8")));

// One bridge per Live session: LiveSession (out) + Transcripts/Delegator (in) + Binding + event pump.
const bridges = new Map();

app.post("/api/session", async (req, res) => {
  const { sdp, binding: kind = "thread", ...params } = req.body || {};
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
    const outbox = []; let sseRes = null;
    const send = (msg) => { outbox.push(msg); flush(); };
    const flush = () => { if (!sseRes) return; while (outbox.length) sseRes.write(`data: ${JSON.stringify(outbox.shift())}\n\n`); };
    const log = (...a) => console.log(`[${id}]`, ...a);
    const live = new LiveSession(send, log);
    const delegator = new Delegator({ live, transcripts: new Transcripts(), binding, log });
    const eventsAbort = new AbortController();
    (async () => { try { for await (const ev of binding.events(eventsAbort.signal)) live.think(`[Update from the conversation thread — for awareness, do not read aloud unless relevant] [${ev.kind}] ${ev.text}`, null); } catch {} })();
    bridges.set(id, { live, delegator, binding, eventsAbort, attach: (r) => { sseRes = r; flush(); }, detach: () => { sseRes = null; } });
    log("session created", Binding.kind, binding.info || "");
    res.status(201).json({ ...result, bridge_id: id, binding: binding.info || { kind } });
  } catch (error) {
    if (!(error instanceof OpenAI.APIError)) throw error;
    console.error("Live session creation failed", error.status, error.message);
    res.status(error.status || 502).json({ error: error.message });
  }
});

// Browser → bridge: every DataChannel event, verbatim.
app.post("/api/bridge/:id/event", (req, res) => {
  const b = bridges.get(req.params.id); if (!b) return res.status(404).json({ error: "no such bridge" });
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
app.delete("/api/bridge/:id", (req, res) => {
  const b = bridges.get(req.params.id); if (b) { b.delegator.close(); b.eventsAbort.abort(); bridges.delete(req.params.id); }
  res.json({ ok: true });
});

// Debug: what a binding would seed with.
app.get("/api/seed", async (req, res) => {
  try { const B = BINDINGS[req.query.binding || "thread"]; const b = await B.create(req.query); const text = await b.seed(); res.json({ ...b.info, text }); }
  catch (e) { res.status(e.status || 502).json({ error: e.message }); }
});
app.get("/api/health", (_req, res) => res.json({ ok: true, key: !!process.env.OPENAI_API_KEY, runtime: runtime.base, bindings: Object.keys(BINDINGS), active: bridges.size }));
app.get("/api/config", (_req, res) => res.json({ bindings: Object.keys(BINDINGS) }));

app.use((err, _req, res, _next) => { console.error(err); res.status(500).json({ error: "internal error" }); });
app.listen(port, "0.0.0.0", () => console.log(`starchild-live bridge listening on :${port}`));
