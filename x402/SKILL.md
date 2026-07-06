---
name: x402
version: 2.3.3
description: |
  Monetize any user project/service with the x402 payment protocol on Base (Starchild platform billing: pay_per_use / lifetime / weekly / monthly / quarterly / yearly / prepaid, plus multi-plan services), and pay other agents' x402 services.

  Use when the user wants to charge for an API/service, accept USDC from other agents, or call a paid x402 endpoint.
author: starchild
tags: [x402, payments, base, usdc, monetization, api, subscription, metered, agent-commerce]
delivery: script
metadata:
  starchild:
    emoji: 💸
    skillKey: x402
    requires:
      bins: [python3]
---

# 💸 x402 Monetization Skill

Turn any local HTTP service into a paid service on Base (x402 V2 protocol,
`exact` scheme, USDC via EIP-3009 — buyer pays zero gas), and act as a buyer
paying other agents' x402 services with the user's Privy wallet.

**Architecture: reverse-proxy sidecar.** The gateway (`gateway/app.py`) sits in
front of the user's untouched service. One unified gateway, three billing modes
as config presets — the error contract is identical across all modes.

```
buyer agent ──402/PAYMENT-SIGNATURE──> gateway :840x ──plain HTTP──> user service :port
                     │
              facilitator (verify + settle on Base) ──USDC──> user's Privy wallet
```

## Quick start — monetize a service (PLATFORM MODES, use these by default)

Platform modes implement the Starchild community-gateway billing contract
(x402-facilitator `docs/pricing-models.md`): 402 JSON body with
`accepts.pricingModel`, buyer sends `X-PAYMENT`, the **facilitator is the
single source of truth for "already paid"** (no local payment state), and
every settle auto-callbacks community-gateway for purchase/call records.

```bash
FAC=https://starchild-x402-facilitator.fly.dev

# pay_per_use: verify -> settle on EVERY request
python3 skills/x402/scripts/monetize.py --name my-api --upstream-port 5173 \
    --mode pay_per_use --price 0.01 --network eip155:8453 --facilitator $FAC

# lifetime: one payment = permanent access (checked via /facilitator/access-status)
# NOTE: lifetime/monthly REQUIRE --facilitator-admin-token (fail-closed at startup;
# access-status/settlements are admin-gated — without it the gateway cannot know
# "already paid" and would re-settle every request, double-charging buyers)
python3 skills/x402/scripts/monetize.py --name my-api --upstream-port 5173 \
    --mode lifetime --price 5.00 --network eip155:8453 --facilitator $FAC \
    --facilitator-admin-token $ADMIN_TOKEN

# monthly: natural-month subscription (same day next month, clamped to month end;
# expiry computed from /facilitator/settlements confirmed_at)
python3 skills/x402/scripts/monetize.py --name my-api --upstream-port 5173 \
    --mode monthly --price 10.00 --network eip155:8453 --facilitator $FAC \
    --facilitator-admin-token $ADMIN_TOKEN

# weekly / quarterly / yearly: fixed-length subscriptions (7/90/365 days after the
# newest qualifying payment). Same admin-token requirement as lifetime/monthly.
# Facilitator contract: queried as access-status pricing_model=monthly +
# period_days=7/90/365 (monthly WITHOUT period_days = natural-month semantics).
python3 skills/x402/scripts/monetize.py --name my-api --upstream-port 5173 \
    --mode weekly --price 3.00 --network eip155:8453 --facilitator $FAC \
    --facilitator-admin-token $ADMIN_TOKEN

# multi-plan (docs/pricing-models.md 多支付方式): --mode is the DEFAULT plan,
# each --plan MODE=PRICE adds an option. Buyers pick a plan per request with the
# X-Pricing-Model header; the 402 quotes THAT plan's amount (audit requirement).
# pay_per_use cannot be combined with other plans.
python3 skills/x402/scripts/monetize.py --name my-api --upstream-port 5173 \
    --mode monthly --price 10.00 --plan weekly=3 --plan yearly=90 \
    --network eip155:8453 --facilitator $FAC --facilitator-admin-token $ADMIN_TOKEN

# prepaid: one on-chain deposit, then every call is a millisecond off-chain debit.
# For HIGH-FREQUENCY / metered APIs: no per-call settle (2-5s + gas + 30/min
# rate limit), per-call price can be sub-cent. --deposit = suggested top-up size
# (default 100 calls worth, min $0.10 = facilitator X402_MIN_DEPOSIT_AMOUNT).
python3 skills/x402/scripts/monetize.py --name my-api --upstream-port 5173 \
    --mode prepaid --price 0.001 --deposit 1.00 --network eip155:8453 --facilitator $FAC
```

Default protected routes: `/api/*` (override with `--route 'METHOD /path'`;
one service price via `--price` — platform modes have no per-route pricing).
lifetime/monthly need `--facilitator-admin-token` because
`/facilitator/access-status` + `/facilitator/settlements` are admin-gated
(platform ops holds the token; ask for a scoped one per deployment).
Lifetime semantics: first call settles on-chain; repeat calls pass the
already-paid check with NO second charge.

## Legacy/extended modes (local-ledger billing — still supported)

```bash
# per-call pricing via x402 SDK middleware (V2 PAYMENT-REQUIRED headers)
python3 skills/x402/scripts/monetize.py --name my-api --upstream-port 5173 \
    --mode payperuse --route 'GET /api/*=$0.01'

# subscription: buyers top up via x402 -> get API key + credits, 1 credit/call
python3 skills/x402/scripts/monetize.py --name my-api --upstream-port 5173 \
    --mode subscription --price-per-credit 0.001 --min-credits 100 \
    --route 'GET /api/*=1'

# metered: same as subscription but routes cost different unit weights
python3 skills/x402/scripts/monetize.py --name my-api --upstream-port 5173 \
    --mode metered --price-per-credit 0.001 --min-credits 100 \
    --route 'GET /api/cheap/*=1' --route 'POST /api/heavy=25'
```

These keep payment state in the gateway's local SQLite ledger (deterministic
API keys, credit refunds on upstream 5xx). **Deprecated for new deployments**
since v2.1: prefer `--mode prepaid` (same prepaid-credit UX, balance held by
the facilitator instead of a local SQLite file). Still fully supported for
existing deployments; `timepass` has no platform equivalent yet.

Output includes `gateway_port`. **Expose the GATEWAY port, not the upstream**
(via `preview` or community-publish). `pay_to` defaults to the user's Privy
EVM wallet — revenue lands there directly.

Registry of all monetized services: `/data/workspace/.x402/services.json`.
Per-service config/log/state: `/data/workspace/.x402/<name>/`.

## Billing mode decision table

| Mode | Tier | Buyer UX | When |
|------|------|----------|------|
| `pay_per_use` | **platform** | X-PAYMENT each request, settled every call | simple data endpoints, agent-to-agent one-shots |
| `lifetime` | **platform** | pay once, permanent access (facilitator-verified) | one-time unlock, buyout pricing |
| `monthly` | **platform** | pay once per natural month | SaaS-style subscriptions |
| `weekly` / `quarterly` / `yearly` | **platform** | fixed-length pass: 7 / 90 / 365 days from newest payment | short trials, annual discounts |
| `prepaid` | **platform** | one on-chain deposit → off-chain debit per call | high-frequency / sub-cent / usage-metered APIs |
| `payperuse` | legacy | SDK V2 headers, pay per request | pre-2.0 deployments |
| `subscription` | extended | x402 top-up → API key + N credits, 1 credit/call | prepaid credits, avoids per-call payment latency |
| `metered` | extended | like subscription, route-weighted units | mixed cheap/expensive endpoints (LLM calls etc.) |
| `timepass` | extended | x402 payment → N-day pass on an API key | fixed-duration passes (non-natural-month) |

Prefer **platform** modes: they match the community-gateway audit checklist,
get automatic purchase/call records via the settle callback, and keep zero
payment state in the gateway. `prepaid` supersedes the local-ledger
`subscription`/`metered` modes for new deployments: same prepaid-credit UX,
but the balance lives in the FACILITATOR (survives gateway restarts/moves,
auditable by platform ops) instead of a gateway-local SQLite file. The
legacy/extended modes remain for pre-2.1 deployments and for the timepass
model the platform contract doesn't cover.

### How prepaid works (v2.1, facilitator balance primitives)

```
first call    buyer signs deposit ($1)  -> gateway -> /facilitator/deposit-settle
                                            (ONE on-chain settle, credits balance)
every call    buyer signs per-call price -> gateway verifies sig (auth only,
                                            NEVER settled) -> /facilitator/debit
                                            (off-chain, ~ms) -> forward upstream
upstream 5xx  gateway auto-refunds the debit (negative debit, request_id:refund)
balance empty gateway answers 402 insufficient_balance with accepts.amount =
              deposit size -> client auto-signs the top-up and retries
```

Contract details (all verified against the deployed platform facilitator):
- 402 challenge: `accepts.pricingModel = "prepaid"`, `accepts.amount` = per-call
  price normally, deposit size when topping up; extra fields
  `accepts.depositAtomic` + `accepts.pricePerCallAtomic` tell buyers both numbers.
- The per-call X-PAYMENT signature is authentication only — the gateway calls
  /verify (cached per signature until its validBefore) then /facilitator/debit;
  the signed value is settled ONLY when it is an actual deposit (value >=
  depositAtomic AND balance insufficient). Buyer exposure to a malicious
  gateway is therefore one per-call price, same as pay_per_use.
- Debit idempotency: gateway generates a fresh `request_id` (uuid) per call;
  the facilitator binds request_id to (payer, amount) — cross-payer reuse is 409.
- Route `units` multiply the per-call price (metered pricing, e.g.
  `--route 'POST /api/heavy=25'` charges 25x).
- Deposit minimum: facilitator `X402_MIN_DEPOSIT_AMOUNT` (default $0.10).

### Multi-plan services (v2.2, docs/pricing-models.md 多支付方式)

One service can offer several pricing options simultaneously (e.g. weekly $3 /
monthly $10 / yearly $90 / lifetime $150). Contract (community-gateway audits
this per plan before listing):

- Config: `"plans": {"weekly": {"price_usd": "3"}, ...}`; `"mode"` is the
  DEFAULT plan. CLI: `--plan MODE=PRICE` (repeatable).
- Buyer selects a plan per request with the `X-Pricing-Model` header
  (`client.paid_request(..., pricing_model="yearly")`); the 402 then quotes
  THAT plan's `accepts.amount` + `pricingModel`. Unknown plan -> HTTP 400
  listing available plans. No header -> default plan; its 402 (and
  `/.well-known/x402`) carries a `plans` map with every option's accepts.
- Combination rules (enforced by the gateway): `pay_per_use` cannot be
  combined with anything (startup error). Before charging under ANY plan the
  gateway checks access under ALL subscription plans of the service — a
  lifetime holder requesting the weekly plan is never re-charged
  (access-status is consulted per plan until a hit, with zero settles).
- Subscriptions + prepaid can be combined: a subscription holder is forwarded
  without debiting the prepaid balance.
- weekly/quarterly/yearly access checks go to the facilitator as
  `pricing_model=monthly&period_days=7|90|365` (period_days contract) with
  `min_amount` = that plan's price; the access cache is keyed per
  (payer, plan).

Ready-to-use config templates (fill `pay_to` + `upstream`):
platform — `templates/pay_per_use.json`, `templates/lifetime.json`,
`templates/monthly.json`, `templates/weekly.json`, `templates/quarterly.json`,
`templates/yearly.json`, `templates/prepaid.json`, `templates/multi_plan.json`;
legacy/extended — `templates/payperuse.json`, `templates/subscription.json`,
`templates/metered.json`, `templates/timepass.json`.
Timepass CLI: `--mode timepass --pass-days 30 --pass-price 4.99`; repeat
purchases EXTEND expiry from max(now, current expiry). Prepaid behavior: one
on-chain deposit, then pure off-chain per-call debits (sub-second), exact
balance accounting, automatic refund on upstream 5xx.
Buyers need NO special handling: `client.paid_request` detects the prepaid
challenge, signs the per-call price for auth, and auto-signs the deposit only
when the gateway answers insufficient_balance (spend guard applies to both).

Subscription/metered specifics:
- Account = payer wallet address; API key is **deterministic** per payer (re-topup returns the same key).
- Top-up: buyer x402-pays `POST /x402/topup` → key returned immediately, credits added in the settle hook.
- Ledger (SQLite, `state/ledger.db`): settlement `tx_hash` is UNIQUE → replayed settlements can never double-credit.
- Refund semantics: upstream unreachable or 5xx → units auto-refunded (buyer never pays for our failure).
- Buyer endpoints: `GET /x402/balance` (X-API-Key), `GET /x402/info` (public pricing), `GET /x402/health`.

## Networks & facilitators

| Network | ID | Facilitator | Needs |
|---------|----|-------------|-------|
| Base Sepolia (default) | `eip155:84532` | `https://x402.org/facilitator` (default) | nothing |
| Base mainnet | `eip155:8453` | **self-hosted** (`facilitator/server.py`, default `http://127.0.0.1:8410`, override via `X402_FACILITATOR_URL` or `--facilitator`) | settler key gas ETH on Base |

**Self-hosted facilitator** (`skills/x402/facilitator/`): our own /verify + /settle
— no CDP account, no KYC, full transaction visibility. Start:
`python3 skills/x402/facilitator/server.py` (port 8410). The settlement key
(auto-generated at `.x402/facilitator/settler.key`, or `X402_SETTLER_PRIVATE_KEY`
env) ONLY pays gas — fund flow is fixed by the buyer's signature; it can never
touch user funds. It needs a little Base ETH for gas (~$0.001/settlement).
Safety: mandatory `eth_call` simulation before spending gas, per-payer rate
limit (`X402_PAYER_RATE_LIMIT`, default 30/min), authorization-nonce idempotency,
full settlement ledger at `/facilitator/stats`.
Testnet USDC (Base Sepolia): `0x036CbD53842c5426634e7929541eC2318f3dCF7e`,
faucet at faucet.circle.com. Prices auto-convert: `$0.01` → `10000` atomic USDC units.

## Keepalive (register once per machine)

One watchdog guards ALL x402 gateways (cloudflare-skill pattern: idempotent,
prints only on state change → silent scheduled task when healthy):

1. Boot: append to `/data/workspace/setup.sh`:
   `bash /data/workspace/skills/x402/scripts/keepalive.sh || true`
2. Watchdog: `scheduled_task(action="schedule", schedule="every 10 minutes", command="bash /data/workspace/skills/x402/scripts/keepalive.sh", deliver="origin")` — empty output = silent.

Gateway down → restarted from its config. Upstream down → reported but NOT
restarted (upstream has its own supervisor via previews — don't fight it).

## Always-on availability (required for listed paid services)

A published paid service must stay reachable 24/7. Two platform behaviors
work against that — handle both when you publish:

1. **Idle suspend** (automatic): the platform suspends idle machines. Busy
   signals (interactive runs, active previews, scheduled jobs, live
   websockets) keep a machine awake — a gateway registered as a preview
   service counts. Suspended machines are woken by the platform; processes
   and ports resume, but the first request after a long idle may see wake
   latency.
2. **Auto-update restarts** (the real killer): when a new platform image
   ships, the machine restarts and gateway/upstream processes die until
   keepalive revives them. Switch the machine to MANUAL update mode so
   non-mandatory updates never restart it unattended. Mandatory (security)
   updates still force-apply after a grace period regardless of mode.

Check the current mode from inside the machine (read-only, no extra auth
setup — these env vars are preset in every machine):

    curl -s -H "Authorization: Bearer $CONTAINER_JWT" \
      "$AI_AGENT_API_URL/api/cloud/internal/machines/$FLY_MACHINE_ID/update-mode"
    # → {"update_mode": "auto" | "manual"}

Setting the mode is user-owned: the toggle lives in the web dashboard
(machine settings → update preference; container tokens cannot write it).
Publish flow requirement: after listing a paid service, read the mode — if
it is "auto", tell the user to flip the web toggle to manual, or their
service will go down on the next platform update. In manual mode the web UI
shows a banner when an update is pending, so they can apply it at a chosen
time (keepalive then restores the service after the restart).

## Buyer side — pay other agents' x402 services

```bash
python3 skills/x402/client.py GET https://host/api/thing
X402_MAX_ATOMIC=50000 python3 skills/x402/client.py POST https://host/x402/topup
```

`paid_request` auto-detects BOTH 402 flavors: V2 header challenge
(PAYMENT-REQUIRED → x402 SDK path) and the platform JSON-body challenge
(`accepts.pricingModel` → manual EIP-3009 sign → retry with `X-PAYMENT`).
For lifetime/monthly services, repeat calls within the paid period verify but
do NOT settle — the result has `paid: true` with no new on-chain tx.

**Buyer signer = session EOA by default** (`.x402/buyer.key`, auto-generated).
⚠️ Do NOT sign EIP-3009 with the Privy wallet on Base mainnet: the Privy
address carries EIP-7702 delegation code, so USDC verifies via EIP-1271 and
rejects plain ECDSA on-chain (`FiatTokenV2: invalid signature`) — even though
off-chain recovery passes. Fund the session EOA with a small
USDC budget from the Privy wallet (ERC20 transfer); the budget IS the hard
spend cap.

**Funding the session EOA (when target-chain balance is 0):** signature
verification passes with an empty wallet — settlement then fails with
`invalid_exact_evm_insufficient_balance`. Check before paying, and bridge if
the user's funds sit on a different chain:

1. Snapshot all chains: `wallet_get_all_balances()` (wallet skill).
2. USDC on the wrong chain → move it to the service's network first
   (cross-chain: okx / bridge skills; same-chain swap: 1inch / openocean).
3. Privy → session EOA on the target chain via `wallet_transfer` — an ERC20
   transfer is a CONTRACT call, not a native send: `to` = the token contract
   (Base USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`), `amount` = 0,
   `data` = transfer calldata `0xa9059cbb` + recipient (the session EOA,
   zero-padded to 32 bytes) + atomic amount (32 bytes). Build it:
   `"0xa9059cbb" + eoa[2:].lower().zfill(64) + hex(atomic)[2:].zfill(64)`.
   Setting `to` = the EOA directly sends NATIVE currency instead — wrong tx.
   (The EOA address is printed by client.py on first run.)
4. Re-check the EOA balance, then `paid_request(...)`.
5. No USDC anywhere → stop and tell the user to acquire some (on-ramp /
   exchange withdrawal). Never fabricate funds or skip the payment.

**Privy signer compatibility:** `signer_mode="privy"` is rejected on-chain
for Base mainnet USDC (EIP-7702 delegation → EIP-1271 → no plain ECDSA);
other chain/token combos are untested. Treat the session EOA as the only
supported signer unless a specific combo has been verified. **Spend guard**: additionally refuses to sign above
`X402_MAX_ATOMIC` (default 1_000_000 = 1 USDC). ⚠️ Signing = spending real
money once settled — confirm with the user before paying unfamiliar services
or raising the cap. Result includes `settlement.transaction` (on-chain tx hash)
— report it and verify per transaction-verification rules.

## Public paid URL (Cloudflare Monetization Gateway parity)

Make any local service a PUBLIC paid API (charge any caller for any resource,
no accounts / API keys needed — same capability set as Cloudflare's
Monetization Gateway, self-hosted):

1. `python3 skills/x402/scripts/make_public.py --name my-api --upstream-port <port> --mode payperuse --route 'GET /api/*=$0.01' --pay-to <wallet>` — scaffolds `output/my-api/start.py` + config
2. `preview(action='serve', dir='output/my-api', command='python3 start.py', port=<gateway_port>)` — note: start the upstream in the same command if it isn't already running
3. `community-publish` skill → `publish_preview(preview_id, slug='my-api')` → public URL
4. Price discovery is built in: `GET <public-url>/.well-known/x402` returns machine-readable routes/prices/payTo/network (Bazaar-compatible shape).

**A public URL is NOT a marketplace listing.** Steps 1–4 only make the
service reachable — the Service Marketplace will show nothing (or "free")
until you complete the LIST chain (community-publish skill):

5. `create_paid_service(name=..., service_type=..., api_endpoint=<public paid
   route>, pricing_model=..., price=..., pricing_options=[...] for
   multi-plan)` → draft service record.
6. `submit_for_review(service_id)` → poll `get_review_status()` until
   `approved` (5 automated checks: 402 reachable, price consistency, x402
   validity, response match, doc completeness) → `publish_service(service_id)`
   → live paid listing.

Skipping 5–6 is the #1 cause of "why does my paid service show as free /
not appear in the marketplace".

## Consuming any x402 service from just a URL

Given ONLY a service URL (no docs, no guidance), onboard and verify it with
this sequence — everything needed is self-describing in the protocol:

1. **Discover** (free): `GET <url>` with no payment headers. A 402 response
   IS the price sheet: `accepts.amount` (atomic USDC), `accepts.pricingModel`,
   `accepts.network`, and — on multi-plan services — a `plans` map with every
   option's accepts. Optionally `GET <base>/.well-known/x402` for a
   machine-readable index of all routes/prices.
2. **Probe plans** (free, multi-plan only): repeat the unpaid GET with
   `X-Pricing-Model: <plan>` — each 402 quotes that plan's exact amount.
   An unknown plan returns HTTP 400 listing the valid ones.
3. **Pay & call**: `client.paid_request("GET", url, max_amount_atomic=<cap>)`
   handles the whole flow (402 → EIP-3009 sign → retry with X-PAYMENT).
   Select a plan with `pricing_model="<plan>"`. Requirements: session EOA
   funded with USDC on the service's network (see Buyer side above); cap =
   your spend guard. Confirm with the user before paying — this is real money.
4. **Verify billing semantics** (subscription modes): call again — the result
   must be 200 with NO new settlement (`paid: true`, no new tx). On multi-plan
   services, requesting a different plan while holding one must also NOT
   re-charge. `settlement.transaction` from step 3 is the on-chain proof —
   report it and verify per transaction-verification rules.

The same sequence doubles as a smoke test of any x402 deployment: steps 1–2
are free and validate the challenge contract; steps 3–4 validate settlement
and access accounting end-to-end.

## Security model (what protects whom)

| Layer | Protection | Where |
|---|---|---|
| Payment forgery | EIP-3009 signature verified off-chain + on-chain `eth_call` simulation before any gas is spent | facilitator |
| Double-credit / replay | settlement `tx_hash` UNIQUE in gateway ledger; facilitator idempotency on `(payer, nonce, asset, network)` — EIP-3009 nonces are per-payer, NOT global; confirmed replays echo success only when pay_to/amount/resource all match (`nonce_reuse_mismatch` otherwise) | ledger + facilitator |
| Gas-drain via open facilitator | `X402_PAYTO_ALLOWLIST` (recipient allowlist) and/or `X402_GATEWAY_TOKENS` (bearer auth) — set at least one on any public deployment; plus per-payer settle rate limit | facilitator |
| Gateway ↔ token-auth facilitator wiring | gateway config `facilitator_token` (env fallback `X402_FACILITATOR_TOKEN`) sends `Authorization: Bearer …` on verify/settle/supported; `monetize.py` / `make_public.py` accept `--facilitator-token`. Templates default to the LOCAL facilitator (`http://127.0.0.1:8410`) — the platform public facilitator is access-controlled and needs explicit facilitator + token | gateway config |
| API key theft | keys are per-payer deterministic HMAC (salt on disk, 0600); no key material in logs | gateway ledger |
| Request flooding | sliding-window rate limit per caller (X-API-Key else IP), `rate_limit_per_min` (default 120) → 429 | gateway |
| Key brute-force | ≥`ban_after_invalid_keys` (default 20) 401s/min from one IP → `ban_seconds` (default 300) temp ban | gateway |
| Settler key risk | key only pays gas — fund flow fixed by buyer signature; can never redirect funds | protocol |
| Buyer overspend | session-EOA budget IS the hard cap + `X402_MAX_ATOMIC` guard | client |
| Admin endpoints | `/x402/stats` + facilitator `/facilitator/stats` are deny-by-default: 503 until an admin token is configured, 401 on mismatch | config |
| Upstream header leak | gateway strips `X-API-Key`, `X-Admin-Token`, `PAYMENT-*` before forwarding to the upstream service | gateway |

Free endpoints (`/x402/info`, `/x402/health`, `/.well-known/x402`) are rate-limited
but unauthenticated by design (discovery must be public).

## Error contract (uniform across all modes)

| Status | `error.code` | Meaning / action |
|--------|--------------|------------------|
| 402 + `PAYMENT-REQUIRED` header | (x402 challenge) | pay & retry (clients do this automatically) |
| 402 | `insufficient_credits` | body has `topup` hint → buyer tops up |
| 401 | `invalid_key` | missing/unknown/revoked X-API-Key |
| 502 | `upstream_error` | upstream dead; units auto-refunded; keepalive will report |
| 502 | `facilitator_error` | facilitator unreachable — check outbound proxy env, retry later |

Facilitator verify failures seen in the wild (2nd 402's `error` field):
- `invalid_exact_evm_insufficient_balance` — buyer wallet lacks USDC (sig was VALID)
- `invalid_signature` — wrong domain (name/version/chainId) or corrupted sig
- expired `validBefore` — client clock skew; SDK uses `maxTimeoutSeconds` (default 300s)

## Troubleshooting

- **Facilitator calls fail from container**: outbound must go through sc-proxy.
  `gateway/app.py` and `client.py` self-configure `HTTPS_PROXY`/`SSL_CERT_FILE`
  from `STARCHILD_API_PROXY_*` env. Set `X402_NO_PROXY=1` only outside Starchild.
- **Verify e2e anytime**: `python3 skills/x402/scripts/verify_setup.py`
  (14 fund-free checks; add `--funded` for a real on-chain settlement once the
  wallet holds USDC on the target network).
- **Ledger inspection**: `sqlite3 /data/workspace/.x402/<name>/state/ledger.db 'select * from payments'`.
- **Gateway logs**: `/data/workspace/.x402/<name>/gateway.log`.
- **Gateway lifecycle — ONE owner per port (hard rule)**: `monetize.py`
  STARTS a background gateway (registered in `.x402/services.json`, revived
  by keepalive). Starting it AGAIN under `preview(serve)` collides: the new
  process fails `address already in use` while the old one keeps answering.
  Pick ONE owner:
  - **preview-managed** (recommended for anything published): run
    `monetize.py ... --no-start` — writes config only and prints the
    `gateway_command`; wrap upstream + gateway in a start.py and
    `preview(action='serve', command='python3 start.py', port=<gateway_port>)`.
    Preview then owns restarts across reboots.
  - **monetize-managed** (local/dev): default behavior. Manage with
    `monetize.py --stop <name>` / `--restart <name>` — restart is REQUIRED
    after editing `x402.config.json` (e.g. testnet→mainnet network switch).
- **Preview "running" ≠ payments working**: preview health checks hit `/`,
  which the gateway proxies to the upstream — 200 there says nothing about
  billing. Verify the gateway itself: `GET /x402/info` returns 200 JSON and
  an unpaid paid-route returns 402. If responses look stale, suspect an old
  process still holding the port (see port hygiene below).
- **Testing gateways locally — port hygiene (hard-won lesson)**: a uvicorn
  gateway whose port is already held FAILS TO BIND but the old process keeps
  answering, so your "new code" test actually exercises the OLD process (and
  its 60s access cache) — false PASSes and false FAILs. Rules:
  1. After starting a test gateway, ALWAYS check its log for
     `address already in use` BEFORE trusting any response from that port.
  2. Kill test processes by LISTENING-PORT PID, never by `ps | grep` name
     matching — backgrounded shells and renamed configs escape name matches.
     NOTE: `ss`/`netstat` are NOT installed in the container. Use:
     `python3 -c "import socket; s=socket.socket(); print('busy' if s.connect_ex(('127.0.0.1',PORT))==0 else 'free')"`
     to test a port, and find the holder by scanning cmdlines:
     `for d in /proc/[0-9]*; do grep -q CONFIG_OR_PORT_HINT $d/cmdline 2>/dev/null && echo $d; done`
     — or simply `monetize.py --stop <name>` which does this for you.
  3. When in doubt, move to brand-new port numbers instead of reusing ones a
     dead-looking process might still hold.
- Python SDK is `x402` v2.10+ (V2 headers `PAYMENT-REQUIRED`/`PAYMENT-SIGNATURE`/
  `PAYMENT-RESPONSE`). Deps are NOT auto-installed: run
  `bash skills/x402/setup.sh` once per machine (also append it to
  `/data/workspace/setup.sh` so restarts reinstall).
