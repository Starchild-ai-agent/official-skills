---
name: coinglass
version: 3.0.4
description: |
  Crypto derivatives data: funding rates, open interest, liquidations, long/short ratios.

  Use when researching perp markets, tracking Hyperliquid whale positions, or comparing ETF flows (e.g. BTC funding, ETH OI, liquidation heatmap).
delivery: script
metadata:
  starchild:
    emoji: 📈
    skillKey: coinglass
    plan: professional
    api_version: v4
    version: 3.0.3
    total_tools: 37
    requires:
      env:
      - COINGLASS_API_KEY
user-invocable: false
disable-model-invocation: false

---

## Liquidation Heatmap（真正的价格区间清算压力）

`cg_liquidation_analysis` 返回全0，不可用。正确做法是直接调 API：

```python
from tools._api import cg_request

# 全市场聚合热力图（推荐，无需指定交易所）
# range 支持: 12h, 24h, 3d, 7d, 30d, 90d, 180d, 1y
data = cg_request("api/futures/liquidation/aggregated-heatmap/model1",
                  params={"symbol": "BTC", "range": "24h"})

# 返回结构：
# data["y_axis"]                   → 价格档位列表（从低到高）
# data["liquidation_leverage_data"] → [[y_idx, leverage, usd_value], ...]
# data["price_candlesticks"]        → OHLCV K线，最后一根收盘价 = 当前价
# data["update_time"]               → 更新时间戳

# 解析方法：
from collections import defaultdict
y_axis = data["y_axis"]
current_price = float(data["price_candlesticks"][-1][4])
price_liq = defaultdict(float)
for y_idx, leverage, usd_val in data["liquidation_leverage_data"]:
    if 0 <= y_idx < len(y_axis):
        price_liq[y_axis[y_idx]] += usd_val

longs  = {p: v for p, v in price_liq.items() if p < current_price}  # 多头清算（↓触发）
shorts = {p: v for p, v in price_liq.items() if p > current_price}  # 空头清算（↑触发）
```

注意：单交易所版本（`heatmap/model1` 带 exchange 参数）当前会报 400 错误，改用 aggregated 版本。

## Script Usage

Script-mode skill — read this file, then invoke from a `bash` block:

```bash
python3 - <<'EOF'
import sys, json
sys.path.insert(0, "/data/workspace/skills/coinglass")
from exports import funding_rate, cg_open_interest, cg_liquidations

print(funding_rate(symbol="BTC"))
print(cg_open_interest(symbol="BTC"))
EOF
```

Read `exports.py` for the full list of available functions and exact
signatures. Common ones: `funding_rate`, `long_short_ratio`,
`cg_open_interest`, `cg_liquidations`, `cg_liquidation_analysis`,
`cg_global_account_ratio`, `cg_top_account_ratio`, `cg_top_position_ratio`,
`cg_taker_exchanges`, `cg_net_position`, `cg_supported_coins`,
`cg_supported_exchanges`, `cg_coins_market_data`, `cg_pair_market_data`,
`cg_ohlc_history`, `cg_hyperliquid_whale_alerts`,
`cg_hyperliquid_whale_positions`, `cg_taker_volume_history`,
`cg_aggregated_taker_volume`, `cg_cumulative_volume_delta`,
`cg_coin_netflow`, `cg_whale_transfers`, `cg_btc_etf_flows`,
`cg_eth_etf_flows`, `cg_sol_etf_flows`.


# Coinglass

Coinglass provides the most comprehensive crypto derivatives and institutional data available. 37 tools covering futures positioning, whale tracking, volume analysis, liquidations, and ETF flows.

**API Plan**: Professional ($699/month)
**Rate Limit**: 6000 requests/minute
**API Version**: V4 (with V2 backward compatibility)
**Total Tools**: 37 across 8 categories


## Function Reference (full signatures + return shapes)

All functions live in `exports.py`. Most return `Optional[List[Dict]]` or
`Optional[Dict]`. None means the upstream call failed or returned empty —
always check before indexing.

### ⚠️ Field naming convention (READ THIS FIRST)

CoinGlass v4 API uses **camelCase** for almost all data fields, with a few
legacy snake_case exceptions in liquidation endpoints. Don't assume
snake_case — `inspect` the dict before scripting.

- camelCase: `openInterest`, `volUsd`, `longRate`, `shortVolUsd`,
  `exchangeName`, `nextFundingTime`, `fundingIntervalHours`,
  `oichangePercent`, `h4OIChangePercent`, `avgFundingRateBySymbol`,
  `tokenAmount`, `liquidationUsd` (in some endpoints)
- snake_case (legacy, only in `cg_liquidations`): `liquidation_usd`,
  `longLiquidation_usd`, `shortLiquidation_usd`
- `rate` fields (funding) are STRINGS with "+" / "-" / "%" — parse with
  `float(r.rstrip('%').lstrip('+'))` to compare numerically
- timestamps are millisecond unix epoch (e.g. `1777881600000`)

### Funding & Open Interest

| Function | Signature |
|---|---|
| `funding_rate(symbol, exchange=None)` | dict — keys: `symbol`, `exchange`, `rate` (str), `num_exchanges`, `exchanges_data` (list of {`exchangeName`, `rate`, `nextFundingTime`, `fundingIntervalHours`, `status`}) |
| `cg_open_interest(symbol='BTC', interval='0')` | LIST of dicts (one per exchange) — keys: `symbol`, `openInterest`, `volUsd`, `oichangePercent`, `h4OIChangePercent`, `h24VolChangePercent`, `volChangePercent7d`, `avgFundingRateBySymbol`, `exchangeName`, `exchangeLogo` |

### Long/Short Ratios

| Function | Signature |
|---|---|
| `long_short_ratio(symbol='BTC', interval='h4')` | LIST — top item is aggregated; `list` field inside has per-exchange breakdown. Keys: `longRate`, `shortRate`, `longVolUsd`, `shortVolUsd`, `totalVolUsd`, `list` |
| `cg_global_account_ratio(symbol='BTC', exchange='Binance', interval='1h')` | list of historical bars |
| `cg_top_account_ratio(symbol='BTC', exchange='Binance', interval='1h')` | list — top trader account-count ratio |
| `cg_top_position_ratio(symbol='BTC', exchange='Binance', interval='1h')` | list — top trader position-size ratio |
| `cg_taker_exchanges(symbol='BTC', range_type='4h')` | list — taker buy/sell across exchanges |
| `cg_net_position(symbol='BTC', exchange='Binance', interval='1h')` | list — net long-short USD over time |

### Liquidations

| Function | Signature |
|---|---|
| `cg_liquidations(symbol='BTC', time_type='h24')` | LIST of dicts (one per exchange + an `'All'` row first). Keys: `exchange`, `liquidation_usd`, `longLiquidation_usd`, `shortLiquidation_usd` (NOTE: snake_case legacy fields) |
| `cg_liquidation_analysis(symbol='BTC', time_type='h24')` | dict — aggregated network-wide stats |
| `cg_coin_liquidation_history(symbol='BTC', interval='h4')` | list — historical liq bars |
| `cg_pair_liquidation_history(symbol='BTC', exchange='Binance', interval='h4')` | list — historical liq for one pair on one exchange |
| `cg_liquidation_coin_list(symbol=None)` | list of all coins with liq summary |
| `cg_liquidation_orders(symbol='BTC', exchange=None)` | list — recent individual liq orders |

### Futures Market Data

| Function | Signature |
|---|---|
| `cg_supported_coins()` | List[str] — symbols supported by CoinGlass |
| `cg_supported_exchanges()` | list of exchange info dicts |
| `cg_coins_market_data(symbol=None)` | list — current snapshot for all coins (or one if symbol given) |
| `cg_pair_market_data(symbol='BTC', exchange=None)` | list — pair-level snapshot |
| `cg_ohlc_history(symbol='BTC', interval='h4', exchange=None)` | list of OHLCV bars |

### Hyperliquid Whale Tracking

| Function | Signature |
|---|---|
| `cg_hyperliquid_whale_alerts()` | list — recent large-position alerts |
| `cg_hyperliquid_whale_positions()` | list — current open whale positions |
| `cg_hyperliquid_positions_by_coin(symbol='BTC')` | list — whales holding a specific coin |
| `cg_hyperliquid_position_distribution(symbol='BTC')` | dict — long/short position-size distribution |

### Volume / Flow

| Function | Signature |
|---|---|
| `cg_taker_volume_history(symbol='BTC', exchange='Binance', interval='1h', limit=1000, start_time=None, end_time=None)` | list — taker buy/sell volume bars |
| `cg_aggregated_taker_volume(symbol='BTC', interval='h4')` | list — aggregated across all exchanges |
| `cg_cumulative_volume_delta(symbol='BTC', exchange='Binance', interval='1h', limit=1000, start_time=None, end_time=None)` | list — CVD bars |
| `cg_coin_netflow(symbol=None)` | list — net inflow/outflow per coin |
| `cg_whale_transfers()` | dict — recent on-chain large transfers |

### ETF Flows

| Function | Signature |
|---|---|
| `cg_btc_etf_flows()` | list — daily flows per US BTC ETF |
| `cg_btc_etf_history(etf_ticker=None)` | list — historical AUM/flows |
| `cg_btc_etf_list()` | list of BTC ETF tickers + AUM |
| `cg_btc_etf_premium_discount()` | list — premium/discount % vs NAV |
| `cg_hk_btc_etf_flows()` | list — Hong Kong BTC ETF flows |
| `cg_eth_etf_flows()` / `cg_eth_etf_list()` / `cg_eth_etf_premium_discount()` / `cg_hk_eth_etf_flows()` | ETH ETF equivalents |
| `cg_sol_etf_flows()` / `cg_sol_etf_list()` | SOL ETF data |
| `cg_xrp_etf_flows()` / `cg_xrp_etf_list()` | XRP ETF data |

### Sample responses (most-used functions)

`funding_rate(symbol="BTC")`:
```json
{
  "symbol": "BTC",
  "exchange": "average",
  "rate": "-0.0016%",
  "num_exchanges": 21,
  "exchanges_data": [
    {"exchangeName": "Binance", "rate": "+0.0050%",
     "nextFundingTime": 1777881600000, "fundingIntervalHours": 8, "status": 1}
  ]
}
```

`cg_liquidations(symbol="BTC", time_type="h24")`:
```json
[
  {"exchange": "All", "liquidation_usd": 170497688.16,
   "longLiquidation_usd": 8179073.80, "shortLiquidation_usd": 162318614.36},
  {"exchange": "Bybit", "liquidation_usd": 40454694.98, ...}
]
```

`cg_open_interest(symbol="BTC")`:
```json
[
  {"symbol": "BTC", "openInterest": 61395303653.62, "volUsd": 56349328748.42,
   "oichangePercent": 7.17, "h4OIChangePercent": 5.33,
   "avgFundingRateBySymbol": -0.001874, "exchangeName": "Binance"}
]
```

`long_short_ratio(symbol="BTC", interval="h4")`:
```json
[{
  "symbol": "BTC", "longRate": 53.65, "shortRate": 46.35,
  "longVolUsd": 12558668895.91, "shortVolUsd": 10848776476.99,
  "totalVolUsd": 23407445372.91,
  "list": [
    {"exchangeName": "Binance", "longRate": 55.75, "shortRate": 44.25, ...}
  ]
}]
```


## Tool Selection Guide

### Decision Tree

**Step 1: Is this about LIQUIDATIONS?**

```
Liquidation query?
├─ YES → How many coins?
│   ├─ ALL coins / ranking / 排行 / 汇总
│   │   └─ → cg_liquidation_coin_list  ✅ (most liquidation queries land here)
│   ├─ ONE coin, need history over time
│   │   └─ → cg_coin_liquidation_history
│   ├─ ONE coin, specific orders (price/side/USD)
│   │   └─ → cg_liquidation_orders
│   └─ ONE coin, just a quick total + sentiment label
│       └─ → cg_liquidation_analysis  (rarely needed; only if explicitly "simple summary")
```

**Step 2: Is this about LONG/SHORT RATIO?**

```
Long/short query?
├─ Historical time-series, trend over time, 多空比变化
│   └─ → cg_global_account_ratio  (ALL accounts)
│      or cg_top_account_ratio    (top traders only)
│      or cg_top_position_ratio   (by position size)
└─ Current snapshot only (no history needed)
    └─ → long_short_ratio
```

**Step 3: Is this about OPEN INTEREST?**

```
OI query?
└─ → cg_open_interest  (always — do NOT use cg_coins_market_data for OI)
```

**Step 4: Is this a MARKET OVERVIEW / SENTIMENT query?**

```
Sentiment / 市场情绪 / pre-trade check?
└─ Use: funding_rate + long_short_ratio + cg_open_interest
   DO NOT use cg_coins_market_data as a substitute for any of the above
```

---

### Keyword → Tool Lookup

| Keyword / Pattern | Correct Tool | ❌ Do NOT use |
|---|---|---|
| 爆仓排行 / 今日爆仓 / all coins liquidation | `cg_liquidation_coin_list` | `cg_liquidations` |
| 24h爆仓汇总 / liquidation summary | `cg_liquidation_coin_list` | `cg_liquidation_analysis` |
| 全网账户多空比 / account L/S ratio | `cg_global_account_ratio` | `long_short_ratio` |
| 头部交易者多空 / top trader ratio | `cg_top_account_ratio` | `long_short_ratio` |
| 未平仓合约 / open interest | `cg_open_interest` | `cg_coins_market_data` |
| 市场情绪多空分析 | `funding_rate` + `long_short_ratio` + `cg_open_interest` | `cg_coins_market_data` |
| BTC做多检查 / pre-trade checklist | `funding_rate` + `cg_global_account_ratio` + `cg_liquidation_coin_list` | — |

---

### Common Mistakes

**Mistake 1 (most common — 8x failure): Using `cg_liquidations` when you need `cg_liquidation_coin_list`**
- `cg_liquidations` → one coin, one timeframe, basic total only
- `cg_liquidation_coin_list(exchange)` → ALL coins, multi-timeframe (1h/4h/12h/24h), per-exchange breakdown
- **Rule:** If the question asks for a ranking, overview, or doesn't specify a single coin → use `cg_liquidation_coin_list`

**Mistake 2 (5x failure): Using `cg_liquidation_analysis` for liquidation rankings**
- `cg_liquidation_analysis` adds a sentiment label to a single-coin total — it is NOT a ranking tool
- **Rule:** "今日爆仓排行" / "各币种爆仓" → always `cg_liquidation_coin_list`

**Mistake 3 (3x failure): Using `long_short_ratio` for historical L/S analysis**
- `long_short_ratio` is a current snapshot (no time-series)
- `cg_global_account_ratio` returns history — use it when the user wants trends or comparison over time
- **Rule:** If the question compares 全网 (global) vs 头部 (top traders) → call BOTH `cg_global_account_ratio` AND `cg_top_account_ratio`

**Mistake 4 (2x failure): Using `cg_coins_market_data` for open interest**
- `cg_coins_market_data` is a bulk snapshot of many coins — not a replacement for dedicated OI or L/S tools
- **Rule:** OI question → `cg_open_interest`. L/S question → `long_short_ratio` or `cg_global_account_ratio`. Never route either to `cg_coins_market_data`.

## Rules

### Tool Call Guidance

**❌ FORBIDDEN TOOLS — NEVER USE:**
- `bash` — Do NOT write scripts to process/format data. Use natural language.
- `write_file` / `read_file` / `edit_file` — Do NOT save intermediate data. Answer directly.
- `learning_log` — ONLY for genuine skill bugs or persistent API errors. NOT for empty responses.
- `echo` — Do NOT use for debugging or output.

**✅ CORRECT PATTERN:**
- Tool returns data → Summarize in natural language → Done
- Tool returns empty/null → Report "no data available" → Done
- Need calculation (%, change, ratio) → Do mental math in reply

**Match tool count to question scope:**
  - 单一指标问题（"BTC 资金费率"、"ETH 多空比"）→ 1 个工具，直接返回
  - 多维度分析（"做多是否合适"、"衍生品体检"）→ 3-5 个工具，综合分析
  - 对比问题（"ETH vs SOL"）→ 每个币种调相同工具，并列对比
- **避免重复调用同一工具。** 除非用户明确要求不同币种/交易所的对比。

### Learning Log Usage (CRITICAL)

**`learning_log` is FORBIDDEN for:**
- ❌ Empty API responses — just report "no data available"
- ❌ Tool returning None/null — handle gracefully
- ❌ Uncertainty about tool selection — check decision tree first
- ❌ Normal tool errors — retry once, then report failure

**`learning_log` is ONLY for:**
- ✅ Genuine bugs in skill code (wrong data format returned)
- ✅ Persistent API rate limit errors after 2+ retries
- ✅ Missing tools that should exist per skill definition

### ETF Tool Selection
| Query | Primary Tool | Secondary Tool |
|-------|--------------|----------------|
| BTC ETF 资金流入/流出 | `cg_btc_etf_flows()` | `cg_btc_etf_history()` for detailed history |
| ETH ETF 资金流入/流出 | `cg_eth_etf_flows()` | — |
| SOL/XRP ETF flows | `cg_sol_etf_flows()` / `cg_xrp_etf_flows()` | — |
| HK ETF flows | `cg_hk_btc_etf_flows()` / `cg_hk_eth_etf_flows()` | — |
| ETF 列表/代码 | `cg_btc_etf_list()` / `cg_eth_etf_list()` | — |
| ETF 溢价/折价 | `cg_btc_etf_premium_discount()` | — |

**ETF 对比问题 workflow:**
```
# BTC vs ETH ETF 对比
btc = cg_btc_etf_flows()
eth = cg_eth_etf_flows()
# Compare the latest day's net flows, summarize in 2-3 sentences
```

## Quick Routing (use this first)

| Query type | Tool |
|---|---|
| 爆仓/liquidation summary (24h, by coin) | `cg_liquidation_coin_list` |
| Individual liquidation orders | `cg_liquidation_orders` |
| Liquidation history for a coin | `cg_coin_liquidation_history` |
| Funding rate | `funding_rate` |
| Long/short ratio (global) | `cg_global_account_ratio` |
| Open interest | `cg_open_interest` |
| Whale activity on Hyperliquid | `cg_hyperliquid_whale_alerts` |
| ETF flows (BTC) | `cg_btc_etf_flows` |

## When to Use Coinglass

Use Coinglass for:
- **Derivatives positioning** - What are leveraged traders doing?
- **Whale tracking** - Track large positions on Hyperliquid DEX
- **Funding rates** - Cost of holding perpetual futures
- **Open interest** - Total notional value of open positions
- **Long/Short ratios** - Sentiment among leveraged traders (global, top accounts, top positions)
- **Liquidations** - Forced position closures with heatmaps and individual orders
- **Volume analysis** - Taker volume, CVD, netflow patterns
- **ETF flows** - Institutional adoption (Bitcoin, Ethereum, Solana, XRP, Hong Kong)
- **Whale transfers** - Large on-chain movements (>$10M)
- **Futures market data** - Supported coins, exchanges, pairs, and OHLC price history

## Tool Categories

### 1. Basic Derivatives Analytics (7 tools)

Core derivatives data for market analysis:

- `funding_rate(symbol, exchange?)` - Current funding rates
- `long_short_ratio(symbol, exchange?, interval?)` - Basic L/S ratios
- `cg_open_interest(symbol)` - Current OI across exchanges
- `cg_liquidations(symbol, time?)` - Recent liquidations
- `cg_liquidation_analysis(symbol)` - Liquidation heatmap analysis
- `cg_supported_coins()` - All supported coins
- `cg_supported_exchanges()` - All exchanges with pairs

### 2. Advanced Long/Short Ratios (6 tools)

Deep positioning analysis with multiple metrics:

- `cg_global_account_ratio(symbol, interval?)` - Global account-based L/S ratio
- `cg_top_account_ratio(symbol, exchange, interval?)` - Top trader accounts ratio
- `cg_top_position_ratio(symbol, exchange, interval?)` - Top positions by size
- `cg_taker_exchanges(symbol)` - Taker buy/sell by exchange
- `cg_net_position(symbol, exchange)` - Net long/short positions
- `cg_net_position_v2(symbol)` - Enhanced net position data

**Use cases**:
- Smart money tracking (top accounts vs retail)
- Exchange-specific sentiment
- Position size distribution analysis

### 3. Advanced Liquidations (4 tools)

Granular liquidation tracking for cascade prediction:

- `cg_coin_liquidation_history(symbol, interval?, limit?, start_time?, end_time?)` - Aggregated across all exchanges
- `cg_pair_liquidation_history(symbol, exchange, interval?, limit?, start_time?, end_time?)` - Exchange-specific pair
- `cg_liquidation_coin_list(exchange)` - All coins on an exchange
- `cg_liquidation_orders(symbol, exchange, min_liquidation_amount, start_time?, end_time?)` - Individual orders (past 7 days, max 200)

**Use cases**:
- Identifying liquidation clusters
- Tracking liquidation patterns over time
- Finding large liquidation events

### 4. Hyperliquid Whale Tracking (4 tools)

Track large traders on Hyperliquid DEX (~200 recent alerts):

- `cg_hyperliquid_whale_alerts()` - Recent large position opens/closes (>$1M)
- `cg_hyperliquid_whale_positions()` - Current whale positions with PnL
- `cg_hyperliquid_positions_by_coin()` - All positions grouped by coin
- `cg_hyperliquid_position_distribution()` - Distribution by size with sentiment

**Use cases**:
- Following smart money on Hyperliquid
- Detecting large position changes
- Tracking whale PnL and sentiment

### 5. Futures Market Data (5 tools)

Market overview and price data:

- `cg_coins_market_data()` - ALL coins data in one call (100+ coins)
- `cg_pair_market_data(symbol, exchange)` - Specific pair metrics
- `cg_ohlc_history(symbol, exchange, interval, limit?)` - OHLC candlesticks
- `cg_taker_volume_history(symbol, exchange, interval, limit?, start_time?, end_time?)` - Pair-specific taker volume
- `cg_aggregated_taker_volume(symbol, interval, limit?, start_time?, end_time?)` - Aggregated across exchanges

**Use cases**:
- Market screening (scan all coins at once)
- Price action analysis
- Volume pattern recognition

### 6. Volume & Flow Analysis (4 tools)

Order flow and capital movement tracking:

- `cg_cumulative_volume_delta(symbol, exchange, interval, limit?, start_time?, end_time?)` - CVD = Running total of (buy - sell)
- `cg_coin_netflow()` - Capital flowing into/out of coins
- `cg_whale_transfers()` - Large on-chain transfers (>$10M, past 6 months)

**Use cases**:
- Order flow divergence detection
- Smart money tracking
- Institutional movement monitoring

### 7. Bitcoin ETF Data (5 tools)

Track institutional Bitcoin adoption:

- `cg_btc_etf_flows()` - Daily net inflows/outflows
- `cg_btc_etf_premium_discount()` - ETF price vs NAV
- `cg_btc_etf_history()` - Comprehensive history (price, NAV, premium%, shares, assets)
- `cg_btc_etf_list()` - List of Bitcoin ETFs
- `cg_hk_btc_etf_flows()` - Hong Kong Bitcoin ETF flows

**Use cases**:
- Institutional demand tracking
- Premium/discount arbitrage
- Regional flow comparison (US vs Hong Kong)

### 8. Other ETF Data (8 tools)

Ethereum, Solana, XRP, and Hong Kong ETFs:

- `cg_eth_etf_flows()` - Ethereum ETF flows
- `cg_eth_etf_list()` - Ethereum ETF list
- `cg_eth_etf_premium_discount()` - ETH ETF premium/discount
- `cg_sol_etf_flows()` - Solana ETF flows
- `cg_sol_etf_list()` - Solana ETF list
- `cg_xrp_etf_flows()` - XRP ETF flows
- `cg_xrp_etf_list()` - XRP ETF list
- `cg_hk_eth_etf_flows()` - Hong Kong Ethereum ETF flows

**Use cases**:
- Multi-asset institutional tracking
- Comparative flow analysis
- Regional preference analysis

## Common Workflows

### Quick Market Scan
```
# Get everything in 3 calls
all_coins = cg_coins_market_data()  # 100+ coins with full metrics
btc_liquidations = cg_liquidations("BTC")
whale_alerts = cg_hyperliquid_whale_alerts()
```

### Deep Position Analysis
```
# BTC positioning across metrics
cg_global_account_ratio("BTC")  # Retail sentiment
cg_top_account_ratio("BTC", "Binance")  # Smart money
cg_net_position_v2("BTC")  # Net positioning
cg_liquidation_heatmap("BTC", "Binance")  # Cascade levels
```

### ETF Flow Monitoring
```
# Institutional demand
btc_flows = cg_btc_etf_flows()
eth_flows = cg_eth_etf_flows()
sol_flows = cg_sol_etf_flows()
```

### Whale Tracking
```
# Follow the whales
hyperliquid_whales = cg_hyperliquid_whale_alerts()
whale_positions = cg_hyperliquid_whale_positions()
onchain_whales = cg_whale_transfers()  # >$10M on-chain
```

### Volume Analysis
```
# Order flow
cvd = cg_cumulative_volume_delta("BTC", "Binance", "1h", 100)
netflow = cg_coin_netflow()  # All coins
taker_vol = cg_aggregated_taker_volume("BTC", "1h", 100)
```

## Interpretation Guides

### Funding Rates

| Rate (8h) | Read |
|------------|------|
| > +0.05% | Extreme greed — crowded long, squeeze risk |
| +0.01% to +0.05% | Bullish bias, normal |
| -0.005% to +0.01% | Neutral |
| -0.05% to -0.005% | Bearish bias, normal |
| < -0.05% | Extreme fear — crowded short, bounce risk |

Extreme funding often precedes reversals. The crowd is usually wrong at extremes.

### Open Interest + Price Matrix

| OI | Price | Read |
|----|-------|------|
| Up | Up | New longs entering — bullish conviction |
| Up | Down | New shorts entering — bearish conviction |
| Down | Up | Short covering — weaker rally, less conviction |
| Down | Down | Long liquidation — weaker selloff, capitulation |

### Long/Short Ratio

| Ratio | Read |
|-------|------|
| > 1.5 | Crowded long — contrarian bearish |
| 1.1–1.5 | Moderately bullish |
| 0.9–1.1 | Balanced |
| 0.7–0.9 | Moderately bearish |
| < 0.7 | Crowded short — contrarian bullish |

### CVD (Cumulative Volume Delta)

| Pattern | Read |
|---------|------|
| CVD rising, price rising | Strong buy pressure, healthy uptrend |
| CVD falling, price rising | Weak rally, distribution |
| CVD rising, price falling | Accumulation, potential bottom |
| CVD falling, price falling | Strong sell pressure, healthy downtrend |

### ETF Flows

| Flow | Read |
|------|------|
| Large inflows | Institutional buying, bullish |
| Consistent inflows | Sustained demand |
| Large outflows | Institutional selling, bearish |
| Premium to NAV | High demand, bullish sentiment |
| Discount to NAV | Weak demand, bearish sentiment |

## Analysis Patterns

**Multi-metric confirmation**: Combine tools across categories for high-confidence signals:
- Funding + L/S ratio + liquidations = positioning extremes
- CVD + taker volume + whale alerts = smart money direction
- ETF flows + whale transfers + open interest = institutional conviction

**Smart money vs retail**: Compare metrics to identify divergence:
- `cg_top_account_ratio` (smart money) vs `cg_global_account_ratio` (retail)
- Hyperliquid whale positions vs overall long/short ratios

**Cascade prediction**: Use liquidation tools to predict volatility:
- `cg_coin_liquidation_history` shows liquidation patterns over time
- `cg_liquidation_orders` reveals recent forced closures
- Large liquidation events = cascade risk zones

**Flow divergence**: Track capital movements:
- `cg_coin_netflow` shows where money is flowing
- `cg_whale_transfers` reveals large movements
- ETF flows show institutional demand

## Performance Optimization

### Batch vs Individual Calls

**✅ OPTIMAL**: Use batch endpoints
```
# One call gets 100+ coins
all_coins = cg_coins_market_data()

# One call gets all whale alerts
whales = cg_hyperliquid_whale_alerts()

# One call gets all ETF flows
btc_etf = cg_btc_etf_flows()
```

**❌ INEFFICIENT**: Multiple individual calls
```
# Don't do this - wastes API quota
btc = cg_pair_market_data("BTC", "Binance")
eth = cg_pair_market_data("ETH", "Binance")
sol = cg_pair_market_data("SOL", "Binance")
```

### Query Parameters

Most history endpoints support:
- `interval`: Time granularity (1h, 4h, 12h, 24h, etc.)
- `limit`: Number of records (default varies, max 1000)
- `start_time`: Unix timestamp (milliseconds)
- `end_time`: Unix timestamp (milliseconds)

Example:
```
cg_coin_liquidation_history(
    symbol="BTC",
    interval="1h",
    limit=100,
    start_time=1704067200000,  # 2024-01-01
    end_time=1704153600000     # 2024-01-02
)
```

## Supported Exchanges

Major exchanges with futures data:
- **Tier 1**: Binance, OKX, Bybit, Gate, KuCoin, MEXC
- **Traditional**: CME (Bitcoin and Ethereum futures), Coinbase
- **DEX**: Hyperliquid, dYdX, ApeX
- **Others**: Bitfinex, Kraken, HTX, BingX, Crypto.com, CoinEx, Bitget

Use `cg_supported_exchanges()` for complete list with pair details.

## Important Notes

- **API Key**: Requires COINGLASS_API_KEY environment variable
- **Symbols**: Use standard symbols (BTC, ETH, SOL, etc.) - check with `cg_supported_coins()`
- **Exchanges**: Check `cg_supported_exchanges()` for full list with pairs
- **Update Frequency**:
  - Market data: ≤ 1 minute
  - Funding rates: Every 8 hours (or 1 hour for some exchanges)
  - OHLC: Real-time to 1 minute depending on interval
  - ETF data: Daily (after market close)
  - Whale transfers: Real-time (within minutes)
- **API Versions**:
  - V4 endpoints use `CG-API-KEY` header (most tools)
  - V2 endpoints use `coinglassSecret` header (some legacy tools)
  - Both work with the same COINGLASS_API_KEY environment variable
- **Rate Limits**: Professional plan allows 6000 requests/minute
- **Historical Data Limits**:
  - Liquidation orders: Past 7 days, max 200 records
  - Whale transfers: Past 6 months, minimum $10M
  - Hyperliquid alerts: ~200 most recent large positions
  - Other endpoints: Typically months to years of history

## Data Quality Notes

- **Hyperliquid**: Data is exchange-specific, doesn't include other DEXs
- **Whale Transfers**: Covers Bitcoin, Ethereum, Tron, Ripple, Dogecoin, Litecoin, Polygon, Algorand, Bitcoin Cash, Solana
- **ETF Data**: US ETFs updated after market close (4 PM ET), Hong Kong ETFs updated after Hong Kong market close
- **Liquidation Orders**: Limited to 200 most recent, use heatmap for broader view
- **CVD**: Cumulative metric - resets are not automatic, track changes not absolute values

## Version History

- **v3.0.0** (2025-03): Added 36 new tools
  - Advanced liquidations (5 tools)
  - Hyperliquid whale tracking (5 tools)
  - Volume & flow analysis (5 tools)
  - Whale transfers (1 tool)
  - Bitcoin ETF (6 tools)
  - Other ETFs (8 tools)
  - Advanced L/S ratios (6 tools)
- **v2.2.0** (2024): V4 API migration with futures market data
- **v1.0.0** (2024): Initial release with basic derivatives data
