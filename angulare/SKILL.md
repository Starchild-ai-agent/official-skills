---
name: angulare
version: 1.1.0
description: |
  Angulare (Angular e-Commerce) gym and studio management: class schedule, member
  attendance and check-ins, first-experience detection, the per-class mat/seat map,
  sales orders and payment status, credit-card payment links.

  Use when working with an Angulare-run studio or gym — finding which member is on which mat in a class,
  who actually attended a class, detecting a member's first class so a follow-up can go out, checking whether a customer has paid, looking up a member, or listing plans and aggregator (TotalPass/Wellhub) check-ins.
delivery: script
author: starchild
tags: [gym, fitness, angulare, angular-ecommerce, booking, attendance, checkin, members, pilates, brazil]
metadata:
  starchild:
    emoji: "\U0001F9D8"
    skillKey: angulare
    requires:
      env: [ANGULARE_EMAIL, ANGULARE_PASSWORD, ANGULARE_TENANT]
user-invocable: true
disable-model-invocation: false
---

# 🧘 Angulare (Angular e-Commerce)

Class agenda, **attendance and check-ins**, first-experience detection, sales
orders / payment status and payment links for **Angulare** — the booking and
e-commerce platform used by boutique studios (Pilates, Yoga, cycling) and gyms
in Brazil.

Angulare publishes **no developer documentation**. Every endpoint here was
reverse-engineered from their own dashboards and then verified against
production. Read `references/api-reference.md` before trusting a filter.

## Credentials

Three env vars, collected with `request_env_input` — never ask for these in chat:

| Var | What it is |
|---|---|
| `ANGULARE_EMAIL` | the manager account's login e-mail |
| `ANGULARE_PASSWORD` | that account's password |
| `ANGULARE_TENANT` | the tenant code, e.g. `numa` |

If you don't know the tenant code, `angulare_discover_tenants()` finds it from
the e-mail — it is the only call that needs no credentials.

Then prove the handshake before anything else:

```
angulare_check_credentials()
# -> tenant, site, authenticated user, permission list, token expiry
```

## How to Call

```bash
python3 - <<'EOF'
import sys, json
sys.path.insert(0, "/data/workspace/skills/angulare")
from exports import angulare_check_credentials, angulare_followup_candidates

print(json.dumps(angulare_check_credentials(), indent=2, ensure_ascii=False))
print(json.dumps(angulare_followup_candidates(hours_after=2), indent=2)[:1500])
EOF
```

Or through the platform loader:

```python
from core.skill_tools import _modules
angulare = _modules["angulare"]
angulare.angulare_payment_status(user_id=2200)
```

Standalone CLI while debugging:

```bash
python3 angulare/exports.py angulare_sessions date=2026-10-09
```

Every function returns `{"ok": True, "data": ...}` or
`{"ok": False, "status": ..., "error": ..., "hint": ...}`.

## Functions

### Auth / tenant

| Function | Purpose |
|---|---|
| `angulare_check_credentials()` | Prove the three-part handshake; returns tenant, user, permissions. |
| `angulare_discover_tenants(email=None)` | Which tenants this e-mail may access (public, no auth). |
| `angulare_tenant_settings()` | Tenant config: site, domains, enabled payment methods, `allow_cart_sharing`. |

### Members

| Function | Purpose |
|---|---|
| `angulare_find_members(search=None, cpf=None, is_staff=None, active=None, take=50, skip=0)` | Search members (`search` matches name/e-mail). |
| `angulare_resolve_member(query)` | One identifier (id/CPF/e-mail/name) → one member, or candidates. |
| `angulare_member(user_id)` | One member profile. |
| `angulare_quick_register_member(email, first_name, last_name, confirm=False)` | **[WARN] WRITE** — create a member with only these three fields. Use it to make throwaway members for end-to-end tests instead of testing against a real customer. |

### Schedule

| Function | Purpose |
|---|---|
| `angulare_sessions(date=None, take=100, all_pages=False, max_pages=10)` | Class sessions, optionally for one day. |
| `angulare_session(event_token)` | One session by token. |
| `angulare_session_roster(event_token)` | Everyone booked into one session, with status and spot (`map_spot_code`). |
| `angulare_session_seats(event_token)` | The mat/spot map: `{spot, name, email, is_staff, status}` per attendee, plus `free_spots` and `maintenance_spots`. |
| `angulare_find_session(activity=None, date=None, time=None)` | Resolve "Pilates at 19:00" to one session. |

### Attendance and check-ins

| Function | Purpose |
|---|---|
| `angulare_attendance(status=None, user_id=None, event_token=None, take=200, all_pages=False, max_pages=10)` | The attendance report. `event_token` = one class's roster; `user_id` = one member's history. |
| `angulare_first_experience_checkins(event_token=None, take=200, max_pages=10)` | Checked-in rows flagged `is_first_activity_checkin`. |
| **`angulare_followup_candidates(hours_after=2, window_minutes=90, first_experience_only=False, event_token=None, now=None)`** | **Members whose class ended ~2h ago and who showed up — the post-class follow-up feed.** |
| `angulare_member_attendance(user_id, take=200, max_pages=5)` | One member's attendance history. |
| `angulare_aggregator_checkins(date=None, take=200)` | TotalPass / Wellhub check-ins for a day. |
| `angulare_instructor_stats(take=50)` | books / checkins / no-shows / cancels per instructor. |

### Catalog

| Function | Purpose |
|---|---|
| `angulare_products(active_only=True, take=200)` | Plans/packages with price and granted credits. |
| `angulare_categories(take=50)` | PDV product categories. |
| `angulare_payment_methods(take=50)` | Payment method codes (`creditcard`, `pix`, `cash`, …). |
| `angulare_reference_data(take=1000)` | units, activities, rooms, locations, instructors in one call. |

### Payments

| Function | Purpose |
|---|---|
| `angulare_orders(user_id=None, status=None, take=100, all_pages=False, max_pages=5)` | Sales orders — **where payment status lives**. |
| `angulare_payment_status(user_id, take=50)` | Did this member pay? One-line verdict + counts. |
| `angulare_checkouts(user_id=None, take=100, all_pages=False, max_pages=5)` | Carts; `shared_to_customer` = a link went out. |
| `angulare_checkout(checkout_id)` | One checkout in full. |
| ⚠️ `angulare_checkout_share(checkout_id, channels=None, …, confirm=False)` | **WRITE** — send the credit-card payment link. Requires `confirm=True`. |
| `angulare_send_payment_link(user_id=None, query=None, product_id=None, quantity=1, replace_cart=True, channels=None, expiration=None, set_payment_method=None, confirm=False)` | **WRITE** — the whole sales flow in one call: resolve the member → put the product in their cart → send the payment link → verify it went out. Omit `confirm` for a dry-run plan. |

`date` accepts `"2026-10-09"`, `"09/10/2026"`, `"today"/"hoje"`,
`"tomorrow"/"amanhã"`, `"yesterday"`, or a day offset like `"+1"`.

## Workflows

### Who attended a class? (read-only)

```python
angulare_session_roster("f657c898-b5c4-4662-b03d-e74bc3a04117")
# or, with check-in timestamps and first-experience flags:
angulare_attendance(event_token="f657c898-…")
```

### Which mat is each person on? (read-only)

```python
angulare_session_seats("f657c898-b5c4-4662-b03d-e74bc3a04117")
# -> {"seats": [{"spot": "01", "name": "Thaiane ...", "email": "...",
#                "is_staff": False, "user_id": 1607, "status": "confirmed"}, ...],
#     "free_spots": ["05", ...], "maintenance_spots": []}
```

`spot` ("01"…"24") is Angulare's mat position; `free_spots` lists the unused
ones. Use `angulare_session_roster` when you only need attendance status.

Find the session first with `angulare_find_session(activity="Pilates", date="today", time="19:00")`
— it returns the `token` everything else keys on.

### The 2-hour post-first-class follow-up

```python
angulare_followup_candidates(hours_after=2, window_minutes=90,
                             first_experience_only=True)
```

Returns members whose class **ended** about two hours ago and who actually
checked in, each with `followup_due_at` and the class context. Run it on a
schedule; `window_minutes` stops it re-sending yesterday's cohort.

The class end time is computed as `event_time` + `event_info.duration_time`
(the row's own `end_time` is usually null).

### Did the customer pay?

```python
angulare_payment_status(user_id=2200)
# -> {"verdict": "paid" | "awaiting_payment" | "no orders", "paid": 1, "awaiting_payment": 0, ...}
```

**Payment status lives on the order, not on the cart.** A checkout stays
`Submitted` forever; only the order flips to `paid`. Order statuses:
`paid` (Pago) · `waiting_payment` (Aguardando pagamento) · `not_authorized`
(Pagamento não autorizado) · `canceled` (Cancelado).

Because an order can exist as `waiting_payment` **before** any money moves, poll
`angulare_orders(user_id=…)` and watch for a new `paid` row.

### Aggregator check-ins

```python
angulare_aggregator_checkins(date="2026-10-08")
# -> checkins with aggregator: "totalpass" | "gympass", status, pass_type
```

### Selling a plan over WhatsApp (the one-call flow)

This is the flow the sales team actually runs: a customer asks about a plan in
chat, and the answer ends with "check your e-mail and pay".

```python
# 1. dry run first when you are not sure which cart you are about to overwrite
angulare_send_payment_link(query="<phone|name|cpf|e-mail>", product_id=2)

# 2. execute
angulare_send_payment_link(query="<phone|name|cpf|e-mail>", product_id=2, confirm=True)
# -> {"sent": True, "checkout_id": …, "total": 80.0,
#     "shared_to_customer": True, "expiration": "…",
#     "steps": [{"step":"remove_line","status":200},
#               {"step":"add_product","status":200},
#               {"step":"share","status":200}],
#     "next": "…poll angulare_payment_status(user_id=…) for status 'paid'"}

# 3. tell the customer in your own channel, then poll
angulare_payment_status(user_id=<uid>)     # 'paid' when the money lands
```

`sent: True` is the answer to "did the e-mail go out" — it means Angulare
accepted the share (200) and the cart's `shared_to_customer` came back `true`.
The e-mail's subject is *"Link para pagamento do seu pedido"* and it lists the
cart contents.

Three guards run before anything is written, each turning a confusing API error
into a plain one: **a staff member's cart is refused up front** (Angulare 403s on
those by design), **a member with no e-mail is refused** when the email channel
is used, and **an empty cart after adding is refused**. `replace_cart=True`
(default) clears the member's current cart first, so the link covers exactly what
you asked for — check the dry-run `plan.remove_line_ids` if that matters.

What this function deliberately does **not** do is message the customer. That is
your channel's job; its contract is that the link has been sent and verified.

### Sending the credit-card payment link

```python
angulare_checkout_share(checkout_id=1234, channels=["email"], confirm=True)
```

⚠️ This is a **write** that sends a real e-mail/SMS to the customer. It requires
`confirm=True`; without it you get an explanatory error and nothing is sent.
It does **not** create an order — the order appears only when the customer pays.

**⚠️ A `403 "Você não tem permissão para executar essa ação."` does NOT mean a
missing permission — it means the cart belongs to a STAFF member.** Verified on
five carts: every staff-owned cart 403s, every member-owned cart does not. There
is no permission to ask Angulare for; send the link for a real customer's cart.

The call needs these fields (the API names whichever one you omit):

- **`expiration`** — a datetime. `YYYY-MM-DD` is accepted and normalised to
  `T00:00:00-03:00`; an integer number of days is rejected. Defaults here to
  today 23:59:59 at UTC-3, matching the dashboard.
- `revalidate`, `ask_password`, `ask_card`, `show_checkout` — all required.

The response is a usable success signal:

| Response | Meaning |
|---|---|
| `200 {"ok": …, "expiration": …, "expiration_capped": false}` | queued |
| `403 {"detail":"Você não tem permissão…"}` | the cart's owner is staff |
| `404 {"detail":"No Checkout matches the given query."}` | cart gone |
| `400 {"<field>":[…]}` | that required field is missing |

After a successful share the cart's `shared_to_customer` flips to `true` — a
second, independent confirmation the function already reads back.

**The link looks like this** (captured from a real `share` e-mail):

```
https://numastudios.com.br/?uid=<member_id>&ck=<checkout_id>&ec=<code>
```

⚠️ **Do not try to build this URL yourself.** `ck` is the checkout id but `ec` is
an emailed OTP the API never returns, and the storefront opens a cart only from
those **query parameters** — not from a path or hash segment. In particular
`pay_key_public` on the checkout is the **payment gateway's public key**, not a
route id: `#/checkout/{pay_key_public}` renders the home page and
`/checkout/{pay_key_public}` 404s (verified 2026-10-16). Delivery must go through
`/share/`, or through a link-minting endpoint Angulare would have to expose.
See `references/api-reference.md` → "pay_key_public is NOT a checkout route" and
"Two hand-built link attempts, two failures" — both the `revalidate-url` and the
`pay_key_public` shortcuts have already shipped broken and reached customers.

`uid` and `ck` are readable from the API (`checkout.owner`, `checkout.id`);
`ec` is not — but you do not need it. **`share` delivers the whole link itself**,
inside an e-mail whose subject is *"Link para pagamento do seu pedido"* and which
lists the cart contents. The API does not return the URL, so if you need the link
in your own channel, have the customer forward it — or just let the e-mail do the
job.

The pattern is therefore: call `angulare_checkout_share(...)`, confirm it returned
`200` (and that `shared_to_customer` came back `true`), then poll
`angulare_orders(user_id=…)` for the resulting `paid` order to trigger whatever
comes next. A member with missing required data will be asked to fill it in at
the first checkout step rather than at the payment step — that is normal.

## Key Facts / Gotchas

- **`Authorization: JWT <token>` — not `Bearer`.** Getting this wrong returns
  `401 {"detail":"Login expirado!"}`, which looks like an expiry bug and is not.
- **The `tenant` header is required on every call.** Omit it and you get
  `401 {"detail":"Email não encontrado"}`.
- **Unsupported query params are silently ignored** — a typo returns the full
  dataset with HTTP 200. Check that `count` narrowed before trusting a filter.
  Verified filters: members `search`/`cpf`/`is_staff`/`active`; sessions `date`;
  attendance `status`/`user_id`/`event_token`; orders `user_id`/`status`;
  checkouts `user_id`; aggregator check-ins `date`. No `ordering` anywhere.
- **The attendance report cannot filter on `is_first_activity_checkin`**, so
  `angulare_first_experience_checkins` and `angulare_followup_candidates` scan
  `status=checked-in` pages and filter client-side. On a busy tenant that is
  ~4,400 rows; raise `max_pages`, or pass `event_token` when you know the class.
- **Cart ≠ order.** `shared_to_customer` does not become "paid". Only orders
  carry payment state, and `waiting_payment` means "link out, not settled".
- **Unsubmitted carts are ephemeral.** A checkout in `status: "Open"` expires
  (the share's `expiration`, default same-day 23:59:59) and is then **purged** —
  the id disappears from both the detail endpoint and the list, and the total
  count drops. Verified: one cart was readable in the morning and gone the same
  afternoon, while `Submitted` carts stayed. So never cache a checkout id, and
  read a 404 from `/share/` as "that cart is gone", not as a permission error.
- **Booking cancellation is not implemented** — the `event-books` list omits
  `id` and the attendance row ids do not resolve on the event-book detail
  endpoint. Do not promise a cancel-booking feature.
- Angulare returns **HTTP 500 for a malformed `Authorization` value** (their
  bug); a bad token should be 401.
- Multi-tenant by host: a tenant only exists on its own deployment
  (`prd.angulare.app`, `prd.europa.angulare.app`, `…angularesmart.com`).
- All data is **production** — there is no sandbox.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `missing Angulare credential(s)` | Env not set | `request_env_input` for the three vars |
| `401 Login expirado!` | `Bearer` instead of `JWT`, or a genuinely expired token | The client retries once with a fresh token; if it persists, check the scheme |
| `401 Email não encontrado` | `tenant` header missing/unknown | Set `ANGULARE_TENANT`; find it via `angulare_discover_tenants()` |
| `403 open_api_key_scope` | An Open API Key was used | This skill needs a JWT, not an Open key |
| A filter "does nothing" | The param name isn't supported | Compare `count` before/after; see the verified list above |
| `angulare_checkout_share` refuses | `confirm=True` missing | Deliberate — it messages a real customer |
| Empty `followup_candidates` | Nothing in the window | Widen `window_minutes`, or check the tenant's timezone vs UTC |

## References

- `references/api-reference.md` — hosts, the full auth contract, every verified
  endpoint with its working filters, attendance field map, the checkout/order
  distinction, known-but-unwired write endpoints, and the payment-link gap.
- `docs/integrations/angulare.md` (repo root) — how this was reverse-engineered,
  with the evidence trail.
- `docs/integrations/pt-br-glossary.md` — Portuguese → Chinese glossary of the
  dashboard vocabulary.
