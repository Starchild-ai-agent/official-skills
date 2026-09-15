// The three GPT-Live return channels, wrapped so bindings never touch the wire format.
// Slicing (≤500 tokens ≈ 1500 chars), throttling and merging of null-id thinking live here.
// ≤500 tokens per append: CJK ≈ 1 token/char, Latin ≈ 4 chars/token. Slice on an estimate, not raw chars.
const MAX_TOKENS = 480;
const MAX_CHARS = 1500; // fallback for pure Latin text
export const estTokens = (t) => { const s = String(t); const cjk = (s.match(/[\u3000-\u9fff\uf900-\ufaff]/g) || []).length; return cjk + Math.ceil((s.length - cjk) / 3.5); };
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
  // Only the first ≤500-token slice is spoken; anything longer becomes silent context — a long
  // report should never be read aloud in full (the user can read it in the thread).
  say(content, delegationId = null) {
    const text = String(content ?? "").trim(); if (!text) return;
    const [head, ...rest] = chunk(text, MAX_CHARS);
    this._emit("session.commentary.append", head, delegationId);
    if (rest.length) this._emit("session.thinking.append", `Rest of the reply (already written in the thread, do not read aloud): ${rest.join(" ")}`, delegationId);
  }

  // Official spoken/unspoken split: a reply that begins with a spoken marker speaks only that part.
  // Marker forms: "[spoken] … [/spoken] rest", or first paragraph prefixed with 🔊.
  sayMarked(content, delegationId = null) {
    const text = String(content ?? "").trim(); if (!text) return;
    let m = text.match(/^\[spoken\]([\s\S]*?)\[\/spoken\]([\s\S]*)$/i);
    if (!m) m = text.match(/^🔊\s*([^\n]+)\n*([\s\S]*)$/);
    if (!m) return this.say(text, delegationId);
    const spoken = m[1].trim(), rest = m[2].trim();
    if (spoken) this._emit("session.commentary.append", chunk(spoken, MAX_CHARS)[0], delegationId);
    if (rest) this._emit("session.thinking.append", `Details of the reply (in the thread, not to be read aloud): ${rest}`, delegationId);
  }

  // Behaviour change for the rest of the session (e.g. interruption receipt).
  instruct(content) { this._emit("session.instructions.append", content, null); }
}

function chunk(text, n) {
  if (estTokens(text) <= MAX_TOKENS && text.length <= n) return [text];
  n = Math.min(n, Math.max(200, Math.floor(text.length * MAX_TOKENS / Math.max(1, estTokens(text)))));
  const out = []; let rest = text;
  while (rest.length > n) {
    let cut = rest.lastIndexOf("\n", n); if (cut < n * 0.5) cut = rest.lastIndexOf("。", n); if (cut < n * 0.5) cut = rest.lastIndexOf(". ", n); if (cut < n * 0.5) cut = n;
    out.push(rest.slice(0, cut).trim()); rest = rest.slice(cut).trim();
  }
  if (rest) out.push(rest);
  return out;
}
