---
name: massive-options-data
version: 1.0.0
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
)

# Full chain snapshot (greeks/IV/OI when included in your plan)
snap = massive_option_chain_snapshot(underlying="SPY", limit=10)
print(json.dumps(snap.get("results", [])[:2], indent=2))
EOF
```

## Functions (`exports.py`)

| Function | Endpoint | Purpose |
|---|---|---|
| `massive_option_chain_snapshot(underlying, **filters)` | `GET /v3/snapshot/options/{underlying}` | Full chain snapshot for an underlying (price, greeks, IV, OI, last_quote, last_trade). |
| `massive_option_contract_snapshot(underlying, option_ticker)` | `GET /v3/snapshot/options/{underlying}/{contract}` | Single contract snapshot. |
| `massive_list_contracts(underlying_ticker=None, **filters)` | `GET /v3/reference/options/contracts` | Reference list of option contracts (active or expired). |
| `massive_option_trades(option_ticker, **range)` | `GET /v3/trades/{option_ticker}` | Historical trade ticks. |
| `massive_option_quotes(option_ticker, **range)` | `GET /v3/quotes/{option_ticker}` | Historical NBBO quotes. |
| `massive_option_aggregates(option_ticker, multiplier, timespan, from_, to, **opts)` | `GET /v2/aggs/ticker/{ticker}/range/...` | OHLCV bars for an option contract. |
| `massive_paginate(url, params=None, max_pages=20)` | — | Helper for `next_url` cursor pagination. |

All functions return the raw JSON from upstream (`{"results": [...], "status": "OK", ...}`).
HTTP errors raise via `Response.raise_for_status()`.

## Plan & Data Delays

Endpoint availability follows your Massive plan:

| Plan | Quotes | Greeks/IV | Aggregates | Delay |
|---|---|---|---|---|
| Options Basic (free) | ❌ | ❌ | ❌ | n/a |
| Options Starter ($29/mo) | ✅ | ✅ | minute | 15 min |
| Options Developer ($79/mo) | ✅ | ✅ | minute + second | 15 min |
| Options Advanced ($199/mo) | ✅ | ✅ | full | real-time |

Fields like `last_quote`, `last_trade`, `greeks` may be omitted on lower plans
or for illiquid contracts. The functions surface fields as-returned; null
values are kept as null.

## Pagination

Long results use `next_url`. Use `massive_paginate` to walk pages:

```python
from exports import massive_paginate
url = "https://api.polygon.io/v3/snapshot/options/SPY"
pages = massive_paginate(url, params={"limit": 250}, max_pages=8)
```

## Credentials

Set `MASSIVE_API_KEY` via the agent's secure input flow. The key is injected
by sc-proxy when present; the local script also reads it from the
environment so it works in BYOK setups.

## Source of truth
- Massive options docs: https://massive.com/docs/rest/options/overview
- Follow official field names and endpoint behavior; if upstream changes the
  contract, update this skill rather than papering over it in callers.
