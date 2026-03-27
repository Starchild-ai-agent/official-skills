---
name: charting
version: 1.0.0
description: Generate TradingView-style candlestick charts with indicators. Use when the user wants a visual chart, price visualization, or technical analysis plot.

metadata:
  starchild:
    emoji: "📊"
    skillKey: charting
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

# Charting

## ⚠️ DO NOT CALL DATA TOOLS

**NEVER** call `price_chart`, `get_coin_ohlc_range_by_id`, `twelvedata_time_series`, or ANY market data tools. Chart scripts fetch data internally. Calling them floods context with 78KB+ of unnecessary data.

**Workflow:** Read template → Write script → Run with bash → `read_file` output PNG → display with `![Chart](output/filename.png)`

Tools: `write_file`, `bash`, `read_file`

## Chart Selection

| Need | Chart type |
|------|-----------|
| Price action | Candlestick, no indicators |
| Trend analysis | Add EMA/SMA overlays |
| Momentum | RSI or MACD subplots |
| Full technical | Candles + Bollinger + RSI + MACD |
| Asset comparison | Line chart, normalized or percentage-based |

## Templates

In `skills/charting/scripts/`:
- `chart_template.py` — Candlestick with TradingView styling (crypto/CoinGecko)
- `chart_with_indicators.py` — RSI, MACD, Bollinger, EMA/SMA (crypto)
- `chart_stock_template.py` — Stocks/forex via Twelve Data
- `chart_comparison_template.py` — Compare two assets

Copy template to `scripts/`, customize config (coin, days, indicators), run it.

## Data Sources

**CoinGecko** (crypto): `https://pro-api.coingecko.com/api/v3/coins/{coin_id}/ohlc/range`
- Auth: `x-cg-pro-api-key` header. Returns `[timestamp_ms, O, H, L, C]` — no volume.

**Twelve Data** (stocks/forex/commodities): `https://api.twelvedata.com/time_series`
- Auth: `apikey` query param. Symbols: `AAPL`, `XAU/USD` (gold), `EUR/USD`
- ⚠️ Returns **reverse chronological** — always `values[::-1]` before DataFrame

## Auto-Interval

| Range | Interval |
|-------|----------|
| ≤31d | Hourly |
| 32-365d | Daily |
| >365d | Daily |

Override: set `INTERVAL = "daily"` or `"hourly"` in config.

## Color Palette (TradingView Dark)

Up: `#26a69a` | Down: `#ef5350` | BG: `#131722` | Grid: `#1e222d` | Text: `#d1d4dc`
MA: `#2196f3`/`#ff9800` | RSI: `#b39ddb` | MACD: `#2196f3` | Signal: `#ff9800`

## Key Gotchas

- **savefig facecolor**: MUST set `facecolor='#131722'` and `edgecolor='#131722'` or PNG reverts to white
- **Title spacing**: prefix with `\n`
- **`returnfig=True`**: call `fig.savefig()` manually, don't pass `savefig` to `mpf.plot()`
- **No volume in OHLC**: use `volume=False` or fetch separately from `coin_chart` endpoint
- **Panel ratios**: set when adding subplots. E.g. `(5, 1, 2, 2)` for candles + vol + 2 indicators
- **Figure size**: default `(14, 8)`, increase to `(14, 12)` with subplots

## Rules

- Write to `scripts/`, save output to `output/`. Paths relative to workspace.
- Scripts must be standalone: `requests` + `os.getenv()`. **No** `core.http_client` imports.
- Env vars inherited — `os.getenv("COINGECKO_API_KEY")` works directly.
- Default dark theme. Descriptive filenames: `btc_30d_candles.png`.
- One data source per script — don't mix CoinGecko and Twelve Data.
- Think about what you're measuring: normalized charts hide gain magnitude. Use actual multipliers when comparing investment performance.

## Troubleshooting

401 errors: templates auto-configure proxy from `PROXY_HOST`/`PROXY_PORT` env vars. Check `env | grep -E 'PROXY|REQUESTS_CA'`. If vars missing, it's an environment config issue.
