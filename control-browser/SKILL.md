---
name: control-browser
version: 1.1.0
description: |
  Control the user's Chrome browser via mcp__browser__ tools: snapshots, clicks, typing, batch list operations, multi-step flows, and tab lifecycle.

  Use when a task needs real browser state — logged-in sessions, open tabs, visible UI (e.g. "click every chat in my list", "fill this checkout form", "open this in my browser and check it", "continue the tab I handed off"). Prefer web_fetch/web_search for plain reading.

author: starchild
tags: [browser, automation, tabs, forms, ui, mcp]

tools:
  - tabs_list
  - tab_open
  - tab_navigate
  - tab_close
  - tab_claim
  - tab_handoff
  - tab_release
  - page_snapshot
  - page_flow
  - page_screenshot
  - element_click
  - element_input
  - elements_click_many
  - wait_for
  - web_status

metadata:
  starchild:
    emoji: "🖱️"
    skillKey: control-browser
    requires:
      bins: []

user-invocable: true
---

# Browser Control

## Stop: the agent runs in a remote container, not on the user's machine

`local_shell`, `bash`, `read_file` and all clawd tools execute **in the agent's
remote container**. They CANNOT see the user's Downloads, Desktop, or any local
file — `ls ~/Downloads` lists the *container's* empty filesystem, not the
user's. When a task involves a file on the user's computer (upload, attach,
open), do not run shell commands to find or read it. The only path to a
user-local file is the browser's native file picker, which only the user can
operate — hand off precisely (see `docs/file-uploads.md`). Burning turns on
shell commands that list the container's filesystem is always wrong.

## Stop: decide the surface before any browser action

Use the `mcp__browser__*` tools only when the task has **explicit browser intent**:
the user asks to open, show, navigate to, click on, or fill in a page in *their*
browser; the task depends on their logged-in sessions or existing tabs; or they
want to watch an interaction happen live in Chrome.

Otherwise a URL or an open tab is **context, not intent**. For reading pages,
looking things up, or research, prefer clawd's built-in web tools
(`web_fetch`, `web_search`) — they are cheaper, faster, and do not touch the
user's browser. Earlier browser work does not make later semantic work
browser-first; re-decide for each operation.

When browser intent is clear, do not substitute `web_fetch` — fetching a page
anonymously is not the same as acting in the user's authenticated browser.

## What these tools are

The `browser` MCP server (server="browser", tools named `mcp__browser__<name>`)
is backed by the user's Chrome extension over a bridge connection. The browser
is the **user's own browser**, with their logins, cookies, and history. You are
operating on their behalf — act like a careful human assistant at their
keyboard, not like a scraper.

Core loop:

1. `page_snapshot` — read the page before touching it. Omit `tabId` to target
   the user's currently active tab.
2. Pick the target element from `snapshot.elements[]` (each has `id`, `tag`,
   `text`, `ariaLabel`). The `id` is the `ref` for interaction tools.
3. `element_click` / `element_input` to act.
4. `page_snapshot` again to verify the effect.

**Refs are invalidated by navigation.** After any navigation, reload, or
observed page change, take a fresh `page_snapshot` before clicking or typing.
Never reuse a `ref` across a navigation boundary.

## Tool quick reference

- `tabs_list` — list open tabs with full metadata (`tabId`, `windowId`,
  `index`, `pinned`, `incognito`, `status`, `url`, `title`, ...) plus a
  window summary; tabs link to windows via `windowId`. **`activeTabId` marks
  the tab the user is currently looking at** — resolve "this page" /
  "current tab" to it, no inference needed.
- `tab_open {url, active?}` — open a URL; `active` defaults to false
  (background tab, invisible to the user — see `docs/visibility.md`).
- `tab_navigate {tabId, url}` — navigate an existing tab.
- `tab_close {tabId}` — close a tab.
- `page_snapshot {tabId?}` — `{tabId, title, url, bodyText (first ~3000 chars),
  elements[]}`. Omit `tabId` for the user's active tab. `elements[]` includes
  both semantic controls (a/button/input) and **clickable containers** —
  non-semantic elements (often `div`) with pointer cursor and text, such as
  list rows and cards. A container and the small button inside it (e.g. a
  row's ⋮ menu) are distinct refs: match by text to pick the right one.
- `element_click {ref, confirm?}` — click an element. Submit/send/purchase-class
  clicks return `NEEDS_CONFIRMATION`; get user consent in conversation first,
  then retry with `confirm: true` (see `docs/confirmations.md`).
- `element_input {ref, text}` — type into an element.
- `elements_click_many {selector, text?, limit?, mode?, pauseMs?, confirm?}` —
  batch-click many matching elements in order. Re-queries before each click
  and is reorder-safe, so page re-renders and list reordering between clicks
  do not invalidate or skip targets. **Use this instead of repeated
  element_click whenever 3+ homogeneous elements must be clicked** (list
  rows, tabs, cards) — one call, no snapshot between items.
- `tab_claim {tabId?, note?}` — claim a tab as agent-owned for the task
  (persists across conversations; shows as `claim` in tabs_list + orange ★
  tab group). Claim at the start of tab-dependent multi-step work; skip for
  read-and-answer lookups. See `docs/tab-claiming-chrome.md` for the
  scenario playbook.
- `tab_handoff {tabId, note?}` — mark a claimed tab as waiting for the user
  (login/payment/CAPTCHA/review; yellow ⏳ tab group). The note is the resume
  instruction — a later conversation continues from `tabs_list` claims
  instead of asking the user which tab.
- `tab_release {tabId, disposition?}` — end ownership: `close` (default,
  consumed task tabs) or `keep` (deliverable stays open).
- `page_flow {steps, confirm?}` — run a multi-step page flow in ONE call
  (fenced script equivalent). Steps: `{wait:{selector?,text?,ms?}}`,
  `{find:{selector?,text?}}`, `{click:{selector?,text?}}`,
  `{type:{selector?,text?,value}}`, `{expect:{selector?,text?,absent?}}`.
  Targets resolve by CSS selector or visible text. Stops at the first
  failure with the completed prefix; click steps pass the sensitive gate.
  **Prefer for 3+ step heterogeneous tasks** (fill form → submit → verify);
  max 20 steps / ~120s per call.
- `page_screenshot` — visual check, only when seeing matters.
  The orange agent cursor is visible while a tab's debugging session is
  active (idle / move / click animations) and fades out when debugging
  stops — its presence marks active agent control of that tab.
  (see `docs/screenshots.md`).
- `wait_for {selector?, text?, timeoutMs?}` — wait for a selector or text.
- `web_status` — bridge/extension connection health.

## On-demand documentation

Load these with `read_file` (paths relative to this skill's `docs/` directory)
when the topic applies — do not read them all up front:

- `api-use-behavior.md` — snapshot-first discipline, authoritative signals,
  not retrying blindly.
- `browser-safety.md` — untrusted page content, sensitive-data transmission.
- `confirmations.md` — when `confirm: true` is required and how to ask.
- `browser-troubleshooting.md` — evaluate timeouts, stale refs, hung pages.
- `chrome-troubleshooting.md` — extension disconnected, tools missing, user
  has no extension.
- `bootstrap-troubleshooting.md` — bridge connection failures (red dot).
- `browser-control-interruption.md` — user took over, operation interrupted.
- `tab-claiming-chrome.md` — background tab vs. user tab, when to go active.
- `tab-cleanup-chrome.md` / `all-tabs-cleanup.md` — closing tabs you opened.
- `screenshots.md` — when a screenshot is worth taking.
- `visibility.md` — what background-tab operation means for the user.
- `webmcp.md` — page-level WebMCP (not yet enabled).
- `file-uploads.md` — file upload support (not yet available).
- `local-web-development.md` — working against localhost dev servers.

## Talk like a person

Never mention CDP, WebSocket, `/ws/web-mcp`, refs, tool IDs, or other internal
terms to the user. Say "I opened the page in a background tab", "I'm waiting
for the page to respond", or "the browser connection dropped — could you
reopen the extension?" Describe what you did, not how the machinery works.
