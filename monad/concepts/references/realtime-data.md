## Real-Time Data Sources

Monad's high throughput (~10,000 tps) makes traditional JSON-RPC polling impractical. Three real-time data sources are available:

### 1. Geth-Compatible WebSocket Events
- Standard `eth_subscribe` with `newHeads` and `logs`.
- Data publishes at **Proposed** state.
- Available via third-party RPC providers (Alchemy, QuickNode, etc.).
- Best for: apps migrating from Ethereum with minimal changes.

### 2. Monad Extended WebSocket Events
- `monadNewHeads` and `monadLogs` subscriptions.
- Data publishes at **Proposed** state (earlier than standard).
- Includes consensus progression tracking.
- Best for: apps that need the lowest latency and can handle speculative data.

### 3. Execution Events SDK (C/C++/Rust)
- Transaction-level granularity with logs, call frames, and state reads/writes.
- Fastest option — powers the other two sources internally.
- Requires running a custom program on the same host as a Monad node.
- Best for: indexers, analytics, MEV, and high-performance infrastructure.

**Which to choose:**
- Most app developers should use **Source 1** (Geth-compatible) via their RPC provider.
- Use **Source 2** if you need earlier data and understand speculative execution.
- Use **Source 3** only if you run your own node and need maximum performance.

Reference: https://docs.monad.xyz/monad-arch/realtime-data/data-sources
