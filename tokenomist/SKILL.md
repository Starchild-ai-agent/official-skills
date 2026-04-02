---
name: tokenomist
version: 1.0.0
description: Tokenomist unlock/emission/allocation API skill. Use when users ask token unlock schedules, cliff unlock events, daily emissions, allocation breakdowns, or tokenomics supply pressure analytics.
tools:
  - tokenomist_token_list
  - tokenomist_resolve_token
  - tokenomist_allocations
  - tokenomist_allocations_summary
  - tokenomist_daily_emission
  - tokenomist_unlock_events
  - tokenomist_token_overview

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

# Tokenomist (Tokenomist API)

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
