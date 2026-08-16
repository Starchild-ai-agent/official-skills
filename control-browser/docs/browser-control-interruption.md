# Browser Control Interruption

What to do when the user takes over, or an in-flight browser operation is
interrupted mid-step.

## The user is always in control

The browser is the user's. They can click, type, switch tabs, navigate, or
close tabs at any moment — including between your `page_snapshot` and your
`element_click`. That is not an error condition; it is the operating reality
of driving a live browser someone else is sitting in front of.

## Signs you were interrupted

- A snapshot that no longer matches the previous one (different `url`,
  `title`, or wildly different content).
- An `element_click` / `element_input` that fails on a ref you just resolved.
- A tool error indicating the tab changed state, navigated, or closed.
- Your background tab suddenly contains user-typed content.

## Recovery procedure

1. **Stop the planned action sequence.** Do not replay your queued steps on
   stale assumptions; the page state that justified them may be gone.
2. **Re-snapshot.** `page_snapshot` (with the explicit `tabId` if you had
   one) and compare `title`/`url`/`bodyText` against what you expected.
3. **Reconcile, don't overwrite.** If the user's interference changed the
   state — they navigated away, typed into a field, dismissed a dialog —
   preserve their state and continue from it. Never "fix" the page back to
   your previous state (no undoing their navigation, no clearing their
   input) without asking.
4. **Resume or ask.** If the new state is compatible with the goal, continue
   from it with fresh refs. If the user's action diverges from the task (they
   seem to be doing something else in that tab), pause and ask: "Looks like
   you're using this tab — want me to continue here, or open my own tab?"

## If the tab is gone

The user may have closed your tab. Check `tabs_list`. If the task still
needs the page, reopen with `tab_open` (background by default). Losing a tab
this way is routine — do not report it as a failure, just quietly reopen.

## If the user pauses or redirects you verbally

- If the user says stop / wait / "let me do this part": stop immediately,
   even mid-form. Report the exact state you left things in ("the form is
   filled but not submitted") so they can take over cleanly.
- When they hand control back, re-snapshot before acting — time has passed
   and the page has likely changed. Old refs are almost certainly stale.
- For steps the user chose to do themselves (login, payment, CAPTCHA), wait
   for their "done" and verify with a snapshot rather than assuming.

## Reporting

- Describe interruptions naturally: "It looked like you were using that tab,
  so I paused." No internal error strings, ref IDs, or tool call details.
- If an interruption means a step may or may not have completed (you clicked,
  the page churned, and you lost the thread), say so honestly and verify the
  outcome before claiming success.
