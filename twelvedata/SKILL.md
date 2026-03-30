---
name: twelvedata
version: 1.0.0
description: Stocks and forex price data, time series, quotes, and reference data
tools:
  - twelvedata_time_series
  - twelvedata_price
  - twelvedata_eod
  - twelvedata_quote
  - twelvedata_quote_batch
  - twelvedata_price_batch
  - twelvedata_search
  - twelvedata_stocks
  - twelvedata_forex_pairs
  - twelvedata_exchanges

metadata:
  starchild:
    emoji: "📊"
    skillKey: twelvedata
    requires:
      env:
        - TWELVEDATA_API_KEY

user-invocable: false
disable-model-invocation: false
---

# Twelve Data

Stocks and forex market data. **For crypto use CoinGecko, not this.**

## Tools

| Tool | Use |
|------|-----|
| `twelvedata_quote(symbol)` | Real-time quote (price, OHLC, volume, change%) |
| `twelvedata_price(symbol)` | Price only |
| `twelvedata_eod(symbol)` | End of day |
| `twelvedata_time_series(symbol, interval, outputsize)` | Historical OHLCV |
| `twelvedata_quote_batch(symbols=[...])` | Up to 120 symbols at once |
| `twelvedata_price_batch(symbols=[...])` | Batch prices |
| `twelvedata_search(query)` | Find symbol by name |
| `twelvedata_stocks(exchange)` | List all stocks on exchange |
| `twelvedata_forex_pairs()` | All forex pairs |
| `twelvedata_exchanges(type)` | List exchanges |

## Symbol Format

- **Stocks**: `AAPL`, `MSFT`, `TSLA`, `GOOGL`
- **Forex**: `EUR/USD`, `GBP/JPY`, `USD/CHF`

## Intervals

Intraday: `1min`, `5min`, `15min`, `30min`, `1h`, `2h`, `4h`, `8h`
Daily+: `1day`, `1week`, `1month`

`outputsize`: `compact` (30 points, default) | `full` (up to 5000 points)

## Common Patterns

```
# Current price
twelvedata_quote(symbol="AAPL")

# Historical data
twelvedata_time_series(symbol="AAPL", interval="1day", outputsize="compact")

# Batch portfolio check
twelvedata_quote_batch(symbols=["AAPL", "MSFT", "GOOGL", "TSLA"])

# Symbol lookup
twelvedata_search(query="Apple")
```
