# Third-party service census

Census of the remaining stack from Leonardo's integration priority list, taken
2026-10-09. Depth is deliberately *breadth over detail*: entry point, auth model,
sandbox availability, commercial gate, and — the actionable part — **exactly what
credential each one needs to run a technical validation**.

Confidence markers: **CONFIRMED** = read in vendor docs/portal · **INFERRED** =
derived, not literally stated · **NOT FOUND** = could not locate.

> Method note: the built-in `web_search` was fully blocked during this research
> (Google/DuckDuckGo/Ecosia/Mojeek/Startpage all refuse automated queries, and
> `cn.bing.com` returns nothing for most queries). Everything below comes from
> direct URL reads, Zendesk/ReadMe JSON and `.md` endpoints, Wayback CDX, and
> `search.brave.com` through a browser. That is why some doc sites are marked as
> 403-to-automated-fetchers.

---

# Phase 2 — Payments

## Asaas

- **WHAT** Brazilian PSP: Pix, boleto, card, subscriptions (recorrência), payment
  links, checkout, split, plus white-label/BaaS subaccounts. Best fit: core
  billing and recurring gym/studio subscriptions.
- **DOCS** `https://docs.asaas.com/` · full API index `https://docs.asaas.com/reference/llms.txt` · linked from `https://asaas.com/developers`
- **AUTH** Custom API key sent in the **`access_token` header**. Lifetime/scope NOT FOUND.
  Bases: sandbox `https://api-sandbox.asaas.com/v3`, production `https://api.asaas.com/v3`.
  A sandbox key is rejected (401) on prod and vice-versa. **CONFIRMED**
- **SANDBOX** **YES, fully self-service** — sign up at `https://sandbox.asaas.com/`,
  generate an API key immediately. Sandbox is independent of any production
  account. Sandbox-only helpers exist to approve the account, confirm a payment
  and force a due date (`https://docs.asaas.com/reference/acoes-em-sandbox.md`).
  No CNPJ, no partner agreement, no paid plan documented for sandbox. **CONFIRMED**
- **GATE** None for sandbox. Production needs a normal Asaas account.
  Integration support: `integracoes@asaas.com.br`.
- **ENDPOINTS** `POST /v3/webhooks` (CONFIRMED from the docs' OpenAPI);
  `/v3/payments` (create/retrieve), `/v3/payments/{id}/pixQrCode`,
  `/v3/subscriptions`, `/v3/paymentLinks` — path shapes INFERRED from reference
  page names.
- **WEBHOOKS** **YES** — `POST /v3/webhooks`, max 10 per account, auto-generated
  validation `authToken` (`whsec_…`, returned only on creation),
  `sendType` SEQUENTIALLY/NON_SEQUENTIALLY. Events: `PAYMENT_RECEIVED`,
  `PAYMENT_CONFIRMED`, `PAYMENT_OVERDUE`, `PAYMENT_REFUNDED`, `TRANSFER_*`, `INVOICE_*`. **CONFIRMED**
- **TEST_CREDENTIALS_NEEDED** A sandbox account + its API key. Nothing else.
- **BLOCKERS** Token lifetime/scope and production onboarding requirements not published.

## Pagar.me

- **WHAT** Brazilian gateway/PSP, now part of the **Stone** group. Orders/charges/
  subscriptions, checkout, Pix/boleto/cards, webhooks, marketplace/split. The
  public gateway counterpart to Stone's partner-only stack.
- **DOCS** `https://docs.pagar.me/` (API **V5**) · reference `https://docs.pagar.me/reference` · index `https://docs.pagar.me/llms.txt`
- **AUTH** **HTTP Basic**: username = **Secret Key** (`sk_live_…`/`sk_test_…`),
  password empty → `Authorization: Basic base64(sk:)`. A **Public Key** (`pk_…`)
  is client-side only, for card encryption. Static keys, no expiry. **CONFIRMED**
- **SANDBOX** **Test mode on the same host** — no separate domain. Toggle the
  dashboard (`https://id.pagar.me`) to test mode to get `sk_test_`/`pk_test_`.
  Test operations never create real receivables. Simulators exist (e.g. Pix). **CONFIRMED**
- **GATE** Requires a Pagar.me account (commercial signup). No partner program
  needed, unlike Stone. Contacts: `comercial@pagar.me`, `relacionamento@pagar.me`.
- **ENDPOINTS** `POST https://api.pagar.me/core/v5/orders` (CONFIRMED, full curl in
  docs); charges attached to orders; Pix via `payment_method: "pix"`.
  `/core/v5/subscriptions`, `/core/v5/plans`, `/core/v5/paymentlinks` INFERRED.
- **WEBHOOKS** **YES** — configurable retries, API to list/resend failures.
  Events: `order.paid`, `order.payment_failed`, `order.canceled`,
  `charge.*`, `subscription.*`, `invoice.paid`, `checkout.*`, `recipient.*`. **CONFIRMED**
- **TEST_CREDENTIALS_NEEDED** A Pagar.me account + test-mode `sk_test_` / `pk_test_`.
- **BLOCKERS** Exact V5 subscription/plan/webhook-config paths not opened (INFERRED);
  key generation is login-gated.

## Stone

- **WHAT** Brazilian acquirer/bank. Developer surface exists (Connect Stone,
  Partner Hub, POS SDK) but is **partner-only**.
- **DOCS** `https://www.stone.com.br/devcenter/` · `https://connect.stone.com.br/` ·
  Partner Program `https://partner.stone.com.br/` · Partner Hub API
  `https://partnerhubapi.stone.com.br/` (has `/llms.txt` + OpenAPI) · POS SDK
  `https://sdkpos.stone.com.br/`. Note `developers.stone.com.br` does **not**
  resolve (TLS cert error) — not a live portal. `docs.stone.com.br` is
  investor/legal docs only.
- **AUTH** Connect Stone rides the Pagar.me stack: **Basic auth with a Secret Key**.
  The partner holds a Pagar.me merchant; each client establishment is an
  **account** with its own transactional Secret Key, linked to a **Stonecode**
  under which POS terminals are registered. **CONFIRMED**
- **SANDBOX** **NO self-service sandbox.** Gated by the **Stone Partner Program**:
  apply at `https://partner.stone.com.br/formulario`, a Stone team validates
  prerequisites, you get an account manager, keys/rules, then product activation
  in Partner Hub. Homologation ends with written sign-off before production. **CONFIRMED**
- **GATE** Partner program + commercial negotiation + homologation. FAQ states
  joining the program is mandatory to obtain keys. **CONFIRMED**
- **ENDPOINTS** `POST https://partnerhub-sdx-external-api.stone.com.br/applications/connect-stone/activation`
  (CONFIRMED). Transactional orders go through Pagar.me's order endpoint.
- **WEBHOOKS** Presumed via the Connect/Pagar.me mechanism — **NOT CONFIRMED**.
- **TEST_CREDENTIALS_NEEDED** Partner Program acceptance, Partner Hub access, a
  Pagar.me merchant Secret Key, per-client account Secret Keys, a Stonecode, and
  likely test POS terminals. **Highest friction of the five.**

## Mercado Pago

- **WHAT** Largest LatAm PSP. Pix, Checkout Pro (hosted link), Checkout
  Transparente/API, payment status, subscriptions, webhooks, Point in-person.
- **DOCS** `https://www.mercadopago.com.br/developers/pt/docs` · panel `/developers/panel/app` · test accounts `/developers/pt/docs/your-integrations/test/accounts` · webhooks `/developers/pt/docs/your-integrations/notifications/webhooks`
- **AUTH** **Access Token** as `Authorization: Bearer <token>` for backend calls;
  Public Key client-side. **Client ID + Client Secret** exist for OAuth
  client-credentials. Test tokens share the `APP_USR` prefix but only work in test. **CONFIRMED**
- **SANDBOX** **YES, self-service.** Test credentials auto-created with an
  application; up to **15 test accounts** (Seller/Buyer/Integrator) with generated
  user/password/6-digit code and fictional balance. Needs only a free MP account.
  For Pix, register a Pix key on the seller account. **CONFIRMED**
- **GATE** Free for dev/test. Production credentials need business info + T&C.
- **ENDPOINTS** `POST /v1/payments` (Pix via `payment_method_id: "pix"`, supports
  `notification_url`), `GET /v1/payments/{id}`, `POST /checkout/preferences`,
  `GET /v1/payment_methods` — **INFERRED** (the `/reference/` pages 404'd).
  MP also ships a CLI and an MCP server at `https://mcp.mercadopago.com/mcp` (CONFIRMED).
- **WEBHOOKS** **YES** — configure per test/prod URL in the panel or per-payment
  via `notification_url` (creation config wins). Topics include `orders`,
  `payment`, `subscription_preapproval`, `subscription_authorized_payment`,
  `plan`, `topic_chargebacks_wh`. Signature via `x-signature` (HMAC-SHA256). **CONFIRMED**
- **TEST_CREDENTIALS_NEEDED** An MP account + one application, its Test Access
  Token and Test Public Key, plus ≥1 test Buyer account.
- **BLOCKERS** REST reference pages 404; some test sections login-gated.

## Stripe

- **WHAT** Global PSP. Brazil accounts support **Pix one-time** settling in BRL;
  cards, Checkout, Subscriptions, Payment Links, webhooks.
- **DOCS** `https://docs.stripe.com/` · Pix `https://docs.stripe.com/payments/pix.md` · country availability `https://stripe.com/global`
- **AUTH** Secret + publishable keys (`sk_test_`/`sk_live_`, `pk_…`), restricted
  keys, OAuth for Connect. Test vs live is only a key prefix on the same API.
- **SANDBOX** **YES, self-service** — register at
  `https://dashboard.stripe.com/register?country=BR` and test-mode keys are
  available immediately; no CNPJ or verification for test mode. **CONFIRMED**
- **GATE** None for test mode. Live mode = standard Stripe activation;
  whether a Brazilian CNPJ is required for a BR live account is **INFERRED**
  (normally yes), not directly cited.
- **ENDPOINTS** `/v1/payment_intents`, `/v1/checkout/sessions`, `/v1/subscriptions`,
  `/v1/payment_links` — standard Stripe REST, **INFERRED** this pass.
- **WEBHOOKS** **YES** — Dashboard or `POST /v1/webhook_endpoints`; verify with
  the `Stripe-Signature` header.
- **BRAZIL PIX NOTES (CONFIRMED)** Pix one-time settles in BRL; **Pix Automático
  (recurring) is NOT available for Brazil accounts** (only non-BR accounts
  settling in USD/EUR/GBP); BRL Pix min 0.50, single Pix max 3,000 USD
  equivalent, 10,000 USD/month per customer; non-BR accounts collecting Pix pay
  **IOF 3.5%** via EBANX (`amount_includes_iof` = never/always). Prohibited
  categories include crypto, insurance, telehealth.
- **TEST_CREDENTIALS_NEEDED** A free Stripe account + test-mode keys; set currency
  BRL and enable Pix to exercise it.

### Payments cross-cut

Self-service today, no CNPJ, no waiting: **Asaas**, **Mercado Pago**, **Stripe**;
**Pagar.me** needs an account but no partner program. **Stone** is the outlier —
partner program, account manager, homologation, no public sandbox.

Auth patterns differ per vendor and are a real source of bugs:
`access_token` **header** (Asaas) vs **Basic with an empty password** (Pagar.me,
Stone) vs **Bearer** (Mercado Pago, Stripe).

---

# Phase 2 — Fitness benefit aggregators

## Wellhub (ex-Gympass)

- **WHAT** Global corporate wellness/fitness-benefit aggregator. Gym-side usage:
  **Booking API** (push class schedules + manage slots so Wellhub users book in
  the Wellhub app) and **Access Control API** (validate app check-ins).
- **DOCS** Partner developer portal **`https://developers.wellhub.com/`**
  (products: Booking API, Access Control API, Integration Setup API, Partner App
  APIs) — e.g. `/product/booking-api/1.0/getting-started`, `/endpoints`,
  `/webhooks`; `/product/access-control-api/1.0/getting-started`, `/endpoints`,
  `/faq`, `/check-in-webhook`; `/product/integration-setup-api/1.0/getting-started`.
  Onboarding: `https://wellhub.com/en-us/partners/integrate-with-wellhub/` →
  "Request to integrate" → `https://support.gympass.com/hc/en-us/requests/new`.
  ⚠️ `developer-hub.wellhub.com` is the **client/HR** portal (eligibility,
  payroll) — a *different product*; do not use it for gym booking/check-in.
- **AUTH** One shared **Bearer** credential ("Wellhub Authentication Token") for
  both Access Control and Booking: `Authorization: Bearer {{token}}`. Access
  Control additionally sends **`X-Gym-Id`**. The token is **issued by Wellhub**,
  not self-generated; lifetime not documented. Legacy `X-Api-key` still works but
  is being deprecated. **CONFIRMED**
- **SANDBOX** **YES**, separate base URLs (not self-service — they come with
  onboarding): Booking `https://apitesting.partners.gympass.com/booking/v1` →
  prod `https://api.partners.gympass.com`; Access Control
  `https://apitesting.partners.gympass.com/access/v1` → prod
  `https://api.partners.gympass.com/access/v1`. Integration Setup API is
  production-only. **CONFIRMED**
- **GATE** Commercial/partner gate; no public pricing or self-service. Token and
  Gym-ID come from the **Wellhub Relationship / Tech Sales team**; the CMS
  integration is requested via the "Request to integrate" form. **CONFIRMED**
- **ENDPOINTS** Booking: `POST|GET {booking}/booking/v1/gyms/:gym_id/classes`,
  `GET|PUT …/classes/:class_id`, `POST …/classes/:class_id/slots`,
  `GET …/slots?from=&to=`, `GET {booking}/setup/v1/gyms/:gym_id/products`.
  Access Control: `POST https://api.partners.gympass.com/access/v1/validate`
  (body `{gympass_id, custom_code?}`), `POST|PUT|DELETE
  …/access/v1/code/:wellhub_id`. Integration Setup:
  `GET|POST …/v1/systems/gyms/:gym_id/webhooks`. No payment API — Wellhub pays
  partners monthly based on check-ins.
- **WEBHOOKS** **YES.** Booking events `booking-requested`, `booking-canceled`,
  `booking-late-canceled`; **a booking request must be answered with a PATCH
  within 15 minutes or it is auto-rejected.** Signed with header
  **`X-Gympass-Signature`** (HMAC-SHA-1 over the stringified body, partner secret
  key ≤100 chars, handed to Wellhub Tech Sales). Access Control has a check-in
  webhook; subscription is via the Integration Setup API / onboarding. **CONFIRMED**
- **TEST_CREDENTIALS_NEEDED** (1) Wellhub Authentication Token from Tech Sales;
  (2) one or more Gym IDs; (3) a webhook secret key; (4) the sandbox base URLs.
  Realistically these only exist after a CMS integration request + Wellhub
  contact → **we need a Wellhub partner/tech-sales contact.**
- **BLOCKERS** `developers.wellhub.com` is client-rendered (had to render via a
  proxy). Token lifetime undocumented. HR-side portal must not be confused with
  the gym APIs.

## TotalPass

- **WHAT** Brazilian corporate fitness-benefit aggregator. Gym/ERP integrates as
  a **Partner (ERP)** via the Check-in Validation API (receive check-in webhooks
  from the TotalPass app and confirm access) and the Booking API (mirror class
  schedule, manage slots/seat maps, confirm/deny reservations).
- **DOCS** API reference `https://dev.totalpass.com/reference` (ReadMe; Try-It is
  login-gated, but `.md`/`llms.txt` are agent-friendly) · developer portal
  `https://developers.totalpass.com/` · help center `https://ajuda.totalpass.com.br`
  (Zendesk JSON API works: `/api/v2/help_center/articles/search.json?query=API`).
  Key articles: check-in API `48920022036635`, auth/credentials `48941731530139`,
  booking `48923933171483`, onboarding steps `48941417163931`.
- **AUTH** **Two keys, then a JWT.** (1) `partner_api_key` identifies the ERP —
  generated **by TotalPass** and sent after the ERP signs the **Termo de Adesão**;
  strictly confidential, never requested from clients. (2) `place_api_key`
  identifies the unit — generated by the **gym** in the Portal de Parceiros
  (Integrações ▸ Configurar integrações) and handed to the ERP. Both are sent to
  the auth endpoint, which returns the unit's active plans + a JWT.
  **Token expires every 24h.** The same two keys serve both products, but the
  **auth endpoints differ** for Check-in vs Booking. **CONFIRMED**
- **SANDBOX** **NO sandbox — everything runs against PRODUCTION.** Instead
  TotalPass creates a **test user** for you: email `tp.integracoes@totalpass.com.br`
  with full name, a CPF **not already registered** on TotalPass, an e-mail, and a
  physical address **within 200 m** of the test check-in location (for app
  geolocation). TotalPass then activates a plan in the app. **CONFIRMED**
- **GATE** **Sign the Termo de Adesão.** Send ERP name, CNPJ and legal
  responsible to `tp.integracoes@totalpass.com.br`; also register at
  `https://developers.totalpass.com/`, which after signup shows the APIs and
  gives you a `partner_api_key` plus a **test** `place_api_key`. Go-live requires
  TotalPass homologation, after which the ERP appears in the official integration
  list and gyms generate their real `place_api_key`. **CONFIRMED**
- **ENDPOINTS** Check-in auth
  `POST https://gym-service-api.totalpass.com/partner/auth` (body
  `place_api_key`, `partner_api_key` → 201 + JWT); Booking auth
  `POST https://booking-api.totalpass.com/partner/auth`. Check-in webhook:
  `POST {gym-service-api}/partner/webhook/create` (only type `CHECKIN`), plus
  update/delete/get. Check-in validation: POST to the URL delivered inside the
  webhook payload (`endpoint` field) — **must be done within 90 minutes** or the
  check-in expires; returns 422 if reception validated manually first. Booking:
  `POST {booking-api}/partner/events`, `/partner/event-occurrence`,
  `PUT …/event-occurrence/{uuid}/slot`, `POST …/event-occurrence/status`,
  `GET …/partner/slot`, `PUT …/partner/slot/confirm-slot/{slotId}` (reject
  requires a reason), seat maps `POST|GET|PUT|DELETE …/partner/seat-maps`,
  `PUT …/partner/places/update-configs`, `GET …/partner/plans`.
- **WEBHOOKS** **YES.** Check-in: `POST {gym-service-api}/partner/webhook/create`;
  TotalPass POSTs on every app check-in with access data + the exclusive
  validation link. Booking: `POST {booking-api}/partner/webhook/subscribe`;
  reservations arrive and must be confirmed/denied. One URL can serve all units
  if the code distinguishes units by credentials. **CONFIRMED**
- **TEST_CREDENTIALS_NEEDED** `partner_api_key` (after Termo de Adesão / portal
  signup), a test `place_api_key`, a TotalPass-created **test user** (name + fresh
  CPF + e-mail + address within 200 m of the test gym), and a receiving webhook URL.
- **BLOCKERS** No sandbox (production only). `dev.totalpass.com` is a ReadMe SPA
  (rendered via proxy). Test-user creation is email-gated.

**Aggregator cross-cut:** both are **partner-gated with vendor-issued tokens**, and
both give us a **webhook-first** model. Wellhub needs a Tech Sales contact and has
a 15-minute response SLA on booking requests; TotalPass needs a signed Termo de
Adesão and a 90-minute check-in confirmation window. **TotalPass has no sandbox at
all** — validation runs on production, mitigated by a vendor-created test user.

---

# Phase 4 — ERP / fiscal

## Omie

- **WHAT** Brazilian SMB ERP (financials, NF-e/NFS-e, sales/service orders, CRM, stock).
- **DOCS** `https://developer.omie.com.br/` · service list `/service-list/` · help
  collection `https://ajuda.omie.com.br/pt-BR/collections/3045828-apis-e-webhooks`
- **AUTH** Static **`app_key` + `app_secret`** ("Chave de Integração") sent in the
  **request body** of every JSON/SOAP call. No OAuth, no expiry. Only an
  *administrator* user can view/rotate keys; rotating the secret **invalidates all
  existing integrations**. **CONFIRMED**
- **SANDBOX** No separate host. A free **"Aplicativo Teste"** creates a demo tenant
  with fictitious data, **valid 7 days**, extendable via `ajuda@omie.com.br`. **CONFIRMED**
- **GATE** API included; testing needs no paid plan. Production needs a real
  subscription. No mandatory partner agreement found.
- **ENDPOINTS** Base `https://app.omie.com.br/api/v1/<modulo>/<servico>/` with
  `call`+`param` in the body. Relevant: `/produtos/pedidovenda/`, `/produtos/pedido/`,
  `/produtos/nfconsultar/`, `/produtos/dfedocs/`, `/financas/contareceber/`,
  `/financas/pix/`, `/financas/pesquisartitulos/`, `/servicos/os/`,
  `/servicos/contrato/`, `/geral/clientes/`.
- **WEBHOOKS** **YES** — per-app in the developer portal ("Adicionar novo webhook"),
  administrator profile required; e.g. event `produto.alterado`.
- **TEST_CREDENTIALS_NEEDED** A 7-day trial account → App Key + App Secret from
  `https://developer.omie.com.br/my-apps/` (login-gated); company/CNPJ data for
  the app form.

## Conta Azul

- **WHAT** Brazilian SMB ERP (financial, sales, NF-e/NFS-e, customer/product
  registry, collections).
- **DOCS** `https://developers.contaazul.com/` (guide + OpenAPI; markdown endpoints
  `/guide.md`, `/auth.md`, `/faq.md`, index at `/llms.txt`) · portal
  `https://developers-portal.contaazul.com`
- **AUTH** **OAuth 2.0 Authorization Code.** `client_id`/`client_secret` from the
  Developer Portal; token at `https://api-v2.contaazul.com/oauth/token` with Basic
  `base64(client_id:client_secret)`; returns access + refresh tokens; calls use
  `Bearer`. Authorization code TTL **3 minutes**. Multi-tenant: one token per
  connected company. Rate limit **600/min and 10/s** per account. **CONFIRMED**
- **SANDBOX** **No sandbox host** — FAQ states explicitly "Existe ambiente de
  sandbox? Não". Substitute: a **"Desenvolvimento" app** grants a development
  environment with fictitious data and a **Conta Azul Pro test login valid 30
  days** (extendable). Self-service via the portal. **CONFIRMED**
- **GATE** Docs free. Production needs an active Conta Azul plan; integration
  types public/private/internal. Partnerships: `integracoes@contaazul.com`.
- **ENDPOINTS** Base `https://api-v2.contaazul.com/` — `POST /v1/financeiro/contas-a-pagar`,
  `POST /v1/financeiro/contas-a-receber`, contracts, charges, sales (v1),
  products/inventory (v1), persons/customers (v1), services (v1), notas-fiscais
  (v1, consult only). ⚠️ **Breaking change 18/10/2026**: POST returns the created
  account directly; `/v1/protocolo/{id}` is being removed. **CONFIRMED**
- **WEBHOOKS** **NO** — explicitly not natively available; the vendor advises
  recurring polling. **CONFIRMED** ← matters for our sync design.
- **TEST_CREDENTIALS_NEEDED** A free developer account (email + PIN), a
  "Desenvolvimento" app → client_id/client_secret + the temporary Pro user/password.
- **BLOCKERS** `developers.contaazul.com` and the portal return 403 to automated
  fetchers (read via markdown + render proxy).

## Bling

- **WHAT** Brazilian ERP / e-commerce back office (orders, stock, NF-e/NFS-e,
  contacts, finance).
- **DOCS** `https://developer.bling.com.br/home` — Guia, Referência, Limites,
  Webhooks (cadastro, autenticação, idempotência, retentativas), Publicando um
  aplicativo, Changelogs, **Migração para autenticação JWT**.
- **AUTH** **OAuth 2.0 Authorization Code** — `client_id`/`client_secret`, token at
  `https://api.bling.com.br/Api/v3/oauth/token` with Basic `base64(creds)` and
  `grant_type=authorization_code` (or `refresh_token`), then `Bearer`. **Migration
  to JWT in progress**: send `enable-jwt: 1` on token and API calls; the opaque
  token path is deprecated (cut-off TBD). **CONFIRMED**
- **SANDBOX** No dedicated host documented; a "Como testar" guide + a **free Bling
  trial account** (`https://www.bling.com.br/inscricao/`) is the test path. **CONFIRMED**
  that a how-to-test path exists; that it is a plain trial ERP account is INFERRED.
- **GATE** API for Bling subscribers; free trial to test. Publishing in the
  "Central de Extensões" requires a homologação process. CNPJ required to open an
  account (INFERRED).
- **ENDPOINTS** Base `https://api.bling.com.br/Api/v3/`. Confirmed: `POST /Api/v3/oauth/token`,
  `GET /Api/v3/produtos`. Other resources exist per the Referência but exact paths
  were not enumerated.
- **WEBHOOKS** **YES** — dedicated docs incl. authentication, idempotency and retries;
  configured per app. **CONFIRMED**
- **TEST_CREDENTIALS_NEEDED** A Bling account + a developer app → client_id/client_secret,
  then complete OAuth.
- **BLOCKERS** `developer.bling.com.br` 403s automated fetchers (read via render
  proxy); deep SPA routes 404 without internal routing.

## Qive (ex-Arquivei)

- **WHAT** Fiscal-document platform: NF-e/CT-e/NFS-e/NFC-e/MDF-e capture, storage,
  manifestação do destinatário, OCR, Tax Document API. Best fit: centralize fiscal
  documents by CNPJ.
- **DOCS** `https://developers.qive.com.br/docs` (JS SPA) · legacy mirror still live
  `https://developers.arquivei.com.br/docs` · help `https://ajuda.qive.com.br`
- **AUTH** **Static headers: `X-API-ID` + `X-API-KEY`, plus `X-Use-ApiGateway: always`.**
  No OAuth. **CONFIRMED** (seen in the official curl example).
- **SANDBOX** **YES** — docs name two bases: production `https://api.arquivei.com.br`
  and test `https://sandbox-api.arquivei.com.br`. Whether sandbox credentials are
  self-service or plan-gated is **NOT FOUND**.
- **GATE** Commercial/sales-gated: the API is a feature of the paid **"Gestão"**
  plan ("Integrações via API") and "Customizado"; the plans page says to ask for
  custom integration conditions → `https://qive.com.br/contato`. Signup exists at
  `https://auth.qive.com.br/auth/realms/saas/signup`. CNPJ required (INFERRED —
  it is a CNPJ-keyed fiscal platform).
- **ENDPOINTS** Base `https://api.arquivei.com.br`. Confirmed: `POST /v2/dfe/nfe`
  (list NF-e with filters/fields/paginator), `/v1/nfe/{role}` (role =
  received|emitted|transporter|authorized|autXML), `/v1/nfe/danfe` (PDF base64),
  events at `/v1/dfe/nfe/events`, `/v1/events/nfe`, `/v2/nfe/events`;
  manifestação supported. CT-e list `/v2/cte` INFERRED.
- **WEBHOOKS** **NOT FOUND** — appears to be pull/polling only.
- **TEST_CREDENTIALS_NEEDED** Sandbox `X-API-ID` + `X-API-KEY` from a Qive account
  and a test CNPJ. **Where to issue those keys is NOT FOUND** — likely inside the
  Qive app under the Integrações area.
- **BLOCKERS** SPA docs; no public auth/onboarding page; sandbox self-service status unknown.

**ERP cross-cut:** **no vendor has a real sandbox host.** Omie substitutes a
7-day demo app tenant, Conta Azul a 30-day "Desenvolvimento" environment with a
Pro test login, Bling a free trial, Qive an actual `sandbox-api` host (but with
unknown key issuance). Auth models are wildly inconsistent — static keys in the
**body** (Omie), OAuth2 (Conta Azul, Bling), static headers (Qive) — so a shared
"ERP connector" abstraction would be a mistake; each is its own skill.

---

# Phase 1 / 3 — Meta stack

## WhatsApp Business Platform (Cloud API)

- **WHAT** Programmatic 1:1 WhatsApp messaging — booking confirmations, reminders,
  opt-in marketing. The agent's main channel.
- **DOCS** `https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started`
  (+ `/about-the-platform`, `/access-tokens`, `/permissions`, `/messages/send-messages`,
  `/templates/overview`, `/webhooks/overview`)
- **AUTH** Access tokens as `Authorization: Bearer`. Two types: a temporary **User
  access token** from App Dashboard ▸ WhatsApp ▸ API Setup (expires in hours,
  dev only), and a long-lived **System User access token** from Business Settings ▸
  System Users, scoped with `business_management`, `whatsapp_business_messaging`,
  `whatsapp_business_management` — the recommended production credential.
  Default throughput 80 msg/s. **CONFIRMED**
- **SANDBOX** **YES, self-service** — creating an app with the WhatsApp use case
  auto-creates a **test WABA + test business phone number** with relaxed limits and
  **no payment method required** to send template messages. Only needs a Facebook
  account + developer registration. Official Postman collection:
  `https://www.postman.com/meta/whatsapp-business-platform/`. **CONFIRMED**
- **GATE** For a **direct developer** (own business data only): **no App Review,
  no Advanced Access** — permissions are self-granted via the system user. Business
  Verification is not required to start (test number works unverified) but is
  required for higher throughput (unverified portfolio capped at **250 templates
  vs 6,000**). **Partners/Tech Providers acting for other businesses must pass App
  Review + Advanced Access + Business Verification.** Pricing is per conversation
  (SERVICE/UTILITY/MARKETING). **CONFIRMED**
- **ENDPOINTS** `POST /<PHONE_NUMBER_ID>/messages` (shared send path for
  `type:template` | `text` | `interactive`), `POST /<WABA_ID>/message_templates`,
  `GET /<TEMPLATE_ID>?fields=status`, `GET /<WABA_ID>/phone_numbers`,
  `GET|POST|DELETE /<WABA_ID>/message_templates`, `/<WABA_ID>/subscribed_apps`. **CONFIRMED**
- **WEBHOOKS** **YES** — per-field subscription in App Dashboard ▸ WhatsApp ▸
  Configuration; key field **`messages`** (incoming + outgoing status). Verify
  handshake `hub.mode=subscribe`, `hub.verify_token`, `hub.challenge`. Signature
  via app secret; payloads ≤3 MB; retries up to 7 days; mTLS supported. **CONFIRMED**
- **TEST_CREDENTIALS_NEEDED** Nothing from the user beyond a Meta developer account.
  For production: the client's WABA access / a real phone number not already on
  WhatsApp + a System User token. Templates sent outside the 24h customer-service
  window must be pre-approved.

## Instagram DM (Instagram Messaging API)

- **WHAT** Read/send Instagram Direct messages for the gym's IG inbox (lead
  capture, booking, auto-replies).
- **DOCS** `https://developers.facebook.com/documentation/business-messaging/instagram-messaging`
  (+ `/get-started`, `/app-review`, `/app-review/apps-for-other-businesses`)
- **AUTH** **Page access token** on behalf of a Facebook Page linked to the
  Instagram professional account. Flow: Facebook Login → user token with
  `instagram_basic`, `instagram_manage_messages`, `pages_manage_metadata` →
  `GET /me/accounts` → `GET /{page-id}?fields=access_token`. Short-lived user
  token ⇒ PAT valid 1h; long-lived ⇒ PAT with no expiration. Instagram-Login
  variant uses `instagram_business_basic` / `instagram_business_manage_messages`
  (old `business_*` scopes deprecated 2025-01-27). **CONFIRMED**
- **SANDBOX** No first-class sandbox. Testing uses your **own** Instagram
  professional account + linked Page while the app is in Development mode (app
  role-holders can be granted any permission without review). Requires an IG
  **Professional** account, a linked Facebook Page, and "Allow Access to Messages"
  enabled in IG settings. **CONFIRMED**
- **GATE** **App Review is mandatory** before anyone outside app roles can use it
  (Advanced Access). "Apps For Other Businesses" requires a **screen recording** of
  setup + testing, step-by-step instructions, and test credentials. Business
  Verification applies. **CONFIRMED — this is the timeline bottleneck (weeks).**
- **ENDPOINTS** `GET /{page-id}/conversations?platform=instagram`,
  `POST /{page-id}/messages`, Conversation API for reading threads.
- **WEBHOOKS** **YES** — subscribe the Instagram topic on the Page webhook
  (`messages` field); app must be installed on the Page. Exact field name not
  spelled out on the pages opened.
- **TEST_CREDENTIALS_NEEDED** A real Instagram Professional account linked to a
  Facebook Page, a Meta app with the developer as a Page-role user, the
  "Allow Access to Messages" toggle ON, and a long-lived Page token. Production
  additionally needs App Review + Business Verification + a reviewer test account.

## Meta Ads (Lead Ads + Conversions API)

- **WHAT** (a) Lead Ads → pull leads into the gym CRM near-real-time; (b) CAPI →
  send server-side conversion events (e.g. membership signup) for optimization.
- **DOCS** `https://developers.facebook.com/documentation/ads-commerce/marketing-api/guides/lead-ads`
  (+ `/lead-ads/retrieving`, `/lead-ads/testing-troubleshooting`,
  `/lead-ads/quickstart/webhooks-integration`, `/conversions-api`, `/conversions-api/get-started`)
- **AUTH** Lead Ads: **Page access token** (long-lived preferred) with
  `leads_retrieval`, `pages_manage_ads`, plus `ads_management`, `pages_show_list`,
  `pages_read_engagement`, `pages_manage_metadata`. CAPI: a **dataset/Pixel-scoped
  access token** generated in Events Manager or via your own app + system user.
  **CONFIRMED**
- **SANDBOX** No formal sandbox for Lead Ads, but **test leads** exist:
  `POST /{FORM_ID}/test_leads` (one per form; Page Advertiser role required) and
  the tool `https://developers.facebook.com/tools/lead-ads-testing`. Real leads
  are **not retrievable while the app is in Development mode**. CAPI: the **Test
  Events** tool generates a `test_event_code`; a test Pixel can be created in
  Business Manager. **CONFIRMED**
- **GATE** Lead Ads: **App Review required** to retrieve leads (submit
  `leads_retrieval` + `pages_manage_ads`), then **Business Verification**.
  **CAPI: no gate at all** — docs state plainly that using Events Manager requires
  "no App Review and no permissions". Marketing API access tier governs scale
  (Full Access threshold: 500 calls/15 days). **CONFIRMED**
- **ENDPOINTS** Lead retrieval: webhook gives `leadgen_id` → `GET /<LEAD_ID>` →
  `field_data`; bulk `GET /<AD_ID>/leads`, `GET /<FORM_ID>/leads`; subscribe
  `POST /{page-id}/subscribed_apps?subscribed_fields=leadgen`; test leads
  `POST|GET|DELETE /{FORM_ID}/test_leads`. CAPI:
  `POST https://graph.facebook.com/{v}/{PIXEL_ID}/events` (batch ≤1,000). **CONFIRMED**
- **WEBHOOKS** Lead Ads: **Page** webhook subscribed to the **`leadgen`** field.
  CAPI is push-only, no webhook subscription. **CONFIRMED**
- **TEST_CREDENTIALS_NEEDED** Business Manager with a **test Pixel/dataset** +
  CAPI token (self-serve, no review), a `test_event_code`, a test Ad Account +
  Page (Advertiser role), a Lead Ad form, and a Page token with `leads_retrieval`.
  Production lead retrieval needs App Review + Business Verification.

**Meta cross-cut:** one app + one Business Portfolio behind three products. **CAPI
is essentially ungated and can be validated immediately**; everything else waits on
App Review and/or Business Verification. WhatsApp is the exception where a *direct*
developer needs no review at all — only partners do.

---

# Phase 4 — Calendars

## Google Calendar API

- **WHAT** Read/write instructor & class events (two-way sync) + free/busy lookups.
- **DOCS** `https://developers.google.com/workspace/calendar/api/auth` (scopes) ·
  `/guides/overview` · `/guides/push` · `https://developers.google.com/workspace/guides/configure-oauth-consent` ·
  `/guides/create-credentials` · `/api/v3/reference/events` · `/api/v3/reference/freebusy/query`
- **AUTH** **OAuth 2.0** (authorization code + PKCE, refresh tokens). Core scope
  `https://www.googleapis.com/auth/calendar.events`; also `calendar.events.readonly`,
  `calendar.freebusy`, `calendar.events.freebusy`, `calendar.app.created` (own a
  dedicated secondary calendar — good for isolating gym events). Access token ~1h,
  refresh token long-lived. Alternative: **service account with domain-wide
  delegation** via the JWT `sub` claim — **Workspace domains only**, requires a
  domain admin to authorize the client ID + scopes. **CONFIRMED**
- **SANDBOX** No sandbox product; validate against real accounts in a test GCP
  project. Create project → enable Calendar API → configure OAuth consent screen →
  create a Web OAuth Client ID → add Test users. Only a Google account needed —
  no CNPJ, no partner agreement, no paid plan. **CONFIRMED**
- **GATE** None commercial; free per-project quota. `calendar.events`/`readonly`/
  `freebusy` are **sensitive** scopes (app verification needed to publish publicly);
  none are *restricted*. A "Testing" app works only for explicitly added test users.
- **ENDPOINTS** Base `https://www.googleapis.com/calendar/v3` —
  `GET|POST /calendars/{calendarId}/events`, `GET|PATCH /calendars/{calendarId}/events/{eventId}`,
  incremental sync with `syncToken`/`updatedMin`, `POST /freeBusy`,
  `POST /calendars`, refresh `POST https://oauth2.googleapis.com/token`.
- **WEBHOOKS** **YES** — `POST /calendars/{calendarId}/events/watch` (also Acl,
  CalendarList, Settings). Needs an HTTPS receiver with a valid, hostname-matching
  cert. **Channels expire and there is NO automatic renewal** — re-call `watch`
  before expiry. A `sync` message arrives on channel creation. **CONFIRMED**
- **TEST_CREDENTIALS_NEEDED** A GCP project with Calendar API enabled; a Web OAuth
  client ID + secret; a consent screen declaring the sensitive scopes; ≥1 test
  user; a public HTTPS webhook receiver. Domain-wide delegation additionally needs
  a Workspace test domain + SA key + a super-admin. **CONFIRMED**
- **BLOCKERS** Test-user cap not stated (commonly 100, unverified).

## Microsoft Outlook Calendar (Graph)

- **WHAT** Read/write instructor & class events in Microsoft 365/Outlook +
  free/busy via `getSchedule`, for delegated and app-only sync.
- **DOCS** `https://learn.microsoft.com/en-us/graph/api/resources/calendar` ·
  `/graph/auth/auth-concepts` · `/graph/permissions-reference#calendarsreadwrite` ·
  `/graph/api/calendar-getschedule` · `/graph/change-notifications-overview` ·
  `/graph/api/subscription-post-subscriptions` · `/office/developer-program/microsoft-365-developer-program-get-started`
- **AUTH** Microsoft identity platform (Entra ID). **Delegated** (MSAL,
  authorization code) or **app-only** (client credentials with secret/certificate,
  no user). `Calendars.ReadWrite` — application id `ef54d2bf-…`
  (**AdminConsentRequired = YES**, all mailboxes), delegated id `1ec239c2-…`
  (admin consent not required). Least-privilege for free/busy:
  `Calendars.ReadBasic`. Bearer tokens, ~1h. Restrict app-only access to specific
  mailboxes with an **application access policy**. **CONFIRMED**
- **SANDBOX** **YES** — Microsoft 365 Developer Program instant sandbox: an **E5
  developer subscription**, 25 user licenses, **90-day renewable**, with 16
  fictitious sample users and sample Graph calendar data.
  ⚠️ **Gate: a valid billing account (Microsoft Customer Agreement) with an active
  Azure subscription is REQUIRED and cannot be bypassed** (spending limit removed);
  the sandbox itself is free. Portal: `https://developer.microsoft.com/en-us/microsoft-365/profile`.
- **GATE** No commercial program for Graph itself; the hard gate is **admin consent**
  in the target tenant for application permissions. Delegated `Calendars.ReadWrite`
  can be user-consented.
- **ENDPOINTS** Base `https://graph.microsoft.com/v1.0` —
  `GET /users/{id}/calendars`, `GET /users/{id}/calendarView?startDateTime=&endDateTime=`,
  `GET|POST /users/{id}/events`, `PATCH /users/{id}/events/{id}`,
  `POST /users/{id}/calendar/getSchedule`, delta sync `/users/{id}/calendarView/delta`.
- **WEBHOOKS** **YES** — `POST https://graph.microsoft.com/v1.0/subscriptions`
  (resource `/users/{id}/events`, changeType created/updated/deleted,
  `notificationUrl`, `clientState`, `expirationDateTime`). Delivery via webhooks,
  Event Hubs or Event Grid. **Max Outlook subscription lifetime 10,080 minutes
  (<7 days)**; rich subscriptions 1,440 minutes. Must be renewed; creation requires
  answering a `validationToken` handshake. **CONFIRMED**
- **TEST_CREDENTIALS_NEEDED** An M365 E5 developer tenant (admin creds), an Entra
  app registration with a secret + redirect URI, `Calendars.ReadWrite` application
  permission with admin consent (or `Calendars.ReadBasic` for free/busy only),
  1–2 licensed sandbox users, and a public HTTPS notification URL. No CNPJ.
- **BLOCKERS** None for the docs read. Note app-only `Calendars.ReadWrite` spans
  **all** mailboxes in the tenant unless constrained by an application access policy.
