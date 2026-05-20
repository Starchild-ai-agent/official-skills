---
name: cn-stock
version: 1.3.0
description: "China A-share data — Tushare-via-sc-proxy integrated skill for quotes, market cap, financials, shareholders, fund flow, K-line, concept boards, dragon-tiger list, and market movers. Use for ANY 沪深北 A股 stock data request (e.g. 603186 华正新材, 300476 胜宏科技, 000001 平安银行). News is intentionally NOT covered here — use normal web search."
metadata:
  starchild:
    emoji: "🇨🇳"
    skillKey: cn-stock
    requires:
      bins: [python]
    install:
      - kind: pip
        package: pandas
user-invocable: false
disable-model-invocation: false
---

# 🇨🇳 cn-stock — China A-Share Data (Tushare via sc-proxy)

Comprehensive A-share skill that uses **Tushare Pro** as the single upstream source.
All API calls are routed through **sc-proxy** (transparent-proxy `tushare` plugin),
which injects the real API token server-side and bills the request per call.
**No local `TUSHARE_TOKEN` env var needed** — the skill sends a fake token and
sc-proxy replaces it before the request reaches Tushare.

## Source Strategy

```
your call → exports.py (cn-stock)
            └─ proxied_post → sc-proxy (tushare plugin) → http://api.tushare.pro/
```

- No Sina / Eastmoney / akshare scraping fallback.
- No local API key needed.
- Charging is per-request via sc-proxy.

## Output Contract

Most functions return:
```python
{"ok": bool, "source": str, "data": <payload>, "error": str|None, "ts": int}
```

Exception:
- `get_full_report(code)` returns a combined dict of sub-results.

## Code Format

Accepts:
- `000001` / `603186` / `300476` (preferred)
- `000001.SZ` / `600000.SH` / `830799.BJ` (also accepted)

Auto mapping for 6-digit code:
- `60/68/90` → SH
- `00/20/30` → SZ
- `4/8` → BJ

## Function Map

### Quote / company / K-line
| Function | What it returns | Tushare endpoint(s) |
|---|---|---|
| `get_realtime_quote(code)` | latest quote-like snapshot + valuation | `daily` + `daily_basic` |
| `get_company_info(code)` | listed company profile | `stock_company` |
| `get_kline(code, period, start, end, adjust, limit)` | daily/weekly/monthly K-line (unadjusted) | `daily/weekly/monthly` |
| `get_adj_factor(code, days)` | adjust-factor series (for computing qfq/hfq manually) | `adj_factor` |
| `get_bid_ask(code)` | L1-L5 order book | not available in baseline permissions |
| `get_stock_list(market, industry, list_status, limit)` | listed stock universe with optional filters | `stock_basic` |
| `get_trade_calendar(start, end, exchange, open_only)` | trading day calendar | `trade_cal` |

### Financials
| Function | What it returns | Tushare endpoint(s) |
|---|---|---|
| `get_financial(code, max_periods)` | key financial indicators by period | `fina_indicator` |
| `get_income_statement(code, max_periods, period)` | 利润表 | `income` |
| `get_balance_sheet(code, max_periods, period)` | 资产负债表 | `balancesheet` |
| `get_cashflow_statement(code, max_periods, period)` | 现金流量表 | `cashflow` |
| `get_earnings_forecast(code, limit)` | 业绩预告 | `forecast` |
| `get_earnings_express(code, limit)` | 业绩快报 | `express` |
| `get_dividends(code, limit)` | 分红送股 | `dividend` |

### Shareholders & ownership
| Function | What it returns | Tushare endpoint(s) |
|---|---|---|
| `get_holders(code, top)` | latest top shareholders | `top10_holders` |
| `get_shareholder_count(code, periods)` | 股东户数变化 | `stk_holdernumber` |
| `get_shareholder_trades(code, days)` | 重要股东增减持 | `stk_holdertrade` |
| `get_block_trades(code, days)` | 大宗交易 | `block_trade` |

### Fund flow & northbound
| Function | What it returns | Tushare endpoint(s) |
|---|---|---|
| `get_fund_flow(code, days)` | recent fund flow | `moneyflow` |
| `get_margin_detail(code, days)` | 融资融券明细 | `margin_detail` |
| `get_north_holdings(code, days)` | 沪深股通持股明细 (northbound) | `hk_hold` |
| `get_north_flow(days)` | 沪深港通每日资金流向 | `moneyflow_hsgt` |

### Concept / industry / dragon-tiger / market-wide
| Function | What it returns | Tushare endpoint(s) |
|---|---|---|
| `get_concept_boards(top, sort_by)` | concept board list | `ths_index` |
| `get_stock_concepts(code)` | stock concept membership | `ths_member` |
| `get_lhb(code, days)` | dragon-tiger records for stock | `top_list` (recent dates scan) |
| `get_top_movers(direction, limit)` | market-wide top movers | `daily` (+ `daily_basic`) |
| `get_limit_prices(code, trade_date, days)` | 每日涨跌停价 | `stk_limit` |
| `get_limit_board(trade_date, limit_type)` | 当日涨停/跌停/炸板股 | `limit_list_d` |
| `get_suspended(trade_date)` | 每日停复牌 | `suspend_d` |

### Index data
| Function | What it returns | Tushare endpoint(s) |
|---|---|---|
| `get_index_basic(market)` | 指数列表 (SSE/SZSE/MSCI/CSI/SW/...) | `index_basic` |
| `get_index_kline(index_code, period, start, end, limit)` | 指数 K-line（含沪深300/上证/创业板等） | `index_daily/weekly/monthly` |

### One-shot bundle
| Function | What it returns | |
|---|---|---|
| `get_full_report(code)` | quote + company + holders + fund_flow | combo |

## What this skill intentionally does NOT cover

- **News.** Use normal web search (e.g. `web_search`) for stock-related news, announcements, and articles. Tushare news has heavy rate limits and overlaps with general web coverage; running it through the paid proxy adds no value.
- **Adjusted K-line (qfq/hfq).** The HTTP path only returns unadjusted bars. Use `get_adj_factor` + the unadjusted bars from `get_kline` if you need adjusted prices.
- **Intraday tick / bid-ask L1-L5.** Requires upstream independent realtime permission that is not in baseline.
- **Minute bars.** Requires upstream independent permission; not exposed here. Use `get_kline` for end-of-day.

## User-facing reply guidance

When answering users:
- Show values in readable Chinese market units (`亿`, `%`).
- Clearly label data as end-of-day, not intraday tick.
- If a capability is unavailable, say it directly.
- Add source note: `数据来源：Tushare Pro，非投资建议`.

## Maintenance notes

- All requests POST `http://api.tushare.pro/` with body `{api_name, token, params, fields}`.
- `token` field is set to a fake key; sc-proxy `tushare` plugin replaces it before the upstream call.
- To change pricing or rate limit, edit the proxy `tushare` plugin (see `transparent-proxy-maintenance` skill), not this skill.
- Adding a new Tushare endpoint = adding one thin wrapper around `_call(api_name, **params)`.
