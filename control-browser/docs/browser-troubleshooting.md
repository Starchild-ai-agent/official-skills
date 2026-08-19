# Browser Interaction Troubleshooting

Diagnose failures at the page level: evaluate timeouts, stale refs, and pages
that hang. For extension/bridge-level problems (all tools gone), see
`chrome-troubleshooting.md` and `bootstrap-troubleshooting.md` instead.

## Evaluate timeouts (15 s hard limit)

- Page evaluation has a **hard 15-second timeout**. If a call times out, the
  page was too busy, the script blocked, or the main thread was jammed — it is
  not evidence that the page is broken.
- Do not immediately rerun the same call. First try a cheaper probe:
  `page_snapshot` or `wait_for {text: ..., timeoutMs: 5000}` to see whether
  the page responds at all.
- If cheap probes also stall, the page (or tab) is hung. Options in order:
  1. `wait_for` with a modest `timeoutMs` to ride out a busy period (SPA
     hydration, heavy redirect chain, long job).
  2. `tab_navigate` to reload the target URL and start fresh — but only if
     you will not destroy user state (typed input, in-progress forms).
  3. Report to the user that the page is not responding and ask whether to
     reload or abandon the tab.
- A page that times out repeatedly is a finding, not an obstacle: tell the
  user "this page seems stuck" rather than looping retries.

## Stale or invalid refs

Symptom: `element_click` / `element_input` errors that the element or ref is
unknown or no longer present.

- Refs come from a specific snapshot and are invalidated by navigation,
  reloads, and significant DOM replacement (SPAs re-rendering routes count).
- Fix: `page_snapshot` again, locate the element in the fresh `elements[]`,
  use the new ref. Do not retry the old ref, and do not guess ref values.
- If the element genuinely disappeared (dialog closed, list re-rendered,
  flow moved on), read the new snapshot state and continue from there —
  the step may already be done.
- If two snapshots disagree wildly, the page navigated without you noticing;
  check `title`/`url` in the snapshot before doing anything else.

## Page or flow hangs

- `wait_for` accepts `timeoutMs`; use short, explicit budgets (5–10 s) for
  interaction steps rather than relying on defaults when you expect a fast
  page.
- Infinite spinners / skeleton loaders: verify with `wait_for {text}` on the
  content you expect. If it never lands, snapshot once, then decide — many
  SPAs render content into `bodyText` long after the spinner clears, or vice
  versa.
- Login walls mid-flow: do not attempt to enter credentials yourself. Ask the
  user to sign in, then re-snapshot.
- CAPTCHA: stop and ask the user whether they want you to solve it (see
  `browser-safety.md`).

## page_snapshot consistently fails

Every interaction depends on refs from a snapshot. If `page_snapshot` fails
repeatedly (across different tabs and pages, not just one hung page), the
interaction loop is broken — do not keep retrying clicks, waits, or
screenshots on the assumption the page is at fault.

- Distinguish the layer first: if other browser tools (`tabs_list`,
  `web_status`) also fail or are absent, this is a bridge/extension problem —
  go to `chrome-troubleshooting.md` / `bootstrap-troubleshooting.md`, and do
  not retry here.
- If only snapshot-like calls fail while tab tools work, that points to the
  page-data channel itself (content script injection or the DOM collection
  path). Try one other tab: same failure across tabs confirms it is not the
  page.
- Stop after two consecutive snapshot failures on the same tab. Report to
  the user in plain language ("I can't read the page right now") rather than
  looping. Fallbacks: `wait_for {text}` can still confirm a page reached a
  state, and `page_screenshot` can still show it — but neither yields refs,
  so element interaction is unavailable until snapshots recover.
- Never fabricate element state from a screenshot or stale snapshot to keep
  a flow moving. If refs are unavailable, the interaction stops.

## Tab-level problems

- Wrong tab? Check `tabs_list`; every `page_snapshot` result carries its
  `tabId` — confirm it is the tab you think you are driving.
- Omitting `tabId` targets the user's *active* tab, which can change between
  your calls if the user switches tabs. If your mental model of "the page"
  suddenly does not match the snapshot, pass an explicit `tabId`.
- Tab closed underneath you (by the user or a script): the tab is gone.
  Reopen with `tab_open` if the task still needs it; do not treat this as a
  bridge failure.

## Principles

- One retry after a state change (fresh snapshot, new ref, longer wait) is
  reasonable. Two identical failures in a row mean stop, report, ask.
- Never switch to an unrelated control mechanism (curl, guessing URLs,
  external browser automation) because a tool call failed — diagnose within
  the documented tools.
- Report failures to the user in plain language: "the page stopped
  responding", "that button disappeared" — no internal error strings, ref
  IDs, or timeout internals unless asked.
