---
name: taapi
version: 1.0.0
description: Technical analysis indicators - RSI, MACD, Bollinger Bands, and 200+ indicators
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

Pre-calculated technical indicators from exchanges. No local computation.

## Tools

**indicator** — Get any indicator value.
```
indicator(exchange="binance", symbol="BTC/USDT", interval="1h", indicator="rsi")
indicator(exchange="binance", symbol="ETH/USDT", interval="4h", indicator="macd")
indicator(exchange="binance", symbol="SOL/USDT", interval="1d", indicator="bbands")
```

**support_resistance** — Key price levels.
```
support_resistance(exchange="binance", symbol="BTC/USDT", interval="1d")
```

## Parameters

- **symbol**: Exchange format — `BTC/USDT`, `ETH/USDT`, `SOL/USDT`
- **exchange**: `binance` (default), `coinbase`, `kraken`, `bitfinex`, etc.
- **interval**: `1m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `8h`, `12h`, `1d`, `1w`, `1M`

## Key Indicators

| Category | Indicators |
|----------|-----------|
| Momentum | `rsi`, `stoch`, `cci`, `williams`, `roc` |
| Trend | `macd`, `adx`, `ema`, `sma`, `dema` |
| Volatility | `bbands`, `atr`, `keltner` |
| Volume | `obv`, `vwap` |

200+ indicators supported — see TaAPI docs for full list.

## Quick Interpretation

| Indicator | Bullish | Bearish |
|-----------|---------|---------|
| RSI | < 30 (oversold) | > 70 (overbought) |
| MACD | Histogram > 0, crossing up | Histogram < 0, crossing down |
| BBands | Price at lower band | Price at upper band |
| ADX | > 25, +DI > -DI | > 25, -DI > +DI |
| Stoch | < 20 (oversold) | > 80 (overbought) |

**Trend confirmation**: ADX > 25 + EMA/SMA cross.
**Divergence**: Price makes new high/low but indicator doesn't = potential reversal.
