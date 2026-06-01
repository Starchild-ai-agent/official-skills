## Parallel Execution

Monad executes transactions in parallel using optimistic concurrency control, but the **final result is identical to sequential Ethereum execution**. Transaction ordering within a block is preserved.

**What this means for developers:**

- **No code changes required.** Existing Solidity contracts work as-is. The execution semantics are identical to Ethereum.
- Monad starts executing transactions optimistically before predecessors complete. It tracks reads and compares them against prior writes. If a conflict is detected, the transaction is re-executed with correct state.
- Expensive computations like signature recovery and state lookups are cached, so re-execution overhead is minimal.
- Contracts that touch frequently-updated storage slots (e.g. a single global counter) may cause more re-executions, but this is handled transparently — it only affects node performance, not correctness.

Reference: https://docs.monad.xyz/monad-arch/execution/parallel-execution
