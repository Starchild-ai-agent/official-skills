---
name: massive-options-data
version: 1.3.1
description: |
  US options data: chain snapshots, contracts, trades, quotes, greeks, IV, OI.

  Use when pulling option chains or contract metrics for analysis (e.g. AAPL Jan calls, SPY chain, NVDA IV, weekly puts).
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

## Plan: Developer — REAL field availability

We are on **Massive Options Developer ($79/mo)**. Build your callers against 
what's actually present in the API responses:

| Field | Developer returns? | Notes |
|---|---|---|
| `details.*` (ticker, strike, expiration, type) | ✅ | Always present. |
| `implied_volatility` | ✅ | Per contract, 15-min delayed. |
| `greeks` (delta, gamma, theta, vega) | ✅ | Per contract, 15-min delayed. |
| `open_interest` | ✅ | Per contract, previous session. |
| `day.{open,high,low,close,volume,vwap}` | ✅ | **Option prices** (previous session OHLC), 15-min delayed. |
| `underlying_asset.ticker` | ✅ | Always present. |
| `underlying_asset.price` | ✅ | **Current underlying price**, 15-min delayed. |
| `last_trade` (price, size, timestamp) | ✅ | **Last trade**, 15-min delayed. |
| `last_quote` (bid/ask) | ❌ | **Still not returned** on Developer. Cannot calculate real-time spread. |
| Historical IV / IV Rank / IV Percentile | ❌ | Not exposed on any plan; build your own historical series. |

**ATM filtering now uses real underlying price:**
```python
chain = massive_option_chain_snapshot("AAPL")
# No need for twelvedata — underlying price is now included!
spot_price = chain["results"][0]["underlying_asset"]["price"]
atm_low, atm_high = spot_price * 0.95, spot_price * 1.05
for contract in chain["results"]:
    strike = contract["details"]["strike_price"]  
    if atm_low <= strike <= atm_high:
        # This is an ATM contract
```

If you need real-time bid/ask quotes, upgrade to **Advanced ($199/mo)**.

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
| `massive_option_trades(option_ticker, **range)` | `GET /v3/trades/{option_ticker}` | Historical trade ticks. **Available on Developer+.** |
| `massive_option_quotes(option_ticker, **range)` | `GET /v3/quotes/{option_ticker}` | Historical NBBO quotes. **Still returns 403 on Developer.** Requires Advanced. |
| `massive_option_aggregates(option_ticker, multiplier, timespan, from_, to, **opts)` | `GET /v2/aggs/ticker/{ticker}/range/...` | OHLCV bars. Minute + second bars on Developer, all bars on Advanced. |
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
