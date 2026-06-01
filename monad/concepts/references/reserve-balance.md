## Reserve Balance

Reserve balance is a safety mechanism that prevents transactions from failing due to insufficient gas in the asynchronous execution model. It sets a **10 MON floor** per EOA.

**What this means for developers:**

- **Most apps won't be affected.** This only matters for accounts with low MON balances.
- Transactions revert if an account's ending balance (before gas refunds) drops below `min(starting_balance, 10 MON)`.
- **Low-balance accounts** (below 10 MON) can only send one transaction every 3 blocks (~1.2 seconds).
- An **emptying transaction** exception exists: undelegated accounts that sent no other transactions in the past 3 blocks can spend below the reserve. This allows users to fully withdraw their balance.
- **EIP-7702 delegated accounts cannot use the emptying exception** — they are always subject to the 10 MON floor when their balance decreases.
- For transaction senders, consensus enforces a cumulative gas budget across all inflight transactions (past 3 blocks): `min(10 MON, lagged_state_balance)`.

Reference: https://docs.monad.xyz/developer-essentials/reserve-balance
