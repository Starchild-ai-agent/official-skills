---
name: lighter
version: 2.0.0
description: >
  Lighter.xyz (zklighter) perpetual and spot DEX — order placement, cancellation,
  modification, close-all positions, leverage, margin, withdrawals, fund transfers,
  orderbook depth, market data, candles, funding rates, account positions, balances,
  PnL, and trade history. Supports symbol resolution (BTC, ETH/USDC) and human-unit
  auto-scaling for prices and amounts. Triggers on: "lighter", "zklighter", "elliot",
  perpetual futures trading on lighter, lighter orderbook, lighter funding, lighter
  positions, lighter margin, "robinhood chain", "lighter on robinhood",
  robinhoodchain.lighter.xyz. Supports two separate deployments: Lighter on Ethereum
  and Lighter on Robinhood Chain — the user must pick one (LIGHTER_NETWORK).
  Do NOT use for CoinGecko price data, Hyperliquid, or general CEX trading.
tools:
  - lighter_get_network
  - lighter_get_markets
  - lighter_get_orderbook
  - lighter_get_recent_trades
  - lighter_get_candles
  - lighter_get_exchange_stats
  - lighter_get_funding_rates
  - lighter_get_asset_details
  - lighter_get_account
  - lighter_get_active_orders
  - lighter_get_order_history
  - lighter_get_trade_history
  - lighter_get_pnl
  - lighter_create_order
  - lighter_cancel_order
  - lighter_cancel_all_orders
  - lighter_modify_order
  - lighter_close_all_positions
  - lighter_set_leverage
  - lighter_adjust_margin
  - lighter_withdraw
  - lighter_transfer_funds
  - lighter_paper_init
  - lighter_paper_reset
  - lighter_paper_status
  - lighter_paper_positions
  - lighter_paper_order
  - lighter_paper_trades
  - lighter_paper_health

metadata:
  starchild:
    emoji: "⚡"
    skillKey: lighter
    requires:
      env:
        - LIGHTER_NETWORK
        - LIGHTER_API_URL
        - LIGHTER_PRIVATE_KEY
        - LIGHTER_ACCOUNT_INDEX

user-invocable: false
disable-model-invocation: false
---

# Lighter.xyz (zklighter)

Lighter is a high-performance **ZK-rollup DEX** offering perpetual futures and spot trading with sub-second finality.
It supports **220+ markets** (perpetuals for crypto, stocks, forex, commodities; spot pairs like ETH/USDC).
All orders are signed L2 transactions settled on the deployment's L1.

## Networks — the user MUST pick one

Lighter runs as **two independent deployments**. They share the same API shape but have
**different hosts, accounts, API keys, contracts, markets and quote assets**. Credentials
from one do not work on the other.

| `LIGHTER_NETWORK` | App | REST base URL | Signing chain ID | L1 | Quote |
|---|---|---|---|---|---|
| `ethereum` | https://app.lighter.xyz | `https://mainnet.zklighter.elliot.ai` | 304 | Ethereum (1) | USDC |
| `robinhood` | https://robinhoodchain.lighter.xyz | `https://api.rh.lighter.xyz` | 466324 | Robinhood Chain (4663) | USDG |

Testnets: `ethereum-testnet` (`https://testnet.zklighter.elliot.ai`) and `robinhood-testnet` (`https://api.rh-testnet.lighter.xyz`).

**Before the first Lighter call in a session**, run `lighter_get_network()`.
- If `selected` is `false`, **stop and ask the user**: *"Are you on Lighter (app.lighter.xyz) or Lighter on Robinhood Chain (robinhoodchain.lighter.xyz)?"* Do not guess — the wrong choice means wrong markets and failed signatures.
- Then have them set `LIGHTER_NETWORK=ethereum` or `LIGHTER_NETWORK=robinhood` (env var or credentials file). Aliases accepted: `eth`, `mainnet`, `rh`, `robinhoodchain`.
- Every tool errors with a clear message until a network is selected. An explicit `LIGHTER_API_URL` also counts as a selection and takes precedence.

Network-specific notes:
- **Robinhood Chain** spot pairs are quoted in **USDG** (e.g. `META/USDG`), not USDC. It also lists tokenized stocks (`HOOD`, `SPY`, `QQQ`) and fewer markets overall. Always check `lighter_get_markets()` rather than assuming a symbol exists.
- Accounts are created by depositing in the respective app. Look up the account index against the selected network — an Ethereum wallet address may have an account on one deployment and not the other.
- Paper trading keeps a separate state file per network.

## When to Use Lighter

- **Market data** — orderbook depth, recent trades, OHLCV candles, funding rates
- **Exchange overview** — 24h volume, open interest, mark/index prices
- **Account queries** — positions, balances, active orders, PnL, trade history
- **Order management** — place limit/market/stop/TP orders, cancel, modify, close-all
- **Position management** — set leverage, adjust isolated margin
- **Fund management** — withdraw assets, transfer between perp/spot buckets
- **Funding analysis** — compare funding rates across Binance, Bybit, Hyperliquid, Lighter

## Symbol Convention

- **Perp markets** use bare tickers: `BTC`, `ETH`, `SOL`, `LIT`
- **Spot markets** use quote-qualified pairs: `ETH/USDC`, `LIT/USDC`, `LINK/USDC`
- The `/` is the discriminator — no `--market_type` flag needed
- Numeric `market_id` is also accepted as an escape hatch
- Symbol resolution is automatic with a 5-minute cache

## Human-Unit Auto-Scaling

Trading tools accept **human-readable prices and amounts** (e.g. `amount=0.1`, `price=3200.50`).
The tools automatically fetch market metadata and scale to integer ticks/lots.
Response includes `effective_amount` and `effective_price` showing what actually landed after rounding.

## Account Setup Flow

Setting up Lighter trading requires two different values from different places:

### Step 0: Pick the network

Ask which deployment they trade on and set `LIGHTER_NETWORK` accordingly (see **Networks** above). Everything below is per network.

### Step 1: Get your Account Index

`LIGHTER_ACCOUNT_INDEX` is a **number** (e.g. `12345`), not a key.

Ask the user for their **Ethereum L1 wallet address** (public address, e.g. `0xabc...`), then look it up:
```
lighter_get_account(l1_address="0xabc...")
```
The response will contain the account `index` — that's the `LIGHTER_ACCOUNT_INDEX`.

If no account is found, the user needs to create one first by connecting their wallet and depositing in the app for the selected network (https://app.lighter.xyz or https://robinhoodchain.lighter.xyz).

### Step 2: Get API Keys

`LIGHTER_PRIVATE_KEY` is a **hex string** — the L2 API private key.

The user generates this on the API keys page of the selected network's app
(https://app.lighter.xyz/apikeys or https://robinhoodchain.lighter.xyz/apikeys):
1. Go to the API keys page
2. If using a sub-account, switch to it first
3. Generate a new API key — the private key is shown **only once**
4. Note the **API key index** number (this becomes `LIGHTER_API_KEY_INDEX`)

See the [lighter-python setup example](https://github.com/elliottech/lighter-python) for programmatic key generation (requires L1 wallet signature).

### Step 3: Configure Credentials

Sanity check before saving:
- `LIGHTER_ACCOUNT_INDEX` = numeric only (e.g. `12345`)
- `LIGHTER_PRIVATE_KEY` = long hex key string
- `LIGHTER_API_KEY_INDEX` = small integer key slot (e.g. `4`)

Credentials can be set via environment variables OR a credentials file.

#### Option 1: Environment Variables

```env
LIGHTER_NETWORK=ethereum            # or: robinhood
LIGHTER_PRIVATE_KEY=your_lighter_api_private_key_here
LIGHTER_ACCOUNT_INDEX=your_account_index_here
LIGHTER_API_KEY_INDEX=2
```

#### Option 2: Credentials File

`~/.lighter/lighter-agent-kit/credentials`:
```text
LIGHTER_API_PRIVATE_KEY=...
LIGHTER_ACCOUNT_INDEX=...
LIGHTER_API_KEY_INDEX=...
LIGHTER_NETWORK=robinhood
```

Environment variables take precedence. Both `LIGHTER_PRIVATE_KEY` and `LIGHTER_API_PRIVATE_KEY` are accepted.

| Variable | Required | Description |
|----------|----------|-------------|
| `LIGHTER_NETWORK` | Yes (unless `LIGHTER_API_URL` set) | `ethereum` or `robinhood` (also `ethereum-testnet`, `robinhood-testnet`). No default — the user must choose. |
| `LIGHTER_API_URL` | No | Explicit base URL; overrides `LIGHTER_NETWORK`. `LIGHTER_HOST` is accepted as an alias. |
| `LIGHTER_PRIVATE_KEY` | For trading | Lighter L2 API private key (hex). Not your wallet key. |
| `LIGHTER_ACCOUNT_INDEX` | For trading | Your numeric account index on Lighter |
| `LIGHTER_API_KEY_INDEX` | No | Which API key slot to use (default `2`, range 2-254) |

> **Note:** Read-only tools (market data, orderbook, candles, funding rates) work without any keys, but still need `LIGHTER_NETWORK`.
> Trading tools require `LIGHTER_PRIVATE_KEY` and `LIGHTER_ACCOUNT_INDEX`.

## Common Workflows

### Check / choose network
```
lighter_get_network()      # shows selected network, base URL, and the available options
```

### Check Market Info
```
lighter_get_markets()                        # all markets
lighter_get_markets(filter="perp")           # perps only
lighter_get_markets(market_id=0)             # specific market
```

### Get Orderbook
```
lighter_get_orderbook(symbol="BTC", limit=20)
lighter_get_orderbook(symbol="ETH/USDC", limit=10)
```

### Get OHLCV Candles
```
lighter_get_candles(symbol="ETH", resolution="1h", count_back=100)
```

### Check Positions & Balances
```
lighter_get_account()                        # uses configured account
lighter_get_active_orders(symbol="BTC")
lighter_get_pnl(resolution="1d", count_back=30)
```

### Place Orders (human units, auto-scaled)
```
# Market buy 0.1 BTC
lighter_create_order(symbol="BTC", side="long", amount=0.1, order_type="market")

# Limit sell 1 ETH at $3200
lighter_create_order(symbol="ETH", side="short", amount=1.0, price=3200, order_type="limit")

# Stop-loss at $2800
lighter_create_order(symbol="ETH", side="short", amount=1.0, price=2800,
                     order_type="stop_loss", trigger_price=2800, reduce_only=true)
```

### Modify / Cancel
```
lighter_modify_order(symbol="BTC", order_index=12345, amount=0.2, price=61000)
lighter_cancel_order(symbol="BTC", order_index=12345)
lighter_cancel_all_orders()
```

### Close All Positions
```
# ALWAYS preview first
lighter_close_all_positions(preview=true)
# Then execute after user confirms
lighter_close_all_positions(preview=false)
```

### Leverage & Margin
```
lighter_set_leverage(symbol="BTC", leverage=10)
lighter_set_leverage(symbol="ETH", leverage=5, margin_mode="isolated")
lighter_adjust_margin(symbol="ETH", amount=100, direction="add")
```

### Withdraw & Transfer
```
lighter_withdraw(asset="usdc", amount=100)
lighter_transfer_funds(asset="usdc", amount=250, from_route="perp", to_route="spot")
```

### Compare Funding Rates
```
lighter_get_funding_rates()   # Returns rates from Binance, Bybit, Hyperliquid, Lighter
```

## Paper Trading

Simulate trades against real Lighter order book snapshots — no credentials, no broadcast, no risk. All state is local.

**Perp markets only.** No spot, no resting limits, no funding accrual. Market orders only (taker fills).

### Quick Start
```
# 1. Create account (once)
lighter_paper_init(collateral=10000, tier="premium")

# 2. Place trades
lighter_paper_order(symbol="BTC", side="long", amount=0.1)
lighter_paper_order(symbol="ETH", side="short", amount=1.0)

# 3. Check status
lighter_paper_status()
lighter_paper_positions()
lighter_paper_health()
lighter_paper_trades(limit=10)

# 4. Reset when done
lighter_paper_reset()
```

### Paper vs Live Caveats

These cause paper-to-live PnL divergence:
1. **Maker fills never occur** — every fill is charged taker fee
2. **No order-impact model** — paper orders walk the book but don't move it
3. **No latency / partial-fill modeling** — fills instantly in full
4. **No funding accrual** — dominant PnL drag/credit for longer holds
5. **Cross-margin only** — no isolated margin simulation

### Fee Tiers

| Tier | Taker bps | Maker bps |
|------|-----------|-----------|
| `standard` | 0.0 | 0.0 |
| `premium` (default) | 2.8 | 0.4 |
| `premium_1` | 2.73 | 0.39 |
| `premium_2` | 2.66 | 0.38 |
| `premium_3` | 2.52 | 0.36 |
| `premium_4` | 2.38 | 0.34 |
| `premium_5` | 2.24 | 0.32 |
| `premium_6` | 2.1 | 0.3 |
| `premium_7` | 1.96 | 0.28 |

State file: `~/.lighter/lighter-agent-kit/paper-state.json` for `ethereum`, `paper-state-<network>.json` for others (override with `LIGHTER_PAPER_STATE_PATH` env var).

## Safety Notes

- **`lighter_close_all_positions`** is high-risk. ALWAYS run `preview=true` first, show the plan to the user, and get explicit confirmation before executing. Never infer intent from vague prompts.
- **`lighter_withdraw`** creates a withdrawal request; funds may go through a pending/claim flow.
- Write commands sign and broadcast immediately.
- Private keys are wrapped in `SecretValue` objects — never attempt to read or display them.

## Decision Tree

| User Wants | Tool | Key Params |
|------------|------|------------|
| Which deployment am I on / options | `lighter_get_network` | — |
| List available markets | `lighter_get_markets` | `filter`, `market_id` |
| Orderbook snapshot | `lighter_get_orderbook` | `symbol`, `limit` |
| Recent trade prints | `lighter_get_recent_trades` | `symbol`, `limit` |
| OHLCV chart data | `lighter_get_candles` | `symbol`, `resolution`, `count_back` |
| 24h volume/OI/prices | `lighter_get_exchange_stats` | — |
| Cross-exchange funding | `lighter_get_funding_rates` | — |
| Asset info (decimals, caps) | `lighter_get_asset_details` | `asset_id` |
| Account info/balances | `lighter_get_account` | `account_index` |
| Open orders | `lighter_get_active_orders` | `symbol` |
| Filled/canceled orders | `lighter_get_order_history` | `symbol`, `limit` |
| Trade history | `lighter_get_trade_history` | `symbol`, `limit` |
| PnL over time | `lighter_get_pnl` | `resolution`, `count_back` |
| Place an order | `lighter_create_order` | `symbol`, `side`, `amount`, `price` |
| Cancel one order | `lighter_cancel_order` | `symbol`, `order_index` |
| Cancel all orders | `lighter_cancel_all_orders` | — |
| Modify existing order | `lighter_modify_order` | `symbol`, `order_index`, `amount`, `price` |
| Close all positions | `lighter_close_all_positions` | `preview`, `slippage` |
| Set leverage | `lighter_set_leverage` | `symbol`, `leverage`, `margin_mode` |
| Adjust margin | `lighter_adjust_margin` | `symbol`, `amount`, `direction` |
| Withdraw assets | `lighter_withdraw` | `asset`, `amount`, `route` |
| Transfer perp/spot | `lighter_transfer_funds` | `asset`, `amount`, `from_route`, `to_route` |
| Paper: create account | `lighter_paper_init` | `collateral`, `tier` |
| Paper: reset account | `lighter_paper_reset` | `collateral`, `tier` |
| Paper: account summary | `lighter_paper_status` | — |
| Paper: open positions | `lighter_paper_positions` | `symbol` |
| Paper: place trade | `lighter_paper_order` | `symbol`, `side`, `amount` |
| Paper: trade history | `lighter_paper_trades` | `symbol`, `limit` |
| Paper: margin/health | `lighter_paper_health` | — |
