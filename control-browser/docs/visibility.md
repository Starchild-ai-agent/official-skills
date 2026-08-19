# Visibility

`tab_open` defaults to a background tab (`active: false`). This is the right
default — but it changes what the user experiences, and you must account for
that in how you act and how you report.

## The orange cursor signals control mode

- The agent cursor (orange arrow) becomes visible the moment a tab's
  **debugging session starts** — the first browser tool touches that tab via
  CDP (snapshot, click, wait, or screenshot alike) — and stays visible for
  the whole session: it breathes while idle, springs to targets when acting,
  and pulses on click. When debugging stops (user cancels the debug infobar,
  or the bridge detaches), the cursor fades out — cursor visibility marks
  **active agent control**, nothing more.

## Tab-strip visual states (claim groups)

- Claimed tabs carry a native Chrome tab-group badge: **orange "★ Starchild"**
  group = agent-owned for a task; **yellow "⏳ Starchild"** group = handoff,
  waiting for the user. `tab_release {disposition:"keep"}` removes the badge
  and leaves the page open.
- Together with the cursor: cursor visible = being controlled right now;
  orange group = agent's task tab; yellow group = the user owes an action
  there. Describe tab states to the user in these terms.
- Consequence: a tab with the cursor idling is under agent control, even if
  you have since moved on to other work. The user sees this at a glance when
  they return to the tab.

## What the user sees (and doesn't)

- Actions in a **background tab are invisible to the user**. The orange agent
  cursor moves and clicks in a tab they are not looking at; pages load and
  forms fill with no visible trace in their current view. From their chair,
  the browser looks idle.
- Therefore: narrate. When working in the background, tell the user what is
  happening in words — "opening the order history page in a background tab",
  "filling in the form now". Silence plus an invisible browser reads as
  nothing happening.
- When you act in the **user's active tab**, the opposite holds: they see
  the orange cursor jump and move. A cursor teleporting across their page
  unannounced is startling. Say what you are about to do first ("I'll click
  the export button on the right").

## Background by default

Keep work in background tabs when:
- the page is a means to an answer (research, verification, data
  extraction);
- the user is doing something else and should not be interrupted;
- localhost testing where you will report findings in conversation anyway
  (screenshots where needed — see `screenshots.md`).

Navigation and page loads do not, by themselves, justify taking over the
user's screen.

## Foreground when the point is to be seen

Use `active: true` (or surface an already-open tab) when:
- the user asked you to "open" or "show" something — the deliverable is them
  looking at the page;
- the flow reaches a user-only step (login, payment, CAPTCHA, review) and
  they need to take over in that tab;
- they explicitly want to watch you work.

Announce foreground tabs when you open them: "I've opened the dashboard in a
new tab."

## Switching costs

- Do not flip the user's view repeatedly. Going active, then background,
  then active again is disorienting. Batch what you can; flip once, at the
  moment it matters.
- If you started in the background and the user asks "where is this
  happening?", either describe it or bring the tab forward once — their
  question is the signal they want to see.
- When handing off mid-flow (see `tab-cleanup-chrome.md`), bring the
  handoff tab to the front so they land directly on the step awaiting them.

## Reporting honestly

Never imply the user watched something they couldn't have. "I filled the form
and submitted it in a background tab" is honest; "as you saw" is not. The
orange cursor is your visible presence — but only in whatever tab is actually
on screen.
