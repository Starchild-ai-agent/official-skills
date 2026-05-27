---
name: "polymarket"
version: 6.0.0
description: |
  Trade on Polymarket prediction markets (CLOB V2) from a Privy EOA wallet.
  Search markets, place/cancel orders, manage positions. No private key handling.

  Use when the user wants to bet on event outcomes (e.g. "buy YES at 0.65 on the
  ceasefire market", "what are my open positions", "close my Trump bet").
author: starchild
tags: [polymarket, trading, prediction-markets, polygon, defi]
tools:
  - wallet_sign_typed_data
  - wallet_transfer
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

# Polymarket Trading (CLOB V2)

Script-first. Every workflow is one bash call + at most one `wallet_sign_typed_data` (which can't be scripted because it's a wallet RPC). Verified live: see Changelog v5.1.0.

---

## TL;DR — Trade in 3 steps

```bash
# 1. One-time setup (idempotent — safe to re-run)
python3 scripts/setup.py --all 10        # wrap 10 USDC.e -> pUSD + all approvals

# 2. Find a market
python3 scripts/search.py "trump" --limit 3   # returns token_ids

# 3. Place order
python3 scripts/prepare_order.py <token_id> BUY <price> <size>
# → sign /tmp/poly_order.json via wallet_sign_typed_data
python3 scripts/post_order.py <signature>
```

All scripts live in `skills/polymarket/scripts/` and assume working dir is the skill folder.

---

## Account prerequisites (one-time, on-chain)

CLOB V2 settles in **pUSD** (an ERC-20 USDC wrapper), NOT raw USDC.e. Before the first order, the EOA must:

1. Hold USDC.e on Polygon (any amount ≥ what you want to trade).
2. Wrap USDC.e → pUSD via `CollateralOnramp.wrap()`.
3. `approve(pUSD, spender, MAX)` for the 3 V2 exchange spenders.
4. `setApprovalForAll(CTF, spender, true)` for the same 3 spenders (needed for SELL/redemption).

`scripts/setup.py` does all of this and is **idempotent**: it reads on-chain state and skips anything already done. Gas is sponsored by the Privy/Alchemy paymaster — user pays 0 MATIC.

```bash
python3 scripts/setup.py                  # dry-run: show current state + next step
python3 scripts/setup.py --all 10         # wrap 10 USDC.e + approve everything
python3 scripts/setup.py --wrap 50        # wrap more later
python3 scripts/setup.py --approve        # re-issue approvals only
```

---

## Scripts

| Script | Purpose | Tool calls |
|---|---|---|
| `setup.py`           | One-time wrap + approvals (idempotent)                | 0–8 wallet_transfer |
| `search.py`          | Find events/markets, returns token_ids + live prices | 0 |
| `status.py`          | Balance + positions + open orders + recent trades    | 0 |
| `prepare_order.py`   | Fetch orderbook + build EIP-712 payload              | 0 |
| `post_order.py`      | Submit signed order, verify fill                     | 0 |
| `cancel.py`          | Cancel one order (`--id`) or all (`--all`)           | 0 |
| `close_positions.py` | Build SELL orders for all positions                  | 0 |
| `auth.py`            | Check / derive CLOB API key from wallet              | 0–1 sign |

### Search

```bash
python3 scripts/search.py "ceasefire" --limit 3
```

- Use **short keywords** (`trump`, `btc`, `ceasefire`), not full literal questions — long queries often return empty.
- Output JSON includes `outcomes[i].token_id` (YES = index 0, NO = index 1) and current price.

### Place an order — full flow

```bash
# 1. Prepare: fetches market info + orderbook, writes /tmp/poly_order.json
python3 scripts/prepare_order.py 7892825...50228 BUY 0.65 10

# 2. Sign (Python in agent runtime, ONE tool call)
#    from core.skill_tools import wallet
#    p = json.load(open('/tmp/poly_order.json'))
#    sig = wallet.wallet_sign_typed_data(
#        domain=p['domain'], types=p['types'],
#        primaryType=p['primaryType'], message=p['message']
#    )['signature']

# 3. Post: submits and prints order ID + fill status + tx hash
python3 scripts/post_order.py 0xSIGNATURE
```

### Close one or all positions

```bash
python3 scripts/close_positions.py                # all positions
python3 scripts/close_positions.py --token_id X   # one position
# → writes one /tmp/poly_close_N.json per position; sign each + post
```

---

## YES / NO & orderbook

Every binary market has two complementary tokens: `YES + NO ≈ $1.00`.

| Bet | Action | Use | Buy price |
|---|---|---|---|
| Event happens     | BUY YES | `outcomes[0].token_id` | YES price |
| Event won't happen | BUY NO  | `outcomes[1].token_id` | NO price |

Always check the book for the token **you intend to buy**:
- BUY → entry ≈ `best_ask`
- SELL → exit ≈ `best_bid`
- If you see 0.01 / 0.99, you're looking at the wrong token's book.

---

## Order rules (CLOB V2)

- **Minimum order value:** $1 (i.e. `price × size ≥ 1.0`)
- **Minimum size:** 5 shares
- **Tick:** normalized automatically by `prepare_order.py` (usually $0.01)
- **`signatureType`:** always `0` (EOA) for Privy wallets

V2 wire format is strict — `post_order.py` already handles this, but if you ever build a payload by hand:
- `salt` must be **int** (not string)
- Do **NOT** send `taker` / `nonce` / `feeRateBps` (V1 fields, removed in V2)
- `metadata` and `builder` are `bytes32` zeros (`0x` + 64 zeros)

---

## Auth refresh

CLOB credentials (`POLY_API_KEY` / `POLY_SECRET` / `POLY_PASSPHRASE`) are derived from a wallet signature once and persist. If `status.py` returns 401:

```bash
python3 scripts/auth.py --check                   # quick sanity check
python3 scripts/auth.py --prepare 0xWALLET        # build signing payload
# → wallet_sign_typed_data(...)
python3 scripts/auth.py --save 0xSIG 0xWALLET TIMESTAMP
```

Invariants: `TIMESTAMP` and `0xWALLET` in `--save` must match the most recent `--prepare`. If 401 persists, rerun the full prepare→sign→save flow with a fresh timestamp.

---

## Geo / VPN

CLOB API is geo-blocked from US IPs. `scripts/common.py` transparently routes through `sc-vpn.internal:8080` and caches the fastest region. No agent action needed. Override with `POLY_VPN_REGION=ar` or disable with `POLY_DISABLE_VPN=true`.

---

## Errors → fixes

| Error | Cause | Fix |
|---|---|---|
| `Invalid order payload` | Wrong V2 wire format (string salt / extra V1 fields) | Use `post_order.py` (it sends the right shape) |
| `invalid amount for a marketable BUY order ($X), min size: $1` | Order value < $1 | Increase price × size to ≥ $1 |
| `not enough balance` / 0 buying power | pUSD not wrapped yet, OR `signature_type` mismatch in cache | `setup.py --all 10`, then `status.py` |
| `L2_BALANCE_TOO_LOW` | No pUSD in EOA | Wrap more: `setup.py --wrap N` |
| `order_version_mismatch` | Old V1 signing schema | Re-run `prepare_order.py` (uses V2 domain `version=2`) |
| 401 / Invalid API key | Stale CLOB credentials | `auth.py` refresh flow |
| 403 geo-block | VPN unhealthy | Retry; if persists, set `POLY_VPN_REGION` to another region |
| Orderbook shows 0.01 / 0.99 | Looking at the wrong outcome's book | Use the token_id you actually plan to buy |

---

## Architecture summary

- **Wallet:** Privy EOA, `signatureType=0`. Agent signs EIP-712 via `wallet_sign_typed_data`; no private key in agent context.
- **Gas:** sponsored (Alchemy paymaster) — every on-chain call routes through `wallet_transfer`.
- **Collateral:** pUSD (`0xC011a7E1...DFB`), 6 decimals, 1:1 wrap of USDC.e.
- **Exchanges:** CTF Exchange V2 (binary), Neg-Risk Adapter, Neg-Risk Exchange V2 — all 3 must be approved for SELL/settlement.
- **CLOB:** `https://clob.polymarket.com` (V2 backend, live since Apr 28 2026). L1 = wallet sig, L2 = HMAC with derived API key.

---

## Changelog

- **v6.0.0** — Major: full SKILL rewrite for clarity ("3 steps to trade"), new idempotent `setup.py` for one-time wrap + approvals, end-to-end live-verified on CLOB V2 (BUY `0x43f20c67...20b653` → SELL `0x19f475e4...fedde1`, 5 NO @ 0.989 → @ 0.988, ~$0.005 slippage). Supersedes the V1-era flow entirely.
- **v5.1.0** — Added `setup.py` (idempotent wrap + approvals). Full SKILL rewrite for clarity. Live-verified: BUY `0x43f20c67...20b653`, SELL `0x19f475e4...fedde1` (5 NO @ 0.989 → @ 0.988, ~$0.005 slippage).
- **v5.0.5** — CLOB V2 wire format fix: `salt` must be int; remove `taker`/`nonce`/`feeRateBps`.
- **v5.0.4** — Migrated to V2 EIP-712 domain (version=2), V2 contracts, V2 order fields.
- **v5.0.0** — Script-first architecture (BUY: 8 calls → 3).
