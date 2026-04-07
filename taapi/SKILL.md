---
name: taapi
version: 1.1.0
description: "Technical analysis indicators — RSI, MACD, Bollinger Bands, support/resistance, and 200+ pre-calculated indicators"
tools:
  - indicator
  - support_resistance

metadata:
  starchild:
    emoji: "📉"
    skillKey: taapi
    requires:
      env:
        - TAAPI_API_KEY

user-invocable: false
disable-model-invocation: false
---

# TaAPI

Technical analysis indicators: RSI, MACD, Bollinger Bands, support/resistance, 200+ pre-calculated. No local computation needed.

## Keyword → Tool Lookup

| User asks about | Tool | NOT this |
|----------------|------|----------|
| "RSI", "MACD", "布林带", any indicator name | `indicator` | — |
| "支撑位", "阻力位", "support/resistance" | `support_resistance` | Not `indicator` |
| "funding rate", "OI", "long/short ratio" | **Coinglass** | ❌ Not taapi — those are derivatives metrics |
| "Galaxy Score", "social sentiment" | **LunarCrush** | ❌ Not taapi |
| "BTC 价格" (just price) | **CoinGecko** `coin_price` | ❌ Not taapi |

## TaAPI vs Others — Boundary

| Need | Use | Why |
|------|-----|-----|
| Technical indicators (RSI, MACD, BB) | **TaAPI** | Pre-calculated, 200+ indicators |
| Derivatives metrics (funding, OI, L/S) | **Coinglass** | Different data source entirely |
| Price data only | **CoinGecko** (crypto) / **TwelveData** (stocks) | TaAPI is for indicators, not raw prices |
| Social sentiment | **LunarCrush** | Different data type |

## MISTAKES — Read Before Calling

### ❌ MISTAKE 1: Wrong symbol format
```
❌ WRONG: indicator(symbol="BTC")
✅ RIGHT: indicator(symbol="BTC/USDT")  ← always pair format
```

### ❌ MISTAKE 2: Wrong interval format
```
❌ WRONG: indicator(interval="1day")  ← TwelveData format
❌ WRONG: indicator(interval="1D")
✅ RIGHT: indicator(interval="1d")
```
Valid: `1m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `8h`, `12h`, `1d`, `1w`, `1M`

### ❌ MISTAKE 3: Using taapi for derivatives data
```
User: "BTC funding rate"
❌ WRONG: indicator(indicator="funding_rate")  ← doesn't exist in taapi
✅ RIGHT: funding_rate(symbol="BTC")  ← Coinglass tool
```

### ❌ MISTAKE 4: Forgetting exchange parameter
```
❌ WRONG: indicator(symbol="BTC/USDT", interval="1h", indicator="rsi")  ← missing exchange
✅ RIGHT: indicator(exchange="binance", symbol="BTC/USDT", interval="1h", indicator="rsi")
```
Default exchange is `binance` but always specify explicitly for clarity.

### ❌ MISTAKE 5: Calling support_resistance with indicator tool
```
User: "BTC 支撑位阻力位"
❌ WRONG: indicator(indicator="support_resistance")
✅ RIGHT: support_resistance(exchange="binance", symbol="BTC/USDT", interval="1d")
```
Support/resistance is a separate tool, not an indicator name.

## Indicator Quick Reference

### Momentum
| Indicator | Code | Bullish | Bearish |
|-----------|------|---------|---------|
| RSI | `rsi` | < 30 (oversold) | > 70 (overbought) |
| Stochastic | `stoch` | < 20 (oversold) | > 80 (overbought) |
| CCI | `cci` | < -100 (oversold) | > 100 (overbought) |
| Williams %R | `williams` | < -80 (oversold) | > -20 (overbought) |

### Trend
| Indicator | Code | Bullish | Bearish |
|-----------|------|---------|---------|
| MACD | `macd` | Histogram > 0, crossing up | Histogram < 0, crossing down |
| ADX | `adx` | > 25 with +DI > -DI | > 25 with -DI > +DI |
| EMA | `ema` | Price above EMA | Price below EMA |
| SMA | `sma` | Price above SMA | Price below SMA |

### Volatility
| Indicator | Code | Signal |
|-----------|------|--------|
| Bollinger Bands | `bbands` | Upper = overbought, Lower = oversold, Squeeze = breakout coming |
| ATR | `atr` | Rising = increasing volatility, Falling = decreasing |
| Keltner | `keltner` | Similar to BB but uses ATR instead of stddev |

### Volume
| Indicator | Code | Signal |
|-----------|------|--------|
| OBV | `obv` | Rising OBV + rising price = trend confirmed |
| VWAP | `vwap` | Price above = bullish, below = bearish |

## Divergence Detection Pattern

```
User: "BTC 有没有背离"
1. indicator(exchange="binance", symbol="BTC/USDT", interval="4h", indicator="rsi")
2. Compare RSI direction vs price direction:
   - Price new high + RSI lower high = bearish divergence
   - Price new low + RSI higher low = bullish divergence
```

## Compound Queries

### Full Technical Scan
```
1. indicator(exchange="binance", symbol="BTC/USDT", interval="4h", indicator="rsi")
2. indicator(exchange="binance", symbol="BTC/USDT", interval="4h", indicator="macd")
3. support_resistance(exchange="binance", symbol="BTC/USDT", interval="1d")
→ Synthesize: momentum + trend + key levels
```

### Multi-Timeframe Analysis
```
1. indicator(exchange="binance", symbol="BTC/USDT", interval="1d", indicator="rsi")   → daily trend
2. indicator(exchange="binance", symbol="BTC/USDT", interval="4h", indicator="rsi")   → entry timing
3. indicator(exchange="binance", symbol="BTC/USDT", interval="1h", indicator="rsi")   → immediate momentum
```
