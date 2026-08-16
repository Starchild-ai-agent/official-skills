# Confirmations

When `element_click` targets a consequential action, the tool itself enforces
a two-step flow: the first call returns `NEEDS_CONFIRMATION`, and the action
only executes when you retry with `confirm: true` **after** the user has
agreed in the conversation. This document defines when to use it and how to
ask.

## How the mechanism works

1. You call `element_click {ref}` on, e.g., a "Place order" button.
2. The tool returns `NEEDS_CONFIRMATION` instead of clicking.
3. You ask the user in plain language and wait for their reply.
4. On approval, call `element_click {ref, confirm: true}`.

Rules:
- `confirm: true` is only valid as a **retry after NEEDS_CONFIRMATION** plus
  user consent. Never pre-emptively pass it to skip the gate.
- User consent must come from the conversation, this turn, about this action.
  "The user asked me to buy the book" covers the checkout submit; it does not
  cover a price change discovered since, an upsell added mid-flow, or a
  different item.
- Take a fresh `page_snapshot` if the user's reply took a while — the page may
  have changed, and the old `ref` may be stale. Re-identify the element, then
  click with `confirm: true`.
- If the user declines or goes silent, stop. Do not click, do not "click
  anyway without confirm" — that is what the gate exists to prevent.

## What triggers NEEDS_CONFIRMATION

The tool returns `NEEDS_CONFIRMATION` for submit/send/purchase-class actions,
typically:
- form submissions with external side effects (orders, applications, posts);
- sending messages, emails, comments, replies;
- payment / checkout / purchase steps;
- other irreversible-looking actions the classifier flags.

Respect it even when you think the click is trivial. If the gate fires, the
flow is: ask, get consent, retry with `confirm: true`.

## Actions the tool does not gate (you still must)

Some consequential actions do not go through `element_click`'s gate — e.g.
`element_input` that transmits on blur, or an `element_click` the classifier
does not flag. You are still responsible for the confirmation policy in
`browser-safety.md`. If the action transmits sensitive data or has an
external side effect and the user's original request did not specifically
authorize it, ask first even if no tool gate forced you to.

## How to ask

- Name the exact action, destination, and data: "Submit the refund request
  form on acme.com with the reason 'damaged in shipping'?"
- Surface the cost/irreversibility when relevant: amount, recipient, and that
  it cannot be undone.
- Ask one focused question, then stop and wait. Do not bundle three
  confirmations into one paragraph.
- If the user already gave specific, current-turn authorization ("reply 'yes
  please' to that thread"), the confirmation is satisfied — proceed with
  `confirm: true` without re-asking. Re-asking the identical question is
  friction, not safety.
- If anything material changed since consent — price, recipient, quantity —
  the old consent is void. Ask again.

## After approval

- Retry promptly; do not wander off and let the page session expire.
- Verify the effect with a `page_snapshot` (order confirmation, sent state,
  success toast) and report the outcome to the user with the authoritative
  signal you saw.
