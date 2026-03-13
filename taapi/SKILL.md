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

TaAPI provides technical analysis indicators including RSI, MACD, Bollinger Bands, support/resistance, and 200+ pre-calculated indicators. No local computation needed.

## When to Use TaAPI

Use TaAPI for:
- **Technical indicators** - RSI, MACD, Bollinger Bands, ADX, Stochastic, etc.
- **Support/Resistance** - Key price levels
- **Trend analysis** - Moving averages, ADX, trend indicators
- **Momentum** - RSI, Stochastic, CCI
- **Volatility** - Bollinger Bands, ATR

## Common Workflows

### Get Indicator
```
indicator(exchange="binance", symbol="BTC/USDT", interval="1h", indicator="rsi")
indicator(exchange="binance", symbol="ETH/USDT", interval="4h", indicator="macd")
indicator(exchange="binance", symbol="SOL/USDT", interval="1d", indicator="bbands")
```

### Support/Resistance
```
support_resistance(exchange="binance", symbol="BTC/USDT", interval="1d")
```

## Available Indicators

### Momentum Indicators
- `rsi` - Relative Strength Index
- `stoch` - Stochastic Oscillator
- `cci` - Commodity Channel Index
- `williams` - Williams %R
- `roc` - Rate of Change

### Trend Indicators
- `macd` - Moving Average Convergence Divergence
- `adx` - Average Directional Index
- `ema` - Exponential Moving Average
- `sma` - Simple Moving Average
- `dema` - Double Exponential Moving Average

### Volatility Indicators
- `bbands` - Bollinger Bands
- `atr` - Average True Range
- `keltner` - Keltner Channels

### Volume Indicators
- `obv` - On Balance Volume
- `vwap` - Volume Weighted Average Price

See TaAPI documentation for the full list of 200+ indicators.

## Intervals

- `1m`, `5m`, `15m`, `30m` - Minutes
- `1h`, `2h`, `4h`, `8h`, `12h` - Hours
- `1d`, `1w`, `1M` - Days, Weeks, Months

## Exchanges

Default exchange is Binance. Supports:
- `binance`
- `coinbase`
- `kraken`
- `bitfinex`
- And many more...

## Symbol Format

Use exchange format: `BTC/USDT`, `ETH/USDT`, `SOL/USDT`

## Interpretation Guides

### Common Indicator Reads

| Indicator | Bullish | Bearish |
|-----------|---------|---------|
| RSI | < 30 (oversold) | > 70 (overbought) |
| MACD | Histogram crossing above zero | Histogram crossing below zero |
| Bollinger Bands | Price touching lower band | Price touching upper band |
| ADX | > 25 with +DI > -DI | > 25 with -DI > +DI |
| Stochastic | < 20 (oversold) | > 80 (overbought) |

### RSI Levels
- **> 70**: Overbought (potential reversal down)
- **50-70**: Bullish momentum
- **30-50**: Bearish momentum
- **< 30**: Oversold (potential reversal up)

### MACD Signals
- **Histogram > 0**: Bullish
- **Histogram < 0**: Bearish
- **Histogram crossing zero**: Trend change
- **MACD line crossing signal line**: Buy/sell signal

### Bollinger Bands
- **Price at upper band**: Overbought
- **Price at lower band**: Oversold
- **Bands widening**: Increasing volatility
- **Bands narrowing**: Decreasing volatility (squeeze)

## Analysis Patterns

**Trend confirmation**: Use ADX + EMA/SMA. ADX > 25 indicates strong trend. EMA crossing SMA confirms direction.

**Overbought/Oversold**: Use RSI + Stochastic together. Both confirming increases signal strength.

**Divergence**: Price making new highs/lows but indicator not confirming = potential reversal.

## Important Notes

- **API Key**: Requires TAAPI_API_KEY environment variable
- **Pre-calculated**: All indicators are pre-calculated by TaAPI - no local computation needed
- **Real-time**: Data is near real-time from exchanges
- **200+ Indicators**: TaAPI supports 200+ technical indicators
