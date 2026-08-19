# Tab Cleanup

Leave the browser as you found it, minus the tabs you were done with. Tabs
you opened are yours to close; tabs the user opened are theirs to keep.
**If you claimed tabs (`tab_claim`), close them via `tab_release
{disposition: "close"}`** — it closes the tab and clears the claim record in
one step; `keep` leaves the page open and just clears the record.

## Rule: close what you opened

Before ending a browser task, close every tab you opened with `tab_open`
unless it falls under "keep" below. Use `tab_close {tabId}` on each. Do not
leave a trail of search results, source pages, and intermediate navigation
tabs behind — the user's Chrome is not your scratch space.

## Close

- Research and search result pages you have already extracted the answer
  from.
- Intermediate steps of a flow (the product list page once you are on the
  product page, the login page after auth completed).
- Duplicates, blank tabs, error pages, and dead ends.
- Pages the user only needed to see transiently and has already acknowledged
  ("there it is" → you can close it).

If the user asked a question and you can answer it in the conversation, the
tab that answered it is closeable — the *answer* is the deliverable, not the
page.

## Keep open

- **Deliverable tabs** — the page itself is the output: a created/edited
  document, dashboard, cart, or submitted-form confirmation the user needs
  to look at. Say that you left it open.
- **Handoff tabs** — the flow stops at a step only the user can do: login,
  payment, CAPTCHA, a review-and-approve screen. Leave the page open at that
  step and tell the user exactly where to pick up ("the form is filled and
  waiting on the payment step — the tab is open in your browser").
- Tabs the user explicitly asked to keep open or to open in the first place.
- **User tabs — always.** Never close a tab the user opened as part of your
  cleanup, even if it looks useless to you. Only close user tabs when the
  user asked you to.

## Mechanics

- Track your tabs: every `page_snapshot` response carries the `tabId` you
  are working in; `tabs_list` shows the full picture at the end.
- Close tabs as soon as they are consumed rather than batching at the very
  end where possible — fewer loose ends if the session is interrupted.
- Closing the last tab you opened is normal and is not an error condition;
  do not treat an empty result or a gone `tabId` as a bridge failure
  afterwards.
- If a tab you meant to close is already gone (user or site closed it),
  fine — nothing to do.

## Report

One line suffices: "I closed the tabs I opened" or "I left the checkout tab
open for you." No inventory lists, no `tabId`s.
