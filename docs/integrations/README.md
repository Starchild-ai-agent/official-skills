# Integration research — index

Research artefacts for the Brazilian fitness integration stack, so that
knowledge does not live only in chat.

| File | Content |
|---|---|
| `census.md` | Breadth census of 16 third-party services: docs entry point, auth model, sandbox, commercial gate, credentials needed |
| `angulare.md` | Deep dossier — reverse-engineered API surfaces, why `count: 0` happens, what to ask the vendor |
| `angulare_diagnose.py` | Read-only diagnostic script for the Angulare API (safe against production) |
| `tecnofit.md` | Public API is 2 endpoints, access-control shaped |
| `nextfit.md` | Paid add-on, GET-only, docs behind the customer login |
| `../evo/references/api-reference.md` | The one **shipped** skill (`evo/`) — curated endpoint/enum index |
| `../composio/SKILL.md` | **Already-shipped gateway to 1000+ SaaS apps.** Before building any generic connector, check here — see "Composio overlap" below. |

Non-skill directory by design: these are research records, not installable
capabilities. CI only indexes top-level directories containing a `SKILL.md`, so
`docs/` is ignored by the build.

---

## Composio overlap — check BEFORE building anything generic

`composio/` is an **already-shipped** skill (v1.4.1) that reaches 1000+ SaaS apps
through a gateway. It is not a build item. Anything Composio already covers must
**not** get a bespoke connector here.

Verified from that skill's own *Common Tools Quick Reference* (it documents the
toolkits it has actually been driven with):

| Toolkit | In our 16? | Verdict |
|---|---|---|
| **Google Calendar** | ✅ #17 | 🚫 **do not build** — Composio has it, with a documented quick reference |
| **Instagram** | ✅ #11 | ⚠️ **posting works today**; DM is a different toolkit — verify before building |
| Gmail / Drive / Docs / Notion / GitHub / Twitter | — | not in our list |

**Unverified but likely covered** — Composio's public catalogue is broad; these
should be probed through the gateway before anyone writes a connector:

| Service | Why it might be covered |
|---|---|
| **Outlook / Microsoft 365** | Microsoft toolkits are standard in Composio |
| **Stripe** | standard in Composio |
| **Meta / Facebook** | Composio ships Meta toolkits |

**How to check** (only possible from inside a Fly agent — the gateway is on the
internal network, `http://composio-gateway.flycast`, and is unreachable from a
laptop):

```bash
curl -s -X POST $GATEWAY/internal/search -H "Content-Type: application/json" \
  -d '{"query": "create a calendar event"}'
```

If a toolkit answers, **use Composio and skip the connector**. Note the gateway
must not be proxied (`sc-proxy` rewrites caller identity — see `composio/SKILL.md`).

**The rule this gives us:** the ~9 connectors figure below is an *upper bound*.
Subtract anything Composio already reaches.

---

## Capability matrix

Legend — **Write?**: can we mutate bookings/members through the API.
**Sandbox**: `self` = self-service signup, `gated` = needs a contract/partner
program, `none` = production only.

### Gym management systems

| Service | Docs | Auth | Write? | Webhooks | Sandbox | Gate | Status |
|---|---|---|---|---|---|---|---|
| **EVO** (W12/ABC Evo) | ✅ public OpenAPI, 134 paths | HTTP Basic (gym DNS + token) | ✅ **yes** | ✅ | none (docs' "sandbox" hits production) | EVO Black + API Plus/Pro quota | ✅ **`evo/` skill shipped** |
| **Angulare** (Angular e-Commerce) | ⚠️ no public docs, but **fully reverse-engineered from the dashboard SPA** | `POST /api/v1/jwt/token-auth/` → then **`Authorization: JWT <token>`** + **`tenant: <code>`** on every call | ✅ yes | ✅ | none (production only) | needs a tenant account — self-serve after that | ✅ **`angulare/` skill shipped** (25 functions, live-verified) |
| **Tecnofit** | ✅ `tecnofit.readme.io` (2 endpoints) | user/pass → 1h token, sent as `Authorization: <token>` | ❌ no | ❌ | none | partner program / "integração avançada" add-on | ✅ **`tecnofit/` skill shipped** (entitlement only) |
| **NextFit** | ⚠️ only inside the customer panel | panel-issued access key | ❌ **GET-only** | ❌ | none | paid "API Next Fit" add-on | 🔴 blocked on customer account + docs |

### Payments / revenue

| Service | Docs | Auth | Sandbox | Gate | Status |
|---|---|---|---|---|---|
| **Asaas** | ✅ `docs.asaas.com` | key in `access_token` **header** | ✅ **self-service** (`sandbox.asaas.com`) | none for sandbox | 🟢 easiest to validate |
| **Pagar.me** | ✅ `docs.pagar.me` (V5) | Basic `sk_` secret key, empty password | ✅ test mode, same host | Pagar.me account | 🟢 easy |
| **Stone** | ⚠️ partner-only (`connect.stone.com.br`) | Basic `sk_` + Stonecode | ❌ **none** | **Stone Partner Program** + homologation | 🔴 highest friction |
| **Mercado Pago** | ✅ `mercadopago.com.br/developers` | `Bearer` access token | ✅ **self-service** (+15 test accounts) | none for test | 🟢 easy |
| **Stripe** | ✅ `docs.stripe.com` | `Bearer` secret key | ✅ **self-service** | none for test | 🟢 easy; Pix = one-time only in BR |

### Aggregators

| Service | Docs | Auth | Sandbox | Gate | Status |
|---|---|---|---|---|---|
| **Wellhub** (ex-Gympass) | ✅ `developers.wellhub.com` | Vendor-issued Bearer + `X-Gym-Id` | ✅ separate hosts (`apitesting.partners.gympass.com`), gated | partner + Tech Sales contact | 🔴 need contact |
| **TotalPass** | ✅ `dev.totalpass.com` + help center | `partner_api_key` (TotalPass-issued) + `place_api_key` (gym-issued) → 24h JWT | ❌ **none — production only** | **Termo de Adesão** | 🟡 signable; test user by email |

### Messaging / marketing (Meta)

| Service | Auth | Sandbox | Gate | Status |
|---|---|---|---|---|
| **WhatsApp Cloud API** | Bearer (System User token) | ✅ **self-service test WABA + number** | none for own business | 🟢 ready |
| **Instagram DM** | Page access token | ⚠️ own assets in dev mode | **App Review + Business Verification** | 🔴 weeks |
| **Meta Ads (Lead Ads)** | Page token + `leads_retrieval` | ⚠️ test leads only | **App Review + Business Verification** | 🔴 weeks |
| **Meta Ads (CAPI)** | dataset/Pixel token | ✅ Test Events code | **none at all** | 🟢 ready now |

### ERP / fiscal

| Service | Auth | Sandbox | Webhooks | Gate | Status |
|---|---|---|---|---|---|
| **Omie** | static `app_key`/`app_secret` **in body** | free app tenant, 7 days | ✅ | trial free | 🟡 testable |
| **Conta Azul** | OAuth2 (code TTL 3 min) | "Desenvolvimento" env, 30 days (no real sandbox) | ❌ **none — poll only** | paid plan for prod | 🟡 testable |
| **Bling** | OAuth2 (+JWT migration in progress) | free trial account | ✅ | subscriber; homologação to publish | 🟡 testable |
| **Qive** | static `X-API-ID` + `X-API-KEY` | ✅ `sandbox-api.arquivei.com.br` (key issuance unknown) | ❌ none found | paid "Gestão" plan | 🟡 key source unclear |

### Calendars

| Service | Auth | Sandbox | Webhooks | Gate | Status |
|---|---|---|---|---|---|
| **Google Calendar** | OAuth2 (+SA domain-wide delegation, Workspace only) | test GCP project, only a Google account needed | ✅ `watch` channels (expire, no auto-renew) | none for test | 🟢 ready |
| **Outlook / Graph** | Entra ID app-only or delegated | ✅ M365 E5 dev tenant — **needs a billing account + Azure subscription** | ✅ subscriptions (<7 days, must renew) | admin consent | 🟡 billing gate |

---

## Provenance: Leonardo's phase classification

Recorded from the 7–8 Oct group chat, so the roadmap can be read correctly
later. **It is a service/vendor list ordered by product value, not a verified
API list and not a build order.**

| Phase | Framing | Items |
|---|---|---|
| **1 — Core** | schedule, members, communication | WhatsApp Business Platform (1), Angulare (2), EVO by W12 (3), Next Fit (4) |
| **2 — Revenue** | payments, benefit redemption, income | Wellhub/Gympass (5), TotalPass (6), Asaas (7), Pagar.me / Stone (8), Mercado Pago (9), Stripe (10) |
| **3 — Acquisition & Marketing** | lead gen, attribution | Instagram DM / Meta API (11), Meta Ads — Lead Ads + CAPI (12); **no 13–14 in the original** |
| **4 — Finance & Back Office** | records sync, back-office automation | Omie (15), Conta Azul (15), Bling ERP (16), Google Calendar (17), Microsoft Outlook Calendar (17) |
| **added later, unphased** | — | **Qive**, **Tecnofit** |

**Footnote, 2026-10-13 — Phase 1 #4 (Next Fit) does not hold.** The entry is a
*system of record*, but its public API is **GET-only** (vendor's own wording in
`nextfit.md`), so it cannot carry the booking loop that justifies its Phase-1
slot. Reclassified as a read-only reporting source and dropped from the build
queue. **Leonardo has not been told yet** — the table above is left as he wrote
it, with this footnote as the correction.

The generalisable point: of Phase 1's four systems of record, **only two are
writable** — EVO and Angulare. Tecnofit's public API is two access-control
endpoints; NextFit's is read-only. "System of record" in the vendor list does not
imply "we can write to it".

### His stated rationale

> "The order starts where the operational data lives and where conversations
> happen, since that's what makes the AI valuable from day one. Payments and
> marketing come next, and the ERP comes last because it's rarely what a studio
> owner misses first."

Plus the chat framing: Phase 1 items matter most **because they hold core
operational data or carry customer conversations**, and WhatsApp was assigned to
Almo's message-gateway workstream rather than to this one.

### How to read it

The sort key is **time-to-value for the studio owner** — a product/growth lens.
That is the right lens for a roadmap and the wrong lens for a build sequence,
because value-priority and lead-time disagree on several items:

- **Angulare is #2 by value but cannot be #2 by execution** — no public docs, and
  blocked on a vendor conversation for a Tenant slug + Open API Key.
- **EVO is #3 by value but is the only system buildable today** (public OpenAPI,
  full write path) — by execution order it is #1, and it is the one already shipped.
- **Wellhub and TotalPass sit in Phase 2 but carry weeks of paperwork.** If they
  are needed at launch, their applications must start during Phase 1.
- **Numbering note:** the duplicated 15s (Omie/Conta Azul) and 17s (Google/Outlook)
  correctly mark *substitutes* — but the same convention was not applied to the
  five payment vendors (7–10), which are also substitutes for each other. Treat
  payment rails as **one slot with alternatives**, not a four-step sequence.
- **Qive and Tecnofit were added without a phase.** Qive is a fiscal-document
  overlay (belongs with Phase 4); Tecnofit is a **system of record** and belongs
  in Phase 1 alongside EVO/NextFit — it was missing from the core list.
- **Calendars are mis-bucketed.** Instructor/class calendar sync is operational,
  not "finance & back office" — by his own criterion ("where the operational data
  lives") it sits closer to Phase 1 than to ERP.

---

## Functional classification

The 16 services cut by *function in the stack*, not by Leonardo's rollout phase.
The point of this view is the last column: how many connectors we actually need.

| # | Service | Function | Sub-role | Direction | Relationship to siblings |
|---|---|---|---|---|---|
| 1 | **Asaas** | 💳 Payment rail | Pix + boleto + subscription + split | two-way (charge → webhook) | **substitute** |
| 2 | **Pagar.me** | 💳 Payment rail | Orders + charges + subscriptions | two-way | **substitute** |
| 3 | **Stone** | 💳 Payment rail | Card acquiring + POS + Connect | two-way | **substitute** (offline) |
| 4 | **Mercado Pago** | 💳 Payment rail | Pix + payment links + Point | two-way | **substitute** |
| 5 | **Stripe** | 💳 Payment rail | Subscription engine, international | two-way | **substitute** |
| 6 | **Wellhub** | 🎟️ Benefit network bridge | Booking sync + access-control validation | **two-way, inbound-led** | **complement** |
| 7 | **TotalPass** | 🎟️ Benefit network bridge | Booking sync + check-in validation | **two-way, inbound-led** | **complement** |
| 8 | **WhatsApp Cloud API** | 💬 Conversation channel | Primary customer channel | two-way | **complement** |
| 9 | **Instagram DM** | 💬 Conversation channel | Secondary inbound channel | two-way | **complement** |
| 10 | **Meta Ads** | 📣 Acquisition & attribution | Lead Ads (inbound) + CAPI (outbound) | **two-way, both directions** | standalone loop |
| 11 | **Omie** | 🧾 Finance / fiscal back office | Full ERP: finance + NF-e + orders | outbound-led | **substitute** |
| 12 | **Conta Azul** | 🧾 Finance / fiscal back office | Finance ERP (⚠️ poll-only) | outbound-led | **substitute** |
| 13 | **Bling** | 🧾 Finance / fiscal back office | Orders + stock + NF-e | outbound-led | **substitute** |
| 14 | **Qive** | 🧾 Finance / fiscal back office | **Fiscal documents only** (NF-e/CT-e), not an ERP | inbound (pull) | **complement** — overlays any ERP |
| 15 | **Google Calendar** | 📅 Schedule mirror | Instructor/class calendar sync | two-way | **substitute** |
| 16 | **Outlook / Graph** | 📅 Schedule mirror | Instructor/class calendar sync | two-way | **substitute** |

### What that means for the build

| Function | Distinct connectors needed | Reasoning |
|---|---|---|
| 💳 Payment rails | **2** (1 primary + 1 fallback) | Five vendors solve the same problem. Pick by the client's existing provider, not by feature list. |
| 🎟️ Benefit networks | **2** (both) | Genuinely complementary — a studio is on Wellhub *and/or* TotalPass. Both are webhook-first. |
| 💬 Conversation channels | **2** | WhatsApp now; Instagram DM only after App Review clears. |
| 📣 Acquisition | **1** | Meta Ads is one loop with two directions (Lead Ads in, CAPI out). CAPI is ungated today. |
| 🧾 Finance / fiscal | **1 per client + optional 1** | Omie/Conta Azul/Bling are substitutes — a gym has one ERP. Qive overlays any of them for fiscal docs. |
| 📅 Schedule mirror | **0** (or 1) | **Google Calendar is already covered by Composio** — do not build it. Outlook only if the client is on Microsoft 365 **and** Composio cannot reach it. |

**≈ 8 connectors, not 16** — down from 9 once the Composio overlap is removed
(Google Calendar was counted here; Composio already covers it). Several of the
rest are thin: Qive is a pull-only fiscal-document reader, Meta Ads is two
endpoints.

**Before writing any connector, search Composio.** The gateway is on the Fly
internal network, so this check is only possible from inside an agent — but it
costs one call and can delete a whole build item.

### Event-source vs sink

Worth separating, because it decides what needs a webhook receiver and what needs
a scheduler:

| Role | Services |
|---|---|
| **Push into us** (need a webhook receiver) | WhatsApp `messages`, Instagram `messages`, Meta `leadgen`, TotalPass check-in webhook, Wellhub booking-request webhook, Angulare purchase webhook, all payment webhooks, Bling/Omie webhooks, Google `watch` + Graph subscriptions |
| **We push / query** (need a scheduler) | Aggregator slot + class sync, ERP financial sync, calendar event mirroring, Conta Azul (poll-only), Qive (pull-only), NextFit (read-only reports) |
| **Both** | Aggregators (booking request in → confirmation out), Meta Ads (leads in → conversions out) |

---

## Priority-ordered index (message-ready)

Leonardo's phase order × type × difficulty × access requirements. This table is
the single source for status messages to the team.

**Two orderings exist on purpose — do not mix them:**

| Ordering | Use it for | Sequence |
|---|---|---|
| **Data-integration order** (used in team messages) | explaining *how the pieces connect* and what unblocks what | ① systems of record → ② conversation channel → ③ benefit networks → ④ payment rails → ⑤ acquisition → ⑥ finance/fiscal → ⑦ calendar mirror |
| **Leonardo's phase order** (this table) | explaining *what the business values first* | ① core → ② revenue → ③ acquisition → ④ back office |

They disagree in two places worth remembering: instructor/class calendars are
operational (early in data order, last in phase order), and the aggregators are
booking writers (early in data order, Phase 2 in phase order).

**Difficulty = the cost of *getting access***, not the cost of coding:
`LOW` = public docs + self-service credentials · `MED` = needs a customer/vendor
account or a paid add-on · `HIGH` = needs a contract, an approval process, or has
no public documentation.

| # | Service | Type | Diff | Public API | Sandbox | Account needed | Contract |
|---|---|---|---|---|---|---|---|
| 1 | **WhatsApp Business Platform** | 💬 channel | LOW (prod MED) | ✅ | ✅ self-serve | no for test; client WABA + fresh number for prod | no (only if we're a Tech Provider) |
| 2 | **Angulare** | 🗄️ system of record | LOW (was HIGH) | ⚠️ none public, reverse-engineered | none — production only | a tenant account; then `tenant` + `JWT` headers | none needed — ✅ verified live |
| 3 | **EVO by W12** | 🗄️ system of record | LOW | ✅ 134 paths | none (hits prod) | yes — gym DNS + EVO token | EVO Black; Plus free/capped, Pro metered |
| 4 | **Next Fit** | 🗄️ system of record | MED | ⚠️ read-only, in-panel only | none | **yes** — gym + paid add-on + access key | paid add-on | 🔴 **reclassified — see below** |
| 5 | **Wellhub** | 🎟️ benefit bridge | HIGH | ✅ | ✅ gated | yes — vendor-issued token + Gym ID | **yes** — partner + Tech Sales |
| 6 | **TotalPass** | 🎟️ benefit bridge | HIGH | ✅ | **none — prod only** | yes — 2 keys + a test user | **yes** — Termo de Adesão |
| 7 | **Asaas** | 💳 payment | LOW | ✅ | ✅ self-serve | no | no (prod: Asaas account) |
| 8a | **Pagar.me** | 💳 payment | LOW | ✅ V5 | ✅ test mode | a Pagar.me account | no |
| 8b | **Stone** | 💳 payment | **HIGH** | ⚠️ partner-only | **none** | partner credentials | **yes** — Partner Program + homologation |
| 9 | **Mercado Pago** | 💳 payment | LOW | ✅ | ✅ self-serve | no | no |
| 10 | **Stripe** | 💳 payment | LOW | ✅ | ✅ self-serve | no | no |
| 11 | **Instagram DM** | 💬 channel | HIGH | ✅ | ⚠️ own assets in dev mode | IG Professional + FB Page | App Review + Business Verification |
| 12a | **Meta Lead Ads** | 📣 acquisition | HIGH | ✅ | ⚠️ test leads only | BM + test Ad Account + `leads_retrieval` | App Review + Business Verification |
| 12b | **Meta CAPI** | 📣 attribution | LOW | ✅ | ✅ test event code | BM + test Pixel | **none** |
| 15 | **Omie** | 🧾 finance/fiscal | MED | ✅ | ⚠️ no host; 7-day test tenant | trial account → App Key/Secret | none to test; subscription for prod |
| 15 | **Conta Azul** | 🧾 finance/fiscal | MED | ✅ | ⚠️ no host; 30-day dev tenant | free developer account | active plan for prod |
| 16 | **Bling** | 🧾 finance/fiscal | MED | ✅ | ⚠️ no host; trial account | Bling account + dev app | subscriber; homologação to publish |
| 17 | **Google Calendar** | 📅 schedule mirror | ~~LOW~~ | ✅ | ✅ test project | ~~no (Google account)~~ | no | 🚫 **Composio covers it — skip** |
| 17 | **Outlook / Graph** | 📅 schedule mirror | MED | ✅ | ✅ dev tenant, **needs billing + Azure sub** | Entra app registration | admin consent for app permissions | ⚠️ **probe Composio first** |
| — | **Qive** | 🧾 fiscal overlay | HIGH | ✅ | ✅ host exists, key source unknown | X-API-ID + X-API-KEY + test CNPJ | paid plan |
| — | **Tecnofit** | 🗄️ system of record | MED | ✅ 2 endpoints only | none | tenant user + password | partner programme / paid add-on |

---

## What we need from JT / Leon — test accounts per service

Ordered by what unblocks the most work first.

### 1. Blocking (nothing can be validated without these)

| Service | What we need | Where it comes from |
|---|---|---|
| ~~**Angulare**~~ | ✅ **RESOLVED 2026-10-10** — Leon supplied an account (tenant `numa`); auth + all read endpoints verified live. No vendor contact needed. See `angulare.md`. | — |
| **Wellhub** | Authentication Token + **Gym ID** + webhook secret key (sandbox hosts already documented) | **Wellhub Technical Sales / Relationship** — via "Request to integrate" at `support.gympass.com/hc/en-us/requests/new` |
| **TotalPass** | `partner_api_key` (after **Termo de Adesão**) + test `place_api_key` + a **test user** (name, *unregistered* CPF, e-mail, address within 200 m of the test gym) | `tp.integracoes@totalpass.com.br`; sign up at `developers.totalpass.com` |
| **NextFit** | A gym account **with the "API Next Fit" add-on activated** + one access key + the **in-panel API documentation** | The client gym, or a NextFit vendor demo tenant |

### 2. Self-service — we can do these ourselves (no ask needed)

| Service | What we do | Note |
|---|---|---|
| **Asaas** | Sign up at `sandbox.asaas.com`, generate the key | Fully independent sandbox; no CNPJ |
| **Mercado Pago** | Free account + one app → test Access Token, ≥1 test Buyer | Up to 15 test accounts, fictional balance |
| **Stripe** | Register `dashboard.stripe.com/register?country=BR` → test keys | Pix is **one-time only** for BR accounts |
| **WhatsApp Cloud API** | Create an app with the WhatsApp use case | Test WABA + test number auto-created |
| **Meta Ads / CAPI** | Events Manager → dataset token + `test_event_code` | **No App Review, no permissions** |
| **Google Calendar** | Test GCP project + OAuth client + test users | Only a Google account needed |

### 2b. Self-service but needs a company account (no contract, real signup)

| Service | What we need | Note |
|---|---|---|
| **Pagar.me** | A Pagar.me account, then test-mode `sk_test_`/`pk_test_` | Keys are dashboard-issued |
| **Omie** | Free 7-day app tenant; company/CNPJ data for the app form | Extendable via `ajuda@omie.com.br` |
| **Conta Azul** | Free developer account (email + PIN) → "Desenvolvimento" app | ⚠️ **no webhooks at all — polling only** |
| **Bling** | Free trial account → developer app → OAuth | JWT migration in progress |
| **Outlook / Graph** | M365 E5 dev tenant | ⚠️ **requires a billing account + active Azure subscription** |

### 3. Needs a contact or a decision

| Service | What we need | Who to ask |
|---|---|---|
| **Stone** | Partner Program acceptance, Partner Hub access, merchant + per-client secret keys, Stonecode, test POS | Stone account/sales manager (`partner.stone.com.br/formulario`) |
| **Outlook / Graph** | Confirmation we have (or will create) a billing account with an Azure subscription for the M365 dev tenant | Ops / JT |
| **Instagram DM + Lead Ads** | A real IG Professional account linked to a Facebook Page, and a decision on whether to start the **App Review** clock (weeks) now | Marketing owner + JT |
| **Qive** | Sandbox `X-API-ID`/`X-API-KEY` — **where they are issued is unknown**; may need the paid Gestão plan | `qive.com.br/contato` |
| **Meta / WhatsApp (production)** | A client WABA with a phone number not already on WhatsApp + a System User token | JT / first pilot client |

### 4. Questions worth asking them directly

1. **Which of these have you already connected?** Leon has an Angulare
   integration running today — which credential is in it, and is it the Open API
   Key or a panel identity?
2. **Which studios/gyms can act as pilots?** We need one live tenant per gym
   system (EVO, Angulare, Tecnofit, NextFit) to validate for real.
3. **Is anyone already a Wellhub/TotalPass partner** at the ERP level, or is that
   a fresh application? Both are gated on a relationship, not on code.
4. **Do we have the Angulare vendor contact** (`rodrigo@`)? One conversation
   would settle the Tenant/key/attendance questions in `angulare.md`.
