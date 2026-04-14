---
name: tokenomist
version: 1.2.0
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

> **Priority rule**: Specific tool wins over `token_overview`. If an unlock/cliff/emission keyword matches, use that specific tool — do NOT fall back to `token_overview`.

| Intent | Trigger keywords (any match) | Tool | ⛔ NOT |
|--------|------------------------------|------|--------|
| Broad overview | "tokenomics overview", "全面分析", "综合分析", "告诉我所有" | `tokenomist_token_overview` | 4 tools separately |
| Allocation summary | "allocation", "分配", "who holds", "谁持有", "top holders", "team allocation" | `tokenomist_allocations_summary` | `tokenomist_allocations` |
| Allocation raw | "full breakdown", "raw allocation", "complete allocation data" | `tokenomist_allocations` | — |
| **Unlock/Cliff** ⚡ | "unlock", "解锁", "cliff", "vesting", "lockup", "token release" | `tokenomist_unlock_events` | ⛔ `token_overview` |
| **Unlock/Cliff** ⚡ | "unlock schedule", "解锁时间表", "解锁计划", "vesting schedule" | `tokenomist_unlock_events` | ⛔ `token_overview` |
| **Unlock/Cliff** ⚡ | "next unlock", "when unlock", "什么时候解锁", "下一次解锁", "即将解锁" | `tokenomist_unlock_events` | ⛔ `token_overview` |
| **Unlock/Cliff** ⚡ | "lockup expiry", "锁定到期", "代币释放时间", "upcoming unlock" | `tokenomist_unlock_events` | ⛔ `token_overview` |
| Daily emission | "daily emission", "每日释放", "emission rate", "daily release" | `tokenomist_daily_emission` | — |
| Token lookup | "find token", "which token id", "token id for X" | `tokenomist_resolve_token` | — |
| Token list | "list all tokens", "what tokens tracked" | `tokenomist_token_list` | — |

## ⛔ HARD LIMITS — These Rules Are Non-Negotiable

1. **NEVER call `bash` after any `tokenomist_*` tool** — the tools return structured data directly. No post-processing with bash needed.
2. **NEVER call `bash` to sum, filter, or sort emission data** — compute from the tool result in memory.
3. **NEVER call more than 3 `tokenomist_*` tools per question** — use `tokenomist_token_overview` for broad questions.
4. **NEVER pass symbol string directly to granular tools** — resolve first, or use tools that auto-resolve.
5. **NEVER use `token_overview` when unlock/cliff/emission keywords present** — use the specific tool instead.

---

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

### ❌ MISTAKE 5: Calling bash after tokenomist tools
```
User: "ARB 本月解锁总量是多少？"
❌ WRONG: tokenomist_daily_emission(token_id="arb") → bash("python3 -c 'import json; ...'")
✅ RIGHT: tokenomist_daily_emission(token_id="arb")  ← sum the values directly from result, no bash
```
**Rule**: tokenomist tools return structured JSON. Sum/filter/sort IN YOUR HEAD. Never spawn bash to process the result.

### ❌ MISTAKE 6: Using token_overview for unlock/cliff-specific questions

**Any question containing unlock/cliff intent → `tokenomist_unlock_events`, never `token_overview`**

```
User: "ARB 下一个 cliff 解锁事件是什么时候？"
❌ WRONG: tokenomist_token_overview(query="ARB")  ← ignores specific intent
✅ RIGHT: tokenomist_resolve_token(query="ARB") → tokenomist_unlock_events(token_id=..., start="today")

User: "APT 的解锁时间表"
❌ WRONG: tokenomist_token_overview(query="APT")
✅ RIGHT: tokenomist_resolve_token(query="APT") → tokenomist_unlock_events(token_id=...)

User: "SUI 什么时候解锁？"
❌ WRONG: tokenomist_token_overview(query="SUI")
✅ RIGHT: tokenomist_resolve_token(query="SUI") → tokenomist_unlock_events(token_id=...)
```

Full keyword list → always triggers `tokenomist_unlock_events`:
- English: unlock, cliff, vesting, lockup, token release, unlock schedule, next unlock, upcoming unlock, lockup expiry, when does X unlock
- Chinese: 解锁, cliff, 解锁时间表, 解锁计划, 什么时候解锁, 下一次解锁, 即将解锁, 锁定到期, 代币释放时间

> **Generalisation note**: Even if the question seems broad ("tell me about ARB unlocks"), as long as "unlock" is in the question, use `tokenomist_unlock_events` — not `token_overview`.

### ❌ MISTAKE 7: Using token_overview then verifying with bash
```
User: "给我 ARB 的 tokenomics 概览"
❌ WRONG: tokenomist_token_overview(query="ARB") → bash("echo checking...") → bash("python3 ...")
✅ RIGHT: tokenomist_token_overview(query="ARB")  ← STOP. Format the result and reply. No bash verification.
```

### ❌ MISTAKE 8: Confusing tokenomist with coingecko for supply data
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
