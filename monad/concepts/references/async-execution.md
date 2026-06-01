## Asynchronous Execution

Monad decouples consensus from execution. Nodes agree on transaction ordering without executing transactions first. Execution runs in parallel with consensus rather than blocking it.

**What this means for developers:**

- Consensus operates with a **3-block delayed state view** (`D=3`). The state root included in a block is from 3 blocks prior.
- **Newly funded accounts cannot send transactions until their funding transfer is `D` blocks old** (~1.2 seconds after the transaction is included). This is because consensus validates gas budgets against the delayed state, and the funding won't be visible yet.
- **Workaround:** Use a smart contract to atomically combine funding and spending in a single transaction, bypassing the delay.
- Despite the lag, the true state is deterministic as soon as ordering is determined — execution simply catches up.
- `eth_call` and `eth_estimateGas` simulate against speculatively executed state, so they return accurate results even though execution technically lags consensus.

Reference: https://docs.monad.xyz/monad-arch/consensus/asynchronous-execution
