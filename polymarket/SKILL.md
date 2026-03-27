---
name: "polymarket"
version: 2.4.0
description: "Trade on Polymarket prediction markets. Buy/sell outcome tokens via CLOB. Requires USDC.e on Polygon + wallet policy for EIP-712 signing."
author: starchild
tags: [polymarket, trading, prediction-markets, polygon, defi]
tools:
  - polymarket_lookup
  - polymarket_search
  - polymarket_quick_prepare
  - polymarket_get_positions
  - polymarket_get_balance
  - polymarket_get_orders
  - polymarket_get_trades
  - polymarket_post_order
  - polymarket_orderbook
  - polymarket_rr_analysis
  - polymarket_cancel_order
  - polymarket_cancel_all
  - polymarket_prepare_order
  - polymarket_auth
  - wallet_sign_typed_data
  - wallet_transfer
  - web_search
  - web_fetch
metadata:
  starchild:
    emoji: "🎲"
    skillKey: polymarket-trade
    requires:
      env: [POLY_API_KEY, POLY_SECRET, POLY_PASSPHRASE, POLY_WALLET]
---

# Polymarket Trading

Trade on Polymarket CLOB in **EOA mode** (signature_type=0). Agent wallet = signer AND maker directly — no proxy wallet.

## ⚠️ USDC.e Required (NOT Native USDC)

Polymarket **only** accepts USDC.e (bridged): `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174`
Native USDC (`0x3c499c...`) does NOT work. Swap via 1inch if needed.

## First-Time Setup

Say **"I want to trade on Polymarket"** — agent auto-handles:

1. **Credentials** — `polymarket_auth` signs EIP-712 ClobAuth, saves keys to `.env` (instant, no restart)
2. **Fund wallet** — Send USDC.e + ~1 POL (gas) to agent wallet on Polygon
3. **Approve** — One-time USDC.e approval to both CTF Exchange contracts:
   - CTF Exchange: `0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E`
   - CTF Neg-Risk: `0xC5d563A36AE78145C45a50134d48A1215220f80a`
4. **Verify** — `polymarket_get_balance()` confirms readiness

**Wallet policy needed**: `eth_signTypedData_v4` + `eth_sendTransaction` on chain 137.

## VPN Auto-Detection

Zero config. On 403 geo-block, auto-tests regions (br/ar/mx/my/th/au/za), caches fastest. Override: `POLY_VPN_REGION=br` or `POLY_DISABLE_VPN=true`.

## APIs

| API | Base URL | Auth | Purpose |
|-----|----------|------|---------|
| CLOB | `clob.polymarket.com` | HMAC L2 | Orders, balance, orderbook |
| Data | `data-api.polymarket.com` | Public | Positions, trades (historical) |
| Gamma | `gamma-api.polymarket.com` | Public | Markets, events, search |

## ⚠️ MANDATORY: Confirm Before Betting

**NEVER place a bet without explicit user confirmation.** Always: research → present R/R → wait for approval → execute.

## 🚀 Fast Workflow (Recommended)

4 tool calls total:
1. `polymarket_lookup(url)` — get market info + token_ids
2. `polymarket_quick_prepare(token_id, side, size_usd)` — balance + orderbook + R/R + order prep in ONE call
3. `wallet_sign_typed_data(eip712)` — sign the order
4. `polymarket_post_order(token_id, signature, meta)` — submit

## Manual Workflow

1. `polymarket_lookup(url_or_slug)` / `polymarket_search(query)`
2. `polymarket_orderbook(token_id)` + `polymarket_rr_analysis(token_id, side, size_usd)`
3. Present bet summary, wait for confirmation
4. `polymarket_get_balance()` → `polymarket_prepare_order(token_id, side, price, size)` → sign → `polymarket_post_order()`
5. `polymarket_get_orders()` to verify

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Balance shows $0 | Have native USDC, not USDC.e | Swap via 1inch to USDC.e (`0x2791...`) |
| Balance $0 in EOA mode | Normal — USDC.e stays in wallet until fills | Check wallet balance directly, not CLOB balance |
| "Not enough balance" after approval | 10-15s sync delay | Wait 30s, recheck `polymarket_get_balance()` |
| Signature error | Order expired or wrong format | Use `quick_prepare`, sign + post immediately |
| Approval tx fails | Insufficient POL | Need ~0.5-1 POL for gas |

## Key Facts

- Prices = probabilities: $0.55 = 55% implied, pays $1 if correct
- tick_size: 0.01 or 0.001 (check market data)
- neg_risk markets use CTF Exchange Neg-Risk contract
- Orders are GTC by default
- Min order ~5 tokens
- EOA = signature_type 0
