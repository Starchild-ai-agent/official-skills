// The three GPT-Live return channels, wrapped so bindings never touch the wire format.
// Slicing (≤500 tokens ≈ 1500 chars), throttling and merging of null-id thinking live here.
const MAX_CHARS = 1500;
const NULL_THINK_INTERVAL_MS = 1500;

export class LiveSession {
  constructor(send, log = () => {}) { this.send = send; this.log = log; this._nullQueue = []; this._nullTimer = null; this._lastNull = 0; }

  _emit(type, content, delegationId) {
    const text = String(content ?? "").trim(); if (!text) return;
    for (const slice of chunk(text, MAX_CHARS)) {
      this.send({ type, event_id: `${type.split(".")[1]}_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`, delegation_id: delegationId ?? null, content: slice });
    }
    this.log(type, delegationId, text.slice(0, 120));
  }

  // Silent context. With an id: progress of that delegation (sent immediately).
  // With null: general context — merged and rate-limited so rapid events don't flood the model.
  think(content, delegationId = null) {
    if (delegationId) return this._emit("session.thinking.append", content, delegationId);
    this._nullQueue.push(String(content));
    if (this._nullTimer) return;
    const wait = Math.max(0, NULL_THINK_INTERVAL_MS - (Date.now() - this._lastNull));
    this._nullTimer = setTimeout(() => {
      this._nullTimer = null; this._lastNull = Date.now();
      const merged = this._nullQueue.join("\n"); this._nullQueue = [];
      this._emit("session.thinking.append", merged, null);
    }, wait);
  }

  // Say this now, in your own words.
  say(content, delegationId = null) { this._emit("session.commentary.append", content, delegationId); }

  // Behaviour change for the rest of the session (e.g. interruption receipt).
  instruct(content) { this._emit("session.instructions.append", content, null); }
}

function chunk(text, n) {
  if (text.length <= n) return [text];
  const out = []; let rest = text;
  while (rest.length > n) {
    let cut = rest.lastIndexOf("\n", n); if (cut < n * 0.5) cut = rest.lastIndexOf("。", n); if (cut < n * 0.5) cut = rest.lastIndexOf(". ", n); if (cut < n * 0.5) cut = n;
    out.push(rest.slice(0, cut).trim()); rest = rest.slice(cut).trim();
  }
  if (rest) out.push(rest);
  return out;
}
