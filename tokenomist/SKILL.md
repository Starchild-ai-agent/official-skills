---
name: tokenomist
version: 2.0.1
description: Tokenomist unlock/emission/allocation API skill. Use when users ask token unlock schedules, cliff unlock events, daily emissions, allocation breakdowns, or tokenomics supply pressure analytics.
delivery: script
protected: true

metadata:
  starchild:
    emoji: "🧩"
    skillKey: tokenomist
    requires:
      env:
        - TOKENMIST_API_KEY

user-invocable: false
disable-model-invocation: false
---

## Script Usage

Script-mode skill — read this file, then invoke from a `bash` block:

```bash
python3 - <<'EOF'
import sys, json
sys.path.insert(0, "/data/workspace/skills/tokenomist")
from exports import (
    tokenomist_resolve_token,
    tokenomist_token_overview,
    tokenomist_unlock_events,
    tokenomist_daily_emission,
    tokenomist_allocations,
)

# Resolve symbol -> token id
print(tokenomist_resolve_token(query="ARB"))

# Full overview
print(json.dumps(tokenomist_token_overview(query="ARB"), indent=2))
EOF
```

Available functions in `exports.py`: `tokenomist_token_list`,
`tokenomist_resolve_token`, `tokenomist_allocations`,
`tokenomist_allocations_summary`, `tokenomist_daily_emission`,
`tokenomist_unlock_events`, `tokenomist_token_overview`.
Read `exports.py` directly for exact signatures.


# Tokenomist (Tokenomist API)

Use this skill for token unlock timeline analysis.

## Function Reference (full signatures + return shapes)

All functions live in `exports.py`.

### ⚠️ Field naming convention (READ THIS FIRST)

**All Tokenomist response fields use camelCase, not snake_case.** The most
common mistake: looking for `allocation_percentage` when the field is
actually `trackedAllocationPercentage`. Always inspect the dict before
scripting.

### Function Signatures

| Function | Signature |
|---|---|
| `tokenomist_token_list()` | List all supported tokens (id + symbol + name) |
| `tokenomist_resolve_token(query)` | dict — `{match_type, token: {id, symbol, name, marketCap, ...}, candidates}`. Use this to convert a symbol like "ARB" into the canonical id "arbitrum" before other calls (most other endpoints accept either). |
| `tokenomist_allocations(query)` | Full raw allocation data (granular, includes per-recipient breakdown when known) |
| `tokenomist_allocations_summary(query)` | Aggregated allocation summary — recommended for analysis/charts |
| `tokenomist_daily_emission(query, start=None, end=None)` | Daily emission schedule (date + amount) |
| `tokenomist_unlock_events(query, start=None, end=None)` | Cliff unlock events list |
| `tokenomist_token_overview(query, start=None, end=None, include_allocations=True, include_emission=True, include_events=True)` | Composite call — bundles overview + allocations + emission + events into one response. Use this for "give me everything about token X". |

`start` / `end` accept ISO 8601 dates (`"2026-01-01"`) or unix
timestamps. Omit both for "all available history".

### Response Schemas

`tokenomist_allocations_summary(query="ARB")`:
```json
{
  "metadata": {"queryDate": "2026-05-04T..."},
  "status": true,
  "data": {
    "name": "Arbitrum",
    "symbol": "ARB",
    "listedMethod": "INTERNAL",
    "maxSupply": 10000000000,
    "lastUpdatedDate": "2025-06-11T10:31:15Z",
    "totalUnlockedAmount": 5410170736.76,
    "totalLockedAmount": 1186004337.54,
    "totalUntrackedAmount": 0,
    "totalTBDLockedAmount": 3403750000,
    "allocations": [
      {
        "allocationName": "Arbitrum DAO Treasury",
        "allocationType": "TBD",
        "standardAllocationName": "Reserve",
        "allocationUnlockedAmount": 0,
        "allocationLockedAmount": 3403750000,
        "allocationAmount": 3403750000,
        "trackedAllocationPercentage": 34.0375
      },
      ...
    ]
  }
}
```

Common pitfalls in `allocations` items:
- Percentage field: `trackedAllocationPercentage` (NOT `allocation_percentage` / `percentage` / `pct`)
- Three separate amount fields: `allocationAmount` (total), `allocationUnlockedAmount`, `allocationLockedAmount`
- Type field: `allocationType` — string values like `"TBD"`, `"Scheduled"`, `"Vested"`
- Standard category name: `standardAllocationName` (e.g. "Reserve", "Founder / Team", "Private Investors")

`tokenomist_unlock_events(query="ARB")`:
```json
{
  "data": [
    {
      "eventDate": "2026-...",
      "tokenAmount": ...,
      "tokenAmountUSD": ...,
      "allocationName": "Investors",
      "allocationType": "Scheduled"
    }
  ]
}
```

`tokenomist_daily_emission(query="ARB")`:
```json
{
  "data": [
    {"date": "2026-...", "amountEmitted": ..., "amountEmittedUSD": ...}
  ]
}
```

`tokenomist_resolve_token(query="ARB")`:
```json
{
  "match_type": "exact_symbol",
  "token": {
    "id": "arbitrum",
    "name": "Arbitrum",
    "symbol": "ARB",
    "listedMethod": "INTERNAL",
    "marketCap": 721937871,
    "circulatingSupply": 6150718438,
    "maxSupply": 10000000000
  },
  "candidates": []
}
```

`match_type` can be: `"exact_symbol"`, `"exact_id"`, `"exact_name"`,
`"fuzzy"`, or `"none"`. When fuzzy, `candidates` lists alternative tokens
to disambiguate.


## Version Policy (hard rule)

When multiple API versions exist, always use latest stable versions:

- Token List API → **v4** (`/v4/token/list`)
- Allocations API → **v2** (`/v2/allocations`)
- Daily Emission API → **v2** (`/v2/daily-emission`)
- Unlock Events API → **v4** (`/v4/unlock/events`)

Do not downgrade unless user explicitly asks for legacy behavior.

## Auth + Proxy

- Header: `x-api-key: $TOKENMIST_API_KEY`
- Base URL: `https://api.tokenomist.ai`
- This skill uses `core/http_client.py` (`proxied_get`), so requests follow platform sc-proxy behavior.
- Fake key configured in environment is expected (e.g. `fake-tokenomist-key-12345`). Never treat fake prefix as invalid in this platform.

## Tool Map

### `tokenomist_token_list`
Get Token List v4. Supports optional keyword filtering and result cap.

### `tokenomist_resolve_token`
Resolve a token query (id/symbol/name) to canonical `tokenId` from v4 list.

### `tokenomist_allocations`
Fetch Allocations v2 by `token_id`, with normalized output optimized for agent use:
- Primary percentage field: `trackedAllocationPercentage`
- Computed fallback: `effectivePercentage`
- `top_allocations` and `coverage` quality summary included
- Optional `include_raw=true` for upstream payload debugging

### `tokenomist_allocations_summary`
Compact allocation summary wrapper (v2):
- Accepts either `token_id` or `query`
- Auto-resolves query to canonical tokenId when needed
- Returns `top_allocations` (configurable `top_n`) and `coverage` / `quality` flags
- Best default when user asks "top allocation buckets" and you want one concise response

### `tokenomist_daily_emission`
Fetch Daily Emission v2 by `token_id` and optional `start/end` (`YYYY-MM-DD`).

### `tokenomist_unlock_events`
Fetch Unlock Events v4 by `token_id` and optional `start/end` (`YYYY-MM-DD`).

### `tokenomist_token_overview`
One-call wrapper to reduce tool count:
1) resolve token
2) fetch allocations v2
3) fetch daily emission v2
4) fetch unlock events v4

Use this by default when user asks broad tokenomics overview and you want minimal tool calls.

## Recommended workflow

1. If user query is ambiguous, call `tokenomist_resolve_token` first.
2. For comprehensive analysis, call `tokenomist_token_overview` once.
3. For allocations-specific questions, prefer `tokenomist_allocations_summary` (fewest fields, least ambiguity).
4. If full detail is needed, call `tokenomist_allocations` and read:
   - `normalized.top_allocations`
   - `normalized.coverage.tracked_percentage_sum`
   - `normalized.coverage.tracked_sum_close_to_100`
5. Only call granular tools when user asks one specific dataset.
6. Keep dates UTC and use `YYYY-MM-DD`.

## Notes

- `unlock-events v4` focuses on cliff unlocks (linear start/mining-yield style events removed).
- `daily-emission v2` and `allocations v2` include listing method context (`INTERNAL/AI/EXTERNAL`).
