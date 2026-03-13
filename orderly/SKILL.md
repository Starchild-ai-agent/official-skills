---
name: orderly
version: 1.0.0
description: Trade perpetual futures and spot on Orderly Network DEX
tools:
  - orderly_system_info
  - orderly_futures
  - orderly_funding
  - orderly_volume
  - orderly_orderbook
  - orderly_kline
  - orderly_market
  - orderly_chain_info
  - orderly_account
  - orderly_holdings
  - orderly_positions
  - orderly_orders
  - orderly_trades
  - orderly_liquidations
  - orderly_order
  - orderly_modify
  - orderly_cancel
  - orderly_cancel_all
  - orderly_leverage
  - orderly_deposit
  - orderly_withdraw
metadata:
  starchild:
    emoji: "📊"
    skillKey: orderly
    requires:
      env: [WALLET_SERVICE_URL]
user-invocable: true
disable-model-invocation: false
---

# Orderly Network Trading

Trade perpetual futures on Orderly Network, an omnichain orderbook DEX built on unified liquidity. Supports both cryptocurrency pairs (169+ assets) and RWA commodities (Gold, Silver). Orders are signed using Ed25519 keys auto-provisioned via this agent's EVM wallet (Privy). Trades execute through Orderly's central limit orderbook with settlement on Arbitrum (or other supported EVM chains).

## Available Markets

Orderly Network supports two asset categories:

### Cryptocurrency Perpetuals (169+ pairs)
Major cryptocurrencies and altcoins tradable as perpetual futures:
- **Major assets**: BTC, ETH, SOL, AVAX, MATIC, NEAR, OP, ARB
- **DeFi tokens**: UNI, AAVE, SUSHI, CRV, COMP
- **Layer-1/Layer-2**: ATOM, DOT, ADA, FTM, MATIC
- **Symbol format**: `PERP_<TOKEN>_USDC` (e.g., `PERP_BTC_USDC`, `PERP_ETH_USDC`)
- **Shorthand accepted**: Use `"BTC"` instead of `"PERP_BTC_USDC"` — auto-expanded by tools

### RWA Commodities (Launched Dec 2025)
Real-world asset commodities available for perpetual futures trading:
- **Gold**: `$XAU` or `PERP_XAU_USDC` — physical gold price tracking
- **Silver**: `$XAG` or `PERP_XAG_USDC` — physical silver price tracking
- **Leverage**: Up to 20x leverage available
- **Pricing**: Institutional-grade oracle feeds ensure real-world price accuracy
- **Not tokenized**: Direct on-chain exposure without wrapping or tokenization

Use `orderly_futures()` to get the complete real-time list of all available instruments.

## Prerequisites

Before trading, the wallet policy must be active. Load the **wallet-policy** skill and propose the standard wildcard policy (deny key export + allow `*`). This covers all Orderly operations — USDC deposits, vault interactions, account registration, and withdrawal signing.

## Available Tools (19)

### Public Tools (read-only, no auth)

| Tool | Description |
|------|-------------|
| `orderly_system_info` | System maintenance status |
| `orderly_futures` | Futures instrument info (tick sizes, lot sizes, max leverage) |
| `orderly_funding` | Funding rates (current + history) |
| `orderly_volume` | Volume statistics (24h volume, open interest) |
| `orderly_orderbook` | Orderbook snapshot (bids/asks with sizes) |
| `orderly_kline` | OHLCV candlestick data |
| `orderly_market` | Market overview (instruments + recent trades) |
| `orderly_chain_info` | Chain and broker configuration |

### Private Tools (require Ed25519 auth)

| Tool | Description |
|------|-------------|
| `orderly_account` | Account info (fees, tier, status) |
| `orderly_holdings` | Asset balances (available, frozen) |
| `orderly_positions` | Open positions (size, entry, PnL) |
| `orderly_orders` | List orders (open/completed/cancelled) |
| `orderly_trades` | Trade/fill history |
| `orderly_liquidations` | Liquidation history |

### Trading Tools (require Ed25519 auth)

| Tool | Description |
|------|-------------|
| `orderly_order` | Create order (LIMIT/MARKET/IOC/FOK/POST_ONLY) |
| `orderly_modify` | Edit existing order (price/quantity) |
| `orderly_cancel` | Cancel order by ID |
| `orderly_cancel_all` | Cancel all orders (optionally per symbol) |
| `orderly_leverage` | Update leverage for a symbol |

---

## Tool Usage Examples

### Check System Status

```
orderly_system_info()
```

### Check Futures Instruments

```
orderly_futures()                          # All instruments (crypto + RWA)
orderly_futures(symbol="BTC")              # BTC perp details
orderly_futures(symbol="XAU")              # Gold perp details
orderly_futures(symbol="XAG")              # Silver perp details
```

### Check Orderbook

```
orderly_orderbook(symbol="BTC")
orderly_orderbook(symbol="ETH", max_level=10)
orderly_orderbook(symbol="XAU")            # Gold orderbook
orderly_orderbook(symbol="XAG", max_level=5)  # Silver orderbook
```

### Get Candles

```
orderly_kline(symbol="BTC", interval="1h", limit=100)
orderly_kline(symbol="ETH", interval="4h", limit=200)
```

Intervals: `1m`, `5m`, `15m`, `30m`, `1h`, `4h`, `12h`, `1d`, `1w`

### Check Funding Rates

```
orderly_funding(symbol="BTC")                       # Current rate
orderly_funding(symbol="BTC", history=true)          # Current + history
```

### Check Account Info

```
orderly_account()
```

### Check Holdings

```
orderly_holdings()
```

### Check Positions

```
orderly_positions()
```

### Place a Limit Order

```
orderly_order(symbol="BTC", side="buy", quantity=0.01, price=95000)
orderly_order(symbol="XAU", side="buy", quantity=1, price=2800)  # Buy 1 oz Gold at $2,800
orderly_order(symbol="XAG", side="sell", quantity=10, price=32)  # Sell 10 oz Silver at $32
```

Places a GTC limit buy for 0.01 BTC at $95,000.

### Place a Market Order

```
orderly_order(symbol="ETH", side="sell", quantity=0.1, order_type="MARKET")
```

### Place a Post-Only Order

```
orderly_order(symbol="BTC", side="buy", quantity=0.01, price=94000, order_type="POST_ONLY")
```

Rejected if it would immediately fill (maker only).

### Close a Position

```
orderly_order(symbol="BTC", side="sell", quantity=0.01, reduce_only=true)
```

Use `reduce_only=true` to ensure it only closes, never opens a new position.

### Cancel an Order

```
orderly_cancel(symbol="BTC", order_id=12345678)
```

Get `order_id` from `orderly_orders`.

### Cancel All Orders

```
orderly_cancel_all()                    # Cancel everything
orderly_cancel_all(symbol="BTC")        # Cancel only BTC orders
```

### Modify an Order

```
orderly_modify(order_id=12345678, symbol="BTC", side="buy", quantity=0.02, price=94500)
```

### Set Leverage

```
orderly_leverage(symbol="BTC", leverage=10)
orderly_leverage(symbol="ETH", leverage=5)
```

### Check Order History

```
orderly_orders()                                        # All open orders
orderly_orders(symbol="BTC", status="INCOMPLETE")        # Open BTC orders
orderly_orders(status="COMPLETED", limit=20)             # Recent filled orders
```

### Check Trade History

```
orderly_trades()                                # All recent trades
orderly_trades(symbol="BTC", limit=10)          # Recent BTC trades
```

---

## Common Workflows

### Open a Perp Position

1. `orderly_market(symbol="BTC")` — Check current price and instrument details
2. `orderly_leverage(symbol="BTC", leverage=5)` — Set desired leverage
3. `orderly_order(symbol="BTC", side="buy", quantity=0.01, price=95000)` — Place limit order
4. `orderly_orders(symbol="BTC", status="INCOMPLETE")` — Verify order is live
5. `orderly_trades(symbol="BTC")` — Check if filled

### Close a Perp Position

1. `orderly_positions()` — See current positions and sizes
2. `orderly_order(symbol="BTC", side="sell", quantity=0.01, order_type="MARKET", reduce_only=true)` — Close with market order
3. `orderly_positions()` — Verify position is closed

### Market Research

1. `orderly_futures()` — Scan all available instruments
2. `orderly_funding(symbol="BTC", history=true)` — Check funding environment
3. `orderly_kline(symbol="BTC", interval="4h", limit=168)` — 7-day price action
4. `orderly_orderbook(symbol="BTC")` — Check liquidity depth
5. `orderly_volume()` — Check aggregate volume stats

### Trading RWA Commodities (Gold/Silver)

1. `orderly_futures(symbol="XAU")` — Check Gold instrument details (min order size, tick size, leverage limits)
2. `orderly_market(symbol="XAU")` — Get current Gold price and recent trades
3. `orderly_kline(symbol="XAU", interval="1h", limit=24)` — 24-hour Gold price chart
4. `orderly_leverage(symbol="XAU", leverage=10)` — Set 10x leverage for Gold trading
5. `orderly_order(symbol="XAU", side="buy", quantity=1, price=2800)` — Buy 1 oz Gold at $2,800
6. `orderly_positions()` — Check Gold/Silver positions
7. `orderly_order(symbol="XAU", side="sell", quantity=1, order_type="MARKET", reduce_only=true)` — Close Gold position

**RWA Trading Notes:**
- Gold and Silver use same tools as crypto perpetuals
- Quantities in troy ounces (e.g., 1 = 1 oz Gold, 10 = 10 oz Silver)
- Pricing tracks real-world spot prices via institutional oracle feeds
- Up to 20x leverage available
- USDC settlement like all Orderly perps

---

## Order Types

| Type | Parameter | Behavior |
|------|-----------|----------|
| **Limit (GTC)** | `order_type="LIMIT"` | Rests on book until filled or cancelled |
| **Market** | `order_type="MARKET"` | Fills at best available price immediately |
| **IOC** | `order_type="IOC"` | Immediate-or-Cancel: fill what's available, cancel rest |
| **FOK** | `order_type="FOK"` | Fill-or-Kill: fill entirely or cancel entirely |
| **Post-Only** | `order_type="POST_ONLY"` | Rejected if it would cross the spread (maker only) |

Add `reduce_only=true` to any order type to ensure it only closes existing positions.

---

## Symbol Format

Orderly uses structured symbol names. You can use shorthand (just the coin name) and it auto-expands:

| You type | Expands to |
|----------|-----------|
| `"BTC"` | `"PERP_BTC_USDC"` |
| `"ETH"` | `"PERP_ETH_USDC"` |
| `"PERP_BTC_USDC"` | passed through as-is |
| `"SPOT_ETH_USDC"` | passed through as-is |

Full symbol format: `{PERP|SPOT}_{BASE}_{QUOTE}`

---

## Risk Management

- **Always check positions before trading** — know your existing exposure and margin usage
- **Set leverage explicitly** before opening new positions
- **Use reduce_only** when closing to avoid accidentally opening the opposite direction
- **Monitor funding rates** — high positive funding means longs are expensive to hold
- **Start with small sizes** — check instrument details for minimum order sizes
- **Post-only orders** save on fees (maker vs taker rates)
- **Check trades after market orders** — market orders may get partial fills

---

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| "Orderly API 400" | Invalid request parameters | Check symbol name, order type, and required fields |
| "Orderly API 401" | Authentication failed | Ed25519 key may have expired — restart triggers re-registration |
| "Orderly error" | Business logic rejection | Check error message for details (insufficient margin, invalid price, etc.) |
| "Not running on Fly" | No wallet access | Wallet signing only works on Fly.io deployment |
| "Orderly account not registered" | Registration not complete | Private/trading calls auto-register on first use |
| "No ethereum wallet found" | Missing Privy wallet | Ensure WALLET_SERVICE_URL is configured and wallet is provisioned |
| "Policy violation" / signing rejected | Wallet policy doesn't allow required methods | Load the **wallet-policy** skill and propose the standard wildcard policy (deny key export + allow `*`) |
