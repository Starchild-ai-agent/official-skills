---
name: backtest
version: 1.0.0
description: "Build and run backtests against real historical data. Validate strategies with actual performance metrics before committing."
metadata:
  starchild:
    emoji: "🧪"
    skillKey: backtest
    requires:
      env: [COINGECKO_API_KEY]
      install:
        - { kind: pip, package: mplfinance }
        - { kind: pip, package: pandas }
        - { kind: pip, package: numpy }
user-invocable: true
---

# Backtest

Turn strategy ideas into numbers. Entry rule + exit rule + historical data = honest performance metrics.

Tools: `write_file`, `bash`, `read_file`

## Principles

- **Results over theories** — run it and show the numbers, don't nod along
- **Talk first, code second** — clarify entry/exit logic, coin, timeframe before writing anything
- **Honest results** — if it loses money, say so directly
- **Iterate** — first backtest is baseline, not verdict
- **Explain metrics** — "that drawdown means you'd watch 40% evaporate at the worst point"

## Workflow

1. Clarify strategy (entry trigger, exit trigger, coin, timeframe)
2. Check `scripts/` for existing relevant code — reuse before rebuilding
3. Write standalone script to `scripts/`, run with `bash`
4. Output dashboard (equity curve + drawdown + metrics) to `output/`
5. Discuss results honestly, iterate

**Charting**: Add charts directly in backtest script (matplotlib) — data is already in memory. Don't create separate chart scripts.

## Backtesting Biases

| Bias | Mitigation |
|------|------------|
| Look-ahead | Shift signals by 1 bar — trade on next bar's open |
| Survivorship | Be aware with altcoins — many delist |
| Overfitting | Keep parameters minimal, test out-of-sample |
| Transaction costs | Model fees (0.1% default) and slippage |

## Implementation Patterns

### Vectorized (Simple Strategies)

For signal-based strategies (EMA cross, RSI threshold). Signals shifted by 1 to avoid look-ahead.

```python
def backtest_vectorized(prices_df, signal_func, initial_capital=10000, fee_pct=0.001):
    signals = signal_func(prices_df).shift(1).fillna(0)
    returns = prices_df["close"].pct_change()
    position_changes = signals.diff().abs()
    trading_costs = position_changes * fee_pct
    strategy_returns = signals * returns - trading_costs
    equity = (1 + strategy_returns).cumprod() * initial_capital
    return equity, strategy_returns, signals
```

### Event-Driven (Complex Logic)

For stop-losses, trailing stops, position sizing, conditional exits. Bar-by-bar processing.

```python
def backtest_event_driven(ohlc_df, strategy, initial_capital=10000, fee_pct=0.001):
    cash, position, entry_price = initial_capital, 0, 0
    trades, equity_curve = [], []
    for timestamp, bar in ohlc_df.iterrows():
        action = strategy.on_bar(timestamp, bar, position, cash)
        if action.get("buy") and position == 0:
            qty = action.get("qty", cash / bar["close"])
            cost = qty * bar["close"] * (1 + fee_pct)
            if cost <= cash:
                position, entry_price = qty, bar["close"]
                cash -= cost
        elif action.get("sell") and position > 0:
            cash += position * bar["close"] * (1 - fee_pct)
            trades.append({"entry": entry_price, "exit": bar["close"],
                          "pnl_pct": (bar["close"] - entry_price) / entry_price})
            position = 0
        equity_curve.append({"timestamp": timestamp, "equity": cash + position * bar["close"]})
    return pd.DataFrame(equity_curve), trades
```

### Walk-Forward Analysis

Optimize on training window, evaluate on test window, slide forward. Report combined out-of-sample results.

## Metrics Reference

| Metric | Good | Bad | Meaning |
|--------|------|-----|---------|
| Total Return | > 0% | < 0% | Did it make money? |
| Max Drawdown | > -20% | < -40% | Worst peak-to-trough drop |
| Sharpe Ratio | > 1.0 | < 0.5 | Return per unit of risk |
| Win Rate | > 50% | < 40% | % trades in profit |
| Profit Factor | > 1.5 | < 1.0 | Gross profit / gross loss |

## Regime Awareness

| Strategy Type | Works In | Fails In |
|---------------|----------|----------|
| Trend-following (EMA, MACD) | Trending | Choppy/ranging |
| Mean-reversion (RSI, BB) | Ranging | Strong trends |
| Breakout | Compression→expansion | Low vol ranging |

Always note the market regime when reporting results.

## Data Limitations

- CoinGecko OHLC auto-selects granularity: 1-2d→30min, 3-30d→4h, 31+d→daily
- OHLC endpoint has no volume. Volume indicators need market chart endpoint.
- Defaults: 180 days, daily candles, long-only, no fees. Adjust as needed.

## Notes

- Scripts standalone: `requests` + `os.getenv()` for API keys. No internal imports.
- Paths relative to workspace. `bash` CWD is already workspace.
- Run script before discussing results — output is the proof.
