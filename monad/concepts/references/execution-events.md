## Execution Events and Consensus Events

Monad emits two categories of events through its real-time data feeds:

**Consensus events** announce block state transitions:
- `BLOCK_START` — Block execution begins (Proposed state). Includes block tag, round, epoch.
- `BLOCK_QC` — Block received a quorum certificate (Voted state).
- `BLOCK_FINALIZED` — Block is finalized (irreversible).
- `BLOCK_VERIFIED` — State root verified by supermajority.

**Execution events** are EVM trace data (logs, state changes) emitted during block processing. They are **speculative** — the block they belong to might not become canonical.

**What this means for developers:**

- If consuming real-time data, always track consensus events to know which block state you're seeing.
- Data from `BLOCK_START` is speculative. Only treat data as final after `BLOCK_FINALIZED`.
- Block identification requires both a consensus ID and proposed block number (communicated via "block tags").

Reference: https://docs.monad.xyz/execution-events/consensus-events
