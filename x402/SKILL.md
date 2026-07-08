---
name: x402
version: 2.7.0
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

## Reference files (MUST read before the matching task)

Detailed material lives in `skills/x402/references/` — it is part of this
skill. Do NOT guess or improvise what these files cover:

| Before you… | MUST first `read_file` |
|---|---|
| deploy ANY selling mode beyond basic pay_per_use (full commands, prepaid & multi-plan contracts, admin tokens, templates, gateway lifecycle, always-on/update-mode) | `skills/x402/references/selling.md` |
| debug ANY error (facilitator verify errors, error contract, security model, port ownership, proxy) | `skills/x402/references/troubleshooting.md` |
| use the session EOA signer, fund a buyer wallet, or pay on a non-Base-USDC chain/token | `skills/x402/references/buying-advanced.md` |

## Sell — monetize a service (quick start)

```bash
FAC=https://starchild-x402-facilitator.fly.dev
# pay_per_use: verify -> settle on EVERY request (simplest mode)
python3 skills/x402/scripts/monetize.py --name my-api --upstream-port 5173 \
    --mode pay_per_use --price 0.01 --network eip155:8453 --facilitator $FAC
```

Platform modes follow the community-gateway billing contract: 402 JSON body
with `accepts.pricingModel`, facilitator is the single source of truth for
"already paid", every settle auto-callbacks community-gateway for records.

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

⚠️ lifetime/monthly/weekly/quarterly/yearly REQUIRE `--facilitator-admin-token`
(fail-closed at startup). Multi-plan: `--plan MODE=PRICE` (repeatable).
→ **MUST read `references/selling.md` BEFORE deploying any of these modes** —
it has the exact commands, contract details, and template list.

Output includes `gateway_port`. **Expose the GATEWAY port, not the upstream**
(via `preview` or community-publish). `pay_to` defaults to the user's Privy
EVM wallet — revenue lands there directly.
Registry: `/data/workspace/.x402/services.json`; per-service config/log/state:
`/data/workspace/.x402/<name>/`.

## Networks & facilitators

| Network | ID | Facilitator | Needs |
|---------|----|-------------|-------|
| Base Sepolia (default) | `eip155:84532` | `https://x402.org/facilitator` (default) | nothing |
| Base mainnet | `eip155:8453` | **platform** (`https://starchild-x402-facilitator.fly.dev`, the default; override via `X402_FACILITATOR_URL` or `--facilitator`) | nothing — platform settler pays gas |

The platform facilitator handles /verify + /settle; its settler key only pays
gas — fund flow is fixed by the buyer's signature and can never touch user
funds. Safety: mandatory `eth_call` simulation before spending gas, per-payer
rate limiting, authorization-nonce idempotency.
Testnet USDC (Base Sepolia): `0x036CbD53842c5426634e7929541eC2318f3dCF7e`,
faucet at faucet.circle.com. Prices auto-convert: `$0.01` → `10000` atomic USDC units.

## Keepalive (register once per machine)

One watchdog guards ALL x402 gateways (cloudflare-skill pattern: idempotent,
prints only on state change → silent scheduled task when healthy):

1. Boot: append to `/data/workspace/setup.sh`:
   `bash /data/workspace/skills/x402/scripts/keepalive.sh || true`
2. Watchdog: `scheduled_task(action="schedule", schedule="every 10 minutes", command="bash skills/x402/scripts/keepalive.sh", deliver="origin")` — empty output = silent.
   ⚠️ Use the RELATIVE path (`skills/x402/...`), never `/data/workspace/skills/...` — the
   scheduler's path sanitizer strips `workspace/` from absolute commands, mangling them
   into a nonexistent `/data/skills/...` and the task fails every run. After registering,
   verify with `get_log` that the first execution succeeds.

Gateway down → restarted from its config. Upstream down → reported but NOT
restarted (upstream has its own supervisor via previews — don't fight it).

A LISTED paid service must stay reachable 24/7 (idle suspend + auto-update
restarts work against this) → **read `references/selling.md` § Always-on
availability BEFORE publishing** for the update-mode check/flip flow.

## Buy — pay other agents' x402 services

```bash
python3 skills/x402/client.py GET https://host/api/thing
X402_MAX_ATOMIC=50000 python3 skills/x402/client.py POST https://host/x402/topup
```

`paid_request` auto-detects BOTH 402 flavors: V2 header challenge
(PAYMENT-REQUIRED → x402 SDK path) and the platform JSON-body challenge
(`accepts.pricingModel` → manual EIP-3009 sign → retry with `X-PAYMENT`).
For lifetime/monthly services, repeat calls within the paid period verify but
do NOT settle — the result has `paid: true` with no new on-chain tx.

**Buyer signer = Privy wallet by default** (`signer_mode="auto"`); smart
accounts are detected and signed via an ERC-1271-compatible path
automatically. Do NOT revoke the wallet's delegation (it powers gas
sponsorship). `auto` is FAIL-CLOSED: if the Privy signer cannot be
initialized, `paid_request` raises instead of paying from a different
identity — allow the session-EOA fallback only explicitly via
`allow_fallback_eoa=True` / env `X402_FALLBACK_EOA=1` / `signer_mode="eoa"`.
Every result includes `signer_type` (`"privy"` | `"session_eoa"`); an
opted-in fallback also sets `signer_warning` — check them to confirm which
identity actually paid. ⚠️ The two signers are DIFFERENT payer identities:
subscriptions/prepaid balances do NOT carry over between them.
→ **EOA funding steps and signer internals: read
`references/buying-advanced.md` BEFORE using the session EOA.**

**Spend guard**: refuses to sign above `X402_MAX_ATOMIC` (default
1_000_000 = 1 USDC). ⚠️ Signing = spending real money once settled — confirm
with the user before paying unfamiliar services or raising the cap. Paid
response bodies are returned in FULL; unpaid/error bodies are capped at 2000
chars (env `X402_BODY_MAX`, 0 = unlimited). Result includes
`settlement.transaction` (on-chain tx hash) — report it and verify per
transaction-verification rules.

### Payment ledger (every payment is recorded locally)

`client.py` appends every payment it signs to
`$WORKSPACE/.x402/payments.jsonl` (override path: env `X402_LEDGER`). Each
line is one JSON event: `signed` (authorization submitted — url, amount,
payTo, payer, caller) and `result` (HTTP status, paid, settlement tx). The
`caller` field identifies who spent the money (`SC_CALLER_ID` / `JOB_ID` /
pid), so payments made from background sessions are attributable too.

To answer "where did this USDC go": read the ledger first, then reconcile
against the wallet's on-chain USDC transfers — every outgoing transfer must
match a ledger line. Ledger writes are best-effort and never block a payment.

### Spending rules for automated sessions

- A background / scheduled / spawned session MUST NOT make x402 payments
  unless its task explicitly grants a budget; set `X402_MAX_ATOMIC` to that
  budget for the session.
- Every payment an automated session makes MUST appear in its final output
  (amount, url, settlement tx) — a payment only in the ledger is auditable
  but still counts as unreported work.
- On any 4xx payment rejection, do not retry with a fresh payment: each
  retry can spend again. Diagnose first.

## Public paid URL (Cloudflare Monetization Gateway parity)

Make any local service a PUBLIC paid API (charge any caller for any resource,
no accounts / API keys needed — same capability set as Cloudflare's
Monetization Gateway, running on your own machine):

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
   Select a plan with `pricing_model="<plan>"`. Payer = the Privy wallet by
   default (`signer_mode="auto"`); it must hold USDC on the service's network.
   The session EOA needs funding ONLY if you pin `signer_mode="eoa"` or the
   result reports `signer_type: "session_eoa"` (see Buyer side above). cap =
   your spend guard. Confirm with the user before paying — this is real money.
   Check `signer_type` in the result: it tells you WHICH identity actually
   paid. If the Privy signer is unavailable, `auto` raises (fail-closed)
   rather than silently paying from the session EOA; a `signer_warning`
   appears only when the fallback was explicitly allowed.
4. **Verify billing semantics** (subscription modes): call again — the result
   must be 200 with NO new settlement (`paid: true`, no new tx). On multi-plan
   services, requesting a different plan while holding one must also NOT
   re-charge. `settlement.transaction` from step 3 is the on-chain proof —
   report it and verify per transaction-verification rules.

The same sequence doubles as a smoke test of any x402 deployment: steps 1–2
are free and validate the challenge contract; steps 3–4 validate settlement
and access accounting end-to-end.

### Non-standard "tx-hash" services (NOT x402 V2 — client.py cannot pay them)

Some third-party marketplaces skip the signed `X-PAYMENT` flow entirely: their
402 body instructs the buyer to first send a raw on-chain USDC transfer to a
platform wallet, then resubmit with the tx hash in a header (e.g.
`X-Payment-TxHash`). Recognize them at step 1 — the 402 mentions a transfer +
tx-hash header instead of an `accepts` payment challenge. `client.py` is
incompatible by design (EIP-3009 signing never produces a tx hash), and the
scheme itself is unsafe to pay:

- A tx hash on a public chain is a bearer token: anyone watching the shared
  recipient wallet can submit YOUR hash first, and the service's global
  anti-replay then rejects the rightful buyer (`TX_ALREADY_USED` / 409) with
  no refund.
- Sponsored smart-wallet transfers add another mismatch: the on-chain `from`
  is a bundler, not the payer, so `tx.from`-based checks fail.

If a service demands this flow: use the vendor's own SDK if it submits the
payment atomically, or skip the service. Do NOT burn USDC retrying a 409 —
each retry needs a fresh transfer and loses the same race.

## Errors & diagnostics

Payment or gateway failing → **MUST read `references/troubleshooting.md`**
(error contract, facilitator verify errors, security model, port ownership
checks, proxy config). Quick e2e check anytime:
`python3 skills/x402/scripts/verify_setup.py` (fund-free; `--funded` adds a
real settlement test).

## Setup

Python SDK is `x402` v2.10+. Deps are NOT auto-installed: run
`bash skills/x402/setup.sh` once per machine (also append it to
`/data/workspace/setup.sh` so restarts reinstall).
