# Tab Ownership

Which tab you operate in matters: the user's tabs are theirs, your tabs are
temporary guests. Choose deliberately — and for multi-step or cross-turn
tasks, make ownership explicit with the claim lifecycle.

## Claim lifecycle (tab_claim / tab_handoff / tab_release)

Claims persist across conversations (they survive browser restarts) and
surface in `tabs_list` as a per-tab `claim: {status, note, claimedAt}` field
plus a top-level `claims` array. This is your task memory for tabs. The tab
strip shows the state visually: orange "★ Starchild" group = claimed,
yellow "⏳ Starchild" group = handoff.

### When to use — scenario playbook

**CLAIM at the start of tab-dependent multi-step work.**
- You open a tab to run a flow that spans many tool calls (fill a checkout,
  complete a multi-page form, work an admin panel) → `tab_claim` it with a
  note stating the goal ("order #1234 checkout, cart ok, at shipping step").
- You take over the USER's tab for extended operations → claim it too, so
  cleanup and continuation are unambiguous.
- Rule of thumb: if losing the tab mid-task would lose task state, claim it.
  A one-shot lookup ("open this page, read it, answer") needs NO claim.

**HANDOFF the moment only the user can proceed.**
- Login wall, payment step, CAPTCHA, 2FA code, review-and-approve screen,
  choosing between options you shouldn't decide.
- `tab_handoff {tabId, note}` where the note is the resume instruction:
  "waiting for 2FA, then click Confirm on the review page".
- ALWAYS pair it with telling the user exactly where to pick up. Then stop —
  do not keep polling the page.

**READ claims when a conversation starts with continuation intent.**
- "继续那个/上次的 tab"、"接着办那件事" → FIRST `tabs_list`, look at the
  `claims` array: a `handoff` record with its note IS the resume point.
  Navigate there and continue. Do not ask the user "which tab?" — that is
  what the notes are for. No claims found → say so plainly and ask.

**RELEASE with the right disposition at task end.**
- Consumed intermediates (search results, source pages, step N-1 of a flow)
  → `tab_release {disposition: "close"}`.
- Deliverables the user must see (created doc, dashboard, submitted form
  confirmation, an open page they asked for) → `tab_release {disposition:
  "keep"}` and tell them it is left open.
- Turn-ending rule: no claimed tab should survive a turn in `claimed`
  status — it is either still actively being worked, handed off, or
  released.

**Do NOT claim** for: read-and-answer lookups, single-page questions, tabs
you open and close within a couple of calls. Claims are task memory, not a
default action — over-claiming pollutes `tabs_list` and the tab strip.

### Semantics recap

- Claims never block anything — any tool can still target any tab. They are
  memory and hygiene, not access control.
- Records auto-clean when the user closes the tab.

## The two kinds of tabs

- **User tabs** — tabs the user opened or is actively using. Found via
  `tabs_list` / the `tabId`-less `page_snapshot`. They may contain the user's
  in-progress work: typed drafts, scrolled position, half-filled forms.
  Treat them as borrowed.
- **Agent tabs** — tabs you opened with `tab_open`. They default to
  **background** (`active: false`) so they do not yank the user's view away.
  You own their lifecycle: open, use, close (see `tab-cleanup-chrome.md`).

## Default: operate in your own background tab

For most tasks, `tab_open {url}` in a background tab is right:
- it does not disturb whatever the user is looking at;
- the orange agent cursor moves there without the user watching (see
  `visibility.md`);
- cleanup is unambiguous — it is yours to close.

## When to use the user's active tab (omit `tabId`)

Target the user's current tab (omit `tabId` in `page_snapshot`, then carry
that returned `tabId` through subsequent calls) only when the task is
inherently about *that* tab:
- the user says "this page", "here", "the tab I have open" while looking at
  it;
- the task depends on state only that tab has — an in-progress form, a
  mid-checkout cart, an SPA session scoped to the tab;
- the user asks you to do something in the tab they are watching (often so
  they can see it happen).

Before acting on an unqualified snapshot, sanity-check `title`/`url` against
what the user described. If the user has switched tabs since speaking, you
will be looking at the wrong page.

## When to claim a specific existing tab

Use `tabs_list`, match by URL/title, and pass that `tabId` explicitly when:
- the user refers to a page that is already open somewhere ("the GitHub PR
  tab");
- resuming work in a tab a previous turn opened;
- comparing multiple already-open pages.

If two tabs match ambiguously (same site twice), snapshot the candidates
(cheap) or ask the user which one. Do not guess with consequential actions.

## When to go active (`active: true`)

Open a tab in the foreground only when the point of the action is for the
user to see the page:
- they asked you to "open / show" something;
- the deliverable is the page itself (a doc they'll edit, a dashboard to
  review, checkout they must complete);
- you reached a step that requires their eyes (CAPTCHA, payment
  confirmation, "review before I submit").

Announce it: "I've opened it in a new tab for you." If you are mid-task in a
background tab and reach a needs-their-eyes moment, it is usually better to
finish what you can, then open/deliver, than to flip their view repeatedly.

## The tab data model

`tabs_list` returns `{ activeTabId, tabs: [...], windows: [...] }`. Tabs link
to windows via `windowId`. **`activeTabId` is the tab the user is currently
looking at** (active tab of the focused window) — when the user says "this
page", "here", or "the current tab", resolve it to `activeTabId` directly;
never delegate or guess from recency.

- Each tab carries full metadata: `tabId`, `windowId`, `index`, `active`,
  `highlighted`, `pinned`, `audible`, `muted`, `discarded`, `incognito`,
  `status`, `title`, `url`, `pendingUrl`, `favIconUrl`, `groupId`,
  `openerTabId`, `lastAccessed`, `width`, `height`.
- The window summary carries `windowId`, `focused`, `state` (normal /
  minimized / maximized / fullscreen), `type`, `incognito`, `alwaysOnTop`,
  bounds (`left`/`top`/`width`/`height`), and `tabCount`.
- Use it: prefer operating in the **focused window** when the task is about
  "the browser the user is looking at". Group tabs by `windowId` when
  matching "the GitHub window". Exclude `pinned: true` tabs from bulk
  cleanup (see `all-tabs-cleanup.md`).
- `active` is per-window — each window has one. The globally active tab is
  the `active` tab inside the `focused: true` window.
- Incognito tabs/windows are flagged (`incognito: true`). They carry a
  separate, unauthenticated-by-default profile: a site behaving as logged
  out despite the user being signed in may be an incognito window — check
  the flag before debugging.
- Still no cross-checking substitute for state: two same-site tabs remain
  distinguished by `index`/`windowId`/`lastAccessed`, or by snapshotting the
  candidates when the task is consequential.

## Etiquette in user tabs

- Never navigate a user tab somewhere else just for your own convenience —
  navigate your own tab or open a new one.
- Never reload a user tab that may hold unsubmitted input; a reload can eat
  their work. If a reload is genuinely needed, ask.
- If your task in their tab is done, say so — do not close their tab. Only
  close tabs you opened (see `tab-cleanup-chrome.md`), unless the user asked
  you to close theirs.
