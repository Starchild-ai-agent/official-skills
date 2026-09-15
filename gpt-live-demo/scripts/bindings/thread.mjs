
function syncRemoteMessage(userId, threadId, role, content) {
  try {
    const text = String(content || "").trim();
    if (!text) return;
    const proc = spawn("python3", [
      new URL("../sync_messages.py", import.meta.url).pathname,
      String(userId || "2004"),
      String(threadId),
      String(role),
      text
    ], { detached: true, stdio: "ignore" });
    proc.unref();
  } catch (e) {
    // best-effort sync
  }
}
import { spawn } from "node:child_process";
import { estTokens } from "../core/live-session.mjs";
// ThreadBinding — bind a Live session to one existing Starchild thread.
// The thread is the single source of truth: seed from it, delegate into it, write voice-only
// turns back to it, and forward its events to Live as silent context.
import { readFile, writeFile } from "node:fs/promises";
import { runtime } from "../adapters/starchild-runtime.mjs";


// Voice-turn guidance for every delegated turn. Sent as request.system_prompt (appended after the platform
// prompt, identical every turn → prompt-cache friendly); the user message stays just "[Voice] …".
const LIVE_TURN_PROMPT = [
  "The user is speaking by voice through Starchild Live. Start your reply with the spoken part wrapped as [spoken]…[/spoken] (1–2 short sentences, what you would say out loud), then the details for the thread. Only the [spoken] part is voiced; everything after it is read silently.",
  "Resolve pronouns and vague references (他/那边/那个/it/them) from context you already have — the recent turns, the delegated-task list in this prompt, and your <other-threads> block — before asking. Ask only when two candidates are equally plausible.",
  "Transcripts can be garbled. If the words are broken but the intent is clear, act on the intent; if the intent is genuinely unclear, ask one short question instead of guessing.",
].join(" ");

const LIVE_DISPATCH_PROMPT = LIVE_TURN_PROMPT + " " + [
  "This thread is the user's Live voice channel, not a work thread — you are the dispatcher.",
  "PROGRESS QUESTIONS (到哪了 / 合了吗 / 部署了吗 / 好了没): never answer from memory. In the same turn, read the owning thread's latest messages (session_status action=thread_messages) or the real system state (git/PR/deploy) first; if you cannot read it, say you are checking rather than asserting a status.",
  "OWNERSHIP: before doing a task yourself, check whether another thread already owns it (other-threads context, session_status list_threads). If so, hand it over with sessions_message (kind=delegate, include the user's words) and ask that thread to post its outcome back to THIS thread via sessions_message when done — so the user sees results here without switching threads. Tell the user you handed it over, to which thread, and that the result will come back here. Do it here only for a new task, a quick question, or when the user explicitly says to run it here.",
  "THREAD NAMES: whenever you mention another thread, use its REAL sidebar title (session_status list_threads thread_title with title_source=service, or the «title» in other-threads). The title is the only handle the user can find a thread by. Never present a summary headline, gist or your own paraphrase as the title; if no real title exists, say so and quote that thread's first user message.",
  "Do not read internal notifications (memory/topic/skill writes) aloud or mention them unless asked.",
].join(" ");

// Delegated-task ledger: what was handed to Starchild and what came back (short). Seeds the next session and
// each delegated turn so "他 / 那边 / 那个任务" has a referent and progress answers have an anchor.
const LEDGER_FILE = new URL("../data/delegation-ledger.json", import.meta.url);
const LEDGER_MAX = 8;
async function loadLedger() { try { return JSON.parse(await readFile(LEDGER_FILE, "utf8")); } catch { return {}; } }
async function saveLedger(l) { try { await writeFile(LEDGER_FILE, JSON.stringify(l)); } catch {} }

const SEED_TURNS = 10, SEED_PER_MSG = 400, SEED_MAX_TOKENS = 6000; // official ceiling: 128 items / 8,192 tokens total — keep headroom for instructions
const VOICE_LOG_FILE = new URL("../data/voice-log.json", import.meta.url);

// Voice-only turns the runtime has not seen yet (until R2 append-message exists), keyed by session id.
const voiceLog = new Map(Object.entries(await readFile(VOICE_LOG_FILE, "utf8").then(JSON.parse).catch(() => ({}))));
let saveTimer = null;
const saveVoiceLog = () => { clearTimeout(saveTimer); saveTimer = setTimeout(() => writeFile(VOICE_LOG_FILE, JSON.stringify(Object.fromEntries(voiceLog))).catch(() => {}), 300); };

export class ThreadBinding {
  static kind = "thread";
  constructor(sessionId, auth) { this.sessionId = sessionId; this.threadId = sessionId.split(":").pop(); this.runId = null; this.auth = auth || null; }

  static async create({ thread_id, auth }) {
    // Default = the reserved Live channel thread (like TG/WeChat each own a fixed thread).
    const tid = String(thread_id || process.env.LIVE_THREAD_ID || "").trim();
    if (!tid) throw Object.assign(new Error("thread_id is required (?thread_id=<thread uuid> in the page URL)"), { status: 400 });
    const sid = await runtime.resolveSession(tid);
    if (!sid) throw Object.assign(new Error(`thread not found: ${tid}`), { status: 404 });
    return new ThreadBinding(sid, auth);
  }

  _log() { if (!voiceLog.has(this.sessionId)) voiceLog.set(this.sessionId, []); return voiceLog.get(this.sessionId); }

  // ① Seed: recent turns + running work + voice-only tail. Bounded; oldest dropped first.
  async seed() {
    const [msgs, runs] = await Promise.all([runtime.messages(this.sessionId), runtime.runs(this.threadId)]);
    const turns = msgs.filter((m) => m.role === "user" || m.role === "assistant"); const total = turns.length;
    const recent = turns.slice(-SEED_TURNS).map((m) => `${m.role === "user" ? "User" : "Starchild"}: ${m.text.replace(/\s+/g, " ").trim().slice(0, SEED_PER_MSG)}`);
    const voice = this._log().filter((e) => !e.delegated).slice(-6).map((e) => `${e.role === "user" ? "User" : "You"}: ${e.text.slice(0, SEED_PER_MSG)}`);
    this._ledgerCache = (await loadLedger())[this.sessionId] || [];
    const ledger = this._ledgerLines();
    const build = (turns) => [
      `You are continuing an existing Starchild conversation thread (${total} prior messages).`,
      `Answer from this context when you can; delegate anything needing facts, tools, files, writing or decisions. Do not recite this history unless asked.`,
      ...(runs.length ? [`Work currently running in this thread: ${runs.length} run(s).`] : []),
      "", "Recent turns:", ...turns,
      ...(voice.length ? ["", "Recent voice-only exchanges (not yet in the thread):", ...voice] : []),
      ...(ledger.length ? ["", "Tasks recently delegated from this voice session and what came back — use ONLY to resolve 他/那边/那个. These outcomes are snapshots and may be stale: for any progress question (到哪了/合了吗/部署了吗) delegate instead of answering from this list:", ...ledger] : []),
    ].join("\n");
    let text = build(recent);
    while (estTokens(text) > SEED_MAX_TOKENS && recent.length > 2) { recent.shift(); text = build(recent); } // oldest dropped first (same policy as the API)
    this.info = { session_id: this.sessionId, authed: !!this.auth, thread_messages: turns.length, snapshot_turns: recent.length, snapshot_chars: text.length, snapshot_tokens_est: estTokens(text) };
    return text;
  }

  // ② Delegate into the thread. Hands over voice-only turns first (until R2), then streams progress + reply.
  async *handle(text, { signal }) {
    const pending = this._log().filter((e) => !e.delegated);
    const voiceCtx = pending.length ? `[Voice-only exchanges since the last delegation, for context]\n${pending.map((e) => `${e.role === "user" ? "User" : "Live"}: ${e.text}`).join("\n")}\n\n` : "";
    pending.forEach((e) => { e.delegated = true; }); saveVoiceLog();
    const isChannel = this.threadId === String(process.env.LIVE_THREAD_ID || "");
    const ledgerLines = this._ledgerLines();
    // Context (ledger + voice-only tail) rides in system_prompt, NOT the user message: the thread view stays
    // clean ("[Voice] …" only) and the platform prefix before it remains cache-stable.
    const ctx = [
      ...(ledgerLines.length ? [`[Tasks delegated earlier in this voice session — outcomes are snapshots at the time shown and may be stale; for any progress question re-read the source instead of repeating these]\n${ledgerLines.join("\n")}`] : []),
      ...(voiceCtx ? [voiceCtx.trim()] : []),
    ];
    const message = `[Voice] ${text}`;
    const system_prompt = [isChannel ? LIVE_DISPATCH_PROMPT : LIVE_TURN_PROMPT, ...ctx].join("\n\n");
    syncRemoteMessage("2004", this.threadId, "user", message);
    let reply = "", toolsUsed = 0, spokenEarly = false;
    for await (const ev of runtime.chat({ message, thread_id: this.threadId, system_prompt }, signal, this.auth)) {
      if (ev.type === "text_delta") {
        reply += ev.data?.text || "";
        // Speak the [spoken] head as soon as it closes — the rest of the reply is still streaming.
        if (!spokenEarly) { const m = reply.match(/^\s*\[spoken\]([\s\S]*?)\[\/spoken\]/i); if (m && m[1].trim()) { spokenEarly = true; yield { kind: "say", text: m[1].trim(), early: true }; } }
      }
      else if (ev.data?.run_id) this.runId = ev.data.run_id;
      // Milestones only. Token-level reasoning deltas made Live "narrate" every 1.5 s during silence.
      else if (ev.type === "tool_start" && ++toolsUsed <= 3) yield { kind: "think", text: `Progress: using ${ev.data?.tool_name || "a tool"}. Still working — no need to say anything.` };
    }
    reply = reply.trim();
    if (spokenEarly) {
      const rest = reply.replace(/^\s*\[spoken\][\s\S]*?\[\/spoken\]/i, "").trim();
      if (rest) yield { kind: "detail", text: rest };
    } else {
      // Empty stream = the thread was mid-run and the runtime merged this message into it (verified); answer lands in the thread.
      yield { kind: "say", text: reply || "Starchild was busy with another task in this thread, so your message was merged into it — the answer will appear in the conversation shortly." };
    }
    if (reply) { syncRemoteMessage("2004", this.threadId, "assistant", reply); this._ledger(text, reply); }
    yield { kind: "done" };
  }

  // ③ Write-back of turns Live handled itself. Buffered until the runtime offers append-message (R2).
  _ledger(task, reply) {
    loadLedger().then((all) => {
      const a = all[this.sessionId] || [];
      a.push({ task: String(task).slice(0, 160), outcome: String(reply).replace(/\s+/g, " ").slice(0, 200), t: Date.now() });
      if (a.length > LEDGER_MAX) a.splice(0, a.length - LEDGER_MAX);
      all[this.sessionId] = a; this._ledgerCache = a; return saveLedger(all);
    }).catch(() => {});
  }
  _ledgerLines() {
    const a = this._ledgerCache || [];
    const hk = (t) => new Date(t).toLocaleTimeString("en-GB", { timeZone: "Asia/Hong_Kong", hour: "2-digit", minute: "2-digit" });
    return a.map((e) => { const age = Math.round((Date.now() - e.t) / 60000); const tag = age > 30 ? " [STALE — re-check before relying on it]" : ""; return `- [${hk(e.t)} HKT, ${age} min ago${tag}] asked: ${e.task} → ${e.outcome}`; });
  }
  async onUserTurn(text) { this._push("user", text); }
  async onLiveTurn(text) { this._push("live", text); }
  _push(role, text) {
    const a = this._log(); a.push({ role, text: String(text).slice(0, 1000), t: Date.now(), delegated: false }); if (a.length > 60) a.splice(0, a.length - 60); saveVoiceLog();
    syncRemoteMessage("2004", this.threadId, role === "user" ? "user" : "assistant", role === "user" ? `[Voice] ${text}` : `[Live] ${text}`);
  }

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
