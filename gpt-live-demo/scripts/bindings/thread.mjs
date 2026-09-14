// ThreadBinding — bind a Live session to one existing Starchild thread.
// The thread is the single source of truth: seed from it, delegate into it, write voice-only
// turns back to it, and forward its events to Live as silent context.
import { readFile, writeFile } from "node:fs/promises";
import { runtime } from "../adapters/starchild-runtime.mjs";

const SEED_TURNS = 10, SEED_PER_MSG = 400, SEED_MAX_CHARS = 9000; // ≈ well under the 8192-token ceiling
const VOICE_LOG_FILE = new URL("../data/voice-log.json", import.meta.url);

// Voice-only turns the runtime has not seen yet (until R2 append-message exists), keyed by session id.
const voiceLog = new Map(Object.entries(await readFile(VOICE_LOG_FILE, "utf8").then(JSON.parse).catch(() => ({}))));
let saveTimer = null;
const saveVoiceLog = () => { clearTimeout(saveTimer); saveTimer = setTimeout(() => writeFile(VOICE_LOG_FILE, JSON.stringify(Object.fromEntries(voiceLog))).catch(() => {}), 300); };

export class ThreadBinding {
  static kind = "thread";
  constructor(sessionId) { this.sessionId = sessionId; this.threadId = sessionId.split(":").pop(); this.runId = null; }

  static async create({ thread_id }) {
    // Default = the reserved Live channel thread (like TG/WeChat each own a fixed thread).
    const tid = String(thread_id || process.env.LIVE_THREAD_ID || "").trim();
    if (!tid) throw Object.assign(new Error("thread_id is required (?thread_id=<thread uuid> in the page URL)"), { status: 400 });
    const sid = await runtime.resolveSession(tid);
    if (!sid) throw Object.assign(new Error(`thread not found: ${tid}`), { status: 404 });
    return new ThreadBinding(sid);
  }

  _log() { if (!voiceLog.has(this.sessionId)) voiceLog.set(this.sessionId, []); return voiceLog.get(this.sessionId); }

  // ① Seed: recent turns + running work + voice-only tail. Bounded; oldest dropped first.
  async seed() {
    const [msgs, runs] = await Promise.all([runtime.messages(this.sessionId), runtime.runs(this.threadId)]);
    const turns = msgs.filter((m) => m.role === "user" || m.role === "assistant"); const total = turns.length;
    const recent = turns.slice(-SEED_TURNS).map((m) => `${m.role === "user" ? "User" : "Starchild"}: ${m.text.replace(/\s+/g, " ").trim().slice(0, SEED_PER_MSG)}`);
    const voice = this._log().filter((e) => !e.delegated).slice(-6).map((e) => `${e.role === "user" ? "User" : "You"}: ${e.text.slice(0, SEED_PER_MSG)}`);
    const build = (turns) => [
      `You are continuing an existing Starchild conversation thread (${total} prior messages).`,
      `Answer from this context when you can; delegate anything needing facts, tools, files, writing or decisions. Do not recite this history unless asked.`,
      ...(runs.length ? [`Work currently running in this thread: ${runs.length} run(s).`] : []),
      "", "Recent turns:", ...turns,
      ...(voice.length ? ["", "Recent voice-only exchanges (not yet in the thread):", ...voice] : []),
    ].join("\n");
    let text = build(recent);
    while (text.length > SEED_MAX_CHARS && recent.length > 2) { recent.shift(); text = build(recent); } // oldest dropped first
    this.info = { session_id: this.sessionId, thread_messages: turns.length, snapshot_turns: recent.length, snapshot_chars: text.length };
    return text;
  }

  // ② Delegate into the thread. Hands over voice-only turns first (until R2), then streams progress + reply.
  async *handle(text, { signal }) {
    const pending = this._log().filter((e) => !e.delegated);
    const voiceCtx = pending.length ? `[Voice-only exchanges since the last delegation, for context]\n${pending.map((e) => `${e.role === "user" ? "User" : "Live"}: ${e.text}`).join("\n")}\n\n` : "";
    pending.forEach((e) => { e.delegated = true; }); saveVoiceLog();
    const isChannel = this.threadId === String(process.env.LIVE_THREAD_ID || "");
    const dispatch = isChannel ? `\n\n[Live dispatcher mode] This is the user's Live voice channel thread, not a work thread. Before doing the task yourself, check whether it belongs to another thread that is already working on it (session_status locate/list_threads, other-threads context). If it does: hand it over there with sessions_message (kind=delegate, include the user's words) and reply with what you handed over and to which thread — do NOT redo the work here. Do it here only if it is a new task, a quick question, or the user explicitly says to run it here.` : "";
    const message = `${voiceCtx}[Voice] ${text}${dispatch}\n\n(The user is speaking by voice. Lead with 1–2 spoken sentences; leave details in the thread rather than reading them aloud.)`;
    let reply = "", toolsUsed = 0;
    for await (const ev of runtime.chat({ message, thread_id: this.threadId }, signal)) {
      if (ev.type === "text_delta") reply += ev.data?.text || "";
      else if (ev.data?.run_id) this.runId = ev.data.run_id;
      // Milestones only. Token-level reasoning deltas made Live "narrate" every 1.5 s during silence.
      else if (ev.type === "tool_start" && ++toolsUsed <= 3) yield { kind: "think", text: `Progress: using ${ev.data?.tool_name || "a tool"}. Still working — no need to say anything.` };
    }
    reply = reply.trim();
    // Empty stream = the thread was mid-run and the runtime merged this message into it (verified); answer lands in the thread.
    yield { kind: "say", text: reply || "Starchild was busy with another task in this thread, so your message was merged into it — the answer will appear in the conversation shortly." };
    yield { kind: "done" };
  }

  // ③ Write-back of turns Live handled itself. Buffered until the runtime offers append-message (R2).
  async onUserTurn(text) { this._push("user", text); }
  async onLiveTurn(text) { this._push("live", text); }
  _push(role, text) { const a = this._log(); a.push({ role, text: String(text).slice(0, 1000), t: Date.now(), delegated: false }); if (a.length > 60) a.splice(0, a.length - 60); saveVoiceLog(); }

  // ④ Inflow: thread events → one-line texts (payload shape not yet typed on the runtime side — R1).
  async *events(signal) {
    for await (const ev of runtime.events(this.sessionId, signal)) {
      const text = ev.summary || ev.message || ev.text || ev.content || ev.data?.message || ev.data?.text || "";
      if (typeof text === "string" && text.trim()) yield { kind: ev.type || ev.event || "event", text: text.replace(/\s+/g, " ").slice(0, 400) };
    }
  }

  // Barge-in: only claim "stopped" if the runtime confirmed the cancel. run_id is not returned yet (R3) → false.
  async interrupt() { return this.runId ? runtime.cancelRun(this.threadId, this.runId) : false; }
}
