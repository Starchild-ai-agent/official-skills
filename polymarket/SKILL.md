---
name: "polymarket"
version: 5.1.0
description: |
  Polymarket prediction markets: search, place or cancel orders, manage positions.

  Use when betting on event outcomes via Polymarket (e.g. search Iran ceasefire markets, buy YES at 0.65, close my Trump position, list open orders).
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
| 401 / Invalid API key during `--save` | Stale timestamp OR wallet mismatch OR wrong signer | Re-run `--prepare`, re-sign within 5 min, `--save` with the SAME pair |
| 401 / Invalid API key during trading | Stale creds | `scripts/auth.py --check`, re-derive if needed |
| 403 geo-block | US IP | VPN auto-handles; if sc-vpn down → restart infra |
| 400 Invalid order | Wrong tick/amount | `prepare_order.py` auto-normalizes |
| L2_BALANCE_TOO_LOW | No USDC.e | Fund wallet on Polygon |
| Orderbook 0.01/0.99 | Wrong token's book | Check the token you BUY, not complement |

---

## Auth — Defensive Constraints (read before running `--prepare` / `--save`)

The auth flow has three hard rules. Violating any one causes a Polymarket 401 that looks
identical to "bad credentials" but is actually one of these:

**Rule 1 — wallet is current, not remembered.** Always call `wallet_info` first and use
THAT address for `--prepare`. Never reuse a wallet address from memory, an old conversation,
or a previous session. Wallets can rotate; addresses recalled from memory will silently mismatch.

**Rule 2 — signature and timestamp are a pair.** The `timestamp` printed by `--prepare` is
embedded in the EIP-712 message that gets signed. The signature is only valid for THAT
timestamp. Never reuse a timestamp from an earlier `--prepare` with a new signature, or
vice versa. If you have to re-sign for any reason, run `--prepare` again first.

**Rule 3 — 5-minute window.** Polymarket's ClobAuth tolerates ~300s of skew. If more than
5 minutes pass between `--prepare` and `--save`, the auth will be rejected. Re-run `--prepare`.

**If `--save` fails with 401:** do NOT retry `--save` with the same arguments. Restart from
`--prepare`. `auth.py` enforces all three rules above before hitting the API and prints
specific guidance on which rule was violated; the `polymarket_auth` tool does the same.

**Tool path vs script path:** there are two ways to run auth — `polymarket_auth` tool and
`scripts/auth.py`. Pick ONE and stick with it for the whole flow. Mixing them mid-flow
(e.g. tool for step 1, script for step 2) loses the timestamp/wallet linkage and causes
exactly the failure mode described in Rule 2.

---

## Changelog
- **v5.1.0**: Auth hardening. `polymarket_auth` tool now rejects empty signature, invalid timestamp, and stale (>5 min) timestamps with structured error messages instead of falling through to a Polymarket 401. `scripts/auth.py --save` validates signature shape, timestamp staleness, and wallet/timestamp consistency against `/tmp/poly_auth.json` before submission. SKILL.md gains a Defensive Constraints section pinning the three rules that the auth flow enforces.
- **v5.0.0**: Script-first architecture. 6 scripts wrap all flows. BUY order: 8 calls → 3 (2 bash + 1 sign). Status/search/cancel: 0 tool calls. Credential auto-check + auto-derive.
- **v4.3.0**: Fixed HMAC signature, removed POLY_NONCE, mandatory lookup after search.
- **v4.0.0**: Merged official v2.4 + local v3.9. Modular tools/, Privy-only, 13 tools.
