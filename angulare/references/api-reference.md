# Angulare API reference (reverse-engineered)

Angular e-Commerce publishes **no developer documentation**. Everything below
was recovered from their own front-ends and then verified against production:

| Surface | Host | What it is |
|---|---|---|
| API | `https://prd.angulare.app` | every endpoint in this skill |
| Manager dashboard | `https://dash.angulare.app` | SPA; `/login` is the working entry |
| Legacy dashboard | `https://reservas.angulare.app` | older SPA, same API |
| SSO page | `https://crm.angulare.app/api/login/` | Django form login (see caveat below) |
| Static assets | `https://static.angulare.app/web/v4.0.390/*.js` | the customer web app |
| Customer app | `https://<tenant-domain>` | e.g. `numastudios.com.br`, embeds Pagekraft widgets |

Regional deployments: `prd.europa.angulare.app`, `europa.angularesmart.com`,
`brasil.angularesmart.com`. A tenant lives in exactly one of them — use
`check-tenant` to find out which.

## Authentication

```
1) GET  /api/v1/users/users/check-tenant/?email=<email>&is_staff=true      (public)
   -> {"tenants_allowed":[{"tenant_code":"numa",...}], "tenants_blocked":[]}

2) POST /api/v1/jwt/token-auth/
   headers: tenant: <tenant_code>, Content-Type: application/json
   body:    {"email":"…","password":"…"}
   -> {"token":"<JWT>","refresh":"<JWT>"}          TTL ≈ 10 days (exp - iat)

3) every subsequent call
   Authorization: JWT <token>        <-- literal "JWT", NOT "Bearer"
   tenant: <tenant_code>
```

Refresh: `POST /api/v1/jwt/token-refresh/` with **form-encoded** `refresh_token=…`.

### Error fingerprints (these mislead if read literally)

| You send | You get | Actually means |
|---|---|---|
| `Bearer <token>` + tenant | `401 {"detail":"Login expirado!"}` | wrong scheme — use `JWT` |
| `JWT <token>`, no tenant | `401 {"detail":"Email não encontrado"}` | missing `tenant` header |
| nothing | `401 {"detail":"As credenciais de autenticação não foram fornecidas."}` + `WWW-Authenticate: JWT realm="api"` | unauthenticated |
| `Basic user:pass` | `401 {"detail":"Usuário ou senha inválido."}` | Basic exists but is not the integration path |
| `Api-Key <k>` on `/api/v1/…` | `403 {"code":"open_api_key_scope"}` | Open keys are only valid under `/api/open/v1/…` |
| `Bearer <garbage>` | **`500`** | Angulare bug — a malformed token should be 401 |
| tenant header on `/api/open/…` | `400 tenant_required` / `tenant_invalid` | open-API gate, checked before routing |

The SSO page at `crm.angulare.app/api/login/` takes username/password/**tenant**
but rejects tenants it does not host ("Cliente nao encontrado, verifique a URL").
Use `dash.angulare.app/login` instead — e-mail → tenant auto-resolved → password.

## ⚠️ Filters are silently ignored

Most list endpoints are plain DRF views without a filter backend. A **wrong
parameter name returns the full set with HTTP 200** — no error, no warning.
Always confirm the `count` actually changed before trusting a filter. Verified
filters are listed per endpoint below; everything else is noise.

## Verified read endpoints

| Endpoint | Filters that WORK | Notes |
|---|---|---|
| `GET /api/v1/users/users/` | `search`, `cpf`, `is_staff`, `active` | members + staff; `search` matches name/e-mail |
| `GET /api/v1/users/users/{id}/` | — | one member |
| `GET /api/v1/core/settings/` | — | tenant config (site, checkouts, events, users, payments, domains) |
| `GET /api/v1/events/events/` | `date` | class sessions; **`token` (UUID) is the session key** |
| `GET /api/v1/events/events/{token}/` | — | one session |
| `GET /api/v1/events/events/{token}/bookings/` | — | one session's roster (`map_spot_code` = mat position) |
| `GET /api/v1/events/events/{token}/` | — | session detail; `map_spots[]` = `{code, position, bookings[{attendee{first_name,last_name,email,is_staff}, booked_at}], maintenance}` |
| `GET /api/v1/events/schedule/` | — | schedule view (444 rows on the test tenant) |
| `GET /api/v1/events/reports/event-books/` | **`status`, `user_id`, `event_token`** | **the attendance report — the useful one** |
| `GET /api/v1/events/event-books/` | `status`, `user_id`, `event_token` | same data, thinner serializer, **no `id`** |
| `GET /api/v1/events/external-checkins/` | **`date`** | TotalPass / Wellhub check-ins |
| `GET /api/v1/events/event-books/book-stats-by-instructor/` | — | books / checkins / no_shows / cancels per instructor |
| `GET /api/v1/events/units/`, `activities/`, `rooms/`, `locations/`, `instructors/` | — | reference data |
| `GET /api/v1/events/credit-packages/` | — | credit packs |
| `GET /api/v1/events/useraccess/`, `event-tickets/`, `gympass-plans/`, `performances/performances/` | — | present, mostly empty on the test tenant |
| `GET /api/v1/products/products/` | `active` (true/false), `can_sell` (true), `can_sell_mobile` (true) | price is `current_price`; **use the `active=true` filter, not the `active` field** (see below) |
| `GET /api/v1/products/categories/` | — | PDV categories |
| `GET /api/v1/payments/payment-methods/` | — | `creditcard`, `pix`, `cash`, … |
| `GET /api/v1/sales/orders/` | **`user_id`, `status`** | **payment status lives here** |
| `GET /api/v1/checkouts/checkouts/` | `user_id` | carts; `shared_to_customer` = a link went out |
| `GET /api/v1/checkouts/checkout-lines/` | — | cart lines |
| `GET /api/v1/subscriptions/user-subscriptions/` | — | recurring subscriptions |

The dashboard references **132 distinct `/api/` paths** in total
(`checkouts/`, `sales/`, `subscriptions/`, `products/`, `payments/`,
`loyalties/`, `cms/`, `communication/`, `core/`, `jwt/`, `users/`, `events/`).
Extract them from `reservas.angulare.app/js/*.js` when you need more.

## Attendance report — the fields that matter

`GET /api/v1/events/reports/event-books/`

| Field | Meaning |
|---|---|
| `status` | `checked-in` \| `booked` \| `waiting-list` \| `canceled` \| `no-show` \| `late-canceled` |
| `user_id` / `user_info` | the member (`user_info.email`, `first_name`, `last_name`) |
| `checkedin_at` / `checkedout_at` / `noshow_at` | the check-in timeline |
| **`is_first_activity_checkin`** | **true = their first class of that activity** |
| `checkin_number`, `checkin_activity_number`, `checkin_consecutive_weeks` | visit counters / streaks |
| `event_id`, `event_info` | `event_info` carries `{name, token, event_date, event_hour, duration_time, event_type}` |
| `event_time` | class **start**; the row's own `end_time` is usually null — compute the end from `event_info.duration_time` |
| `activity_info`, `instructor_info` | class context |
| `booking_source` | `angulare-mobile` / `angulare-desktop` / aggregators |
| `credits_spended`, `is_unpaid`, `income`, `plans_used` | billing side |
| `crm_case_token`, `crm_case_stage` | built-in CRM hook |

Counts on the test tenant: 7,186 rows total; `status=checked-in` → 4,391;
`status=canceled` → 1,879; `status=no-show` → 382; `status=booked` → 196;
`status=waiting-list` → 5.

## Products — how to read the catalogue

The catalogue is small and stable: one page (26 rows, `next: null`), byte-identical
across consecutive reads, and **tenant-wide** — `pos_id`, `unit`,
`point_of_sale` and `idBranch` do not change it, so it is not POS-scoped.

**The trap: the `active` field is not "sellable now".**

| | |
|---|---|
| `active` field | a manual on/off switch; **ignores** the availability window |
| `active=true` **filter** | honours `active_from` / `active_to` — this is "currently sellable" |

Proof: product **id 13** (`Soft Opening - Quick Massagem`) has `active: true` but
its window ended `2026-04-06`. The full list returns 26; `?active=true` returns
**19**. Filtering client-side on the `active` field would wrongly include it.

Verified filters: `active` (true|false) · `can_sell` (true) · `can_sell_mobile` (true).
Silently ignored: `can_sell=false`, `approval_required`, `category`, `main_category`.

**Prices:** `current_price` is the sellable price and **can differ from
`price_sales_base`** (product 12: base 80.00 → current 60.0). Compare them
numerically — `"80.0" != "80.00"` as strings, which produces false promotions.

Credits live on `current_event_credit_quantity` / `current_event_credit_validity`
(the `event_*` pair is the base config).

## Checkout vs order — the distinction that matters

```
checkout (cart)   Open        cart is open, awaiting payment   <- EPHEMERAL
                  Submitted   cart submitted                   <- persists
   └──► order (sale)          appears when the customer pays; carries the payment state
```

**A shared checkout can exist with NO order at all.** Verified on checkout 15794:
`shared_to_customer: true`, `status: "Open"`, and **no matching order** — the
link went out and nothing has been bought yet. So *link sent* ≠ *order created*,
and *order exists* ≠ *paid*.

⚠️ An earlier scan found all 73 *historical* shared checkouts carrying an order
(71 paid, 2 canceled) and I read that as "share creates the order". That was
survivorship bias — they were old and already settled. The fresh unpaid one
settles it: **the order appears when the customer completes payment.**

### Carts are "current", not created — and they rotate

There is **no create-cart endpoint**. The customer/app API client addresses a
cart as **`current`** (or `user-{id}`), so a cart is a session/POS-scoped working
object that Angulare maintains for you:

```js
// static.angulare.app/ws/v1.8.5/ws.min.js — the app's checkout service
get:                (t, e) => S.get(`/api/v1/checkouts/checkouts/${t || "current"}/`, e),
getCurrentByUserId: (t, e) => S.get(`/api/v1/checkouts/checkouts/user-${t}/`, e),
addProduct:         (t, e, n) => S.post(`.../${t}/add-product/`, e, n),
share, confirm, clear, set-pos, place-order, create-payment, coupon-code …
```

Verified live:

| Request | Result |
|---|---|
| `GET /checkouts/checkouts/user-2207/` | id **15908**, `Open`, owner 2207, `lines_info: []`, total 0 |
| `GET /checkouts/checkouts/user-2200/` | id 15811, same shape (empty) |
| `GET /checkouts/checkouts/current/` | id **15859**, owner **23**, with the `Aula Avulsa` R$80 line |

**Every member always has exactly one current cart.** Checkout 15794 was readable
in the morning and gone by the afternoon — superseded by the fresh empty 15908
for the same member (higher id, empty lines):

| Probe | Morning | Later |
|---|---|---|
| `GET /checkouts/checkouts/15794/` | 200 (status `Open`) | **404** |
| `GET /checkouts/checkouts/?user_id=2207` | count 1 | **count 0** |
| total checkouts | 3454 | **3439** (−15) |
| two `Submitted` carts | 200 | **200** (still there) |

So an **unsubmitted cart is short-lived**: it expires (the share dialog's
`expiration`, default same-day 23:59:59) and becomes unreachable — the id 404s,
`?user_id=` goes to 0, the collection total drops — while `Submitted` carts
survive. Whether the row is deleted or merely excluded from every reachable
endpoint is not determinable from outside (the list serializer omits
`is_expired`); either way the id is unusable.

**Consequences for any integration:** `ck` is a rotating pointer, not a durable
id — never store a link or a cart id, and always fetch the *current* cart at send
time.

Concretely: `angulare_checkout()` will legitimately 404 on a rotated cart, the
payment link is **inherently short-lived**, and a 404 from `/checkouts/{id}/share/`
means "that cart is gone" — not "you lack permission", which is how we found out.

Order statuses: `paid` (Pago) · `waiting_payment` (Aguardando pagamento) ·
`not_authorized` (Pagamento não autorizado) · `canceled` (Cancelado).
Checkout statuses observed: `Open`, `Submitted`.

## Known write endpoints (NOT wired into this skill)

| Method | Path | Notes |
|---|---|---|
| POST | `/api/v1/checkouts/checkouts/{id}/share/` | **wired** as `angulare_checkout_share` — sends the payment link |
| POST | `/api/v1/checkouts/checkouts/{id}/add-product/` | add a product to a cart |
| POST | `/api/v1/checkouts/checkouts/{id}/confirm/` | submit the checkout |
| POST | `/api/v1/checkouts/checkouts/{id}/clear/` | empty the cart |
| PATCH/PUT | `/api/v1/checkouts/checkouts/{id}/` | set payment method, installments… |
| PATCH | `/api/v1/events/event-books/{id}/` | edit a booking |
| POST | `/api/v1/events/event-books/{id}/cancel/` | cancel a booking — **unreachable today** (see below) |
| POST | `/api/v1/events/events/{id}/change-level/`, `/change-room/` | move a session |

### ⚠️ Correction: booking cancellation WAS possible — the id is `token`

An earlier pass through this API concluded cancellation was impossible, because
the `event-books/` list returns `id: null` on every row. **Both halves of that
were wrong**, and the correction matters:

- the list **does** carry an identifier — it is **`token`**, not `id`
- **`token` is exactly what `.../cancel/` wants**

So the blocker was a wrong field name, not a missing capability. Verified against
production: 8/8 rows in a live session roster carried a `booking_token` UUID.

**Do not confuse the two tokens on a booking row.** `token` identifies the
*booking*; `event_info.token` identifies the *class*. Cancel and reschedule take
the first; everything in the schedule endpoints takes the second.

### Booking write endpoints

```
POST /events/events/{event_token}/book/                  {"user": <uid>, "map_spot_code": "<n>"}
POST /events/event-books/{booking_token}/cancel/          {}   (optional ?timezone_from_unit=)
POST /events/events/{event_token}/add-to-waiting-list/    {"user": <uid>}
POST /events/event-books/{booking_token}/reschedule/      (body UNVERIFIED — see booking.py)
```

All four are wrapped by `tools/booking.py`. The first three were taken from
NUMA's production bot, which has run them against real members; `reschedule` was
found in the dashboard bundle but never executed, and `angulare_reschedule_booking`
says so.

### Reading bookings

```
GET /events/event-books/?user={uid}&limit=50        one member's bookings
GET /events/events/{event_token}/bookings/?limit=100 one session's roster
```

Booking row, as returned:

| field | meaning |
|---|---|
| `token` | **the booking token** — what cancel/reschedule take |
| `user` | the member id |
| `status` | `booked` · `waiting-list` · `allocated` |
| `map_spot_code` | mat/bike position, zero-padded (`"08"`) |
| `canceled_at` | set once cancelled — this, not `status`, is the cancelled flag |
| `can_cancel_until` | **the credit-refund deadline, computed server-side** |
| `event_info` | `token`, `name`, `event_date`, `event_hour`, `start_time`, `instructor_detail` |

### ⚠️ `can_cancel_until` comes back in TWO formats

Same field, two serializers — observed on the same day, same tenant:

```
GET /events/events/{token}/bookings/   ->  "2026-10-15T16:15:00"   ISO
GET /events/event-books/?user={uid}    ->  "2026-10-17 06:30"      space-separated
```

Parse defensively; do not assume `fromisoformat` will take both (it will not take
the space form before Python 3.11's relaxed parser, and neither form carries a
timezone). Treat the value as a studio-local wall clock.

Reading `can_cancel_until` is how you honour the "explain the consequence before
acting" rule without re-deriving the cancellation policy yourself.

## The "Link de Pagamento" (credit-card) link — fully decoded

A real link, captured from production (the `ec` in it has since **expired** —
`confirm-email` answers `Este código já expirou` — so it is kept here as a format
example only):

```
https://numastudios.com.br/?uid=<uid>&ck=<ck>&ec=<ec>
```

| Param | Meaning | API-readable? |
|---|---|---|
| `uid` | the **member id** | ✅ yes — `checkout.owner` |
| `ck` | the **checkout id** | ✅ yes — `checkout.id` |
| `ec` | the member's **e-mail confirmation code (OTP)** | ❌ **no** |
| `mc` | the member's **mobile confirmation code (OTP)** | ❌ no |

**All three are required.** Verified in a browser against a real shared checkout:

| URL | Checkout modal opens? |
|---|---|
| `?uid=<uid>&ck=<ck>&ec=<ec>` | ✅ opens — cart, "Aula Avulsa" ×1, R$ 80,00, customer name + CPF, "Continuar para pagamento" |
| `?uid=2207&ck=15794` (no `ec`) | ❌ nothing |
| `?ck=15794` (no `uid`) | ❌ nothing |
| `?uid=2207` (no `ck`) | ❌ nothing |

### What `ec` actually does

`ec` is **not** a checkout token — it is an e-mail OTP that authorises the
*person*. `revalidate.js` treats a URL as a verification link when
`uid && (mc || ec)`, then posts the code:

```js
// revalidate.js
verificationUrlRevalidate2: function(){ var e = c(location.search); if (e.uid && (e.mc || e.ec)) return !0 }
confirmCode: function(code, uid){
  var a = c(location.search), r = {code: code}, i = "";
  a.mc && (i = "confirmMobile");
  a.ec && (i = "confirmEmailWithoutId", r.user_id = a.uid);
  ...
}
// ws.min.js — the API client
confirmEmailWithoutId: (t, e) => S.post("/api/v1/users/users/confirm-email/", t, e)
confirmMobileWithoutId: (t, e) => S.post("/api/v1/users/users/confirm-mobile/", t, e)
```

→ `POST /api/v1/users/users/confirm-email/` with `{code: <ec>, user_id: <uid>}`.

The checkout opens only *after* that gate and a terms step (`web.js`):

```js
acceptTerms: function(accepted){
  if (!uid) return true;
  ... : "cart" === he() && accepted && (document.querySelector("ae-checkout-modal").open = true)
}
```

`he()` returns `"cart"` when the URL carries `ck`. So the link is a **compound
link: "confirm this member's e-mail (`ec`) + open this cart (`ck`)"** — which is
why the customer needs no login.

That is also why dropping `ec` breaks it: without the confirmation the flow never
reaches the terms step, so the modal never opens.

Codes are minted by the `request-email-confirmation` /
`request-mobile-confirmation` endpoints (also in `ws.min.js`) and delivered to the
customer — never returned to the caller.

### How the customer-side app consumes the params

From `static.angulare.app/web/v4.0.390/web.js`:

```js
var t = Object.fromEntries(new URLSearchParams(window.location.search)), n = {...t},
    r = window.AngularEcommerce.web.authToken.get(), i = we(n, e);
i && n.ck && (function(e){ /* strip params from the URL */ })(["ck"]);
!n.uid || n.ck || i || n.mc || n.ec || ( /* "link only for logged-out users" warning */ )
```

`ec` and `mc` are recognised alongside `uid`/`ck`; a logged-in visitor has `ck`
stripped from the address bar after it is consumed. `revalidate.js` strips
`qt`, `uid`, `mc`, `ec`, `r` once the flow completes.

### Consequence

**`ec` is not exposed by the API.** The full checkout payload for 15794 contains
no field holding that value and no 6-digit number at all (checked every key and
grepped the serialised payload). It is an OTP issued per member and delivered to
the customer, so **the link cannot be reconstructed from the API**: `uid` and
`ck` we can read, `ec` we cannot.

The remaining question is therefore narrow and cheap to settle: **what does
`POST /checkouts/{id}/share/` return?** If the response carries the URL (with
`ec`), then calling `share` once is enough — take the URL and send it over
WhatsApp, exactly like the Pix code. If it does not, we need Angulare to expose a
link-minting endpoint, or we fall back to sending the customer to the shop page.

### ⚠️ `share` works — the 403 means the CART BELONGS TO A STAFF MEMBER

**This file previously concluded that `share` was blocked by a missing
permission, and then that it was a wrong-host problem. Both were wrong.** The
endpoint is fine and needs no permission. It returns `403` for exactly one
reason: **the cart's owner is a staff account.**

Five data points, all against production:

| cart owner | `is_staff` | `POST /checkouts/checkouts/{ck}/share/` |
|---|---|---|
| uid 23 | `true` | **403** `{"detail":"Você não tem permissão para executar essa ação."}` |
| uid 21 | `true` | **403** |
| uid 25 | `true` | **403** |
| uid 2207 | `false` | 400 (missing fields) |
| uid 2246 | `false` | 400 (missing fields) |

So the 403 is a **refusal to send a payment link for a staff member's cart** —
sensible, and nothing an admin can or should "grant". The original investigation
landed on the wrong answer because every early test ran against the operator's
own cart (uid 23), which is the one case that legitimately 403s.

**Working recipe — verified end to end, `200`:**

```json
POST /api/v1/checkouts/checkouts/{ck}/share/       (either host works)
Authorization: JWT <token>      tenant: <code>

{"channels_to_send": ["email"],
 "expiration": "2026-10-17",
 "revalidate": false, "ask_password": false, "ask_card": false, "show_checkout": true}
```

```json
200 {"ok": "A comunicação será enviada em instantes!",
     "expiration": "2026-10-17T00:00:00-03:00",
     "expiration_capped": false}
```

Required fields, discovered by letting the API name them one at a time:
`expiration`, `revalidate`, `ask_password`, `ask_card`, `show_checkout`
(plus `channels_to_send`). Any of them missing gives a `400` naming that field.

Details worth knowing:

- **Both hosts serve this endpoint.** `prd.angulare.app` and the tenant's own
  `angulare.numastudios.com.br` both answer `200`. (`numa.sistemas.angulare.app`
  is not a real host — it fails TLS; it never was the API.)
- **`expiration` must be a datetime.** `YYYY-MM-DD` is accepted and normalised to
  `T00:00:00-03:00`; an integer number of days is rejected with the full format
  hint; `null` → `Este campo não pode ser nulo.`
- **`expiration_capped`** says whether the requested date was clamped. A date in
  2030 came back uncapped, so the ceiling is generous.
- **The response discriminates acceptance** (not delivery — there is no receipt):

  | Response | Meaning |
  |---|---|
  | `200 {"ok": …, "expiration": …}` | accepted — the communication is queued, delivery unconfirmed |
  | `403 {"detail":"Você não tem permissão…"}` | the cart's owner is a staff member |
  | `404 {"detail":"No Checkout matches the given query."}` | bad cart id |
  | `400 {"<field>":[…]}` | that required field is missing / malformed |

- **The side effect is checkable:** after a successful `share` the cart's
  `shared_to_customer` flips to `true` — the same acceptance read back, not a
  delivery receipt. Re-sharing an already-shared cart sends a new e-mail
  (verified 2026-10-15 on cart 16204, received alongside a recadastramento sent
  one second later). Gmail threads repeats into the earlier conversation, so
  verify by searching All Mail, not by scanning the inbox.
- `channels_to_send: []` also answers `200`, so the response alone cannot tell
  you whether an e-mail was suppressed; pass `["email"]` to have it sent.

**So every "build the link ourselves" workaround in this file is unnecessary.**
`share` sends the payment-link e-mail and reports whether it was accepted;
only the recipient's mailbox proves delivery.

### Where the Pix code actually comes from — SOLVED

The Pix value is **not** in any Angulare (`/api/v1/`) response. It comes from the
**payment gateway**, `POST https://pay.sistemas.angulare.app/api/v3/transaction/transaction/`
(the SDK's `window.AngularEcommerce.ws.angularPay2.transactions(payload)`).

Full verified flow (run end-to-end against a throwaway test member):

```
GET  /api/v1/checkouts/checkouts/user-{uid}/          -> ck
POST /api/v1/checkouts/checkouts/{ck}/add-product/    -> 200
PATCH/api/v1/checkouts/checkouts/{ck}/ {payment_method:9}
POST /api/v1/checkouts/checkouts/{ck}/create-payment/ -> 200, gives pay_key_public
POST /api/v1/checkouts/checkouts/{ck}/place-order/    -> 200, status "Submitted"
GET  /api/v1/sales/orders/                            -> status "waiting_payment"
POST {gateway}/api/v3/transaction/transaction/        -> carries the Pix payload
```

The gateway payload (reverse-engineered from `web.js`, then confirmed against the
live gateway by its own validation errors):

```json
{"pos": 1, "channel": "web", "order_number": "<order.number, NOT order.id>",
 "tenant": "numa", "capture": true, "payment_method": "pix",
 "public_key": "<pay_key_public>", "reference": <order.id>, "amount": 80.0,
 "installments": 1, "card_data": {},
 "customer": {"name", "email", "cpf", "mobile_phone", "birthdate"}}
```

Three traps the gateway itself revealed:

- `payment_method` must be the **code string** (`"pix"`), not the numeric id `9`.
  Passing `9` makes the gateway treat it as a card and fail with
  *"Não foi possível processar os dados do seu cartão."*
- `card_data` and `installments` are required **even for Pix** — pass `card_data: {}`.
- `order_number` is the order's `number` (e.g. `"2831"`), not its `id` (`3156`).
  Given a number without a `payment_id` the gateway also demands `amount`.

**The Pix fields live on the gateway response** — this is the complete schema:

```
pix_qrcode        the QR image
pix_copy_paste    the "copia e cola" string  <- what you send over WhatsApp
pix_expires_at    expiry
status / reason / error_code / block_origin
card_token / card_maskednumber / card_holdername / card_expiration /
card_flag / card_type / card_bin / token / amount / reference / order_number
```

### The gateway needs the JWT — without it you get a misleading error

The SDK sends **two** headers that are easy to miss, both set by the axios
interceptor rather than by the caller:

```js
rt.interceptors.request.use(function(t){
  return b() && (t.baseURL = d()),
         t.headers || (t.headers = {}),
         p() && (t.headers.Authorization = u()),   // <- the JWT
         t
})
// and in the method itself:
(e = e || {headers:{}}).headers.tenant = n.data.site.tenant.code;
```

So the call is `POST {angular_pay_url}/api/v3/transaction/transaction/` with
**`tenant: <code>` and `Authorization: JWT <token>` headers**.

Omitting the JWT produces a generic `status: "not-authorized"` with an empty
`error_code`, which reads like a configuration problem but is really just a
missing identity. With the JWT the gateway resolves the merchant and its error
becomes specific — which is how the acquirer was identified:

```
Problema ao decodificar resposta asaas: 404 - b''
```

**Tenant `numa` charges through Asaas.** Pix works there: of the last 80 orders,
**69 are `paid`, including Pix** (`order 3155`, `pm=pix`, `status=paid`). An
empty `angular_pay_partner_key_public` does **not** mean there is no acquirer —
the Asaas credentials live server-side and are not exposed to the frontend.

### `not_authorized` is transient — and why a fresh test member fails

`not_authorized` is a **normal, retryable** outcome here (9 of 80 orders), and
every real customer who hit it later succeeded:

```
cust 135   3130:not_authorized  3131:not_authorized  3133:paid
cust 390   3152:not_authorized  3153:paid
cust 2226  3132:not_authorized  3134:paid
cust 2200  3122:not_authorized  3123:paid
cust  24   3120:not_authorized  3121:paid
cust  23   3113:not_authorized  3141:paid          <- the director's own account
```

A member created with `quick-registration` fails **persistently** instead,
because the record is incomplete by the tenant's own rules:

```
cpf_strategy         = "required-unique"
user_required_fields = ["first_name","last_name","date_of_birth","gender",
                        "mobile_phone","zip_code"]
```

A quick-registered member has none of the last four, and Angulare says so itself
— the record comes back with
`fields_to_update: ["mobile_phone","date_of_birth","zip_code"]`.

For Pix that is fatal twice over: without a CPF the gateway refuses outright
(`CPF é obrigatório para pagamento via Pix`), and supplying one in the request
only moves the failure to Asaas, which 404s because no Asaas customer exists for
that CPF — a real member has one because they signed up through the normal flow.
So Pix needs **both** a CPF on the member record **and** the matching Asaas
customer; a hand-made test member has neither.

**So a hand-made test member cannot exercise Pix**, and completing its fields is
not enough on its own — the Asaas customer is created by the normal signup flow.
**Credit card has no such requirement**, so it is the path to test against a
throwaway member; see the next section for its own two constraints (R$100
minimum, and a real card).

### CPF is genuinely unique — you cannot borrow someone else's

`required-unique` is enforced, not decorative. A full sweep of the tenant found
**2172 members with a CPF and zero duplicates**, and the API rejects a collision
outright rather than silently ignoring it:

```
PATCH /api/v1/users/users/{id}/ {"cpf": "<one already in use>"}
-> 400 {"cpf": ["CPF já cadastrado"]}
```

So a throwaway test member needs a CPF that is **not already among the 2172** —
and it must also be **format-valid**, since the gateway rejects a bad check digit
before it ever reaches Asaas. There is no way to reuse the operator's own CPF.

### Pix and credit card fail for DIFFERENT reasons

Measured against the live gateway, with the JWT and `tenant` headers set, the
two methods do not share a blocker. **Credit card never asks for a CPF.**

```
Pix   cpf=""             -> {'cpf': 'CPF é obrigatório para pagamento via Pix.
                              Acesse o minha-conta para cadastrar seu CPF'}
Pix   cpf="<any>"        -> Problema ao decodificar resposta asaas: 404 - b''
CC    cpf=""             -> (no CPF complaint at any amount)
```

**Pix needs two things the test member lacks:** a CPF on the member record *and*
an Asaas customer for that CPF (the 404 is Asaas failing to find one — a real
member has one because they signed up normally).

**Credit card needs neither.** It walks straight past the customer block into
card validation:

| `amount` | credit-card result |
|---|---|
| 1 / 5 / 10 | `payments[0].split[1].amount: must be greater than or equal to 0` |
| 50 / 80 | `invalid_parameter \| amount \| valor não permitido` |
| **100 / 200 / 1000** | **`Número do cartão inválido. Oriente o usuário a contatar o banco/emissor`** |

So there is a **minimum of R$100 for credit card** — below it the gateway says
the amount is not allowed — and above it the only remaining blocker is the card
itself. `4111111111111111` is refused, so a production card is required to finish
the path; the flow can otherwise be exercised end-to-end.

Two more traps this exposed:

- The valid `payment_method` for cards is **`"creditcard"`** (or `"credit"`).
  The frontend's `"<brand>card"` form (`"visacard"`, `"mastercard"`, …) is
  **rejected** by the gateway with `Método de pagamento inválido`.
- The tenant has **payment splits** configured — small amounts fail inside
  `payments[0].split[1]`, not on the top-level amount.

### Can the link be minted without `share`? No — tested

Since `share` is permission-blocked, two alternative routes were tried and both
fail. Recorded here so nobody re-treads them.

**1. The gateway's `payment-link` channel is a provenance marker, not a
generator.** `ct()` sets `channel = "payment-link"` when `shared_to_customer` is
true, but posting that channel to the gateway still demands card data:

```
channel="payment-link", card_data={}
-> "Não foi possível processar os dados do seu cartão"
```

**2. `revalidate-url` returns a signed URL — but it is not the checkout link.**
This endpoint *does* hand back a token (worth knowing; the API is not uniformly
secretive):

```
GET /api/v1/users/users/{id}/revalidate-url/
-> {"url": "https://prd.app/?revalidated-user=true&user_id=<member_id>&revalidate_token=<token>"}
```

`revalidate.js` shows why that token cannot stand in for `ec` — it takes a
separate branch (`getUserByRevalidateInfo()`) that identifies the person but
never opens a cart. Verified in a browser against a live cart, all four
combinations rendering nothing:

| URL | Checkout opens? |
|---|---|
| `?revalidated-user=true&user_id=2246&revalidate_token=…&ck=15915` | ❌ |
| `?ck=15915` | ❌ |
| `?uid=2246&ck=15915` (no `ec`) | ❌ |
| `?revalidated-user=true&user_id=2246&revalidate_token=…` | ❌ |

So the link still needs `uid` + `ck` + `ec`, and `ec` is **emailed, never
returned** — `POST /api/v1/users/users/request-email-confirmation/` answers
`{"ok": true}` and nothing more.

**Side finding:** the `revalidate-url` domain comes back as `prd.app`, which is
not the tenant's domain (`numastudios.com.br`) — the tenant's link-domain setting
looks like an unset placeholder.

### "Can we at least automate the e-mail?" — only the wrong one

`POST /api/v1/users/users/{id}/send-revalidation-link/` works and is not
permission-blocked:

```
POST /api/v1/users/users/2246/send-revalidation-link/
-> 200 {"ok": "A comunicação será enviada em instantes!"}
```

But it does **not** send the payment link, for three reasons:

1. **It carries the revalidation link, not the checkout link.** The URL it mints
   is `?revalidated-user=true&user_id=…&revalidate_token=…`, and that link was
   browser-verified against a live cart: the checkout modal stays at **height 0**
   and no cart content renders.
2. **It answers `200 {"ok": …}` for *any* body — including `{}`.** Unknown fields
   (`checkout`, `ck`, `checkout_id`) are accepted and silently ignored, so the
   response tells you nothing about what was actually sent.
3. **The messaging module is not on this host.** `POST /api/v1/communication/messages/`
   and `GET /api/v1/communication/contacts/` both 404 here — the SDK passes an
   explicit *host* argument to `sendMessage(host, body)`, so that module lives on
   a different base URL. There is no way to send a custom message, or to read the
   message log to verify what went out.

So triggering *a* communication is available; delivering *the payment link* is
not — that e-mail is a data-update notice, not a cart link. But it turns out to
carry `ec`, which changes the picture; see the next section.

### ⚠️ `send-revalidation-link` leaks `ec` — the missing ingredient

The message that endpoint sends is a **"Link de recadastramento"** (registration
update), and its body carries a URL like:

```
https://numastudios.com.br/?uid=<member_id>&r=1&ec=<ec>
```

Note what is *not* there: no `ck`. So the e-mail is **not** a payment link and
cannot take anyone to a cart — but it **does hand over `ec`**, the value the API
never returns. And `ec` is both **valid** and **reusable**:

```
POST /api/v1/users/users/confirm-email/ {"code":"<ec>","user_id":<member_id>}
-> 200 {"id":2246,"jwt":"eyJhbGciOiJSUzI1NiIs…"}
```

It authenticates the member outright. Across five e-mails sent inside 15 minutes
the value was identical — but **it is an OTP with a TTL, not a permanent value**;
see the correction below. (The value authenticates the member, so it is treated
as a credential here and not reproduced.)

**`shared_to_customer` is also not protected.** `share` is permission-gated, but
the flag it sets is a plain writable field:

```
PATCH /api/v1/checkouts/checkouts/{ck}/ {"shared_to_customer": true}  -> 200
```

So both ingredients of the link (`ec`, and the "shared" flag) can be obtained
without the `share` permission — the permission gates the *endpoint*, not the
*state*.

### ⚠️ `pay_key_public` is NOT a checkout route — do not build a link from it

The checkout object carries `pay_key_public` (a UUID). It is tempting to read that
as "the checkout's public URL key" and mint
`https://numastudios.com.br/#/checkout/{pay_key_public}`. **That URL opens
nothing — verified 2026-10-16, twice:**

| URL | Result |
|---|---|
| `https://numastudios.com.br/#/checkout/7913cfd4-…` | renders the **home page** |
| `https://numastudios.com.br/checkout/7913cfd4-…` | **404** |

`pay_key_public` is the **payment gateway's public key**, handed to the
card-tokenisation SDK — not a route id. From the storefront bundle
(`static.angulare.app/web/v4.0.394/web.js`) it appears only in the payment
payload, next to `installments` and the customer block:

```js
public_key: a.pay_key_public,
installments: a.installments_info || a.installments,
reference: i.id,
customer: { name, email, cpf, mobile_phone, … }
```

and is read as `settings.payments.fixed_pay_customer_public_key ||
currentCheckout.pay_key_public`.

The storefront does not route on a path or hash segment at all. It reads **query
parameters** off `window.location.search` — `uid`, `ck`, `ec` — and loads the cart
by `ck` (the plain checkout id):

```js
var t = Object.fromEntries(new URLSearchParams(window.location.search));
… r.ck && !n.placeOrder ? r.ck : null   →  M.checkout.get(i)
```

So the only link shape that can open a cart is the one the e-mail already uses
(`?uid=…&ck=…&ec=…`), and `ec` is still the emailed OTP. **The bot cannot mint a
payment link from the checkout object; either keep the Angulare `/share/` e-mail
as the delivery path, or ask Angulare for a link-minting endpoint.**

### 🛑 Two hand-built link attempts, two failures — do not attempt a third

Both attempts assumed the checkout object carries something that can be turned
into a cart URL. It does not. The working link needs `ec`, which exists only in
the e-mail and expires.

| Attempt | Field used | Built URL | Result |
|---|---|---|---|
| #1 (original NUMA bot code) | `revalidate-url` → `url` | `?revalidated-user=true&user_id=…&revalidate_token=…` | ❌ renders nothing (browser-verified); domain was the unset `prd.app` placeholder |
| #2 (added 2026-10-15) | `checkout.pay_key_public` | `#/checkout/{pay_key_public}` | ❌ renders the home page (`/checkout/{…}` → 404) |
| ✅ the only working form | — | `?uid={owner}&ck={checkout_id}&ec={from the e-mail}` | ✅ cart renders |

Attempt #1 was removed by the share patch (which also swapped the wrong
`send-revalidation-link` e-mail for `/share/`); attempt #2 was added afterwards
and is the live bug. **`link_pagamento` must stay `None`** — the bot cannot mint
a working payment link, and it must not send a hand-built one to a customer.
Note the consumer side already sends whatever is truthy
(`bot_webhook.py`: *if link and "numastudios.com.br/planos" not in link →
`send_zapi_text(phone, link)`*), so a wrong value here reaches real customers.

### ✅ Verified end to end, 2026-10-16 — the e-mail link does open the cart

With a **complete** member (CPF + mobile + zip + address) the real e-mail link
renders the checkout:

```
https://numastudios.com.br/?uid=2246&ck=16204&ec=<from the e-mail>
-> "Carrinho" modal: Seus Dados (name + CPF), the product line (R$ 80 -> R$ 60),
   coupon field, "Continuar para pagamento"
```

Two corrections to what this file previously implied:

1. **The old "renders nothing" result was the incomplete member, not the link.**
   Confirmed: the same member, once completed, gets a working cart. A complete
   profile is a hard prerequisite (`require_cpf_on_purchase` / `mobile` /
   `address` in `GET /api/v1/core/settings/`).
2. **`ec` is time-limited, so the link is effectively one-shot.** The same `ec`
   that authenticated and loaded the cart was rejected minutes later on a fresh
   load (`web-authorization` was not set and no cart appeared). Treat any minted
   link as short-lived; a customer who does not finish needs a new e-mail.

This is also why the bot must not try to construct the link itself — it cannot
know `ec`, and even a valid one expires.

### Why the reconstructed link still renders nothing

With `uid` + `ck` + `ec` + `shared_to_customer` all in place the page
authenticates (it stores `web-authorization`) but the checkout never renders. The
first API call explains it — the tenant demands a complete member at purchase
time:

```json
GET /api/v1/core/settings/  ->  "checkouts": {
  "require_cpf_on_purchase": true,
  "require_mobile_on_purchase": true,
  "require_address_on_purchase": true,
  "minimum_checkout_total": "0.00"
}
```

The throwaway member has none of the three, so the customer-side checkout refuses
to proceed. **A complete member is a prerequisite on both sides** — the gateway
wants a CPF for Pix, and the storefront wants CPF + mobile + address before it
will even show a cart. Because of this, the "nothing renders" result below is a
property of the *member*, not of the link — see the note at the end of this file.

To read `ec` programmatically you would still have to read the member's inbox —
the API exposes it in the *message*, never in a response body.

### Triggering that e-mail from code — and how to tell it worked

It is a plain API call, no browser interaction:

```bash
POST /api/v1/users/users/{id}/send-revalidation-link/
     {"revalidate": true, "message_method": ["email"]}
-> 200 {"ok": "A comunicação será enviada em instantes!"}
```

**The response is a usable success signal** — it discriminates, unlike a bare
`{"ok": …}`:

| Response | Meaning |
|---|---|
| `200 {"ok": …}` | member found, communication **queued** |
| `404 {"detail":"No BodyUser matches the given query."}` | no such member → **nothing sent** |
| `400 {"non_field_errors":["WhatsApp não está habilitado"]}` | channel not enabled for this tenant → **nothing sent** |
| `400 {"message_method":{"0":["… não é um escolha válido."]}}` | bad enum value → **nothing sent** |

`message_method` is a validated enum with exactly two valid values —
**`"email"`** and **`"whatsapp"`**. WhatsApp is *not* enabled on this tenant, so
it fails with the distinct `non_field_errors` above. Everything else (`sms`,
`mobile`, `push`, …) is rejected as an invalid choice.

Note what this signal is and is not: `200` means the message was **accepted for
dispatch**, not that it was delivered. There is no delivery/bounce receipt and no
reachable message log on this host, so a `200` plus the member's own confirmation
is the best available proof.

Unknown extra fields are ignored silently — `{"checkout": …}`, `{"ck": …}` all
return `200` and change nothing, so this endpoint cannot be steered to a
particular cart.

**Verified in the inbox:** the template never carries a cart. The message was
re-sent with the member's cart already at `shared_to_customer: true`, and the URL
was byte-for-byte the same shape as before:

```
https://numastudios.com.br/?uid=<member_id>&r=1&ec=<ec>      (no `ck`, ever)
```

So this e-mail is a registration-update notice and **cannot** be turned into a
payment link. The only Angulare-side sender of a cart link is `share`, which
requires the permission this account lacks.

### Everything downstream is gated on the member being complete

Note a confound in the link tests above: `require_cpf_on_purchase` is `true`, so
the storefront refuses to render a cart for an incomplete member **no matter
which link is used**. Every "nothing opens" result recorded in this file was
produced with a member that has no CPF, no mobile and no address — so those
results are **inconclusive**, not proof that the link is wrong.

Before re-testing any link shape, complete the member. Then these two are worth
re-running, in this order:

1. `?uid={uid}&ck={ck}&ec={ec}` — `ec` is known to authenticate (it mints a JWT).
2. `?revalidated-user=true&user_id={uid}&revalidate_token={token}&ck={ck}` —
   `revalidate_token` comes from `GET /users/{id}/revalidate-url/` and is the
   only token the **API itself returns**, so if it works the whole flow needs no
   inbox access at all.

## The link is delivered BY ANGULARE — verified end to end

A real `share` call produced this e-mail (subject **"Link para pagamento do seu
pedido"**, a different template from the recadastramento notice):

```
Olá, Sc!
Se estiver procurando o link para pagamento, basta clicar aqui para concluir sua compra.
Veja o que está em seu carrinho:
- Aula Avulsa x 1
```

and the link inside it carries **all three parameters**:

```
https://numastudios.com.br/?uid=<uid>&ck=<ck>&ec=<ec>
```

**So nothing has to be reconstructed.** `ec` — the value no API response ever
returns — is delivered by `share` itself, inside the payment e-mail. That closes
the whole question: call `share`, Angulare sends the link, the customer pays.

### The link opens the checkout — confirmed visually

Loading that link in a browser (clean storage) produced the full checkout chain:

```
200 POST users/users/confirm-email/     -> {"id":…,"jwt":"…"}   (the `ec` is accepted)
200 POST jwt/token-refresh/
200 GET  users/users/current/
200 GET  events/credit-packages/?user_id=…
204      users/terms/?required_to_buy=true&accepted=false&active=true
```

and the modal rendered, on step 2 of 3:

```
Precisamos confirmar alguns dados antes de continuar
Nome* [Sc]  Sobrenome* [Aladdin]  Nascimento* [ ]  CPF* [ ]
Gênero* [Não informar]  Celular* [+55 ____]
```

Those required fields are exactly the ones the tenant enforces
(`require_cpf_on_purchase`, `require_mobile_on_purchase`,
`require_address_on_purchase`), which is why an incomplete test member lands here
rather than on the payment step. **It is a data-collection step, not a failure.**

### ⚠️ Correction: the earlier "nothing renders" results were a PROBE BUG

Every earlier note in this file saying the checkout "renders nothing" was wrong.
The check used `document.querySelector("ae-checkout-modal").getBoundingClientRect().height`,
which is **always 0** — `ae-checkout-modal` is a custom-element host and the
content lives in a child:

```
ae-checkout-modal                    h=0     <- what was being measured
  └─ div.modal-backdrop.ae-checkout-modal   h=1000  <- the real content
       └─ div.modal-body.modal-body-checkout  h=806
```

Measuring the child instead shows the modal is fully rendered. So route B was
never blocked by rendering either — the link works, and the only thing that was
ever missing was the correct measurement.

## Can a staff account (e.g. the operator's own) be used as the test vehicle? No

Worth recording, because it is the obvious shortcut and it does not work. Two
independent blockers:

**1. `revalidate-url` is permission-gated for staff.** The revalidation link is a
*login credential*, so Angulare refuses to mint one for a staff member:

```
GET /api/v1/users/users/23/revalidate-url/    -> 403  {"detail":"Você não tem permissão…"}   (is_staff: true)
GET /api/v1/users/users/2246/revalidate-url/  -> 200  {"url":"https://prd.app/?revalidated-user=true&user_id=2246&revalidate_token=…"}
```

That is sound security design, not a bug: otherwise anyone able to call this
endpoint could mint themselves a director login.

**2. `ec` only ever exists in the e-mail**, and the e-mail goes to that member's
inbox. For the operator's account that is a real person's mailbox, so the value
is unreachable from code. Triggering the send is possible; reading the result is
not.

### `revalidate_token` is DEAD CODE — `ec` is mandatory

The API does hand a `revalidate_token` to non-staff members, which looked like an
inbox-free route. **It is unreachable.** `revalidate.js` gates on the *same
predicate twice*, so the second branch can never run:

```js
beforeMount: function(){
  var t = c(window.location.search);
  this.verificationUrlRevalidate2()          // outer gate: requires uid && (mc || ec)
    ? ( …, Promise.resolve(!0).then(function(n){
          return n ? ( …,
            e.verificationUrlRevalidate2()   // inner call: same function, same input
              ? void e.confirmCode(t.mc || t.ec, t.uid)      // <- always taken
              : ( /* revalidated-user / revalidate_token */ ) // <- unreachable
          ) : … }) )
    : …
}
```

Both calls read `window.location.search`, so if the outer test passed the inner
one passes too — the `revalidated-user` + `revalidate_token` branch is **dead
code**. Confirmed empirically: a freshly minted token, in a browser with storage
cleared, produced no `revalidate-info` call at all — only `/core/settings/`.

**So the link is `uid` + `ck` + (`ec` or `mc`), with no alternative.** `mc` is the
mobile OTP, delivered by SMS — the same inbox problem.

### `ec` is an OTP with a TTL — it does expire

Correction to an earlier note here: `ec` is *not* a permanent per-member value.
It stays constant across repeated sends inside its validity window, which is why
five e-mails in 15 minutes all carried the same code — but an older captured
value is dead:

```
POST /api/v1/users/users/confirm-email/ {"code":"<ec from a much older e-mail>","user_id":2207}
-> 400 {"code": ["Este código já expirou. Solicite um novo código para validação da sua conta"]}
```

So even a leaked link goes stale, and there is no way to mint a fresh one without
the member's inbox.

**Net — the whole picture:** every inbox-free route is closed.

| Route | Status |
|---|---|
| **`share`** | ✅ **works — this is the answer** |
| `share` on a staff member's cart | ❌ 403 — by design, not a permission to grant |
| `ec` in a link we build | ❌ only in the member's inbox, and it expires |
| `revalidate_token` from `GET /users/{id}/revalidate-url/` | ❌ dead code |
| operator / staff account as the vehicle | ❌ `revalidate-url` is 403 for staff by design |

**Everything below this line is superseded** — the workarounds were only ever
needed because `share` was being tested against the operator's own (staff) cart.

## Gotchas

- `Authorization: JWT`, never `Bearer`. The error message for getting this wrong
  is `Login expirado!`, which sends you hunting for an expiry bug that isn't there.
- The `tenant` header is required on **every** call, not just login.
- Unsupported query params are ignored → verify filters by watching `count`.
- No `ordering` / `search` on the attendance report.
- Multi-tenant by host; a tenant is only reachable on its own deployment.
- The customer-facing widgets are version-pinned to `latest`
  (`catalogue-latest.js`, `angulareVersion: 'latest-v4'`), so Angulare can change
  customer-page behaviour without notice. Prefer the versioned API
  (`/api/v1/`, `/api/v3/`) over anything that depends on the customer page.
