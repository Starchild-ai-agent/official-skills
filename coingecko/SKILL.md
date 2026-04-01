---
name: coingecko
version: 1.0.0
description: CoinGecko crypto price data, charts, market discovery, and global stats
tools:
  - coin_price
  - coin_ohlc
  - coin_chart
  - cg_trending
  - cg_top_gainers_losers
  - cg_new_coins
  - cg_global
  - cg_global_defi
  - cg_categories
  - cg_derivatives
  - cg_derivatives_exchanges
  - cg_coins_list
  - cg_coins_markets
  - cg_coin_data
  - cg_coin_tickers
  - cg_exchanges
  - cg_exchange
  - cg_exchange_tickers
  - cg_exchange_volume_chart
  - cg_nfts_list
  - cg_nft
  - cg_nft_by_contract
  - cg_asset_platforms
  - cg_exchange_rates
  - cg_vs_currencies
  - cg_categories_list
  - cg_search
  - cg_token_price
  - cg_coin_by_contract

metadata:
  starchild:
    emoji: "🦎"
    skillKey: coingecko
    requires:
      env:
        - COINGECKO_API_KEY

user-invocable: false
disable-model-invocation: false
---

# CoinGecko

CoinGecko provides comprehensive crypto market data including spot prices, OHLC candles, market cap, trending coins, sector performance, and global stats.

## ⚠️ CRITICAL — Tool Selection Rules

**These rules override any default behavior. Read the table, then pick the tool.**

### Quick Triggers (match first, skip table)

- Any mention of **板块 / sector / category / Layer1 / DeFi / Meme / AI coins** → call `cg_categories()` immediately, no other tool needed.
- Any mention of **exchange volume trend / 交易所交易量变化** → call `cg_exchange_volume_chart(exchange_id=..., days=...)`.
- Any mention of **price / 价格** for a single coin → call `coin_price()`.
- Any mention of **NFT floor / NFT排名** → call `cg_nfts_list()`.

### ⛔ One-Call Rule

Call each tool **once**. If the result is insufficient:
- Narrow the query (smaller `per_page`, different `coin_id`)
- Do NOT call the same tool again with the same params
- Do NOT chain more than 2 tool calls for a single user question

### Decision Table

| User intent | Correct tool | Wrong tool (DO NOT use) |
|---|---|---|
| **Sector/category performance** ("L1 vs DeFi", "AI sector", "板块对比", "meme板块") | `cg_categories()` | ❌ `cg_coins_markets` (individual coins ≠ sector aggregate) |
| **Deep research on ONE coin** ("SOL研究", "BTC fundamentals", "ATH回撤") | `cg_coin_data(coin_id=...)` | ❌ `coin_price` (price only, no ATH/community/dev) |
| **Compare/rank multiple coins** ("top 10", "市值排名", "volume ranking") | `cg_coins_markets(per_page=10)` — always set per_page! | ❌ `cg_coin_data` (one coin at a time, too slow) |
| **Current price** ("BTC价格", "ETH多少钱") | `coin_price()` | ❌ `cg_coins_market_data` (that's coinglass!) |
| **NFT ranking** ("NFT排名", "floor price") | `cg_nfts_list()` | ❌ `cg_coins_markets` (tokens only) |
| **OHLC / K线 / candlestick data** ("K线", "OHLC", "蜡烛图") | `coin_ohlc()` | ❌ `cg_ohlc_history` — that is a **coinglass** tool, wrong skill! |
| **Price chart/trend** ("30天走势", "price history") | `coin_chart()` | ❌ `cg_ohlc_history` (coinglass, wrong skill!) |
| **List exchanges** ("交易所列表", "exchanges") | `cg_exchanges()` | ❌ `cg_supported_exchanges` — that is a **coinglass** tool, wrong skill! |
| **Exchange trading pairs** ("Binance交易对") | `cg_exchange_tickers()` | ❌ `cg_supported_exchanges` (coinglass, wrong skill!) |
| **Exchange volume trend** ("交易量趋势", "volume chart", "过去N天交易量") | `cg_exchange_volume_chart()` | ❌ `cg_taker_volume_history` (coinglass, wrong skill!) |

### Minimal Calls Principle

Most questions need only ONE or TWO tool calls:
- `cg_categories()` → returns ALL sectors in one call. Never loop.
- `cg_coins_markets()` → returns top 20 coins. One call is enough.
- `cg_coin_data(coin_id=...)` → returns everything about one coin. No need for coin_price + cg_coins_markets separately.

### Model-Specific Guidance

**For all models (mandatory rules):**
- "板块"/"sector"/"category" → ALWAYS use `cg_categories()`, NEVER `cg_coins_markets`
- "研究"/"research"/"deep dive" on one coin → ALWAYS use `cg_coin_data()`
- Cross-skill confusion: `cg_coins_market_data`, `cg_ohlc_history`, `cg_supported_exchanges` are coinglass tools, NOT coingecko

**Additional guidance for smaller models (Qwen, Gemini Flash, etc.):**
- If unsure between tools, check the Decision Table above — it covers 90% of cases
- `cg_categories` = aggregated SECTOR data (DeFi total market cap). `cg_coins_markets` = individual COIN data (list of coins). These are completely different
- When user mentions any sector name (AI, DeFi, L1, L2, Meme, Gaming, RWA, NFT sector) → `cg_categories()`
- When user asks about a specific coin's history/background/ATH → `cg_coin_data(coin_id=...)`

## Common Workflows

### Get Coin Price
```
coin_price(coin_id="bitcoin")
coin_price(coin_id="ethereum", vs_currencies="usd,eur")
```

### Historical Data
```
coin_ohlc(coin_id="bitcoin", vs_currency="usd", days=7)
coin_chart(coin_id="ethereum", vs_currency="usd", days=30)
```

### Market Discovery
```
cg_trending()
cg_top_gainers_losers()
cg_new_coins()
cg_coins_markets(vs_currency="usd", order="market_cap_desc")
```

### Coin Deep Research
```
cg_coin_data(coin_id="solana")  # Includes ATH, description, categories
cg_coin_data(coin_id="ethereum", community_data=True, developer_data=True)
```

### Sector / Category Comparison
```
cg_categories()  # ALL sectors in ONE call
cg_categories(order="market_cap_change_24h_desc")
```

### NFT Data
```
cg_nfts_list()  # Top NFTs with floor price + volume
cg_nft(nft_id="bored-ape-yacht-club")  # Deep dive on one collection
```

### Global Metrics
```
cg_global()
cg_global_defi()
```

## Important Notes

- **Coin IDs**: CoinGecko uses slug IDs (e.g., "bitcoin", "ethereum"). Tools auto-resolve BTC, ETH, SOL.
- **Rate Limits**: Use batch endpoints when querying multiple coins.
- If unsure about a coin ID → `cg_search(query="coin name")` first.
