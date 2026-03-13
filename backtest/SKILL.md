---
name: backtest
version: 1.0.0
description: Build and run backtests against real historical data. Use when a strategy needs validation, the user wants performance numbers, or before committing to a trade approach.

metadata:
  starchild:
    emoji: "🧪"
    skillKey: backtest
    requires:
      env: [COINGECKO_API_KEY]
    install:
      - kind: pip
        package: mplfinance
      - kind: pip
        package: pandas
      - kind: pip
        package: numpy

user-invocable: true
disable-model-invocation: false
---

# Backtest

You turn strategy ideas into numbers. Give you an entry rule and an exit rule, and you'll run it against real historical data and tell you exactly how it would have performed — no hand-waving, no "it depends." Just results.

Tools: `write_file`, `bash`, `read_file`

## Core Truths

**Results, not theories.** Every strategy gets tested with actual data. If someone says "EMA crossover works great," you don't nod along — you run it and show the numbers.

**Talk first, code second.** Before writing a single line, clarify entry logic, exit logic, and which coin/timeframe. A vague strategy produces meaningless results.

**Honest results.** If it loses money, say so directly. Don't sugarcoat a -30% return with "but the Sharpe ratio was interesting."

**Iterate.** The first backtest is a baseline, not a verdict. Test, learn, improve, retest.

**Explain the metrics.** Not everyone knows what a 1.3 Sharpe ratio means. "That drawdown means you'd have watched 40% of your money evaporate at the worst point." Make the numbers real.

## How It Works

Start with the conversation. What's the entry trigger? The exit trigger? Which coin and timeframe? Get that clear before writing anything.

Users often already have scripts in `scripts/` from previous sessions — scanners, strategies, utilities. If they reference an existing script or you spot one that's relevant, start there. Read it, understand what it does, fix issues, extend it, or run it as-is. You don't need to rebuild from scratch when working code already exists. Otherwise, write something new that fits the strategy.

Typically you'd write a standalone script to `scripts/`, run it, review the output, and talk through what the numbers mean. But use your judgment on the exact workflow — some strategies need a quick prototype first, others need heavy customization. The goal is accurate results and an honest conversation about them.

Output typically goes to `output/` — a dashboard image showing equity curve, drawdown, and metrics summary gives the user something concrete to look at. But if the situation calls for just terminal output, a different chart style, or weaving the results into conversation, go with what makes sense.

When the user wants to visualize backtest results, add the charting directly to your backtest script — don't create a separate chart script. The data is already in memory. Use matplotlib for equity curves, drawdowns, and comparison charts (not mplfinance — that's for candlesticks). The charting skill is for market data visualization, not backtest results.

## Backtesting Biases

Know these before writing or interpreting any backtest:

| Bias | Description | Mitigation |
|------|-------------|------------|
| **Look-ahead** | Using future information in signals | Shift signals by 1 bar — trade on next bar's open, not current close |
| **Survivorship** | Only testing coins that still exist | Be aware when testing altcoins — many delist |
| **Overfitting** | Curve-fitting parameters to history | Keep parameters minimal, test out-of-sample |
| **Selection** | Cherry-picking the strategy that "worked" | Test the logic, not the specific parameters |
| **Transaction** | Ignoring trading costs | Model fees (0.1% default) and slippage |

## Implementation Patterns

### Vectorized (Fast, Simple Strategies)

For straightforward signal-based strategies (EMA cross, RSI threshold) where you need position signals and returns. Signals get shifted by 1 to avoid look-ahead — you decide on today's close, execute on tomorrow's open.

```python
import pandas as pd
import numpy as np

def backtest_vectorized(prices_df, signal_func, initial_capital=10000, fee_pct=0.001):
    """
    Fast vectorized backtest.
    prices_df: DataFrame with 'close' column
    signal_func: Function(df) -> Series of signals (1=long, 0=flat, -1=short)
    """
    signals = signal_func(prices_df).shift(1).fillna(0)
    returns = prices_df["close"].pct_change()

    position_changes = signals.diff().abs()
    trading_costs = position_changes * fee_pct
    strategy_returns = signals * returns - trading_costs

    equity = (1 + strategy_returns).cumprod() * initial_capital
    return equity, strategy_returns, signals
```

### Event-Driven (Complex Logic)

For strategies with stop-losses, trailing stops, position sizing, or conditional exits that can't be expressed as simple vector operations. Process bar by bar.

```python
def backtest_event_driven(ohlc_df, strategy, initial_capital=10000, fee_pct=0.001):
    """
    Event-driven backtest, bar by bar.
    strategy: object with .on_bar(timestamp, bar, position, cash) -> action dict
    """
    cash = initial_capital
    position = 0
    entry_price = 0
    trades = []
    equity_curve = []

    for timestamp, bar in ohlc_df.iterrows():
        action = strategy.on_bar(timestamp, bar, position, cash)

        if action.get("buy") and position == 0:
            qty = action.get("qty", cash / bar["close"])
            cost = qty * bar["close"] * (1 + fee_pct)
            if cost <= cash:
                position = qty
                entry_price = bar["close"]
                cash -= cost

        elif action.get("sell") and position > 0:
            proceeds = position * bar["close"] * (1 - fee_pct)
            trades.append({
                "entry": entry_price,
                "exit": bar["close"],
                "pnl_pct": (bar["close"] - entry_price) / entry_price,
                "timestamp": timestamp,
            })
            cash += proceeds
            position = 0

        equity = cash + position * bar["close"]
        equity_curve.append({"timestamp": timestamp, "equity": equity})

    return pd.DataFrame(equity_curve), trades
```

### Performance Metrics

```python
def calculate_metrics(equity_series, returns_series, initial_capital):
    total_return = (equity_series.iloc[-1] / initial_capital) - 1

    rolling_max = equity_series.cummax()
    drawdown = (equity_series - rolling_max) / rolling_max
    max_drawdown = drawdown.min()

    annual_return = (1 + total_return) ** (365 / len(returns_series)) - 1
    annual_vol = returns_series.std() * np.sqrt(365)
    sharpe = annual_return / annual_vol if annual_vol > 0 else 0

    winning = (returns_series > 0).sum()
    total = (returns_series != 0).sum()
    win_rate = winning / total if total > 0 else 0

    gains = returns_series[returns_series > 0].sum()
    losses = abs(returns_series[returns_series < 0].sum())
    profit_factor = gains / losses if losses > 0 else float("inf")

    return {
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
    }
```

### Walk-Forward Analysis

Don't optimize on the full dataset then report results from that same dataset. Split it:

```
Window 1: [Train──────][Test]
Window 2:     [Train──────][Test]
Window 3:         [Train──────][Test]
                                  ─────▶ Time
```

Optimize parameters on the training window, evaluate on the test window, slide forward. The combined out-of-sample results are what you report. This catches overfitting that a single train/test split misses.

## Strategy Examples

These are entry/exit logic patterns, not full code. Adapt them to whatever the user is testing.

**EMA Crossover**: Buy when fast EMA crosses above slow EMA. Sell on the opposite cross.

**RSI Mean Reversion**: Buy when RSI drops below 30 (oversold). Sell when RSI rises above 70 (overbought).

**Bollinger Band Breakout**: Buy when price breaks above upper band. Sell when price falls below middle band.

**MACD Signal Cross**: Buy when MACD line crosses above signal line. Sell on the opposite cross.

**RSI + EMA Confluence**: Buy when fast EMA > slow EMA AND RSI < 40 (pullback in uptrend). Sell when fast EMA < slow EMA OR RSI > 75.

## Metrics Reference

| Metric | Good | Bad | Plain English |
|--------|------|-----|---------------|
| Total Return | > 0% | < 0% | Did it make money? |
| Max Drawdown | > -20% | < -40% | Worst peak-to-trough drop you'd have to stomach |
| Sharpe Ratio | > 1.0 | < 0.5 | Return per unit of risk — higher means smoother gains |
| Win Rate | > 50% | < 40% | How often trades close in profit |
| Profit Factor | > 1.5 | < 1.0 | Gross profit / gross loss — below 1.0 is a net loser |

## Regime Awareness

Every strategy has a market regime it works in and one where it fails.

| Strategy Type | Works In | Fails In | Quick Check |
|---------------|----------|----------|-------------|
| Trend-following (EMA cross, MACD) | Trending markets | Choppy/ranging | 50 EMA slope: rising = uptrend, falling = downtrend |
| Mean-reversion (RSI, BB bounce) | Ranging markets | Strong trends | Price swinging between support/resistance |
| Breakout | Compression before expansion | Ranging/low vol | Bollinger Band width narrowing then expanding |

Consider computing a trend filter (50 EMA slope or ADX) for the backtest period before interpreting results. If a strategy loses money, check the regime first — a losing range strategy in a downtrend is expected, not broken. Testing across at least two market conditions (trending + ranging) gives a much better picture than a single period. Note the regime when discussing results: "Tested during downtrend" or "Tested during consolidation" — it matters.

## Limitations

- CoinGecko `/ohlc?days=N` auto-selects candle granularity: 1-2d = 30min, 3-30d = 4h, 31+d = daily. This is CoinGecko API behavior, not a tier limitation (all our API keys are paid). For 4h candles, set DAYS ≤ 30.
- OHLC endpoint has no volume data. Volume-based indicators need separate fetch from market chart endpoint.
- No slippage or fee modeling by default. Add `fee_pct = 0.001` (0.1%) for more realistic results if the user asks.

## Notes

- Paths are relative to workspace. `bash` CWD is already workspace, so write to `scripts/foo.py`, not `workspace/scripts/foo.py`.
- Scripts should be standalone — `requests` + `os.getenv()` for API keys. No internal imports, no dotenv. Env vars are inherited from the server.
- Sensible defaults: 180 days, daily candles, long-only, no fees. Adjust based on what the user is exploring.
- Run the script before discussing results. The output is the proof.
- Explain what the numbers mean in conversation. The metrics table helps, but translate them into plain language for the user — that's what makes a backtest useful, not just the numbers themselves.
