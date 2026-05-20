---
name: massive-options-data
version: 1.2.0
description: "Massive (formerly Polygon) US options market data — option chain snapshots, contract snapshots, trades, quotes, aggregates, contract reference, greeks/IV/OI passthrough"
delivery: script
metadata:
  starchild:
    emoji: "🧩"
    skillKey: massive-options-data
    requires:
      env:
        - MASSIVE_API_KEY

user-invocable: false
disable-model-invocation: false
---

# Massive Options Data

Data supply layer for US options market data. Wraps the Massive (Polygon)
options REST endpoints with a thin, predictable Python interface.

This skill does NOT generate strategies, signals, rankings, or trading
advice — it only exposes options data.

## Plan: Starter — REAL field availability

We are on **Massive Options Starter ($29/mo)**. The official docs list more
fields than this plan actually returns. Build your callers against what's
actually present, not what the docs imply:

| Field | Starter returns? | Notes |
|---|---|---|
| `details.*` (ticker, strike, expiration, type) | ✅ | Always present. |
| `implied_volatility` | ✅ | Per contract. |
| `greeks` (delta, gamma, theta, vega) | ✅ | Per contract. |
| `open_interest` | ✅ | Per contract. |
| `day.{open,high,low,close,volume,vwap}` | ✅ | Previous session, 15-min delayed. |
| `underlying_asset.ticker` | ✅ | Just the ticker string. |
| `underlying_asset.price` | ❌ | **Not returned** on Starter. Use a delta-band (e.g. `0.35 ≤ |Δ| ≤ 0.65`) as an ATM proxy. |
| `last_quote` (bid/ask) | ❌ | **Not returned** on Starter. You cannot filter by bid-ask spread. |
| `last_trade` | ❌ | Not returned on Starter. |
| Historical IV / IV Rank / IV Percentile | ❌ | Not exposed on any plan; you must build your own historical IV series. |

If you need NBBO quotes, last trade, or real-time data, the plan must be
upgraded to **Developer ($79/mo)** or **Advanced ($199/mo)**.

## Pagination — required for any DTE-range scan

Chain snapshots paginate by `ticker` sort order. A 250-row first page often
covers just one expiration. To get all contracts in a DTE window you MUST
walk `next_url` (see `massive_paginate` in `exports.py`). Skipping this is
the #1 reason a "0 results" scan looks broken.

Typical chain sizes for a single underlying with one expiration window can
exceed 450 contracts. Allow at least 4 pages.

## Script Usage

```bash
python3 - <<'EOF'
import sys, json
sys.path.insert(0, "/data/workspace/skills/massive-options-data")
from exports import (
    massive_option_chain_snapshot,
    massive_option_contract_snapshot,
    massive_option_trades,
    massive_option_quotes,
    massive_option_aggregates,
    massive_list_contracts,
    massive_paginate,
)

snap = massive_option_chain_snapshot(underlying="SPY", limit=10)
print(json.dumps(snap.get("results", [])[:2], indent=2))
EOF
```

## Functions (`exports.py`)

| Function | Endpoint | Purpose |
|---|---|---|
| `massive_option_chain_snapshot(underlying, **filters)` | `GET /v3/snapshot/options/{underlying}` | Full chain snapshot (price/greeks/IV/OI; quote+trade missing on Starter). |
| `massive_option_contract_snapshot(underlying, option_ticker)` | `GET /v3/snapshot/options/{underlying}/{contract}` | Single contract snapshot. |
| `massive_list_contracts(underlying_ticker=None, **filters)` | `GET /v3/reference/options/contracts` | Reference list of option contracts (active or expired). |
| `massive_option_trades(option_ticker, **range)` | `GET /v3/trades/{option_ticker}` | Historical trade ticks. **Returns 403 on Starter.** |
| `massive_option_quotes(option_ticker, **range)` | `GET /v3/quotes/{option_ticker}` | Historical NBBO quotes. **Returns 403 on Starter.** |
| `massive_option_aggregates(option_ticker, multiplier, timespan, from_, to, **opts)` | `GET /v2/aggs/ticker/{ticker}/range/...` | OHLCV bars for an option contract. Minute bars on Starter, all bars on Developer+. |
| `massive_paginate(url, params=None, max_pages=20)` | — | Walk `next_url` cursor pagination. |

All functions return the raw JSON from upstream. HTTP errors raise via
`Response.raise_for_status()`.

## Hardening notes

- **Probe first, code second.** Before writing a filter pipeline against a
  new endpoint, dump one full record and inspect actual fields. Saves hours
  of "why is everything filtered out?" debugging.
- **Null handling.** `greeks`, `last_quote`, `last_trade` may be absent;
  keep as `None`, never fabricate.
- **Caller-id.** Every call should include a `caller_id` so transparent-proxy
  can attribute usage.

## Credentials

Set `MASSIVE_API_KEY` via the agent's secure input flow. The key is injected
by sc-proxy when present; the local script also reads it from the
environment so it works in BYOK setups.

## Source of truth
- Massive options docs: https://massive.com/docs/rest/options/overview
- Follow official field names; when upstream changes the contract, update
  this skill rather than papering over it in callers.
