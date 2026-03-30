---
name: "polymarket"
version: 5.0.0
description: "Trade Polymarket prediction markets via Privy wallet. Script-first: most flows are 1 bash + 1 sign. Search, analyze, place/cancel orders, manage positions."
author: starchild
tags: [polymarket, trading, prediction-markets, polygon, defi]
tools:
  - wallet_sign_typed_data
metadata:
  starchild:
    emoji: "🎲"
    skillKey: polymarket-trade
    requires:
      env:
        - POLY_API_KEY
        - POLY_SECRET
        - POLY_PASSPHRASE
        - POLY_WALLET
---

# Polymarket Trading Skill v5.0.0

Trade on Polymarket CLOB via **Privy wallet** (EOA, signature_type=0). No private key needed.

**Script-first architecture**: complex flows are wrapped in `scripts/`. Agent calls bash + one sign.

---

## Scripts (Primary Interface)

All scripts are in `skills/polymarket/scripts/`. Each is self-contained with VPN, auth, error handling.

### 🔍 Search
```bash
bash("cd skills/polymarket && python3 scripts/search.py 'US Iran ceasefire'")
```
**Output**: JSON with events, markets, outcomes (name + price + token_id). Ready for ordering.
**Calls**: 0 tool calls. Everything in one bash.

### 💰 Status (balance + positions + orders)
```bash
bash("cd skills/polymarket && python3 scripts/status.py")
```
**Output**: Balance, open positions, open orders, recent trades — all in one shot.
**Calls**: 0 tool calls.

### 🔐 Auth (first-time or refresh)
```bash
# Step 1: Check if credentials exist and work
bash("cd skills/polymarket && python3 scripts/auth.py --check")

# If missing/stale → Step 2: Prepare signing payload
bash("cd skills/polymarket && python3 scripts/auth.py --prepare 0xWALLET")

# Step 3: Sign (ONLY tool call that can't be scripted)
wallet_sign_typed_data(domain, types, primaryType, message)  # from /tmp/poly_auth.json

# Step 4: Save derived credentials
bash("cd skills/polymarket && python3 scripts/auth.py --save 0xSIG 0xWALLET TIMESTAMP")
```
**Calls**: 1-2 tool calls (check may suffice; full re-derive = 1 sign + 2 bash).

### 📈 Place Order (BUY or SELL)
```bash
# Step 1: Prepare (fetches market info + orderbook + builds EIP-712)
bash("cd skills/polymarket && python3 scripts/prepare_order.py TOKEN_ID BUY 0.76 13")

# Step 2: Sign (read /tmp/poly_order.json for domain/types/message)
wallet_sign_typed_data(domain, types, primaryType="Order", message)

# Step 3: Submit + verify
bash("cd skills/polymarket && python3 scripts/post_order.py 0xSIGNATURE")
```
**Calls**: 1 tool call (sign) + 2 bash. Down from 8 tool calls.

### ❌ Cancel Orders
```bash
bash("cd skills/polymarket && python3 scripts/cancel.py --all")
# or
bash("cd skills/polymarket && python3 scripts/cancel.py --id 0xORDER_ID")
```
**Calls**: 0 tool calls.

### 🔄 Close Positions
```bash
# Step 1: Build SELL orders for all positions
bash("cd skills/polymarket && python3 scripts/close_positions.py")

# Step 2: For each /tmp/poly_close_N.json:
wallet_sign_typed_data(...)  # sign each
bash("cd skills/polymarket && python3 scripts/post_order.py 0xSIG --order /tmp/poly_close_N.json")
```
**Calls**: N signs + N bash (one per position).

---

## Token ID & Orderbook Cheat Sheet

### YES/NO Are Complements
Each market has TWO tokens. Their prices sum to ~$1.00.
- YES at 0.25 ↔ NO at 0.75
- Buying NO at 0.75 = betting AGAINST the event

### Which token_id?
| Bet | Action | Token | Price |
|---|---|---|---|
| Event happens | BUY YES | `outcomes[0].token_id` | YES price |
| Event doesn't happen | BUY NO | `outcomes[1].token_id` | NO price |

### Orderbook Rule
Always check the book for the token you intend to BUY.
- **BUY**: your entry price ≈ `best_ask`
- **SELL**: your exit price ≈ `best_bid`
- If book shows 0.01/0.99 → you're looking at the wrong token

---

## Architecture

| Mode | sig_type | How it works | Gas? |
|---|---|---|---|
| **EOA (we use this)** | `0` | Agent wallet = signer AND maker | Yes for one-time approvals |

**Collateral**: USDC.e on Polygon. NOT native USDC.

---

## VPN

CLOB API is geo-blocked from US. Scripts handle this transparently:
1. Direct → if 403 → parallel-test VPN regions → cache fastest
2. Endpoint: `http://{region}:x@sc-vpn.internal:8080` (HTTP proxy)
3. Regions: `ar, br, mx, my, th, au, za` (also: `au, ch, de, jp`)
4. Override: `POLY_VPN_REGION=ar` or `POLY_DISABLE_VPN=true`

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| 401 / Invalid API key | Stale creds | `scripts/auth.py --check`, re-derive if needed |
| 403 geo-block | US IP | VPN auto-handles; if sc-vpn down → restart infra |
| 400 Invalid order | Wrong tick/amount | `prepare_order.py` auto-normalizes |
| L2_BALANCE_TOO_LOW | No USDC.e | Fund wallet on Polygon |
| Orderbook 0.01/0.99 | Wrong token's book | Check the token you BUY, not complement |

---

## Changelog
- **v5.0.0**: Script-first architecture. 6 scripts wrap all flows. BUY order: 8 calls → 3 (2 bash + 1 sign). Status/search/cancel: 0 tool calls. Credential auto-check + auto-derive.
- **v4.3.0**: Fixed HMAC signature, removed POLY_NONCE, mandatory lookup after search.
- **v4.0.0**: Merged official v2.4 + local v3.9. Modular tools/, Privy-only, 13 tools.
