---
name: taapi
version: 1.2.0
description: "Technical analysis indicators — RSI, MACD, Bollinger Bands, ADX, support/resistance, and 200+ pre-calculated indicators. Use when the user asks about ANY technical indicator for crypto."
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
    intent_triggers:
      - "RSI"
      - "MACD"
      - "布林带"
      - "Bollinger"
      - "支撑位"
      - "阻力位"
      - "技术指标"
      - "超买"
      - "超卖"
      - "ADX"
      - "ATR"
      - "EMA"
      - "SMA"
      - "KDJ"
      - "Stochastic"

user-invocable: false
disable-model-invocation: false
---

# TaAPI — Technical Analysis Indicators

## ⛔ HARD LIMIT

```
最多调用 indicator/support_resistance 共 5 次。
⛔ 绝对禁止：bash、write_file、learning_log、coin_price、cg_ohlc_history 等非 TaAPI 工具。
⛔ 布林带已含中轨（中轨≈当前价），不需要再调 coin_price 获取价格。
⛔ RSI 问题只需 indicator(name="rsi") 一次，不需要 learning_log 或其他工具。
```

## When to Use

**任何加密货币技术指标问题 → 用 TaAPI**
- "BTC RSI 多少？" → `indicator(name="rsi", symbol="BTC/USDT")`
- "ETH MACD 什么信号?" → `indicator(name="macd", symbol="ETH/USDT")`
- "SOL 布林带收缩还是扩张?" → `indicator(name="bbands", symbol="SOL/USDT")`
- "BTC 支撑位阻力位?" → `support_resistance(symbol="BTC/USDT")`

**NOT for:** 股票/外汇技术指标（TwelveData 有自己的技术功能）

## Keyword → Tool

| 用户说 | 工具 | 参数 |
|--------|------|------|
| RSI/超买/超卖 | `indicator` | name="rsi" |
| MACD/金叉/死叉 | `indicator` | name="macd" |
| 布林带/Bollinger/带宽/收缩 | `indicator` | name="bbands" |
| 支撑位/阻力位/关键价位 | `support_resistance` | |
| EMA/均线/移动平均 | `indicator` | name="ema" |
| ADX/趋势强度 | `indicator` | name="adx" |
| ATR/波动率 | `indicator` | name="atr" |
| KDJ/Stochastic/随机指标 | `indicator` | name="stoch" |
| OBV/成交量指标 | `indicator` | name="obv" |
| 综合技术分析 | 多次 `indicator` | 依次调 rsi, macd, bbands |

## Common Mistakes

### ❌ MISTAKE 1: 用 cg_ohlc_history + bash 手动计算指标
```
WRONG: cg_ohlc_history(symbol="BTC") → bash("python3 calc_rsi.py")
RIGHT: indicator(name="rsi", symbol="BTC/USDT", interval="1h")
```
为什么：TaAPI 返回预计算的精确指标值，不需要拉K线再自己算。又快又准。

### ❌ MISTAKE 6: RSI 问题调了 learning_log / request_env_input
```
WRONG: learning_log(...) → indicator(name="rsi", ...) → indicator(name="rsi", ...)
RIGHT: indicator(name="rsi", symbol="BTC/USDT", interval="1h")  # 一次即可
```
已知规则：TaAPI SKILL 已加载，直接调工具，不需要查日志或请求环境变量。

### ❌ MISTAKE 7: 布林带问题额外调 coin_price
```
WRONG: indicator(name="bbands", symbol="BTC/USDT") → coin_price(coin_ids="bitcoin")  # 多余！
RIGHT: indicator(name="bbands", symbol="BTC/USDT", interval="1h")
```
布林带响应包含 upperBand/middleBand/lowerBand，middleBand ≈ 当前价格，无需再查价格。
判断"离哪个轨近"：直接比较 upperBand 和 lowerBand 与 middleBand 的距离即可。

### ❌ MISTAKE 8: 技术面分析混入价格工具
```
WRONG: indicator(name="rsi") + indicator(name="macd") + coin_price(...)  # coin_price 无关
RIGHT: indicator(name="rsi") + indicator(name="macd")  # 技术分析只用 TaAPI 工具
```
MACD histogram 已反映价格趋势，分析不需要额外价格数据。

### ❌ MISTAKE 9: 支撑阻力用 indicator 或 coin_ohlc 手算
```
WRONG: indicator(name="rsi") + coin_ohlc(coin_id="bitcoin")  # 用K线手动找支撑
RIGHT: support_resistance(symbol="BTC/USDT", interval="1d")
```
支撑位/阻力位 = 必须用 `support_resistance` 工具，直接返回关键价格区间，禁止用 coin_ohlc + 推理。

### ❌ MISTAKE 2: 布林带只查一次就判断收缩/扩张
```
WRONG: indicator(name="bbands", symbol="SOL/USDT", interval="1h")  # 单次无法判断趋势
RIGHT:
  indicator(name="bbands", symbol="SOL/USDT", interval="1h")   # 当前带宽
  indicator(name="bbands", symbol="SOL/USDT", interval="4h")   # 更大周期对比
  indicator(name="atr", symbol="SOL/USDT", interval="1h")      # ATR 辅助判断波动率
```
为什么：收缩/扩张是相对概念，需要多周期或 ATR 辅助判断。

### ❌ MISTAKE 3: interval 参数格式错误
```
WRONG: indicator(name="rsi", symbol="BTC/USDT", interval="1hour")
RIGHT: indicator(name="rsi", symbol="BTC/USDT", interval="1h")
```
有效值：1m, 5m, 15m, 30m, 1h, 2h, 4h, 12h, 1d, 1w

### ❌ MISTAKE 4: 综合分析只调一个指标
```
WRONG: indicator(name="rsi") → "RSI 看多所以看多"
RIGHT:
  indicator(name="rsi")     → 动量
  indicator(name="macd")    → 趋势
  indicator(name="bbands")  → 波动率
  → 综合三者给结论
```

### ❌ MISTAKE 5: 混淆 indicator 和 support_resistance
```
WRONG: indicator(name="support_resistance", symbol="BTC/USDT")
RIGHT: support_resistance(symbol="BTC/USDT", interval="1d")
```
Rule: 支撑/阻力是独立工具 `support_resistance`，不是 `indicator` 的参数。

## Available Indicators

### Momentum
| Name | Description | Key Levels |
|------|-------------|------------|
| rsi | Relative Strength Index | >70 超买, <30 超卖 |
| stoch | Stochastic Oscillator | >80 超买, <20 超卖 |
| cci | Commodity Channel Index | >100 超买, <-100 超卖 |
| mfi | Money Flow Index | >80 超买, <20 超卖 |

### Trend
| Name | Description | Signal |
|------|-------------|--------|
| macd | MACD | histogram>0 看多, <0 看空 |
| adx | Average Directional Index | >25 强趋势 |
| ema | Exponential Moving Average | 价格在上=多头 |
| sma | Simple Moving Average | 价格在上=多头 |

### Volatility
| Name | Description | Signal |
|------|-------------|--------|
| bbands | Bollinger Bands | 带宽收缩=将突破 |
| atr | Average True Range | 值大=波动大 |

## Interpretation Guide

### RSI
- **>70**: 超买（可能回调）
- **50-70**: 多头动量
- **30-50**: 空头动量
- **<30**: 超卖（可能反弹）

### MACD
- **Histogram > 0 且增大**: 多头加速
- **Histogram > 0 但减小**: 多头减弱
- **Histogram < 0 且减小**: 空头加速
- **零轴穿越**: 趋势反转信号

### Bollinger Bands
- **价格触上轨**: 超买
- **价格触下轨**: 超卖
- **带宽收窄**: 即将突破（方向待定）
- **带宽扩张**: 趋势进行中

## Workflow Templates

### 快速多空判断
```
indicator(name="rsi", symbol="BTC/USDT", interval="1h")
indicator(name="macd", symbol="BTC/USDT", interval="1h")
→ RSI + MACD 同向 = 强信号
```

### 完整技术体检
```
indicator(name="rsi", symbol="BTC/USDT", interval="4h")
indicator(name="macd", symbol="BTC/USDT", interval="4h")
indicator(name="bbands", symbol="BTC/USDT", interval="4h")
indicator(name="adx", symbol="BTC/USDT", interval="4h")
support_resistance(symbol="BTC/USDT", interval="1d")
→ 5 维度综合分析
```

## Few-Shot 示例（约束遵循）

### 示例 1: 只要数字
```
Q: BTC 当前 RSI 是多少？
✅ 调用: indicator(name="rsi", symbol="BTC/USDT", interval="1h")
✅ 输出: 58.3
❌ 错误: learning_log() → indicator() → indicator()  # 重复调用+无关工具
```

### 示例 2: 布林带"离哪个轨近"
```
Q: BTC 布林带上下轨在哪？当前价格离哪个轨近？
✅ 调用: indicator(name="bbands", symbol="BTC/USDT", interval="1h")
✅ 输出: 上轨 $96,800 | 中轨 $94,200（≈当前价）| 下轨 $91,600 → 离下轨更近
❌ 错误: indicator(name="bbands") + coin_price(coin_ids="bitcoin")  # coin_price 多余
```

### 示例 4: 支撑阻力位
```
Q: BTC 当前支撑位和阻力位在哪？只要两个数字
✅ 调用: support_resistance(symbol="BTC/USDT", interval="1d")
✅ 输出: 支撑 $82,000 | 阻力 $88,500
❌ 错误: indicator(name="rsi") + coin_ohlc(...)  # 完全错工具
```

### 示例 3: 技术面综合
```
Q: BTC 技术面怎么看？RSI 和 MACD 什么信号？
✅ 调用: indicator(name="rsi", ...) → indicator(name="macd", ...)
✅ 输出: RSI 62（多头区间）| MACD histogram +220（多头加速）→ 短期偏多
❌ 错误: indicator() + coin_price()  # 技术分析不需要价格工具
```

## Symbol Format

`COIN/USDT` — 例如：`BTC/USDT`, `ETH/USDT`, `SOL/USDT`

## Default Exchange

Binance（可选：binancefutures, bybit, okex）
