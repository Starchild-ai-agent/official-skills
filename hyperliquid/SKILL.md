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

On-chain DEX for perps (crypto + stocks/RWA) and spot. Orders signed via agent's EVM wallet.

**Prerequisite**: Wallet policy must be active. Load **wallet-policy** skill and propose the standard wildcard policy.

## Tools

### Read

| Tool | Purpose |
|------|---------|
| `hl_total_balance` | Available margin (**always use this**, not hl_account) |
| `hl_account` / `hl_account(dex="xyz")` | Positions, PnL, margin |
| `hl_balances` | Spot token holdings |
| `hl_open_orders` | Pending orders |
| `hl_market(coin?)` / `hl_market(dex="xyz")` | Prices, maxLeverage, szDecimals |
| `hl_orderbook(coin)` | Order book depth |
| `hl_fills(limit?)` | Recent fills |
| `hl_candles(coin, interval, lookback)` | OHLC (1m/5m/15m/1h/4h/1d) |
| `hl_funding(coin?)` | Predicted + historical funding |

### Trade

| Tool | Purpose |
|------|---------|
| `hl_order(coin, side, size, price?)` | Perp order. Omit price → market (IoC mid±3%) |
| `hl_spot_order(coin, side, size, price?)` | Spot order |
| `hl_tpsl_order(coin, side, size, trigger_px, tpsl)` | Stop loss (`sl`) / take profit (`tp`) |
| `hl_leverage(coin, leverage, cross?)` | Set leverage (default cross=true) |
| `hl_cancel(coin, order_id)` / `hl_cancel_all(coin?)` | Cancel orders |
| `hl_modify(order_id, coin, side, size, price)` | Modify order |

### Funds

| Tool | Purpose |
|------|---------|
| `hl_deposit(amount)` | USDC from Arbitrum (min $5) |
| `hl_withdraw(amount)` | USDC to Arbitrum (1 USDC fee, ~5 min) |
| `hl_transfer_usd(amount, to_perp)` | Spot↔perp (rarely needed in unified mode) |

## Coin Resolution

| Type | Format | Examples |
|------|--------|---------|
| Crypto | Plain | BTC, ETH, SOL, HYPE |
| Stocks | `xyz:TICKER` | xyz:NVDA, xyz:TSLA, xyz:AAPL |
| Commodities | `xyz:NAME` | xyz:GOLD, xyz:SILVER |

If unsure: `hl_market(coin="X")` → if not found → `hl_market(dex="xyz")`.

## Agent Behavior (automatic, never ask)

1. `hl_total_balance` before every trade
2. Detect asset type: crypto vs RWA (xyz: prefix)
3. `hl_leverage` before placing orders
4. `hl_fills` after every order → report fill price, size, PnL
5. Suggest SL/TP for leveraged positions

## Order Types

- **Limit**: `hl_order(coin, side, size, price=X)` — rests on book
- **Market**: `hl_order(coin, side, size)` — omit price, IoC mid±3%
- **Post-Only**: `order_type="alo"` — rejected if crosses spread
- **Stop Loss**: `hl_tpsl_order(..., tpsl="sl")` — triggers at trigger_px
- **Take Profit**: `hl_tpsl_order(..., tpsl="tp")` — triggers at trigger_px

**Long SL/TP**: `side="sell"` | **Short SL/TP**: `side="buy"`

## Workflows

**Trade perps**: `hl_total_balance` → `hl_leverage` → `hl_order` → `hl_fills`
**Close position**: `hl_account` (get size) → `hl_order(reduce_only=true)` → `hl_fills`
**Spot**: `hl_total_balance` → `hl_spot_order` → `hl_balances`

## Common Errors

| Error | Fix |
|-------|-----|
| "Unknown perp asset" | Crypto: "BTC", Stocks: "xyz:NVDA" |
| "Insufficient margin" | Check `hl_total_balance`, reduce size |
| "Minimum value of $10" | Increase size × price ≥ $10 |
| "User or wallet does not exist" | `hl_deposit(amount=500)` first |
| "Policy violation" | Load wallet-policy skill, propose wildcard |
