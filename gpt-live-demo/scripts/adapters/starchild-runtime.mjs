// The only file that knows the Starchild runtime HTTP surface (:8000).
// Read-mostly: snapshot + events for seeding/inflow, chat for delegation, cancel for interrupts.
const BASE = process.env.STARCHILD_RUNTIME || "http://localhost:8000";

async function getJson(path, { timeout = 8000 } = {}) {
  const r = await fetch(BASE + path, { signal: AbortSignal.timeout(timeout) });
  if (!r.ok) throw new Error(`runtime ${path} HTTP ${r.status}`);
  return r.json();
}

// Parse a `data: {...}` SSE body into JSON events.
async function* sse(response) {
  const reader = response.body.getReader(); const dec = new TextDecoder(); let buf = "";
  for (;;) {
    const { value, done } = await reader.read(); if (done) break;
    buf += dec.decode(value, { stream: true });
    const lines = buf.split("\n"); buf = lines.pop();
    for (const line of lines) {
      if (!line.startsWith("data:")) continue;
      try { yield JSON.parse(line.slice(5).trim()); } catch { /* keepalive / partial */ }
    }
  }
}

export const runtime = {
  base: BASE,

  // thread_id may be a bare thread uuid or a full session id. /sessions is capped and may
  // omit the most active thread, so derive the "agent:main:thread:<N>" prefix and probe.
  async resolveSession(threadId) {
    if (!threadId) return null;
    if (threadId.includes(":")) return threadId;
    const d = await getJson("/sessions");
    const list = (Array.isArray(d) ? d : d.sessions || []).map((s) => String(s.session_id || s));
    const hit = list.find((s) => s.endsWith(":" + threadId));
    if (hit) return hit;
    const prefix = process.env.STARCHILD_THREAD_PREFIX || list.find((s) => s.includes(":thread:"))?.replace(/:[^:]+$/, "");
    if (!prefix) return null;
    const candidate = `${prefix}:${threadId}`;
    try { const s = await getJson(`/session?session_id=${encodeURIComponent(candidate)}`); return s.messages?.length ? candidate : null; }
    catch { return null; }
  },

  async messages(sessionId) {
    const d = await getJson(`/session?session_id=${encodeURIComponent(sessionId)}`);
    return (d.messages || []).map((m) => ({ role: m.role, text: textOf(m) })).filter((m) => m.text.trim());
  },

  async runs(threadId) {
    try { const d = await getJson(`/chat/runs?thread_id=${encodeURIComponent(threadId)}`); return d.runs || d || []; } catch { return []; }
  },

  async scheduledJobs() {
    try { const d = await getJson("/scheduled-jobs"); return d.jobs || d || []; } catch { return []; }
  },

  // Delegation: POST /chat/stream, yields runtime SSE events (text_delta, tool_start, agent_complete, ...).
  // With a user JWT the runtime treats the turn as a real user turn: the thread is registered in
  // the web thread list and messages persist to DB. Without it, internal calls are forced temporary
  // (main.py: auth_type=internal || call_source!=user → is_temporary) and only live in the local session.
  async *chat(body, signal, auth) {
    const headers = { "Content-Type": "application/json", ...(auth ? { Authorization: auth } : {}) };
    const payload = { call_source: auth ? "user" : "internal", channel: process.env.LIVE_CHANNEL || "web", ...body };
    const r = await fetch(`${BASE}/chat/stream`, { method: "POST", headers, body: JSON.stringify(payload), signal });
    if (!r.ok || !r.body) throw new Error(`runtime /chat/stream HTTP ${r.status}`);
    for await (const ev of sse(r)) { yield ev; if (ev.type === "agent_complete") return; }
  },

  async cancelRun(threadId, runId) {
    try {
      const r = await fetch(`${BASE}/chat/runs/cancel`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ thread_id: threadId, run_id: runId }) });
      return r.ok;
    } catch { return false; }
  },

  // Long-lived push stream for one session. Reconnects until signal aborts.
  async *events(sessionId, signal) {
    while (!signal?.aborted) {
      try {
        const r = await fetch(`${BASE}/push/events?session_id=${encodeURIComponent(sessionId)}&listener_source=live-bridge`, { signal });
        if (!r.ok || !r.body) throw new Error("HTTP " + r.status);
        for await (const ev of sse(r)) yield ev;
      } catch (e) { if (e.name === "AbortError") return; }
      await new Promise((r) => setTimeout(r, 3000));
    }
  },
};

function textOf(m) {
  const c = m.content;
  if (typeof c === "string") return c;
  if (Array.isArray(c)) return c.map((p) => (typeof p === "string" ? p : p.text || "")).join(" ");
  return "";
}
