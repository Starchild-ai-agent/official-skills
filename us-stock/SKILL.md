---
name: us-stock
version: 1.0.0
description: "US equities data — realtime quotes, market cap & shares outstanding, float / insider / institutional % held, top institutional + mutual fund holders, insider transactions (Form 4), full financial statements (income / balance / cashflow, annual + quarterly), earnings calendar, dividends, splits, news, options expirations, analyst ratings. Wraps the existing (paid) twelvedata skill for prices/K-line and yfinance for fundamentals. Use for ANY US ticker (AAPL, MSFT, NVDA, BRK.B, ...) — TwelveData alone does not return shares outstanding / holders / financials / insiders, this skill is the source of truth."
metadata:
  starchild:
    emoji: "🇺🇸"
    skillKey: us-stock
    requires:
      bins: [python]
    install:
      - kind: pip
        package: yfinance
user-invocable: false
disable-model-invocation: false
---

# 🇺🇸 us-stock — US Equities Data

Single Python module with **multi-source fallback** for US stocks. Mirror of `cn-stock` for the US market. Use whenever the user asks about a US ticker — fundamentals, holders, insiders, financials. For pure price/K-line on US tickers, this skill internally calls the paid TwelveData skill, so you get one consistent interface.

## Architecture

```
your call → exports.py
            ├─ twelvedata (paid, primary)  → realtime quote, time series
            └─ yfinance (free, primary for fundamentals)
                                          → info, holders, insiders,
                                            financials, news, options,
                                            dividends, splits, earnings
```

Most functions return a uniform envelope:
```python
{"ok": bool, "source": str, "data": <payload>, "error": str|None, "ts": int}
```
Exception: `get_full_report(symbol)` returns a combined dict of sub-results (quote/company/holders/insiders/earnings/news).

## Quick Start

**Preferred** — use `core.skill_tools` (handles import isolation):

```bash
python3 - <<'EOF'
from core.skill_tools import _modules
us = _modules["us-stock"]

q = us.get_realtime_quote("AAPL")
print(q["data"]["last"], q["data"]["pct_change"], "%")

c = us.get_company_info("NVDA")
d = c["data"]
print(f"{d['name']} | mcap ${d['market_cap']/1e12:.2f}T | shares {d['shares_outstanding']/1e9:.2f}B")

full = us.get_full_report("MSFT")
print(full["company"]["data"]["sector"])
EOF
```

**Fallback** (single-skill scripts only):

```bash
python3 - <<'EOF'
import importlib.util as ilu
spec = ilu.spec_from_file_location("us_stock_mod", "/data/workspace/skills/us-stock/exports.py")
us = ilu.module_from_spec(spec); spec.loader.exec_module(us)
print(us.get_realtime_quote("AAPL")["data"])
EOF
```

⚠️ **Do NOT use** `sys.path.insert + from exports import ...` — `cn-stock` also defines `exports.py` and they will collide in the same process.

## Function Map

| Function | Returns | Source |
|---|---|---|
| `get_realtime_quote(symbol)` | price, OHLC, change, 52w range, mcap | twelvedata → yfinance fallback |
| `get_company_info(symbol)` | mcap, **shares_outstanding**, **float_shares**, **pct_held_insiders**, **pct_held_institutions**, sector, industry, business summary, valuation, margins, dividend, analyst targets | yfinance.get_info |
| `get_institutional_holders(symbol, top=15)` | Top N institutional holders + value + pctChange | yfinance |
| `get_mutualfund_holders(symbol, top=15)` | Top N mutual fund holders | yfinance |
| `get_insider_transactions(symbol, limit=20)` | Recent Form 4 buys/sells | yfinance |
| `get_financials(symbol, statement, period, max_periods=5)` | Income / Balance / Cashflow, annual or quarterly | yfinance |
| `get_earnings(symbol, limit=8)` | Past + upcoming earnings dates with EPS est. vs actual | yfinance |
| `get_dividends(symbol, limit=20)` | Historical dividends | yfinance |
| `get_splits(symbol, limit=10)` | Historical splits | yfinance |
| `get_news(symbol, limit=10)` | Recent news titles + summaries + URLs | yfinance |
| `get_kline(symbol, interval, outputsize)` | OHLCV bars | twelvedata → yfinance fallback |
| `get_recommendations(symbol, limit=12)` | Analyst rating buckets per period | yfinance |
| `get_options_expirations(symbol)` | All available option expiry dates | yfinance |
| `get_etf_holdings(symbol, top=15)` | ETF/fund top holdings + sector/asset weights (e.g. SPY/QQQ) | yfinance.funds_data |
| `get_full_report(symbol)` | quote + company + institutional + insiders + earnings + news combined | combo |

## Symbol Format

Pure US ticker — no exchange suffix:
- `AAPL`, `MSFT`, `NVDA`, `GOOGL`, `TSLA`
- Dual-class: `BRK.B`, `BRK-B`, `GOOG` / `GOOGL`
- Both formats accepted; pass through as-is

## TwelveData Reuse (important)

This skill **does not register a separate TwelveData credential**. It loads the existing TwelveData skill by explicit file path (`/data/workspace/skills/twelvedata/exports.py`) via `importlib`, avoiding `exports.py` name collisions with other skills.
Starchild's TwelveData billing covers these calls. If TwelveData fails, yfinance fallback kicks in automatically.

## get_company_info Field Reference

Fields most useful for Telegram replies (all from yfinance):

| Field | Meaning | Notes |
|---|---|---|
| `market_cap` | 总市值 (USD) | divide by 1e9 → 十亿, 1e12 → 万亿 |
| `enterprise_value` | EV | mcap + debt − cash |
| `shares_outstanding` | 流通股 (实际为已发行股数) | divide by 1e9 |
| `float_shares` | 自由流通股 (排除限售) | usually slightly < shares_outstanding |
| `shares_short` | 当前空头持仓 | |
| `short_pct_of_float` | 空头占流通比 | already ratio, ×100 for % |
| `pct_held_insiders` | 内部人持股比例 | already ratio |
| `pct_held_institutions` | 机构持股比例 | already ratio |
| `trailing_pe` / `forward_pe` | 静态/动态 PE | |
| `price_to_book` | 市净率 | |
| `dividend_yield` | 股息率 | already ratio (0.0036 = 0.36%) |
| `beta` | 贝塔系数 | vs SP500 |
| `recommendation` | 'buy' / 'hold' / 'sell' | analyst consensus |
| `target_mean_price` | 分析师目标均价 | |

## Gotchas

- **yfinance rate limits**: Yahoo throttles aggressive callers (~2000/hour). Per `get_full_report` is ~6 calls. For batch monitoring use `time.sleep(0.3)` between tickers. The skill already has `_retry(tries=2)`.
- **`get_info()` is heavy** (~1-2s, returns 120+ fields). For pure price use `get_realtime_quote()` instead (TwelveData ~150ms).
- **NaN handling**: yfinance returns NaN for missing fields (e.g. dividend yield for non-dividend payers). The skill converts NaN → `null` in JSON. Always check for `None` before formatting.
- **Quarterly financials limit**: yfinance returns ~4 quarters back. For deeper history use SEC EDGAR 10-Q parsing (future enhancement).
- **Real-time vs delayed**: TwelveData is exchange-direct (low latency). yfinance has ~1 min lag during market hours. When they conflict, trust TwelveData.
- **Institutional holders staleness**: 13F filings lag 45 days after quarter-end. `Date Reported` field tells you the as-of date.
- **News provider IDs change**: yfinance's `news` schema occasionally adds/removes fields. The skill normalizes to `{title, summary, publisher, pub_date, url, type}`.
- **Options data weight**: `get_options_expirations` is fast but fetching the full chain (Calls/Puts at each strike) requires per-expiry calls — not exposed yet to keep this skill light.

## Output Style for User-Facing Replies

Telegram users want plain text, no markdown. Follow these conventions:

- Market cap: `$3.91T` (万亿 = T, 十亿 = B, 百万 = M)
- Shares: `14.69B 股`
- Ratios: `+2.34%` (sign required), `PE 36.2`, `Beta 1.07`
- Holders: `贝莱德 (BlackRock) 7.32%`
- Always cite source at end: `数据来源：TwelveData + Yahoo Finance (yfinance)，非投资建议`

## Future Enhancements (not implemented)

- SEC EDGAR 13F deep dive (top N positions over multiple quarters)
- Form 4 raw filings with explicit transaction type (P/S/A/D codes)
- Pre/post-market quote (TwelveData supports `prepost=True` — exposed via `get_realtime_quote` if needed)
- Options chain greeks (requires per-expiry × per-strike calls)
