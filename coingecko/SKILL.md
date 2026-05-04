---
name: coingecko
version: 2.0.2
description: CoinGecko crypto price data, charts, market discovery, and global stats
delivery: script
protected: true
metadata:
  starchild:
    emoji: 🦎
    skillKey: coingecko
    requires:
      env:
      - COINGECKO_API_KEY
user-invocable: false
disable-model-invocation: false
---

## Script Usage

Script-mode skill — read this file, then invoke from a `bash` block:

```bash
python3 - <<'EOF'
import sys, json
sys.path.insert(0, "/data/workspace/skills/coingecko")
from exports import coin_price, cg_trending, cg_global

print(coin_price(coin_ids="bitcoin,ethereum"))
print(cg_trending())
EOF
```

Read `exports.py` for the full list of available functions. Common ones:
`coin_price`, `coin_ohlc`, `coin_chart`, `cg_trending`,
`cg_top_gainers_losers`, `cg_new_coins`, `cg_global`, `cg_global_defi`,
`cg_categories`, `cg_derivatives`, `cg_coins_markets`, `cg_coin_data`,
`cg_coin_tickers`, `cg_search`, `cg_token_price`, `cg_coin_by_contract`.


# CoinGecko Skill


## Function Reference (signatures)

All public functions are in `exports.py`. `coin_id` is the CoinGecko id
(e.g. `bitcoin`, `ethereum`) — use `cg_search(query)` first if unsure.
`vs_currency` defaults to `usd`.

### Prices & Charts
| Function | Description |
|---|---|
| `coin_price(coin_ids, timestamps=None, vs_currency='usd')` | Current or historical price. `coin_ids` = comma-string like `"bitcoin,ethereum"`. `timestamps` = list of unix ts for historical (default: now). |
| `coin_ohlc(coin_id, days=30, vs_currency='usd')` | OHLC bars for last N days. Returns list of `[ts, o, h, l, c]`. Granularity auto-selected: 1d=30min, 7-30d=4h, 30d+=4h. |
| `coin_chart(coin_id, days=30, vs_currency='usd')` | Price + market_cap + total_volume timeseries. Returns `{prices, market_caps, total_volumes}` (each list of `[ts, val]`). |

### Discovery
| Function | Description |
|---|---|
| `cg_trending()` | Trending coins, NFTs, categories (last 24h). |
| `cg_top_gainers_losers(vs_currency='usd', duration='24h')` | Top gainers/losers. `duration` = `1h`/`24h`/`7d`/`14d`/`30d`/`60d`/`1y`. |
| `cg_new_coins()` | Recently listed coins. |
| `cg_search(query)` | Search coins/exchanges/categories by name. |

### Market Data
| Function | Description |
|---|---|
| `cg_global()` | Global crypto market: total market_cap, volume, dominance. |
| `cg_global_defi()` | Global DeFi: TVL, dominance, top protocols. |
| `cg_coins_markets(vs_currency='usd', order='market_cap_desc', per_page=100, page=1, sparkline=False, price_change_percentage='24h', category=None, ids=None)` | Top coins with full market data. |
| `cg_coin_data(coin_id, localization=False, tickers=False, market_data=True, community_data=False, developer_data=False, sparkline=False)` | Detailed data for one coin. |
| `cg_coin_tickers(coin_id, exchange_ids=None, include_exchange_logo=False, page=1, order='volume_desc', depth=False)` | Where a coin trades + volumes. |
| `cg_coins_list(include_platform=False)` | All coin ids/symbols (for resolving). |

### Categories / Derivatives / NFTs
| Function | Description |
|---|---|
| `cg_categories(order='market_cap_desc')` | Top categories with market_cap and volume. |
| `cg_categories_list()` | Just category ids/names. |
| `cg_derivatives(include_tickers='unexpired')` | Derivatives tickers across exchanges. |
| `cg_derivatives_exchanges(order='open_interest_btc_desc', per_page=50)` | Derivatives exchange rankings. |
| `cg_nfts_list(order='market_cap_usd_desc', per_page=100, page=1)` | Top NFT collections. |
| `cg_nft(nft_id)` | NFT collection detail. |
| `cg_nft_by_contract(asset_platform, contract_address)` | NFT by contract address. |

### Exchanges
| Function | Description |
|---|---|
| `cg_exchanges(per_page=100, page=1)` | Exchange rankings. |
| `cg_exchange(exchange_id)` | One exchange's detail. |
| `cg_exchange_tickers(exchange_id, ...)` | Tickers on an exchange. |
| `cg_exchange_volume_chart(exchange_id, days=30)` | Exchange volume history. |

### Contracts / Tokens (by platform)
| Function | Description |
|---|---|
| `cg_token_price(platform, contract_addresses, vs_currencies='usd', include_market_cap=False, include_24hr_vol=False, include_24hr_change=False, include_last_updated_at=False)` | Price by contract address on a platform. |
| `cg_coin_by_contract(platform, contract_address)` | Coin metadata by contract. |
| `cg_asset_platforms(filter=None)` | Supported chains. |
| `cg_vs_currencies()` | Supported quote currencies. |
| `cg_exchange_rates()` | BTC-denominated rates for fiat/major coins. |

## 🚫 CRITICAL: STOP — READ THIS BEFORE CALLING ANY TOOL

**The #1 error is calling Coinglass tools instead of CoinGecko tools.** They have similar names but are COMPLETELY DIFFERENT systems.

### WRONG → RIGHT Tool Substitution Table

| ❌ NEVER call this | ✅ Call this instead | How to tell them apart |
|---|---|---|
| `cg_coins_market_data` | **`cg_coins_markets`** | market_data=Coinglass derivatives. markets=CoinGecko spot. |
| `cg_ohlc_history` | **`coin_ohlc`** | ohlc_history=Coinglass futures candles. coin_ohlc=CoinGecko spot candles. |
| `cg_pair_market_data` | **`cg_coin_tickers`** | pair_market_data=Coinglass futures pair. coin_tickers=CoinGecko spot pairs. |
| `cg_supported_exchanges` | **`cg_exchanges`** | supported_exchanges=Coinglass futures. exchanges=CoinGecko spot. |
| `cg_taker_exchanges` | **`cg_exchange`** | taker=Coinglass volume. exchange=CoinGecko exchange info. |
| `cg_aggregated_taker_volume` | **`cg_coin_tickers`** | taker_volume=Coinglass. coin_tickers=CoinGecko volume across exchanges. |
| `defillama_chains` | **`cg_global_defi`** | For DeFi stats from CoinGecko, use cg_global_defi(). |

### Also FORBIDDEN:
- ❌ `web_search` / `web_fetch` — ALL data is available via native CoinGecko tools above. NEVER use web_search for crypto market data.
- ❌ `bash` for data processing — CoinGecko tools return clean data. No bash needed.
- ❌ **NEVER answer with training data** — all prices, rankings, OHLC are stale. CALL THE TOOL.

## ⚠️ MANDATORY TOOL CALLS — You MUST call a tool before answering these

| Request type | You MUST call | Why |
|---|---|---|
| K线 / OHLC / candlestick / open high low close | `coin_ohlc(coin_id, days)` | Price data is real-time; training data is stale |
| 走势图 / price chart / 价格趋势 | `coin_chart(coin_id, days)` | Same reason |
| 当前价格 / price right now | `coin_price(coin_ids)` | Training data has no live prices |

**DO NOT return any numeric market data (prices, OHLC values, percentages) without calling a tool first.**

## ⚡ Question → Tool Map (match first keyword, call immediately)

| Question keyword | Tool to call | Example |
|---|---|---|
| 价格 / price / 多少钱 (single coin) | `coin_price(coin_id)` | `coin_price(coin_ids="bitcoin")` |
| K线 / OHLC / candlestick / 蜡烛图 | `coin_ohlc(coin_id, days)` | `coin_ohlc(coin_id="ethereum", days=7)` |
| 走势 / trend / price chart / 价格历史 | `coin_chart(coin_id, days)` | `coin_chart(coin_id="solana", days=30)` |
| 热门 / trending / 趋势币 | `cg_trending()` | `cg_trending()` |
| 涨幅最大 / 跌幅最大 / gainers / losers | `cg_top_gainers_losers()` | `cg_top_gainers_losers()` |
| 新币 / 新上线 / new coins / recently added | `cg_new_coins()` | `cg_new_coins()` |
| 总市值 / BTC市占率 / global / 晨报 / 市场概况 | `cg_global()` | `cg_global()` |
| DeFi总市值 / DeFi TVL / DeFi dominance | `cg_global_defi()` | `cg_global_defi()` |
| 板块 / sector / category / L1 / L2 / Meme / AI coins | `cg_categories()` | `cg_categories()` |
| 板块内个币 / Meme前10 / AI币排名 / DeFi币排名 | `cg_coins_markets(category=X)` | `cg_coins_markets(category="meme-token", per_page=10)` |
| 市值排名 / top 10 / ranking / 前10币 | `cg_coins_markets(per_page=N)` | `cg_coins_markets(per_page=10)` |
| ATH / 历史最高 / 社区 / dev / 研究 / fundamentals | `cg_coin_data(coin_id)` | `cg_coin_data(coin_id="solana", community_data=True)` |
| 对比两个币 / compare / XX vs YY | `cg_coin_data()` × 2 | call once per coin |
| NFT排名 / NFT市场 / floor price / top NFTs | `cg_nfts_list()` | `cg_nfts_list()` |
| 某个NFT (BAYC/Punks/Azuki) | `cg_nft(nft_id)` | `cg_nft(nft_id="bored-ape-yacht-club")` |
| 交易所详情 / Binance详情 / exchange data | `cg_exchange(exchange_id)` | `cg_exchange(exchange_id="binance")` |
| 交易所列表 / exchange ranking | `cg_exchanges()` | `cg_exchanges()` |
| 交易对 / trading pairs / 流动性分布 | `cg_coin_tickers(coin_id)` | `cg_coin_tickers(coin_id="bitcoin")` |
| 交易所交易量趋势 / volume chart | `cg_exchange_volume_chart(exchange_id)` | `cg_exchange_volume_chart(exchange_id="binance", days=30)` |
| 合约地址价格 / token price on-chain | `cg_token_price(platform, contract)` | `cg_token_price(platform="ethereum", contract_addresses="0xa0b...")` |
| 搜索币 / 找币 / coin lookup / search | `cg_search(query)` | `cg_search(query="pepe")` |
| 永续合约交易所 / derivatives exchange / OI排名 | `cg_derivatives_exchanges()` | `cg_derivatives_exchanges()` |
| 合约ticker / perpetual / funding / basis | `cg_derivatives()` | `cg_derivatives()` |
| 交易所对比 + 永续交易所 | `cg_exchanges()` + `cg_derivatives_exchanges()` | both calls |

## 🌳 Decision Tree

```
How many coins?
├─ ONE coin
│   ├─ Just price? → coin_price()
│   ├─ ATH/community/dev/deep? → cg_coin_data()
│   ├─ OHLC candles? → coin_ohlc()
│   ├─ Price trend? → coin_chart()
│   └─ Unknown ID? → cg_search() first
├─ MULTIPLE coins / ranking
│   ├─ Sector aggregate (板块总市值)? → cg_categories()
│   ├─ Sector individual (Meme前10)? → cg_coins_markets(category=X)
│   └─ General ranking? → cg_coins_markets(per_page=N)
├─ NFTs → cg_nfts_list() or cg_nft(nft_id)
├─ Exchange → cg_exchange(id) or cg_exchanges()
├─ Global → cg_global() or cg_global_defi()
└─ Token by contract → cg_token_price()
```

## Common Category IDs

`meme-token`, `artificial-intelligence`, `layer-1`, `layer-2`, `decentralized-finance-defi`, `gaming`, `real-world-assets-rwa`

## Output Formatting

- Prices: always use `$` sign → `$66,697`
- Percentages: always use `%` → `+4.2%`
- NFT floor in ETH: show USD too → `5.17 ETH ($10,534)`

## Important Notes

- CoinGecko uses slug IDs: "bitcoin", "ethereum", "solana". Symbols (BTC, ETH, SOL) auto-resolve.
- If unsure about a coin ID → `cg_search(query="coin name")` first.
- Most questions need only 1-2 tool calls. Do NOT chain 3+ calls.

## Common Issues

### coin_price failed with invalid ID
**Solution:** Use `cg_search(query="coin name")` to find the correct CoinGecko ID first, or use the symbol directly (e.g., 'COMP').

---
