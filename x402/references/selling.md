# x402 Selling Reference — full mode commands, contracts, operations

Complete command examples, billing contracts, and deployment operations.
Read this BEFORE deploying any mode beyond a basic `pay_per_use`.

## Platform modes — full commands & contract

Platform modes implement the Starchild community-gateway billing contract
(x402-facilitator `docs/pricing-models.md`): 402 JSON body with `accepts` as a
**list** (multi-accepts, one entry per network — the buyer picks one chain per
payment), `accepts[].pricingModel`, buyer sends `X-PAYMENT`, the **facilitator
is the single source of truth for "already paid"** (no local payment state),
and every settle auto-callbacks community-gateway for purchase/call records.

### Multi-chain: `--networks all` (default) vs custom

By default a service follows the **platform mainnet full set** (Base + Monad +
Robinhood): the 402 challenge returns an accepts list with one entry per chain,
and the buyer picks one chain to pay on. Lock to specific chains with
`--networks` (comma-separated CAIP-2 list).

```bash
FAC=https://starchild-x402-facilitator.fly.dev

# pay_per_use: verify -> settle on EVERY request
# --networks defaults to "all" (Base + Monad + Robinhood mainnet); omit it to follow the
# platform full set. The 402 returns a multi-accepts list.
python3 skills/x402/scripts/monetize.py --name my-api --upstream-port 5173 \
    --mode pay_per_use --price 0.01 --facilitator $FAC

# custom: lock to a single chain (or a comma-separated list)
python3 skills/x402/scripts/monetize.py --name my-api --upstream-port 5173 \
    --mode pay_per_use --price 0.01 --networks eip155:8453 --facilitator $FAC

# lifetime: one payment = permanent access (checked via /facilitator/access-status)
# The gateway checks access-status automatically:
#   - With --facilitator-admin-token: calls facilitator directly
#   - Without it: proxies through community-gateway (COMMUNITY_GATEWAY_URL env,
#     already set in user containers) which holds the admin token server-side
python3 skills/x402/scripts/monetize.py --name my-api --upstream-port 5173 \
    --mode lifetime --price 5.00 --facilitator $FAC

# monthly: natural-month subscription (same day next month, clamped to month end;
# expiry computed from /facilitator/settlements confirmed_at)
python3 skills/x402/scripts/monetize.py --name my-api --upstream-port 5173 \
    --mode monthly --price 10.00 --facilitator $FAC

# weekly / quarterly / yearly: fixed-length subscriptions (7/90/365 days after the
# newest qualifying payment).
# Facilitator contract: queried as access-status pricing_model=monthly +
# period_days=7/90/365 (monthly WITHOUT period_days = natural-month semantics).
python3 skills/x402/scripts/monetize.py --name my-api --upstream-port 5173 \
    --mode weekly --price 3.00 --facilitator $FAC

# multi-plan (docs/pricing-models.md): --mode is the DEFAULT plan,
# each --plan MODE=PRICE adds an option. Buyers pick a plan per request with the
# X-Pricing-Model header; the 402 quotes THAT plan's amount (audit requirement).
# pay_per_use cannot be combined with other plans.
python3 skills/x402/scripts/monetize.py --name my-api --upstream-port 5173 \
    --mode monthly --price 10.00 --plan weekly=3 --plan yearly=90 \
    --facilitator $FAC

# prepaid: one on-chain deposit, then every call is a millisecond off-chain debit.
# For HIGH-FREQUENCY / metered APIs: no per-call settle (2-5s + gas + 30/min
# rate limit), per-call price can be sub-cent. --deposit = suggested top-up size
# (default 100 calls worth, min $0.10 = facilitator X402_MIN_DEPOSIT_AMOUNT).
# Prepaid balance is cumulative across chains: a buyer who deposits on Monad
# can spend on Base (same pooled (payer, pay_to) balance).
python3 skills/x402/scripts/monetize.py --name my-api --upstream-port 5173 \
    --mode prepaid --price 0.001 --deposit 1.00 --facilitator $FAC
```

Default protected routes: `/api/*` (override with `--route 'METHOD /path'`;
one service price via `--price` — platform modes have no per-route pricing).
lifetime/monthly/weekly/quarterly/yearly check "already paid" via the
facilitator's `/access-status` endpoint. The gateway resolves this
automatically: with `--facilitator-admin-token` it calls the facilitator
directly; without it, it proxies through community-gateway
(`COMMUNITY_GATEWAY_URL`, already set in user containers) which holds the
admin token server-side — **no admin token needed in user containers**.
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
API keys, credit refunds on upstream 5xx). For new deployments prefer
`--mode prepaid` (same prepaid-credit UX, balance held by the facilitator
instead of a local SQLite file); use these modes only when you need
`timepass` (no platform equivalent) or to keep an existing deployment running.

Output includes `gateway_port`. **Expose the GATEWAY port, not the upstream**
(via `preview` or community-publish). `pay_to` defaults to the user's Privy
EVM wallet — revenue lands there directly.

Registry of all monetized services: `/data/workspace/.x402/services.json`.
Per-service config/log/state: `/data/workspace/.x402/<name>/`.

## Billing mode decision notes

Prefer **platform** modes: they match the community-gateway audit checklist,
get automatic purchase/call records via the settle callback, and keep zero
payment state in the gateway. `prepaid` supersedes the local-ledger
`subscription`/`metered` modes for new deployments: same prepaid-credit UX,
but the balance lives in the FACILITATOR (survives gateway restarts/moves,
auditable by platform ops) instead of a gateway-local SQLite file. The
legacy/extended modes remain for pre-2.1 deployments and for the timepass
model the platform contract doesn't cover.

### How prepaid works (facilitator balance primitives)

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

Contract details:
- 402 challenge: `accepts` is a **list** (multi-accepts, one entry per
  network); each entry has `pricingModel = "prepaid"`, `amount` = per-call
  price normally (deposit size when topping up), and extra fields
  `depositAtomic` + `pricePerCallAtomic` telling buyers both numbers.
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
- **Multi-chain cumulative balance**: the facilitator ledger key is
  `(payer, pay_to)`, NOT per-network. A buyer who deposits on Monad can spend
  on Base — the balance is pooled. The buyer picks one chain per deposit
  (one accept from the multi-accepts list); the resulting credit is chain-agnostic.

### Connecting to the marketplace (community-publish)

After `monetize.py` starts the gateway, list the service on the marketplace
via the `community-publish` skill so buyers can discover and pay it:

```python
# community-publish skill (required fields shown; see community-publish SKILL.md)
create_paid_service(
    name="my-api",
    description="Short description of the paid API",
    category="工具服务",
    service_type="paid_api",          # or "paid_project" — NOT "api"
    api_endpoint="https://community.iamstarchild.com/<user>-<slug>/api/data",
    provider_wallet="<your EVM address — same on every chain>",
    pricing_model="pay_per_use",      # or lifetime/monthly/weekly/...
    price=0.01,                       # float USDC, not a string
    api_documentation="...",          # required for paid_api
    example_request="...",            # required for paid_api
    example_response="...",           # required for paid_api
    # networks_mode="all" is the default — omit it to follow platform mainnets
    # networks_mode="custom", supported_networks=["eip155:8453"],  # lock chain
)
publish_service(service_id)
```

The listing's `networks_mode` should match the gateway's config: `all` for a
multi-accepts gateway (default), `custom` + a list for a locked-chain gateway.
The marketplace reads `all` as "current platform full set" at display time, so
adding a new chain later requires no listing update.

### Multi-plan services (docs/pricing-models.md)

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

Agents can also SET the mode for their own machine (container JWT, scoped —
writing another machine's id returns 403):

    curl -s -X PUT -H "Authorization: Bearer $CONTAINER_JWT" \
      -H "Content-Type: application/json" -d '{"update_mode":"manual"}' \
      "$AI_AGENT_API_URL/api/cloud/internal/machines/$FLY_MACHINE_ID/update-mode"
    # → {"update_mode": "manual"}   (or "auto" to re-enable)

Publish flow requirement: after listing a paid service, read the mode — if
"auto", recommend switching to manual and, WITH the user's confirmation,
flip it via the PUT above (never switch silently). The web dashboard toggle
(`PUT /containers/{id}/update-preference`, user JWT) remains available. In
manual mode the web UI shows a banner when an update is pending; mandatory
updates still force-apply after the grace period (keepalive then restores
the service after the restart).
