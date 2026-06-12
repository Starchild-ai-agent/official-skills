---
name: pancakeswap
description: >-
  PancakeSwap on BSC/BNB Chain — CAKE swaps, LP, yield farming, syrup pools, fee collection, PCS Hub.
version: 1.0.0
metadata:
  starchild:
    emoji: "🥞"
    skillKey: pancakeswap
    requires:
      bins:
        - curl
        - jq
      any_bins:
        - node
        - python3
user-invocable: true
disable-model-invocation: false
---

# PancakeSwap Skill Directory

This skill is a directory. Read the specific guide for the user's request using `read_file`.

All guides live under this skill folder, organized into three plugins:

## When to use

PancakeSwap DeFi operations — token swaps, liquidity provision, yield farming,
fee collection, reward harvesting, and PCS Hub integration. Use when the user
mentions PancakeSwap, CAKE, swapping on BSC/BNB Chain, LP positions, farming,
staking, syrup pools, or any PancakeSwap-related DeFi action.

## How to Use

1. Match the user's intent to a guide below
2. `read_file` the corresponding SKILL.md path
3. Follow the instructions in that guide

---

## pancakeswap-driver — Swaps & Liquidity

### swap-planner

> **Path:** `pancakeswap-driver/skills/swap-planner/SKILL.md`

**When to use:** User wants to swap tokens on PancakeSwap — "swap BNB for USDT", "buy CAKE", "exchange tokens", "cross-chain swap", "bridge swap".

**What it does:** Discovers tokens, verifies contracts, fetches prices, generates a `pancakeswap.finance/swap?...` deep link. Does not execute transactions.

### liquidity-planner

> **Path:** `pancakeswap-driver/skills/liquidity-planner/SKILL.md`

**When to use:** User wants to add liquidity — "add liquidity", "LP position", "provide liquidity", "earn yield with my ETH and USDT", "put tokens to work".

**What it does:** Plans LP positions (V2, V3, StableSwap, Infinity), recommends fee tiers and price ranges, assesses impermanent loss risk, generates add-liquidity deep links.

### collect-fees

> **Path:** `pancakeswap-driver/skills/collect-fees/SKILL.md`

**When to use:** User asks about uncollected LP fees — "collect my fees", "pending fees", "how much fees have I earned", "claim LP fees".

**What it does:** Checks uncollected fees across V3, Infinity, and Solana CLMM positions. Generates collection deep links.

**Reference scripts:** `collect-fees/references/` — fetch-v3-positions.mjs, fetch-infinity-positions.mjs, fetch-solana.cjs

### swap-integration

> **Path:** `pancakeswap-driver/skills/swap-integration/SKILL.md`

**When to use:** Developer wants to integrate PancakeSwap swaps into an app — "integrate swaps", "Smart Router SDK", "Universal Router", "build swap frontend", "swap script".

**What it does:** SDK integration guide with working code for Smart Router, Universal Router, and direct V2 Router contract calls.

**Shared utilities:** `pancakeswap-driver/skills/common/` — discover-pools.mjs, pool-apr.mjs, protocol-fee.mjs, farm-apr.py, token-lists.md

---

## pancakeswap-farming — Farms & Staking

### farming-planner

> **Path:** `pancakeswap-farming/skills/farming-planner/SKILL.md`

**When to use:** User wants to farm or stake — "farm on PancakeSwap", "stake CAKE", "unstake CAKE", "yield farming", "syrup pool", "best farm APR", "deposit LP", "withdraw LP".

**What it does:** Discovers active farms, compares APR/APY, plans CAKE staking in Syrup Pools, generates farming UI deep links.

**Note:** If the user has a specific token pair and asks about yield, use `liquidity-planner` instead.

**Reference scripts:** `farming-planner/references/` — fetch-farms.py, fetch-syrup-pools.py

### harvest-rewards

> **Path:** `pancakeswap-farming/skills/harvest-rewards/SKILL.md`

**When to use:** User wants to claim rewards — "harvest rewards", "claim CAKE", "pending rewards", "how much can I harvest", "collect farming rewards".

**What it does:** Checks pending CAKE and partner-token rewards across V2, V3, Infinity farms and Syrup Pools. Generates harvest deep links.

**Reference scripts:** `harvest-rewards/references/` — fetch-v3-pending.py, fetch-infinity-pending.py, fetch-syrup-pending.py

---

## pancakeswap-hub — PCS Hub Distribution

### hub-swap-planner

> **Path:** `pancakeswap-hub/skills/hub-swap-planner/SKILL.md`

**When to use:** User wants to swap via PCS Hub — "PCS Hub swap", "swap via Binance Wallet", "swap via Trust Wallet", "hub route".

**What it does:** Fetches optimal routing via PCS Hub aggregator API, generates channel-specific handoff links. BSC only.

### hub-api-integration

> **Path:** `pancakeswap-hub/skills/hub-api-integration/SKILL.md`

**When to use:** Developer wants to embed PCS Hub — "integrate PCS Hub", "embed PCS Hub swap", "Hub integration spec", "add PCS Hub to my wallet app".

**What it does:** Integration spec with API contracts, frontend state machine, allowance checking, and quote TTL management.

**Shared utilities:** `pancakeswap-hub/skills/common/` — token-lists.md

---

## Supported Chains

| Chain           | ID    | V2 | V3 | Infinity | StableSwap |
|-----------------|-------|----|----|----------|------------|
| BNB Smart Chain | 56    | +  | +  | +        | +          |
| Ethereum        | 1     | +  | +  | -        | +          |
| Arbitrum One    | 42161 | +  | +  | -        | +          |
| Base            | 8453  | +  | +  | +        | -          |
| zkSync Era      | 324   | +  | +  | -        | -          |
| Linea           | 59144 | +  | +  | -        | -          |
| opBNB           | 204   | +  | +  | -        | -          |
| Monad           | 143   | +  | +  | -        | -          |

## Resources

- App: https://pancakeswap.finance/
- Dev Docs: https://developer.pancakeswap.finance/
- BSCScan: https://bscscan.com/
- Smart Router SDK: `@pancakeswap/smart-router`
- Universal Router SDK: `@pancakeswap/universal-router-sdk`
