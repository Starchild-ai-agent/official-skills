# API Use Behavior

How to drive the `mcp__browser__*` tools well: snapshot before acting, trust
authoritative signals, and never retry blindly.

## Snapshot before every interaction

- Call `page_snapshot` before any click or input, always. It is cheap, and the
  `ref` you hold may already be stale — refs from a previous snapshot are
  invalidated as soon as the page navigates or re-renders its interactive DOM.
- After `element_click` or `element_input`, take a fresh `page_snapshot` (or a
  targeted `wait_for`) to verify the effect before deciding the next step.
  "I clicked it" is not knowledge; the post-action snapshot is.
- `page_snapshot` returns `bodyText` (first ~3000 chars) and `elements[]`. Use
  `bodyText` to understand page state and `elements[]` to find the `ref` you
  need. Search elements by `text` or `ariaLabel` first; tag + text is usually
  enough to disambiguate.
- If two elements look identical in the snapshot, do not guess. Use position
  in the list, surrounding `bodyText` context, or ask the user. Clicking the
  wrong "Delete" button costs more than one extra check.
- **Container vs inner control.** Interactive surfaces are often plain `div`
  containers (list rows, cards) with small buttons nested inside (a row's ⋮
  menu, a card's action icon). Both appear in `elements[]` as separate refs.
  When the intent is to open/select/activate the item itself, pick the ref
  whose `text` is the item's title — not a tiny button with little or no
  text. Mismatching these is the classic way to open a context menu instead
  of the item.

## Verify with authoritative signals

- When the page exposes one authoritative signal for the fact you need — a
  success toast, a confirmation modal, a URL change after submit, a cart line
  item, a "saved" badge — treat that as the answer. Do not re-verify the same
  fact with repeated full snapshots or screenshots.
- Conversely, absence of the expected signal is a real result. If you clicked
  "Submit" and the snapshot still shows the form, the click did not take
  effect; investigate instead of clicking again.

## Multi-step heterogeneous flows

When a task is a sequence of DIFFERENT actions (fill this, click that,
verify the result), you can either drive step-by-step (snapshot →
element_click/element_input → verify) or compress it into one `page_flow`
call. Prefer `page_flow` when the step sequence is known and deterministic:

```json
[
  {"type":  {"selector": "#email", "value": "user@example.com"}},
  {"type":  {"selector": "#password", "value": "..."}},
  {"click": {"text": "Sign in"}},
  {"wait":  {"text": "Welcome"}},
  {"expect": {"selector": ".inbox"}}
]
```

- Targets are selector-or-text (refs would go stale mid-flow). Each click
  passes the sensitive gate — a submit step returns NEEDS_CONFIRMATION; ask,
  then retry the WHOLE flow with `confirm: true` (earlier steps re-run, so
  only use this when repeats are safe).
- `expect` with `absent: true` asserts disappearance (toasts closing, modals
  dismissed). `wait` before `expect` on animated SPAs.
- On failure the result names the failing step and the completed prefix —
  snapshot once to diagnose, fix the step list, re-run.
- Branching ("if login wall, do X") does NOT belong in a flow: that is your
  reasoning between calls. Flows are for straight-line sequences.

## Repetitive homogeneous actions

When 3 or more structurally identical elements must be acted on (click every
row of a list, open each tab, check each card), do NOT loop
snapshot → click → snapshot. That loop dies on this workload: each click
re-renders an SPA, refs go stale, and you spend a snapshot per item.

- Take **one** snapshot to locate the pattern and derive a CSS selector for
  the targets (e.g. the clickable row container, not the items' inner
  buttons). Derive the selector from **one row's own classes** — a selector
  matching a shared ancestor (the whole sidebar, the whole list wrapper)
  produces giant wrong targets. Sanity-check before running: the expected
  match count ≈ number of items, and each match's text is a single item's
  title. The tool auto-drops containers with text > 200 chars and
  non-innermost nested matches, but a wrong selector can still miss entirely.
- Call `elements_click_many {selector}` once. It runs inside the page,
  re-querying the selector before each click, so re-renders and route
  changes between clicks do not invalidate anything. It is also
  **reorder-safe**: targets are addressed by text quota, so lists that move
  clicked items to the top (recency-sorted history) are clicked completely —
  never fall back to per-item snapshot loops for reorderable lists. It
  auto-drops wrong targets (huge containers, non-innermost nested matches).
  The virtual cursor moves and clicks through each item visually.
- Verify once at the end (snapshot or the tool's own clicked-count report).
- If clicking an item *removes* it from the list (delete/dismiss flows), use
  `mode: "first"` — it always clicks the first remaining match and stops on
  no-progress.
- Sensitive gate still applies: if any matched element's text looks like
  submit/send/purchase/delete, the tool returns NEEDS_CONFIRMATION — ask,
  then retry with `confirm: true`.
- Same principle for future batch primitives: one locate, one batch action,
  one verify. Bulk work never justifies per-item verification loops.

## Do not blindly retry

- If an interaction has no visible effect, do not repeat it mechanically or
  escalate to hammering the same element. Take a `page_snapshot` and look for
  a blocker: a disabled state, a validation error, an overlay, a login wall,
  a CAPTCHA. Resolve the blocker or report it; only then retry.
- Distinguish retryable from non-retryable failures:
  - Stale `ref` → fresh `page_snapshot`, use the new `ref`.
  - Navigation happened mid-flow → re-snapshot, resume from visible state.
  - `evaluate`-style timeout (hard 15 s limit) → the page is busy or the
    script blocked; do not immediately rerun the same thing, see
    `browser-troubleshooting.md`.
  - All browser tools vanished → bridge disconnected; that is a setup problem,
    not a retry problem. See `chrome-troubleshooting.md`.
- Never loop a failing call more than twice without changing something
  (target, wait, or approach) or asking the user.

## Lookup and navigation economy

- For read-only lookups, one focused `tab_open`/`tab_navigate` to an obvious
  or parameterized URL (e.g. a search URL built from the user's filters)
  followed by verification in the snapshot is better than a long chain of
  UI interactions.
- Do not iterate through guessed URL variants or candidate URL arrays. If the
  one focused attempt fails, fall back to the site's own search UI or report
  the best answer with uncertainty.
- If a tab is already on the target URL, do not navigate to the same URL
  again — you may destroy in-progress user state (typed text, scroll
  position, open menus). Navigate only when you actually intend to change
  the page.
- Prefer `wait_for` over sleep-and-snapshot polling when you know what you
  are waiting for (a selector or text appearing).

## Minimize interruptions

- Only ask the user when you genuinely cannot proceed: ambiguous targets,
  required confirmations, credentials, or CAPTCHAs. Try to fulfill an
  under-specified request first, then ask about what remains.
- Omitting `tabId` targets the user's active tab — convenient, but remember
  you are then reading and acting on whatever the user is looking at right
  now. Double-check the snapshot's `title`/`url` match your assumption before
  acting on an unqualified snapshot.
