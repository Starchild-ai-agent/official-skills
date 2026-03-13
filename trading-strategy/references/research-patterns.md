# Research Patterns

Detailed tool usage patterns for different research scenarios. Load this when you need specific guidance on which tools to use and how.

## Macro Research
- `web_search("[topic] macro outlook [current year]")` — analyst views, articles
- `cg_global` — total market cap, BTC dominance, 24h volume
- `cg_global_defi` — DeFi TVL, DeFi-to-crypto ratio
- `twitter_search_tweets("$BTC macro min_faves:50")` — trader sentiment
- `cg_trending` — what's getting attention right now

## Asset-Level Research
- `market_data(action="price", coin_ids="bitcoin,ethereum,solana")` — current prices
- `market_data(action="ohlc", coin_id="bitcoin", days=30)` — price action
- `market_data(action="indicator", indicator="rsi", symbol="BTC/USDT", interval="1d")` — technicals
- `market_data(action="support_resistance", symbol="BTC/USDT")` — key levels
- `lunar_coin(coin="BTC")` — Galaxy Score, social volume, sentiment

## Derivatives / Positioning
- `market_data(action="funding", symbol="BTC")` — funding rates (>+0.05% extreme greed, <-0.05% extreme fear)
- `market_data(action="long_short", symbol="BTC")` — long/short ratio (>1.5 crowded long, <0.7 crowded short)
- `cg_open_interest(symbol="BTC")` — aggregate OI across exchanges
- `cg_liquidations(symbol="BTC")` — recent liquidations (more long liq = bearish pressure)

## Social / Sentiment
- `twitter_search_tweets("$BTC min_faves:100")` — popular BTC tweets
- `twitter_search_tweets("from:[analyst_handle]")` — specific analyst
- `twitter_user_tweets(username="[handle]")` — recent posts from a trader
- `lunar_topic(topic="bitcoin")` — topic-level sentiment
- `lunar_topic_posts(topic="defi", limit=10)` — top posts on a topic

## Source Fetching
- `web_fetch(url="[substack/article URL]")` — pull full article content
- `web_search("[article topic] site:substack.com")` — find related substacks
- Always cross-reference fetched content with live market data

## Monitoring Scripts
Template for price + indicator monitoring:
```python
import requests, os, json

COINGECKO_KEY = os.getenv("COINGECKO_API_KEY")
TAAPI_KEY = os.getenv("TAAPI_API_KEY")

# Check price
price_resp = requests.get(
    "https://pro-api.coingecko.com/api/v3/simple/price",
    params={"ids": "bitcoin", "vs_currencies": "usd"},
    headers={"x-cg-pro-api-key": COINGECKO_KEY}
)
btc_price = price_resp.json()["bitcoin"]["usd"]

# Check RSI
rsi_resp = requests.get(
    "https://api.taapi.io/rsi",
    params={"secret": TAAPI_KEY, "exchange": "binance", "symbol": "BTC/USDT", "interval": "1d"}
)
rsi = rsi_resp.json()["value"]

# Alert logic
alerts = []
if btc_price < 58000:
    alerts.append(f"BTC at ${btc_price:,.0f} — below 58K target zone")
if rsi < 30:
    alerts.append(f"BTC RSI at {rsi:.1f} — oversold on daily")

if alerts:
    print("ALERTS:\n" + "\n".join(alerts))
else:
    print(f"BTC ${btc_price:,.0f} | RSI {rsi:.1f} — no alerts")
```
