# All-Tabs Cleanup

Handling explicit requests to close everything — "close all my tabs", "clean
up the browser", "shut them all". This is a bulk destructive action against
**the user's own tabs**, so it has stricter rules than ordinary self-cleanup
(`tab-cleanup-chrome.md`).

## Confirm scope before bulk closing

- Closing all tabs can destroy user work: unsaved drafts, half-filled forms,
  in-progress checkouts, pages they parked for later. Always confirm the
  exact scope first, and show it.
- Enumerate with `tabs_list`, then summarize what will close: count plus any
  tabs that look risky (composers, editors, carts, tabs with "draft"/"new"/
  "compose"/"checkout" in URL or title). Example: "That's 14 tabs, including
  a Gmail compose and a checkout page — close all of them?"
- If the user already gave an unambiguous, current-turn instruction ("close
  everything, I don't care"), that is consent; proceed without re-asking.
  Ambiguity ("clean this up a bit") is not consent for closing user tabs —
  ask.
- Never bulk-close based on a stale `tabs_list` — the user may have opened
  something since. Re-list immediately before closing if any time passed.

## Mechanics

- Iterate `tabs_list` results and `tab_close {tabId}` each. There is no bulk
  primitive; close them one by one.
- Expect transient races: a tab may be closed by its own page (popups,
  self-closing dialogs) between listing and closing. A close failing because
  the tab is already gone is success — continue with the rest, don't abort.
- A pinned tab or a tab that refuses to close (beforeunload dialog, in-progress
  download) may survive. Retry once, then report which tabs could not be
  closed rather than hammering.
- Close order does not matter; do not switch tabs to active while closing —
  stay in the background and keep the user's view stable.

## Keep-out list

Unless the user explicitly overrides, exclude from a bulk close:
- pinned tabs (`pinned: true` in `tabs_list` — the user pinned them for a
  reason);
- tabs with obvious in-progress state (compose, edit, checkout, upload);
- the tab the user is actively using, if identifiable — ask specifically
  about it.

Offer the exclusion proactively: "I can close everything except the pinned
Gmail and your draft in Notion — OK?"

## Agent tabs first

If some of the open tabs are ones you opened, close those immediately
without asking — they are yours regardless of the broader request. Then
apply the confirmation flow above to the user's remaining tabs.

## Aftermath

- Report the outcome plainly: "Closed 12 tabs; 2 stayed open (pinned Gmail,
  and your draft)."
- An empty tab list afterwards is the goal state, not an error. Do not
  interpret subsequent "no tabs" results as a bridge failure.
