# Bootstrap Troubleshooting

First-connection diagnostics for the browser bridge — when clawd should have
browser tools and does not, or the extension reports it cannot reach clawd.
For mid-session drops, see `chrome-troubleshooting.md`; for page-level
failures, see `browser-troubleshooting.md`.

## The red dot: extension shows disconnected

The StarChild Chrome extension shows its connection state directly. A **red
dot / disconnected indicator** means the extension cannot reach clawd over
its bridge. The browser tools will be absent or dead.

Work the checklist with the user, in this order:

1. **Is clawd running?** The bridge originates from clawd's side. If the
   session hosting the browser server is down or restarting, the extension
   has nothing to connect to. Ask the user to confirm clawd is up.
2. **Is the extension pointed at the right place?** The extension connects to
   clawd's `/ws/web-mcp` endpoint. A stale configuration (wrong host/port,
   old deployment URL) produces a permanent red dot. Ask the user to check
   the extension's settings against the clawd instance you are running in.
3. **Did the extension reload?** Chrome suspending the extension, a browser
   restart, or an extension update can drop the bridge without an obvious
   event. Have the user click the extension icon / toggle it once to force a
   reconnect attempt.
4. **Network / VPN / proxy**: if clawd is remote (e.g. behind Fly or a
   tunnel), transient network problems can sever the WebSocket. Retry after
   the network settles.
5. **Auth**: if the extension requires an identity/token and it expired or
   was revoked, the connect will fail even with everything else healthy.
   Have the user re-authenticate in the extension.

## What you (the agent) can do

- Very little, by design: the bridge is user-side. You cannot restart the
   user's extension from here. Your job is to diagnose, instruct, and retry
   once after the user says it is green.
- If `web_status` is somehow available, run it once and use its result to
   tell the user which side looks unhealthy. Do not poll it in a loop.
- After the user reconnects, retry the original browser operation once. If
   the tools are still absent, report the persistent failure and suggest
   restarting both clawd's browser server session and the extension, in that
   order.

## What not to do

- Do not fabricate browser results or fall back to `web_fetch` while
  silently implying the user's browser was used. If the task truly needs the
  user's browser state, wait or hand off.
- Do not mention `/ws/web-mcp`, WebSocket internals, or endpoint URLs unless
  the user is actively debugging the configuration and asks.
- Do not reset or reconfigure clawd yourself on the assumption that clawd is
  at fault; verify with the user first.

## First-time setup failures

If this is the user's very first connection attempt: confirm the extension
version matches what clawd expects, confirm they opened the extension after
installing (Chrome does not auto-open it), and confirm clawd's browser server
was enabled for their session at all. A user who has never enabled browser
control in clawd will simply have no browser tools — that is a configuration
answer, not a bug.
