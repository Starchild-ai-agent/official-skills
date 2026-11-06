# Angulare — integration dossier

**Status: ✅ SKILL SHIPPED** — `angulare/` (25 functions, v1.0.0), built on the
findings below and exercised live against production.
Auth + reads verified 2026-10-10 with a real account provided by Leonardo
(`director`, tenant `numa`). **No write operation was performed.**

> The skill lives in `angulare/` at the repo root: `SKILL.md`, `client.py`,
> six modules under `tools/`, and `references/api-reference.md`. This file is
> the research dossier behind it.

> Naming: the vendor is **Angular e-Commerce LTDA** (brand "**Angular**", domain
> `angulare.com`, CNPJ 08.886.686/0001-71). It is **not** `angulare.com.br` —
> that is an unrelated healthtech holding. Search engines conflate "Angular" with
> the JS framework, which is how the name got lost.

## 1. What it is

| Item | Value |
|---|---|
| Products | **Angular Reservas** (bookings/agenda/members) + **Angular Pay** (payments/subscriptions/finance) |
| Scope | e-commerce + reservas + financeiro + redes/franchise; spot-map booking, waitlist, recurring bookings, check-in via reception / totem / app / turnstile |
| Reference customers | Velocity and the other Smartfit boutique studios; Vidya, Aera Pilates, Race Bootcamp, Spincycle, Gangga, The Corner, The Beat, DowntoFight, One2One |
| Aggregators | Wellhub, TotalPass, ClassPass, plus Spivi, Selfloops, Mywellness, OMIE, RD Station, WeHelp, Integra Fácil, Zoom, WhatsApp |

## 2. Hosts (all verified)

| Host | Role |
|---|---|
| `https://prd.angulare.app` | **the API** — everything below lives here |
| `https://reservas.angulare.app` | manager dashboard SPA ("Angulare-Dashboard Reservas", Vue CLI) |
| `https://crm.angulare.app` | SSO login page (`/api/login/`) + Django admin (`/admin/`) |
| `https://static.angulare.app` | static assets (`/crm/login/…`) |
| `https://prd.europa.angulare.app` | regional API (Europe) |
| `https://europa.angularesmart.com`, `https://brasil.angularesmart.com` | **separate "Angular Smart" product line** — its own tenant registry |

The login page queries all three registries to assemble the tenant list.

## 3. Authentication — the exact contract

Read out of the dashboard's `app.js` and then confirmed live:

```js
// token acquisition  (app.js signIn)
C.post(a.domain + "/api/v1/jwt/token-auth/",
       { email: a.email, password: a.password },
       { headers: { tenant: a.tenant, "content-Type": "application/json" } })

// request interceptor — EVERY call carries both headers
if (hasAuthToken()) e.headers.common.Authorization = getAuthToken();  // "JWT " + token
if (getWithTenant()) e.headers.common.tenant = getWithTenant();
```

### The three steps

1. **Find the tenant** (public, no auth):
   ```
   GET /api/v1/users/users/check-tenant/?email=<email>&is_staff=true
   -> {"tenants_allowed":[{"tenant_code":"numa","tenant_name":"numa","tenant_logo":""}],
       "tenants_blocked":[]}
   ```

2. **Get a JWT**:
   ```
   POST /api/v1/jwt/token-auth/
   headers: tenant: numa, Content-Type: application/json
   body:    {"email":"…","password":"…"}
   -> 200 {"token":"<JWT>","refresh":"<JWT>"}      # TTL ~10 days (exp - iat = 864000s)
   ```

3. **Call the API** with **both** headers:
   ```
   Authorization: JWT <token>        # NOT "Bearer" — see gotcha below
   tenant: numa
   ```

Refresh: `POST /api/v1/jwt/token-refresh/` with **form-encoded** `refresh_token=…`.

### ⚠️ The two gotchas that produce the exact symptoms we saw

| What you send | What you get |
|---|---|
| `Authorization: Bearer <token>` + `tenant` | `401 {"detail":"Login expirado!"}` |
| `Authorization: JWT <token>` **without** `tenant` | `401 {"detail":"Email não encontrado"}` |
| `Authorization: JWT <token>` + `tenant` | ✅ `200` |
| `Authorization: Bearer <garbage>` | `500` (Angulare-side bug — should be 401) |
| no auth | `401 WWW-Authenticate: JWT realm="api"` |

The panel API's Basic scheme (`Basic user:pass`) exists but rejects these
credentials — it is not the integration path.

## 4. The `count: 0` mystery — solved

The team's path **works**:

```
GET /api/v1/events/events/{session_token}/bookings/   -> 200, count=23 (real session)
```

With correct credentials it returns the full roster. So `count: 0` was **never a
database-permission problem**. Two causes, both now identified:

1. **Wrong auth scheme / missing tenant header** — `Bearer` or no `tenant` header
   cannot resolve the caller, and a scoped-but-empty queryset returns
   `200 + count: 0` (permission failures return 401/403, never 200+count:0).
2. **Wrong surface** — if an *Open API Key* is used on `/api/v1/…`, the API
   answers explicitly: `403 {"code":"open_api_key_scope","message":"Chaves de API
   Open só podem ser usadas em URLs sob /api/open/…"}`.

## 5. Attendance and check-in — where the data actually is

### The one endpoint you want

```
GET /api/v1/events/reports/event-books/
    ?status=checked-in | canceled | no-show | booked | waiting-list | late-canceled
    &user_id=<id>            # one member's history
    &event_token=<uuid>      # one class session's full roster
    &page= &page_size=
```

Verified live: `event_token=<session>` → `count=23`, statuses
`{checked-in: 13, canceled: 9, late-canceled: 1}`.

**Row fields that matter for the post-class follow-up:**

| Field | Meaning |
|---|---|
| `checkedin_at` | when the member checked in — **the trigger signal** |
| `checkedout_at`, `checkedout_reason` | check-out |
| `noshow_at` | marked as no-show |
| **`is_first_activity_checkin`** | **true = this was their first class of that activity** (verified: 23/100 sampled checked-in rows) |
| `checkin_number`, `checkin_activity_number`, `checkin_consecutive_weeks`, `checkin_instructor_number`, `checkin_unit_number` | visit counters / streaks |
| `event_time`, `end_time`, `event_id`, `event_info` | `event_info` carries `{name, token, event_date, event_hour, duration_time, event_type, map, max_books_per_user}` — **so one query gives you class end time without a second call** |
| `activity_info`, `instructor_info`, `room_…` | class context |
| `booking_source` | `angulare-mobile` / `angulare-desktop` / aggregators |
| `consumption_status`, `credits_spended`, `is_unpaid`, `income`, `plans_used` | billing side |
| `crm_case_token`, `crm_case_stage` | built-in CRM hook |

**`status` enum observed:** `checked-in`, `booked`, `waiting-list`, `canceled`,
`no-show`, `late-canceled`.

### Aggregator (TotalPass / Wellhub) check-ins

```
GET /api/v1/events/external-checkins/?date=YYYY-MM-DD     # `date` is the working filter
```

996 records; `checkin_type` ∈ {`totalpass`, `gympass`}; `status` ∈
{`checked-in`, `book-canceled`}; fields include `user_token`, `pass_type_name`,
`transaction_token`, `booking_event`, `last_error`.

⚠️ `checkin_type`, `status`, `created_at__date` and `user_token` are **silently
ignored** as filters; only `date` worked.

## 6. Verified read surface (all 200, live)

| Endpoint | Result |
|---|---|
| `/api/v1/users/users/` | count=2203 members |
| `/api/v1/events/events/` | count=465 sessions |
| `/api/v1/events/schedule/` | count=444 |
| `/api/v1/events/event-books/` | count=7186 bookings |
| `/api/v1/events/reports/event-books/` | count=7186 (500/page) |
| `/api/v1/events/event-books/book-stats-by-instructor/` | count=10 — `{books, cancels, checkins, late_cancels, no_shows}` |
| `/api/v1/events/external-checkins/` | count=996 |
| `/api/v1/events/units/` `/activities/` `/rooms/` `/locations/` `/instructors/` | 1 / 5 / 1 / 1 / 13 |
| `/api/v1/events/credit-packages/` | count=3012 |
| `/api/v1/events/gympass-plans/` | count=1 |
| `/api/v1/subscriptions/user-subscriptions/` | count=124 |
| `/api/v1/products/products/` | count=26 |
| `/api/v1/sales/orders/` | count=3143 |
| `/api/v1/events/useraccess/` `/event-tickets/` `/performances/performances/` | 0 |
| `/api/v1/core/settings/` | tenant + feature config |

The full frontend-derived inventory is **132 paths** across
`events/`, `users/`, `checkouts/`, `sales/`, `subscriptions/`, `products/`,
`payments/`, `loyalties/`, `cms/`, `communication/`, `core/`, `jwt/` — extract
from `reservas.angulare.app/js/*.js` if you need the rest.

## 7. Gotchas

- **Unsupported query params are silently ignored** — a wrong filter name returns
  the *full* count, not an error. Always sanity-check that a filter changed the
  count before trusting it.
- `ordering`, `search`, `q` are **not** supported on the report endpoint.
- `Authorization: Bearer` ≠ `Authorization: JWT`. Easy to get wrong, and the
  error message (`Login expirado!`) misleads.
- `event_time` is class **start**; the row's own `end_time` was null in samples —
  compute the end from `event_info.duration_time`.
- There is a `POST /api/v1/users/users/login/` and a legacy Django SSO at
  `crm.angulare.app/api/login/` (session cookie, 3 fields: username/password/
  **tenant**). The SPA does **not** use either — it uses the JWT endpoint above.
- Multi-region: a tenant lives in exactly one registry (`prd.angulare.app`,
  `prd.europa.angulare.app`, `europa.angularesmart.com`, `brasil.angularesmart.com`).
  `check-tenant` is the only reliable way to find which.

## 8. The 2-hour post-first-class follow-up — now buildable

1. Poll `GET /api/v1/events/reports/event-books/?status=checked-in&page_size=100`
   (or per session with `event_token`).
2. Keep rows where `is_first_activity_checkin = true`.
3. Class end = `event_time + event_info.duration_time`.
4. Schedule the message at **end + 2h**; use `noshow_at`/`status` only to suppress.

No vendor change request needed — the attendance signal is already in the API.

## 9. Shape of the `angulare` skill

| Function | Purpose |
|---|---|
| `angulare_auth()` | check-tenant → token-auth → cache the JWT (with refresh) |
| `angulare_sessions(date)` | sessions in a window (from `events/events/`) |
| `angulare_session_roster(event_token)` | one class's bookings + statuses |
| `angulare_attendance(status=None, user_id=None, event_token=None)` | the report endpoint |
| `angulare_first_checkins(since)` | `is_first_activity_checkin=true` rows — the follow-up feed |
| `angulare_external_checkins(date)` | TotalPass / Wellhub check-ins |
| `angulare_member(query)` | member lookup (`users/users/`) |
| `angulare_stats_by_instructor()` | checkins / no_shows aggregates |

Auth headers: `Authorization: JWT <token>` + `tenant: <code>` on every call.

## 10. Checkout & the "Link de Pagamento" (credit-card) flow

**Scope: yes — this is Angulare functionality, so it belongs to the `angulare`
skill, not to a payments connector.** The link is produced by Angulare's
checkout (PDV), not by the gateway.

### What the frontend proves

- "Link de pagamento" is **not a payment method** — it is absent from
  `GET /api/v1/payments/payment-methods/` (which returns `creditcard`,
  `creditcard-pos`, `debitcard-pos`, `cash`, `other`, `pix`, `pix-presencial`).
  In the PDV it is a pseudo-method code `send-cart`, rendered only when the
  tenant setting **`settings.checkouts.allow_cart_sharing`** is true
  (this tenant: `true`).
- Clicking it opens `SmsModalCarrinho` ("Enviar carrinho de pagamento online")
  with: channel checkboxes (`sms`, `email`), a start time and an **expiration**
  (defaults to today 23:59:59), plus `revalidate`, `ask_password`, `ask_card`,
  `show_checkout`.
- Confirming calls:

```
POST /api/v1/checkouts/checkouts/{checkout_id}/share/
{
  "channels_to_send": ["email", "sms"],     # lowercased, punctuation stripped
  "expiration": "YYYY-MM-DD HH:mm:ss",
  "revalidate": bool, "ask_password": bool,
  "ask_card": bool, "show_checkout": bool
}
```

- **The dashboard ignores the response** — it only shows a success toast. So the
  panel's flow *sends* the link; it does not *display* or return it.

### Why credit card is harder than Pix

| | Pix | Credit-card link |
|---|---|---|
| Artifact | a Pix code on an existing checkout | a **cart-sharing** action |
| How Starchild gets it | read from the Angular Pay gateway | not readable today |
| API shape | read | **write** (`POST …/share/`) that triggers delivery |

### Related endpoints (same resource)

`GET|PUT|PATCH /api/v1/checkouts/checkouts/{id}/`,
`POST /api/v1/checkouts/checkouts/{id}/add-product/`,
`POST …/confirm/`, `POST …/clear/`, `GET …/user-{id}/`,
`GET /api/v1/checkouts/checkout-lines/`.

Readable checkout state: `status`, `channel`, **`shared_to_customer`**,
**`should_deliver`**, `pay_key_public`, `payment_method`, `total_*`,
`installments_list`, `is_subscription`, `pos_id`.

Payment gateway: `settings.payments.angular_pay_url` =
`https://pay.sistemas.angulare.app` (an API-only host; 404s on `/`).
`angular_pay_version` = `v3`. Card tokenization goes to
`{angular_pay_url}/api/v3/transaction/card/tokenizer/` with header
`tenant: <code>`; charges to `{angular_pay_url}/api/v3/transaction/transaction/`.

### 🔑 The link, decoded (Leon forwarded a real one, 2026-10-10)

```
https://numastudios.com.br/?uid=2207&ck=15794&ec=876422
```

| Param | Meaning | API-readable? |
|---|---|---|
| `uid` | member id | ✅ `checkout.owner` (2207 = José Garcia) |
| `ck` | **checkout id** — my earlier guess was right | ✅ `checkout.id` |
| `ec` | the member's **e-mail confirmation code (OTP)** | ❌ **not in the API** |
| `mc` | the member's **mobile confirmation code (OTP)** | ❌ not in the API |

**What `ec` is** (from `revalidate.js` + `ws.min.js`): not a checkout token, but
an OTP that authorises the *person*. The page treats `uid && (mc || ec)` as a
verification link and posts the code to
**`POST /api/v1/users/users/confirm-email/`** with `{code: <ec>, user_id: <uid>}`
(`confirmEmailWithoutId`; `mc` does the same via `confirm-mobile/`). Only after
that gate plus a terms step does the checkout modal open — `acceptTerms()` does
`"cart" === he() && accepted && (ae-checkout-modal.open = true)`, and `he()`
returns `"cart"` precisely because the URL carries `ck`.

So the link is a **compound link: "confirm this member's e-mail (`ec`) + open
this cart (`ck`)"** — which is why the customer needs no login, and why dropping
`ec` leaves the modal shut.

`checkout-modal.js` reads only `ck` (`ws.checkout.get(n.ck)`), and `web.js`
recognises `uid` / `ck` / `ec` / `mc` as link params (a logged-in visitor gets
`ck` stripped from the address bar after use).

**Browser-verified — all three are required:**

| URL | Modal opens? |
|---|---|
| `?uid=2207&ck=15794&ec=876422` | ✅ cart renders: "Aula Avulsa" ×1, R$ 80,00, customer name + CPF, "Continuar para pagamento" |
| `?uid=2207&ck=15794` | ❌ |
| `?ck=15794` | ❌ |
| `?uid=2207` | ❌ |

**`ec` is not exposed anywhere in the API.** The full checkout payload for 15794
has no such field and contains no 6-digit number at all. It is minted at share
time and delivered only inside the e-mail/SMS.

⇒ **The link cannot be reconstructed from the API.** `uid` and `ck` we can read;
`ec` we cannot.

### What we still need (now a single, narrow question)

The URL pattern is solved. The only open question is:

**Does `POST /checkouts/{id}/share/` return the URL (or the `ec` code) in its
response?**

| If | Then |
|---|---|
| the response **contains** the URL or `ec` | call `share` (one write), take the link, send it over WhatsApp ourselves — full parity with Pix, and the customer never leaves the conversation |
| it does **not** | the link stays inside Angulare's e-mail/SMS. Ask Angulare to expose a link-minting endpoint (or an `ec` field on the checkout). Meanwhile: let Angulare deliver it, and poll `sales/orders?user_id=…` for the resulting `paid` order to drive the downstream flow |

⚠️ Settling it needs a **write** on a throwaway member and checkout — `share`
sends a real message to a real address. Use a test member whose e-mail we
control, never a live customer, and only with explicit sign-off.

### A correction to an earlier conclusion

I previously read "all 73 shared checkouts had an order" as evidence that
`share` creates the order. Checkout **15794 disproves that**: it is
`shared_to_customer: true`, `status: "Open"`, and has **no order at all**. The 73
were historical and already settled — survivorship bias. The order appears when
the customer pays.

## 11. The customer-facing web checkout (and why it matters)

Verified on the live tenant `numa` (`numastudios.com.br`).

**Architecture**

```
numastudios.com.br/planos            ← Webflow marketing page (tenant's own domain)
  └─ pagekraft.angulare.app/angulare/pagekraft/{auth,catalogue,carousel,booking}-latest.js
       └─ static.angulare.app/web/v4.0.390/{web,catalogue,checkout-modal,login-modal,book-v2,…}.js
            └─ API host: angulare.numastudios.com.br  (customer app API)
```

Inline config on the page:

```js
window.pagekraft.auth.config = {
  domain: 'angulare.numastudios.com.br',
  angulareVersion: 'latest-v4',
  config: { packagePageUrl: '/planos', myAccountPageUrl: '/my-account',
            useBookV2: true, useOTPInForgotPassword: true }
}
```

**How a customer pays by card here**

1. The catalogue widget (`ae-catalogue`) emits `toCheckout`.
2. `ae-checkout-modal` opens and calls `AngularEcommerce.ws.checkout.get()` — the
   **cart is server-side**, bound to the visitor's session/user.
3. The modal renders an **inline card form** — `Número do Cartão`, `CVV`,
   `Validade` (MM/AAAA), `Nome do titular do cartão`, `Parcelamento`,
   `Salvar dados para compras futuras` — plus saved cards, Pix and PayPal.
4. Charge happens **on the page**. **No link, no email.**

**Key difference from the PDV**

| | Customer web checkout | PDV "Link de Pagamento" |
|---|---|---|
| Initiated by | the customer | staff |
| Payment happens | **inline, on the page** | later, on the linked page |
| Link/email | **none** | Angulare emails/SMSes the customer |

`?openModal=checkout` exists as a URL parameter that opens the modal
(handled in `pagekraft/.../auth-latest.js`); the element is created on the page.
Auto-open was **not** reproduced in a headless run (the `window.pagekraft`
global was not ready at probe time) — needs one manual browser check.

There is **no product-level deep link**: `URLSearchParams` is essentially unused
in these bundles, so no `?package=` / `?plan=` / `?add=`.

### Feasibility of "just send the customer a link"

| Variant | Feasible | Writes | Experience |
|---|---|---|---|
| **B1 — send the plan/booking page URL** | ✅ **today** | **none** | customer picks the plan → buys → pays by card inline |
| **B2 — pre-selected plan / pre-filled cart** | ❌ | add-to-cart (write) **+** the customer's own session | not achievable from our side |
| **A — PDV `share`** | ✅ | 1 write | Angulare emails/SMSes the link; leaves the WhatsApp thread |

**Conclusion: B works as B1, not as "a pre-filled payment page".** The cart is
server-side and session-bound, and there is no URL parameter to add or select a
product — so we cannot put the item in the customer's cart for them.

## 12. Sources

- Live probes against `prd.angulare.app` (2026-10-09/10) with the tenant `numa` account
- `reservas.angulare.app/js/app.*.js` + 47 chunks (132 `/api/` paths, interceptors, JWT helpers)
- `crm.angulare.app/api/login/` (SSO form: username/password/**tenant**)
- `https://angulare.com/pt/` and `/pt/produtos/`, `/pt/agregadores/`, `/pt/termos-de-servico/`
- Wayback CDX for `angulare.app*` (revealed `prd.`, `crm.`, `reservas.`, `static.`, tenant subdomains)
- `angulare.app/totalpass-ativar` (indexed copy) — the "Parceiro = Angulare" instruction
