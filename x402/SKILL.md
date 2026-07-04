---
name: x402
version: 1.5.2
description: |
  Monetize any user project/service with the x402 payment protocol on Base, and pay other agents' x402 services.

  Use when the user wants to charge for an API/service (per-call, subscription top-up, or metered billing), accept USDC from other agents, or call a paid x402 endpoint.
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

## Quick start — monetize a service

```bash
# per-call pricing (pure x402, no accounts)
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

Output includes `gateway_port`. **Expose the GATEWAY port, not the upstream**
(via `preview` or community-publish). `pay_to` defaults to the user's Privy
EVM wallet — revenue lands there directly.

Registry of all monetized services: `/data/workspace/.x402/services.json`.
Per-service config/log/state: `/data/workspace/.x402/<name>/`.

## Billing mode decision table

| Mode | Buyer UX | When |
|------|----------|------|
| `payperuse` | pay per request, no account | simple data endpoints, agent-to-agent one-shots |
| `subscription` | x402 top-up → API key + N credits, 1 credit/call | repeat customers, avoids per-call payment latency |
| `metered` | like subscription, route-weighted units | mixed cheap/expensive endpoints (LLM calls etc.) |
| `timepass` | x402 payment → N-day unlimited access pass on an API key | monthly plans, content/tool sites |

Ready-to-use config templates (fill `pay_to` + `upstream`): `templates/payperuse.json`,
`templates/subscription.json`, `templates/metered.json`, `templates/timepass.json`.
All four modes verified with REAL Base-mainnet settlements (2026-07-03):
subscription 0x3c4a9371…, metered 0xd1070f32…/0x81e668b7…, timepass pass_active
until expiry, payperuse 0x671119cb…. Timepass CLI: `--mode timepass
--pass-days 30 --pass-price 4.99`; repeat purchases EXTEND expiry from
max(now, current expiry).

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
full settlement ledger at `/facilitator/stats`. Platform deployment package
(Dockerfile + fly.toml + OPS.md): `output/x402-facilitator-deploy/`. Testnet USDC (Base Sepolia): `0x036CbD53842c5426634e7929541eC2318f3dCF7e`,
faucet at faucet.circle.com. Prices auto-convert: `$0.01` → `10000` atomic USDC units.

## Keepalive (register once per machine)

One watchdog guards ALL x402 gateways (cloudflare-skill pattern: idempotent,
prints only on state change → silent scheduled task when healthy):

1. Boot: append to `/data/workspace/setup.sh`:
   `bash /data/workspace/skills/x402/scripts/keepalive.sh || true`
2. Watchdog: `scheduled_task(action="schedule", schedule="every 10 minutes", command="bash /data/workspace/skills/x402/scripts/keepalive.sh", deliver="origin")` — empty output = silent.

Gateway down → restarted from its config. Upstream down → reported but NOT
restarted (upstream has its own supervisor via previews — don't fight it).

## Buyer side — pay other agents' x402 services

```bash
python3 skills/x402/client.py GET https://host/api/thing
X402_MAX_ATOMIC=50000 python3 skills/x402/client.py POST https://host/x402/topup
```

**Buyer signer = session EOA by default** (`.x402/buyer.key`, auto-generated).
⚠️ Do NOT sign EIP-3009 with the Privy wallet on Base mainnet: the Privy
address carries EIP-7702 delegation code, so USDC verifies via EIP-1271 and
rejects plain ECDSA on-chain (`FiatTokenV2: invalid signature`) — even though
off-chain recovery passes. Verified 2026-07. Fund the session EOA with a small
USDC budget from the Privy wallet (ERC20 transfer); the budget IS the hard
spend cap. **Spend guard**: additionally refuses to sign above
`X402_MAX_ATOMIC` (default 1_000_000 = 1 USDC). ⚠️ Signing = spending real
money once settled — confirm with the user before paying unfamiliar services
or raising the cap. Result includes `settlement.transaction` (on-chain tx hash)
— report it and verify per transaction-verification rules.

## Public paid URL (Cloudflare Monetization Gateway parity)

Make any local service a PUBLIC paid API (charge any caller for any resource,
no accounts / API keys needed — same capability set as Cloudflare's
Monetization Gateway announced 2026-07-01, but works today and self-hosted):

1. `python3 skills/x402/scripts/make_public.py --name my-api --upstream-port <port> --mode payperuse --route 'GET /api/*=$0.01' --pay-to <wallet>` — scaffolds `output/my-api/start.py` + config
2. `preview(action='serve', dir='output/my-api', command='python3 start.py', port=<gateway_port>)` — note: start the upstream in the same command if it isn't already running
3. `community-publish` skill → `publish_preview(preview_id, slug='my-api')` → public URL
4. Price discovery is built in: `GET <public-url>/.well-known/x402` returns machine-readable routes/prices/payTo/network (Bazaar-compatible shape).

Verified live 2026-07-03: https://community.iamstarchild.com/2004-x402-demo —
public unpaid call → 402 challenge; paid_request through the PUBLIC url settled
on Base mainnet (tx 0x73669f5f…a6d6, $0.01).

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
- Python SDK is `x402` v2.10+ (V2 headers `PAYMENT-REQUIRED`/`PAYMENT-SIGNATURE`/
  `PAYMENT-RESPONSE`); install line lives in `setup.sh`.
