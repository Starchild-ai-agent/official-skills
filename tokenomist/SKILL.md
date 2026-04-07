---
name: tokenomist
version: 1.1.0
description: "Token unlock schedules, cliff events, daily emissions, allocation breakdowns, and supply pressure analytics via Tokenomist API"
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

Token unlock schedules, cliff events, daily emissions, allocation breakdowns, and supply pressure analytics.

## Version Policy (hard rule)

- Token List → **v4** (`/v4/token/list`)
- Allocations → **v2** (`/v2/allocations`)
- Daily Emission → **v2** (`/v2/daily-emission`)
- Unlock Events → **v4** (`/v4/unlock/events`)

Do not downgrade unless user explicitly asks.

## Auth + Proxy

- Header: `x-api-key: $TOKENMIST_API_KEY`
- Base URL: `https://api.tokenomist.ai`
- Uses `core/http_client.py` (`proxied_get`) — sc-proxy handles key replacement.
- Fake key in env (e.g. `fake-tokenomist-key-12345`) is expected. Never treat as invalid.

## Keyword → Tool Lookup

| User asks about | Tool | NOT this |
|----------------|------|----------|
| "tokenomics overview", "全面分析" | `tokenomist_token_overview` | Don't call 4 tools separately |
| "allocation", "分配", "top holders" | `tokenomist_allocations_summary` | Not `tokenomist_allocations` (too verbose) |
| "allocation raw data", "full breakdown" | `tokenomist_allocations` | — |
| "unlock schedule", "解锁", "cliff" | `tokenomist_unlock_events` | — |
| "daily emission", "每日释放" | `tokenomist_daily_emission` | — |
| "find token", "which token id" | `tokenomist_resolve_token` | Not `tokenomist_token_list` |
| "list all tokens" | `tokenomist_token_list` | — |

## MISTAKES — Read Before Calling

### ❌ MISTAKE 1: Calling 4 tools for a general tokenomics question
```
User: "ARB 的 tokenomics 情况"
❌ WRONG: tokenomist_resolve_token → tokenomist_allocations → tokenomist_daily_emission → tokenomist_unlock_events
✅ RIGHT: tokenomist_token_overview(query="ARB")  ← does all 4 in one call
```

### ❌ MISTAKE 2: Using allocations instead of allocations_summary
```
User: "ARB 的代币分配"
❌ WRONG: tokenomist_allocations(token_id="arb")  ← returns raw verbose data
✅ RIGHT: tokenomist_allocations_summary(query="ARB")  ← concise, auto-resolves, has quality flags
```
Only use `tokenomist_allocations` when user explicitly asks for raw/full data or debugging.

### ❌ MISTAKE 3: Passing symbol directly without resolving
```
❌ WRONG: tokenomist_unlock_events(token_id="ARB")  ← might not match API's internal ID
✅ RIGHT: tokenomist_resolve_token(query="ARB") → get canonical token_id → then call events
```
Exception: `tokenomist_token_overview` and `tokenomist_allocations_summary` auto-resolve — no need to call resolve first.

### ❌ MISTAKE 4: Forgetting date format
```
❌ WRONG: tokenomist_unlock_events(token_id="arb", start="2025/01/01")
✅ RIGHT: tokenomist_unlock_events(token_id="arb", start="2025-01-01")  ← YYYY-MM-DD only
```

### ❌ MISTAKE 5: Confusing tokenomist with coingecko for supply data
```
User: "ARB 的 circulating supply"
❌ WRONG: tokenomist_*  ← Tokenomist does unlocks/emissions, not live supply
✅ RIGHT: coin_price(ids="arbitrum") or cg_coin_data(id="arbitrum")  ← CoinGecko has supply
```
**Boundary**: Tokenomist = unlock schedules & emission pressure. CoinGecko = live supply & market cap.

## Tool Reference

### `tokenomist_token_overview` ⭐ Default choice
One-call wrapper: resolve → allocations → emission → unlock events.
Use when user asks broad tokenomics question.

### `tokenomist_allocations_summary`
Compact allocation view with `top_allocations`, `coverage`, `quality` flags.
Accepts `token_id` or `query` (auto-resolves).

### `tokenomist_allocations`
Full allocation data. Use only when user needs raw detail or `include_raw=true` for debugging.

### `tokenomist_unlock_events`
Cliff unlock events (v4). Linear/mining-yield events excluded.
Params: `token_id` (required), `start`/`end` (optional, YYYY-MM-DD).

### `tokenomist_daily_emission`
Daily emission schedule (v2).
Params: `token_id` (required), `start`/`end` (optional, YYYY-MM-DD).

### `tokenomist_resolve_token`
Resolve symbol/name → canonical `tokenId`. Use before granular tools.

### `tokenomist_token_list`
Full token list (v4). Use for browsing, not single-token lookup.

## Interpreting Results — Supply Pressure

When presenting unlock/emission data, help user assess **supply pressure**:

| Signal | Interpretation |
|--------|---------------|
| Large cliff unlock within 7 days | ⚠️ Short-term sell pressure likely |
| Daily emission > 0.5% of circulating supply | ⚠️ Persistent dilution |
| Unlock to team/investor wallets | Higher sell probability than ecosystem/community |
| Multiple unlocks clustering in same week | Compounding pressure — flag explicitly |
| No major unlocks for 30+ days | Reduced supply-side pressure |

**Always contextualise**: "ARB has a $50M team unlock in 3 days" is more actionable than "ARB has an unlock event".
