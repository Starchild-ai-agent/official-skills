---
name: twelvedata
version: 1.2.0
description: "Stocks, forex, and commodities price data — real-time quotes, historical time series, and reference data"
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

Stocks, forex, and commodities price data. **Traditional markets only — not for crypto.**

## Keyword → Tool Lookup

| User asks about | Tool | NOT this |
|----------------|------|----------|
| "AAPL 股价", "current price" (single) | `twelvedata_quote` | Not `twelvedata_price` (less detail) |
| "just the price number" | `twelvedata_price` | — |
| "多只股票对比" (2+ symbols) | `twelvedata_quote_batch` | Not multiple `twelvedata_quote` calls |
| "K线", "历史数据", "time series" | `twelvedata_time_series` | — |
| "收盘价" | `twelvedata_eod` | — |
| "找股票代码" | `twelvedata_search` | — |
| "NASDAQ 有哪些股票" | `twelvedata_stocks` | — |
| "汇率", "EUR/USD" | `twelvedata_quote(symbol="EUR/USD")` | — |
| "外汇对列表" | `twelvedata_forex_pairs` | — |
| "金价", "oil price" | `twelvedata_quote(symbol="XAU/USD")` | Not CoinGecko |
| "BTC price", any crypto | **CoinGecko** `coin_price` | ❌ Never twelvedata for crypto |

## TwelveData vs CoinGecko — Boundary

| Asset class | Use | Why |
|-------------|-----|-----|
| Stocks (AAPL, TSLA) | **TwelveData** | CoinGecko has no stocks |
| Forex (EUR/USD) | **TwelveData** | CoinGecko has no forex |
| Commodities (gold, oil) | **TwelveData** | CoinGecko has no commodities |
| Crypto (BTC, ETH, SOL) | **CoinGecko** | TwelveData crypto data is limited/unreliable |

## MISTAKES — Read Before Calling

### ❌ MISTAKE 1: Using TwelveData for crypto
```
User: "BTC 价格"
❌ WRONG: twelvedata_quote(symbol="BTC/USD")
✅ RIGHT: coin_price(ids="bitcoin")  ← CoinGecko
```

### ❌ MISTAKE 2: Calling quote individually for multiple stocks
```
User: "AAPL MSFT GOOGL 现在什么价"
❌ WRONG: twelvedata_quote("AAPL"), twelvedata_quote("MSFT"), twelvedata_quote("GOOGL")  ← 3 calls
✅ RIGHT: twelvedata_quote_batch(symbols=["AAPL", "MSFT", "GOOGL"])  ← 1 call, up to 120 symbols
```

### ❌ MISTAKE 3: Forex without slash
```
❌ WRONG: twelvedata_quote(symbol="EURUSD")
✅ RIGHT: twelvedata_quote(symbol="EUR/USD")  ← always slash format
```
Also: `USD/CNH` not `USDCNH`, `GBP/JPY` not `GBPJPY`.

### ❌ MISTAKE 4: Expecting bid/ask from quote
```
❌ WRONG: "EUR/USD bid: 1.0850, ask: 1.0852"  ← quote only returns close
✅ RIGHT: "EUR/USD current price: 1.0851 (close/last price — bid/ask spread not available)"
```

### ❌ MISTAKE 5: Wrong interval format
```
❌ WRONG: twelvedata_time_series(interval="1D")  ← uppercase
✅ RIGHT: twelvedata_time_series(interval="1day")
```
Valid: `1min`, `5min`, `15min`, `30min`, `1h`, `2h`, `4h`, `8h`, `1day`, `1week`, `1month`

### ❌ MISTAKE 6: Using full output when compact suffices
```
User: "AAPL 最近走势"
❌ WRONG: twelvedata_time_series(symbol="AAPL", interval="1day", outputsize="full")  ← 5000 candles
✅ RIGHT: twelvedata_time_series(symbol="AAPL", interval="1day", outputsize="compact")  ← 30 candles
```
Use `full` only when user explicitly needs deep history.

## Symbol Reference

### Commodities (verified)

| Asset | Symbol |
|-------|--------|
| Gold | `XAU/USD` |
| Silver | `XAG/USD` |
| Platinum | `XPT/USD` |
| Palladium | `XPD/USD` |
| Crude Oil (WTI) | `WTI/USD` |
| Natural Gas | `NG/USD` |

### Popular Forex Pairs

| Pair | Symbol |
|------|--------|
| Euro / USD | `EUR/USD` |
| GBP / USD | `GBP/USD` |
| USD / JPY | `USD/JPY` |
| USD / CNH | `USD/CNH` |

Use `twelvedata_search` to discover others.

## Pre/Post-Market Data

```
twelvedata_quote(symbol="AAPL", prepost=true)
twelvedata_time_series(symbol="AAPL", interval="1min", prepost=true)
```
Returns `premarket_change`, `premarket_change_percent`, `postmarket_change`, `postmarket_change_percent` when available.

## Output Sizes

- `compact` — Last 30 data points (default, faster). Use for "最近走势".
- `full` — Up to 5000 data points. Use for deep analysis / charting.

⚠️ **Note:** The `outputsize` parameter 只接受 `"compact"` 或 `"full"` 字符串 — 传整数会报 `invalid_type` 错误。

## Proxy-Safe Usage

1. **Agent tool calls**: Always prefer `twelvedata_*` tools (this skill).
2. **Platform code** (`skills/`, `tools/`): use `core.http_client`.
3. **Workspace scripts** (`bash`): Do NOT call TwelveData directly. Use skill tools.

## Compound Queries

### Stock Comparison
```
1. twelvedata_quote_batch(symbols=["AAPL", "MSFT", "GOOGL", "TSLA"])
2. twelvedata_time_series(symbol="AAPL", interval="1day", outputsize="compact")  ← only for the one user cares most about
```

### Macro Dashboard (stocks + forex + commodities)
```
1. twelvedata_quote_batch(symbols=["SPY", "QQQ"])          → US indices
2. twelvedata_quote_batch(symbols=["EUR/USD", "USD/JPY"])   → Forex
3. twelvedata_quote(symbol="XAU/USD")                       → Gold
```
