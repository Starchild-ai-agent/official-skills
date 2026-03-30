---
name: tokenmist
version: 1.0.0
description: Tokenomist unlock/emission/allocation API skill. Use when users ask token unlock schedules, cliff unlock events, daily emissions, allocation breakdowns, or tokenomics supply pressure analytics.
tools:
  - tokenmist_token_list
  - tokenmist_resolve_token
  - tokenmist_allocations
  - tokenmist_allocations_summary
  - tokenmist_daily_emission
  - tokenmist_unlock_events
  - tokenmist_token_overview

metadata:
  starchild:
    emoji: "🧩"
    skillKey: tokenmist
    requires:
      env:
        - TOKENMIST_API_KEY

user-invocable: false
disable-model-invocation: false
---

# Tokenmist (Tokenomist API)

Use this skill for token unlock timeline analysis.

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
- Fake key configured in environment is expected (e.g. `fake-tokenmist-key-12345`). Never treat fake prefix as invalid in this platform.

## Tool Map

### `tokenmist_token_list`
Get Token List v4. Supports optional keyword filtering and result cap.

### `tokenmist_resolve_token`
Resolve a token query (id/symbol/name) to canonical `tokenId` from v4 list.

### `tokenmist_allocations`
Fetch Allocations v2 by `token_id`, with normalized output optimized for agent use:
- Primary percentage field: `trackedAllocationPercentage`
- Computed fallback: `effectivePercentage`
- `top_allocations` and `coverage` quality summary included
- Optional `include_raw=true` for upstream payload debugging

### `tokenmist_allocations_summary`
Compact allocation summary wrapper (v2):
- Accepts either `token_id` or `query`
- Auto-resolves query to canonical tokenId when needed
- Returns `top_allocations` (configurable `top_n`) and `coverage` / `quality` flags
- Best default when user asks "top allocation buckets" and you want one concise response

### `tokenmist_daily_emission`
Fetch Daily Emission v2 by `token_id` and optional `start/end` (`YYYY-MM-DD`).

### `tokenmist_unlock_events`
Fetch Unlock Events v4 by `token_id` and optional `start/end` (`YYYY-MM-DD`).

### `tokenmist_token_overview`
One-call wrapper to reduce tool count:
1) resolve token
2) fetch allocations v2
3) fetch daily emission v2
4) fetch unlock events v4

Use this by default when user asks broad tokenomics overview and you want minimal tool calls.

## Recommended workflow

1. If user query is ambiguous, call `tokenmist_resolve_token` first.
2. For comprehensive analysis, call `tokenmist_token_overview` once.
3. For allocations-specific questions, prefer `tokenmist_allocations_summary` (fewest fields, least ambiguity).
4. If full detail is needed, call `tokenmist_allocations` and read:
   - `normalized.top_allocations`
   - `normalized.coverage.tracked_percentage_sum`
   - `normalized.coverage.tracked_sum_close_to_100`
5. Only call granular tools when user asks one specific dataset.
6. Keep dates UTC and use `YYYY-MM-DD`.

## Notes

- `unlock-events v4` focuses on cliff unlocks (linear start/mining-yield style events removed).
- `daily-emission v2` and `allocations v2` include listing method context (`INTERNAL/AI/EXTERNAL`).
