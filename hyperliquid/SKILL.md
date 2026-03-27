---
name: hyperliquid
version: 1.0.0
description: Trade perpetual futures and spot on Hyperliquid DEX
tools:
  - hl_account
  - hl_balances
  - hl_open_orders
  - hl_market
  - hl_orderbook
  - hl_fills
  - hl_candles
  - hl_funding
  - hl_order
  - hl_spot_order
  - hl_tpsl_order
  - hl_cancel
  - hl_cancel_all
  - hl_modify
  - hl_leverage
  - hl_transfer_usd
  - hl_withdraw
  - hl_deposit
metadata:
  starchild:
    emoji: "📈"
    skillKey: hyperliquid
    requires:
      env: [WALLET_SERVICE_URL]
user-invocable: true
disable-model-invocation: false
---

# Hyperliquid Trading

Fully on-chain DEX for perps (crypto + stocks/RWA) and spot. Orders signed via agent's EVM wallet, submitted to Hyperliquid L1.

## Prerequisites

Wallet policy must be active. Load **wallet-policy** skill and propose the standard wildcard policy (deny key export + allow `*`).

## Tools

### Account & Market

| Tool | Purpose |
|------|---------|
| `hl_total_balance` | Available margin (use this for balance checks, not hl_account) |
| `hl_account` / `hl_account(dex="xyz")` | Positions, PnL, margin. Use `dex="xyz"` for stock/RWA perps |
| `hl_balances` | Spot token holdings (USDC, HYPE, etc.) |
| `hl_open_orders` | Pending orders |
| `hl_market(coin?)` / `hl_market(dex="xyz")` | Prices, maxLeverage, szDecimals |
| `hl_orderbook(coin)` | Order book depth |
| `hl_fills(limit?)` | Recent trade fills |
| `hl_candles(coin, interval, lookback)` | OHLC data. Intervals: 1m/5m/15m/1h/4h/1d |
| `hl_funding(coin?)` | Predicted + historical funding rates |

### Trading

| Tool | Purpose |
|------|---------|
| `hl_order(coin, side, size, price?, order_type?, reduce_only?)` | Perp order. Omit price → market (IoC at mid±3%) |
| `hl_spot_order(coin, side, size, price?)` | Spot order |
| `hl_tpsl_order(coin, side, size, trigger_px, tpsl, is_market?, limit_px?)` | Stop loss / take profit trigger orders |
| `hl_leverage(coin, leverage, cross?)` | Set leverage. Default cross=true |
| `hl_cancel(coin, order_id)` | Cancel one order |
| `hl_cancel_all(coin?)` | Cancel all (optionally per coin) |
| `hl_modify(order_id, coin, side, size, price)` | Modify existing order |

### Funds

| Tool | Purpose |
|------|---------|
| `hl_deposit(amount)` | Deposit USDC from Arbitrum (min $5) |
| `hl_withdraw(amount, destination?)` | Withdraw USDC to Arbitrum (1 USDC fee, ~5 min) |
| `hl_transfer_usd(amount, to_perp)` | Move USDC between spot/perp (rarely needed in unified mode) |

## Agent Behavior

**Always do automatically (never ask):**
1. Check `hl_total_balance` before every trade
2. Detect asset type: crypto (BTC) vs RWA (NVIDIA → xyz:NVDA)
3. Set leverage via `hl_leverage` before placing orders
4. Verify fills via `hl_fills` after every order
5. Report: fill price, size, PnL
6. Suggest stop losses for leveraged positions

**Balance check hierarchy**: ✅ `hl_total_balance` → shows actual available margin | ❌ `hl_account` may show $0 | ❌ `hl_balances` only shows spot tokens

## Coin vs RWA Resolution

| Type | Format | Examples |
|------|--------|---------|
| Crypto | Plain name | BTC, ETH, SOL, DOGE, HYPE |
| Stocks | `xyz:TICKER` | xyz:NVDA, xyz:TSLA, xyz:AAPL, xyz:MSFT |
| Commodities | `xyz:NAME` | xyz:GOLD, xyz:SILVER |
| Forex/Indices | `xyz:NAME` | xyz:EUR, xyz:GBP, xyz:SPY |

**If unsure**: try `hl_market(coin="X")` first → if not found, search `hl_market(dex="xyz")`.

All tools work identically with `xyz:` prefix. Builder perps (HIP-3) use isolated margin only — `hl_leverage` handles this automatically.

## Order Types

| Type | How | Notes |
|------|-----|-------|
| Limit (GTC) | `hl_order(coin, side, size, price=X)` | Rests on book |
| Market (IoC) | `hl_order(coin, side, size)` — omit price | Mid ±3% slippage |
| Post-Only (ALO) | `order_type="alo"` | Rejected if would cross spread |
| Stop Loss | `hl_tpsl_order(..., tpsl="sl")` | Triggers at trigger_px, exits as market |
| Take Profit | `hl_tpsl_order(..., tpsl="tp")` | Triggers at trigger_px, exits as market |

## Stop Loss & Take Profit

Trigger orders that auto-execute when market reaches `trigger_px`. Default: market execution. For limit execution: set `is_market=false, limit_px=X`.

**Long positions**: SL/TP use `side="sell"`. Example: long BTC at 95k → SL at 90k, TP at 100k:
```
hl_tpsl_order(coin="BTC", side="sell", size=0.1, trigger_px=90000, tpsl="sl")
hl_tpsl_order(coin="BTC", side="sell", size=0.1, trigger_px=100000, tpsl="tp")
```

**Short positions**: SL/TP use `side="buy"`. Example: short BTC at 95k → SL at 98k, TP at 92k:
```
hl_tpsl_order(coin="BTC", side="buy", size=0.1, trigger_px=98000, tpsl="sl")
hl_tpsl_order(coin="BTC", side="buy", size=0.1, trigger_px=92000, tpsl="tp")
```

**Best practices**: Always set both TP and SL | Match size to position | Use `reduce_only=true` (default) | Don't set stops too tight

## Common Workflows

**Trade perps**: `hl_total_balance` → `hl_leverage` → `hl_order` → `hl_fills`

**Trade stocks/RWA**: Detect xyz: prefix → same flow as perps with prefixed coin name

**Close position**: `hl_account` (get size) → `hl_order(side="sell/buy", size=X, reduce_only=true)` → `hl_fills` (report PnL)

**Spot trade**: `hl_total_balance` → `hl_spot_order` → `hl_balances`

**Deposit**: `hl_deposit(amount=500)` | **Withdraw**: `hl_withdraw(amount=100)` — 1 USDC fee, ~5 min

## Risk Notes

- Check margin usage before trading. Min order value: $10
- Funding rates: paid/received hourly on perps. High positive = expensive longs
- Post-only (ALO) saves fees (maker vs taker)
- Market orders (IoC) may partially fill — always check `hl_fills`

## Common Errors

| Error | Fix |
|-------|-----|
| "Unknown perp asset" | Crypto: "BTC". Stocks: "xyz:NVDA" |
| "Insufficient margin" | Check `hl_total_balance`, reduce size |
| "Minimum value of $10" | Increase size × price ≥ $10 |
| "Order would cross" | ALO rejected — use regular limit |
| "User or wallet does not exist" | Deposit first: `hl_deposit(amount=500)` |
| "Policy violation" | Load wallet-policy skill, propose wildcard policy |
| "Action disabled when unified account is active" | Transfers blocked in unified mode — just trade directly |
