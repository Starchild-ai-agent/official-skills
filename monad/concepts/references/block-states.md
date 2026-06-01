## Block States

Monad blocks progress through four states. Each maps to a familiar Ethereum JSON-RPC tag:

| State | Description | JSON-RPC Tag |
|-------|-------------|--------------|
| **Proposed** | Leader proposed the block, no votes yet. Speculatively executed. | `"latest"` |
| **Voted** | Supermajority of validators voted affirmatively (Quorum Certificate). | `"safe"` |
| **Finalized** | QC-squared exists — irreversible without a hard fork. | `"finalized"` |
| **Verified** | Delayed merkle root finalized — execution outputs agreed upon by supermajority. | — |

**What this means for developers:**

- Use `"latest"` for fast reads (proposed state, speculative).
- Use `"safe"` for data that has validator backing but could theoretically revert.
- Use `"finalized"` for irreversible actions (e.g. confirming a withdrawal).
- Proposed blocks undergo speculative execution. In rare cases, apps consuming real-time data may see data from blocks that don't become canonical.
- With 400ms block time and 800ms finality, the progression through these states is very fast.

Reference: https://docs.monad.xyz/monad-arch/consensus/block-states
