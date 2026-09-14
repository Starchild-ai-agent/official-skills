// Turn raw DataChannel events into completed user / live turns.
// Event type names are matched loosely (input.*transcript*, output.*transcript*, *completed|done|final*)
// because the exact names are not pinned in the docs.
export class Transcripts {
  constructor() { this.userBuf = ""; this.liveBuf = ""; this.userFinal = ""; }

  // Returns {kind:'user'|'live', text} on a completed turn, {kind:'user_delta'|'live_delta', text} on deltas, else null.
  feed(ev) {
    const t = ev.type || "";
    const full = typeof (ev.transcript ?? ev.text) === "string" ? (ev.transcript ?? ev.text).trim() : "";
    const done = /completed|done|final/.test(t);
    if (/input.*(transcript|transcription)/.test(t)) {
      if (ev.delta) { this.userBuf += ev.delta; if (!done) return { kind: "user_delta", text: ev.delta }; }
      if (done) { const text = full || this.userBuf.trim(); this.userBuf = ""; if (text) { this.userFinal = text; return { kind: "user", text }; } }
      return null;
    }
    if (/output.*(transcript|transcription)/.test(t)) {
      if (ev.delta) { this.liveBuf += ev.delta; if (!done) return { kind: "live_delta", text: ev.delta }; }
      if (done) { const text = full || this.liveBuf.trim(); this.liveBuf = ""; if (text) return { kind: "live", text }; }
      return null;
    }
    return null;
  }

  // The most recent completed user utterance — what a delegation refers to. Consumed once.
  takeUser() { const t = this.userFinal || this.userBuf.trim(); this.userFinal = ""; this.userBuf = ""; return t; }
}
