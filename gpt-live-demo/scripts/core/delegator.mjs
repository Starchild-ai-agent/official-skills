// delegation.created → binding.handle(text) → think/say(id). Owns the "did Live answer this itself?"
// decision (user turn with no delegation within VOICE_ONLY_MS → binding.onUserTurn) and barge-in.
const VOICE_ONLY_MS = 1500;

export class Delegator {
  constructor({ live, transcripts, binding, log = () => {} }) {
    Object.assign(this, { live, transcripts, binding, log });
    this.active = new Map(); // delegation_id -> { controller }
    this._pendingUser = null;
  }

  // Feed every DataChannel event here.
  async onEvent(ev) {
    const t = ev.type || "";
    if (t === "session.delegation.created") return this._delegate(ev.delegation?.id || ev.delegation_id || `d${Date.now()}`);
    if (/input_audio_buffer\.speech_started|input.*speech_started/.test(t)) return this._bargeIn();
    const turn = this.transcripts.feed(ev);
    if (!turn) return;
    if (turn.kind === "user") {
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
        if (chunk.kind === "think") this.live.think(chunk.text, id);
        else if (chunk.kind === "say") this.live.say(chunk.text, id);
      }
    } catch (e) {
      if (!controller.signal.aborted) this.live.say(`I couldn't finish that: ${e.message}`, id);
    } finally { this.active.delete(id); }
  }

  // User started speaking while a delegation runs. Do NOT claim "stopped" unless it really stopped.
  async _bargeIn() {
    if (!this.active.size) return;
    for (const [id, a] of this.active) {
      const stopped = await this.binding.interrupt?.(id, a).catch(() => false);
      if (stopped) { a.controller.abort(); this.active.delete(id); this.live.think(`The task "${a.text.slice(0, 60)}" was cancelled because the user interrupted. Do not repeat its result.`, null); }
      else this.live.think(`The user interrupted; the task "${a.text.slice(0, 60)}" is still running in the thread. Do not repeat anything you already said.`, null);
    }
  }

  close() { for (const a of this.active.values()) a.controller.abort(); this.active.clear(); clearTimeout(this._pendingUser?.timer); }
}
