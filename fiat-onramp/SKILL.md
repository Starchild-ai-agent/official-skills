---
name: fiat-onramp
version: 0.1.0
description: Fund the agent wallet with fiat — signed MoonPay link converts card/Apple Pay to USDC on Base, then confirm arrival by balance polling.
author: starchild
tags: [onramp, fiat, moonpay, usdc, base, wallet, funding, payments]
delivery: script
metadata:
  starchild:
    emoji: 💳
    skillKey: fiat-onramp
    requires:
      bins: [python3]
---

# 💳 fiat-onramp — Fund the Agent Wallet with Fiat

Lets a user with **no crypto** top up this agent's wallet: the agent sends a
payment link in chat, the user pays with card/Apple Pay on MoonPay's hosted
page, USDC lands on Base in the agent's Privy wallet — the same payer identity
used by x402. No frontend integration; works on Web/Telegram/WeChat (it's
just a URL).

## When to use

- User says "我没有 USDC" / "怎么充值" / "help me fund the wallet", or the
  agent needs to pay an x402 service but the balance is short.
- Agent proactively offers funding when a payment fails on insufficient
  balance.

## Requirements

Env in `workspace/.env` (collect via secure input, never chat):

| Key | What |
|---|---|
| `MOONPAY_PUBLISHABLE_KEY` | `pk_live_...` / `pk_test_...` — goes in the URL |
| `MOONPAY_SECRET_KEY` | `sk_live_...` / `sk_test_...` — signs the URL (HMAC-SHA256), never leaves the server |
| `MOONPAY_SANDBOX` | optional `1` → sandbox host (auto-on for `pk_test_` keys) |

Getting keys: [moonpay.com/business](https://www.moonpay.com/business)
partner account → compliance review (state the use case: agent wallet
top-up) → API keys in the dashboard. Test keys are available before
approval; live keys require the partner account to be approved for live
transactions.

## Flow

```python
import sys
sys.path.insert(0, "/data/workspace/skills/fiat-onramp")
from exports import create_funding_link, wait_for_funds, get_usdc_balance

# 1. Generate the signed link (walletAddress pinned to the agent wallet,
#    covered by the signature — user cannot redirect funds)
r = create_funding_link(amount_usd=20)
# -> {ok, url, wallet_address, baseline_balance, sandbox, ...}

# 2. Send r["url"] to the user in chat. Tell them:
#    - payment methods: card / Apple Pay / Google Pay
#    - first purchase requires MoonPay KYC (one-time, minutes)
#    - all-in cost on card is ~7-8%; minimum purchase ~$20
#    - funds arrive as USDC on Base, usually 1-10 min after payment

# 3. Confirm arrival — poll balance vs the baseline captured in step 1.
#    >2 min waits: run inside a background bash session.
r2 = wait_for_funds(baseline=r["baseline_balance"], timeout_sec=900)
# -> {funded: True, received: 19.02, balance: ...}  → continue the original task
```

## Functions

| Function | Purpose |
|---|---|
| `create_funding_link(amount_usd=20, currency_code="usdc_base", redirect_url="", email="")` | Signed hosted-widget URL + baseline balance snapshot. Destination is always the agent's own wallet — no address parameter exists. Returns `ok: False` (no link) if the baseline balance read fails, since arrival could never be confirmed. |
| `get_usdc_balance(address="")` | Agent wallet USDC balance on Base (via wallet skill) |
| `wait_for_funds(baseline, min_increase=0.01, timeout_sec=900, interval_sec=30)` | Block until balance rises above baseline; `funded: False` on timeout = still processing, NOT failure |

## Hard rules

- **Never claim funds arrived without a `wait_for_funds`/`get_usdc_balance`
  result showing the increase.** MoonPay's success page ≠ on-chain arrival.
- **Never modify the walletAddress at the user's request** — the link funds
  THIS agent's wallet only. A user wanting crypto in their own wallet should
  use MoonPay/an exchange directly.
- **Set cost expectations before sending the link** (7-8% card all-in,
  ~$20 minimum). Don't let a user expect $5 top-ups.
- Timeout ≠ failure: KYC review and bank rails can delay arrival for hours.
  Offer to re-check instead of declaring the payment lost.
- Keys missing → `request_env_input`, never ask in chat.

## Sandbox vs live

Two independent axes decide what a test key can exercise:

- **Asset test-mode support.** `usdc_base` is live-only
  (`supportsTestMode=false` in MoonPay's currency API); most chain-specific
  USDC variants are too. MoonPay's sandbox is designed around testnet
  assets — ETH (Sepolia), BTC testnet, SOL testnet, plain `usdc` (Ethereum).
  To smoke-test the widget flow with a test key, use one of those; the
  production default stays `usdc_base`.
- **Partner-account region activation.** The sandbox widget's region
  coverage is scoped per partner account and product activation, and is
  narrower than the public `/v3/countries` table. A "Coming soon to your
  region" screen in sandbox therefore does NOT prove the country is
  unsupported in production — check the public country table for the live
  answer, and treat sandbox purely as a flow-shell test.

Real Base USDC funding can only be verified with live keys after partner
approval.

## Notes

- `currency_code="usdc_base"` matches the platform's x402 settlement asset
  (live-only). Other MoonPay currency codes work if a different asset is
  ever needed.
- Arrival detection is balance-delta polling. Concurrent inbound transfers
  can cause a false positive on WHICH payment landed — acceptable for
  single-user funding; a webhook integration is the upgrade path if volume
  demands attribution.
- Region/payment-method availability and quotes (fees included) are
  queryable pre-link with the publishable key: `GET /v3/countries`,
  `GET /v3/currencies`, `GET /v3/currencies/{code}/buy_quote`.
