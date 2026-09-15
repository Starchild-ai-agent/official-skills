// delegation.created → binding.handle(text) → think/say(id). Owns the "did Live answer this itself?"
// decision (user turn with no delegation within VOICE_ONLY_MS → binding.onUserTurn) and barge-in.
const VOICE_ONLY_MS = 1500;
const isNoise = (t) => { const s = String(t || "").replace(/[\s\p{P}\p{S}]/gu, ""); return s.length <= 1 || /^(嗯+|啊+|呃+|哦+|uh+|um+|hmm+|ok)$/i.test(s); };

export class Delegator {
  constructor({ live, transcripts, binding, log = () => {} }) {
    Object.assign(this, { live, transcripts, binding, log });
    this.active = new Map(); // delegation_id -> { controller }
    this._pendingUser = null;
    // Gap-closed turns (GPT-Live has no turn-completed event) arrive through this callback.
    this.transcripts.onTurn = (turn) => this._onTurn(turn);
  }

  // Feed every DataChannel event here.
  async onEvent(ev) {
    const t = ev.type || "";
    if (t === "session.delegation.created") return this._delegate(ev.delegation?.id || ev.delegation_id || `d${Date.now()}`);
    if (/input_audio_buffer\.speech_started|input.*speech_started/.test(t)) { this.transcripts.userSpeechStarted(); return this._bargeIn(); }
    const turn = this.transcripts.feed(ev);
    if (turn) return this._onTurn(turn);
  }

  _onTurn(turn) {
    if (turn.kind !== "user" && turn.kind !== "live") return;
    // ASR noise / mis-taps ("x", "嗯", ".") are not turns.
    if (isNoise(turn.text)) { this.log("noise-dropped", turn.kind, turn.text); if (turn.kind === "user") this.transcripts.userFinal = ""; return; }
    if (turn.kind === "user") { this._lastUserText = turn.text; 
      if (this.active.size && /^(stop|cancel|never ?mind|forget it|别查了|不用查了|不用了|取消|算了|停)/i.test(turn.text.trim())) { this.cancelAll().catch((e) => this.log("cancel-failed", e.message)); }
      // If no delegation follows shortly, Live handled this turn itself → write it back.
      clearTimeout(this._pendingUser?.timer);
      const text = turn.text;
      this._pendingUser = { text, timer: setTimeout(() => { this._pendingUser = null; this.transcripts.takeUser(); this.binding.onUserTurn?.(text).catch?.(() => {}); this.log("voice-only", "user", text.slice(0, 80)); }, VOICE_ONLY_MS) };
    } else if (turn.kind === "live") {
      this.binding.onLiveTurn?.(turn.text).catch?.(() => {});
      this.log("voice-only", "live", turn.text.slice(0, 80));
    }
  }

  async _delegate(id) {
    clearTimeout(this._pendingUser?.timer); this._pendingUser = null;
    const text = this.transcripts.takeUser();
    if (!text) { this.log("delegation", id, "no user text captured — skipped"); return; }
    this.log("delegation", id, text.slice(0, 120));
    const controller = new AbortController();
    this.active.set(id, { controller, text });
    try {
      for await (const chunk of this.binding.handle(text, { delegationId: id, signal: controller.signal })) {
        if (controller.signal.aborted) break;
        const a = this.active.get(id);
        if (chunk.kind === "think") this.live.think(chunk.text, id);
        else if (chunk.kind === "say") {
          if (a && !this._stillRelevant(a)) { this.live.think(`Result of the earlier task "${a.text.slice(0, 60)}" (the user has since moved on — mention it only if asked or clearly useful): ${chunk.text}`, id); this.log("result-demoted", id); }
          else if (chunk.early) { this.live.say(chunk.text, id); this.log("spoken-early", id); }
          else this.live.sayMarked(chunk.text, id);
        }
        else if (chunk.kind === "detail") this.live.think(`Details of the reply (in the thread, not to be read aloud): ${chunk.text}`, id);
      }
    } catch (e) {
      if (!controller.signal.aborted) this.live.say(`I couldn't finish that: ${e.message}`, id);
    } finally { this.active.delete(id); }
  }

  // User started speaking while a delegation runs. Official GPT-Live semantics: an interruption does NOT
  // cancel backend work — the model just stops talking. We keep the task running, mark it "interrupted",
  // and when it finishes decide how to surface it: still relevant → spoken (commentary); user has moved on
  // → silent context (thinking) so Live can bring it up only if asked.
  async _bargeIn() {
    if (!this.active.size) return;
    for (const [id, a] of this.active) {
      if (a.interrupted) continue;
      a.interrupted = true; a.interruptedAt = Date.now();
      this.live.think(`The user started speaking while the task "${a.text.slice(0, 60)}" is still running in the thread. Stop talking and listen; the task continues and its result will arrive later. Do not repeat anything you already said.`, null);
      this.log("barge-in", id, "task kept running");
    }
  }

  // Explicit cancel only (user says "stop / 别查了 / 取消") — never triggered by barge-in.
  async cancelAll(reason = "user asked to stop") {
    for (const [id, a] of this.active) {
      const stopped = await this.binding.interrupt?.(id, a).catch(() => false);
      a.controller.abort(); this.active.delete(id);
      this.live.think(`The task "${a.text.slice(0, 60)}" was cancelled (${reason}${stopped ? "" : "; the thread may still finish it"}). Do not report its result.`, null);
    }
  }

  // After an interruption: did the user change the subject? Compare the latest user turn to the delegated one.
  _stillRelevant(a) {
    if (!a.interrupted) return true;
    const later = this._lastUserText || "";
    if (!later) return true;
    const toks = (t) => new Set(String(t).toLowerCase().replace(/[\s\p{P}]/gu, "").match(/[\u4e00-\u9fff]|[a-z0-9]+/g) || []);
    const A = toks(a.text), B = toks(later); let hit = 0; for (const x of B) if (A.has(x)) hit++;
    return hit / Math.max(1, Math.min(A.size, B.size)) >= 0.25;
  }

  close() { for (const a of this.active.values()) a.controller.abort(); this.active.clear(); clearTimeout(this._pendingUser?.timer); this.transcripts.close?.(); }
}
