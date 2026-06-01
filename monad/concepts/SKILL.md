---
name: concepts
description: Monad architecture concepts that affect how developers build apps — async execution, parallel execution, block states, reserve balance, EIP-7702, real-time data sources, and execution events. Fetch this skill when the developer needs to understand Monad-specific behavior that differs from Ethereum.
---

Monad is Ethereum-compatible but its architecture introduces behaviors that developers must understand. Only fetch the references relevant to the task at hand.

## What to Fetch by Task

| I'm dealing with... | Fetch |
|----------------------|-------|
| Newly funded accounts can't send transactions, funding delays | [async-execution.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/concepts/references/async-execution.md) |
| Whether existing Solidity contracts need changes for Monad | [parallel-execution.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/concepts/references/parallel-execution.md) |
| Choosing between `latest`, `safe`, `finalized` block tags | [block-states.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/concepts/references/block-states.md) |
| Transaction reverts due to low balance, 10 MON floor, emptying transactions | [reserve-balance.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/concepts/references/reserve-balance.md) |
| Smart wallet delegation, EIP-7702, session keys, gas sponsorship | [eip-7702.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/concepts/references/eip-7702.md) |
| Subscribing to events, WebSocket feeds, high-throughput data ingestion | [realtime-data.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/concepts/references/realtime-data.md) |
| Block lifecycle events, speculative data, BLOCK_START/QC/FINALIZED | [execution-events.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/concepts/references/execution-events.md) |

## Quick Summary

- **Async execution:** Consensus and execution are decoupled. 3-block delayed state view. Newly funded accounts need ~1.2s before sending txs.
- **Parallel execution:** Optimistic concurrency — identical results to Ethereum. No contract changes needed.
- **Block states:** Proposed → Voted → Finalized → Verified. Maps to `latest` / `safe` / `finalized`.
- **Reserve balance:** 10 MON floor per EOA. Low-balance accounts limited to 1 tx per ~1.2s.
- **EIP-7702:** EOAs delegate to contracts for smart wallet features. 10 MON floor applies. No CREATE/CREATE2 in delegated context.
- **Real-time data:** 3 sources — Geth-compatible WS, Monad extended WS, Execution Events SDK. Most apps use source 1.
- **Execution events:** Consensus events track block state transitions. Execution events are speculative EVM traces.
