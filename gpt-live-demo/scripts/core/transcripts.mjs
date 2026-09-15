// Turn raw DataChannel transcript events into user / live turns.
// GPT-Live emits ONLY `session.input_transcript.delta` / `session.output_transcript.delta`
// (fields: delta, start_ms, end_ms). There is NO turn-completed event (docs: "Transcript deltas
// have no item ID or authoritative turn-completed event"), so turns are closed by a silence gap.
// Legacy Realtime `*transcript*.completed|done` events are still honoured when present.
const USER_GAP_MS = 900;   // user pause that closes a user turn (delegation.created also closes it)
const LIVE_GAP_MS = 1200;  // assistant pause that closes a live turn (user speech_started also closes it)

export class Transcripts {
  constructor({ onTurn = () => {} } = {}) {
    this.onTurn = onTurn;
    this.userBuf = ""; this.liveBuf = ""; this.userFinal = "";
    this._userTimer = null; this._liveTimer = null;
  }

  // Returns {kind:'user_delta'|'live_delta', text} on deltas, {kind:'user'|'live', text} on explicit completions.
  feed(ev) {
    const t = ev.type || "";
    const full = typeof (ev.transcript ?? ev.text) === "string" ? (ev.transcript ?? ev.text).trim() : "";
    const done = /completed|done|final/.test(t);
    if (/input.*(transcript|transcription)/.test(t)) {
      if (ev.delta) { this.userBuf += ev.delta; this._arm("user"); if (!done) return { kind: "user_delta", text: ev.delta }; }
      if (done) return this._closeUser(full);
      return null;
    }
    if (/output.*(transcript|transcription)/.test(t)) {
      if (ev.delta) { this.liveBuf += ev.delta; this._arm("live"); if (!done) return { kind: "live_delta", text: ev.delta }; }
      if (done) return this._closeLive(full);
      return null;
    }
    return null;
  }

  _arm(kind) {
    if (kind === "user") { clearTimeout(this._userTimer); this._userTimer = setTimeout(() => { const t = this._closeUser(); if (t) this.onTurn(t); }, USER_GAP_MS); }
    else { clearTimeout(this._liveTimer); this._liveTimer = setTimeout(() => { const t = this._closeLive(); if (t) this.onTurn(t); }, LIVE_GAP_MS); }
  }
  _closeUser(full = "") { clearTimeout(this._userTimer); const text = (full || this.userBuf).trim(); this.userBuf = ""; if (!text) return null; this.userFinal = text; return { kind: "user", text }; }
  _closeLive(full = "") { clearTimeout(this._liveTimer); const text = (full || this.liveBuf).trim(); this.liveBuf = ""; return text ? { kind: "live", text } : null; }

  // The user started speaking → whatever Live was saying is a finished (possibly interrupted) live turn.
  userSpeechStarted() { const t = this._closeLive(); if (t) this.onTurn(t); }

  // The most recent completed user utterance — what a delegation refers to. Consumed once.
  takeUser() { clearTimeout(this._userTimer); const t = (this.userFinal || this.userBuf).trim(); this.userFinal = ""; this.userBuf = ""; return t; }

  close() { clearTimeout(this._userTimer); clearTimeout(this._liveTimer); }
}
