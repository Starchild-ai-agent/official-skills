# Chrome Extension Troubleshooting

The `mcp__browser__*` tools exist only while the user's Chrome extension is
installed, enabled, and connected. When that link breaks, **the entire browser
toolset disappears** — this is the key diagnostic signature.

## Symptom: browser tools are gone entirely

If `mcp__browser__*` tools are not present in the session at all:

- The extension is not installed, not enabled, or its bridge to clawd is
  down. This is a setup fact, not a transient error.
- **Do not retry** tool calls hoping they reappear, and do not try to work
  around it with unrelated mechanisms. Ask the user to open (or reinstall /
  re-enable) the StarChild Chrome extension and confirm the connection is
  green.
- Suggested wording: "I can't reach your browser right now — could you open
  the StarChild Chrome extension and check that it shows connected? Then I'll
  retry."
- Once the user confirms, the tools should re-register on the next session /
  reconnect; retry the operation then.

## Symptom: tools exist but calls fail with connection errors

- Run `web_status` (if available) to check bridge health.
- If it reports disconnected or calls consistently fail with connection
  errors: same story — the extension dropped the bridge. Tell the user
  plainly ("the browser connection dropped — please reopen the extension"),
  wait for their confirmation, then retry once.
- One retry after the user says the extension is reconnected. If it still
  fails, report and stop; do not enter a retry loop.

## Symptom: user has no extension installed

- If the user asks for browser work and has never installed the extension,
  explain what is needed: install the StarChild Chrome extension in Chrome,
  open it, and connect. Offer to continue with `web_fetch` / `web_search` for
  the reading-only parts of the task in the meantime.
- Do not pretend to control a browser you cannot reach, and do not silently
  substitute anonymous fetching for actions that need the user's logged-in
  browser.

## What NOT to conclude from these failures

- Missing browser tools do not mean Chrome is broken, the machine is broken,
  or clawd is broken. The failure is localized to the extension ↔ clawd link.
- A single failed call during an otherwise healthy session is usually a
  page-level problem (see `browser-troubleshooting.md`) — check whether other
  browser tools still respond before assuming a bridge failure.
- Never mention WebSocket endpoints, bridge internals, or tool IDs to the
  user. "The browser connection dropped" is the correct register.

## Quick triage order

1. Are `mcp__browser__*` tools present at all? → No: extension/bridge is
   down; ask the user to open the extension. (See also
   `bootstrap-troubleshooting.md` for first-connect failures.)
2. Tools present but one call failed → retry the *call* once after a fresh
   `page_snapshot`; if the tool itself errors as unreachable, go to step 1.
3. Only `web_status` usable → run it, report the result to the user in plain
   language, wait for the fix.
