---
name: gas
description: How gas pricing works on Monad and how it differs from Ethereum. Monad charges gas based on gas_limit (not gas used), has a different base fee controller, and different block gas limits. Fetch this skill whenever writing smart contracts, setting gas limits, estimating gas, or building any transaction-related UI on Monad incorrect gas handling can cost users real money.
---

Monad's gas pricing is EIP-1559 compatible but differs from Ethereum in critical ways. If you're building apps that submit transactions, estimate gas, or display gas costs, you need to understand these differences.

## Key Difference: Monad Charges on Gas Limit, Not Gas Used

On Ethereum, users pay for the gas actually consumed by their transaction. On Monad, users pay based on the **gas limit** they set:

```
gas_paid = gas_limit * price_per_gas
```

This exists because Monad uses asynchronous execution — block leaders build blocks before executing them, so actual gas consumption isn't known at inclusion time. This prevents DOS attacks where transactions claim cheap gas but consume expensive computation.

**What this means for developers:**

- Setting an unnecessarily high gas limit directly costs users more MON.
- Always set tight, accurate gas limits especially for transactions with known fixed costs.
- For native MON transfers, the gas cost is always 21,000. Hardcode this instead of relying on `eth_estimateGas`.

## EIP-1559 Transaction Pricing

Monad uses type 2 (EIP-1559) transactions:

```
price_per_gas = min(base_price_per_gas + priority_price_per_gas, max_price_per_gas)
```

Users specify two values when signing:
- `priority_price_per_gas` — tip for transaction prioritization within a block
- `max_price_per_gas` — safety cap on total gas price

The network controls `base_price_per_gas`, which is the same for all transactions in a block.

## Block and Transaction Limits

| Parameter | Value |
|-----------|-------|
| Block gas limit | 200M gas |
| Transaction gas limit | 30M gas |
| Minimum base fee | 100 MON-gwei (100 x 10^-9 MON) |

These are significantly higher than Ethereum's 30M block gas limit, which means Monad blocks can fit more transactions.

## Base Fee Controller

Monad's base fee controller is different from Ethereum's. It **increases more slowly and decreases more quickly** to prevent blockspace underutilization from overpricing.

**Controller parameters:**
- max_step_size = 1/28
- target = 160M gas (80% of block capacity)
- beta = 0.96
- epsilon = 160M

The base fee updates each block using an exponential adjustment based on how full the block was relative to the target. The formula uses exponential smoothing (beta = 0.96) to track historical variance in block fullness, producing smoother fee transitions than Ethereum's simpler mechanism.

In practice, this means gas prices on Monad are more stable and recover faster after spikes.

## Transaction Ordering

The default Monad client orders transactions using a **Priority Gas Auction**, transactions are sorted by descending total gas price (base fee + priority fee).

## Developer Guidelines

### Always Set Explicit Gas Limits for Known Costs

For operations with fixed gas costs, set the gas limit explicitly before submitting to wallets:

```typescript
// Good: explicit gas limit for a native transfer
const tx = {
  to: recipient,
  value: parseEther("1.0"),
  gasLimit: 21000n,
};
```

This is important because some wallets (like MetaMask) use `eth_estimateGas` to determine the gas limit. If that call reverts (e.g., the contract call would fail), the wallet may fall back to a very high gas limit. On Monad, the user would then pay for that entire inflated limit since **gas is charged on the limit, not on actual usage**.

### Gas Estimation in Frontend Code

When using viem or wagmi to estimate gas, remember that the estimate is what users will actually pay not a lower bound. Add only a small buffer if needed:

```typescript
// If you must estimate, keep the buffer small
const estimate = await publicClient.estimateGas({ ... });
const gasLimit = estimate + (estimate / 10n); // 10% buffer at most
```

### Displaying Gas Costs to Users

When showing gas costs in your UI, calculate from the gas limit (not "gas used" from receipts on other chains):

```typescript
const gasCost = gasLimit * gasPrice;
```

### Smart Contract Considerations

- Monad's 30M transaction gas limit is the same as Ethereum's block gas limit, so individual transactions can be very large.
- Optimize your contracts to use less gas on Monad this directly saves users money since they pay for the limit, and tighter estimates mean tighter limits.
- If your contract has functions with predictable gas costs, document them so frontends can set explicit limits.

## Opcode Pricing Differences

Monad adjusts a few opcode prices **upward** rather than discounting everything. This achieves the same relative effect with minimal disruption. The changes reflect different resource scarcity in Monad's high-performance architecture, particularly for disk-based state operations.

### Cold State Access is Much More Expensive

| Operation | Ethereum | Monad | Increase |
|-----------|----------|-------|----------|
| Account access (cold) | 2,600 gas | 10,100 gas | +7,500 |
| Storage access (cold) | 2,100 gas | 8,100 gas | +6,000 |
| Account access (warm) | 100 gas | 100 gas | unchanged |
| Storage access (warm) | 100 gas | 100 gas | unchanged |

**Affected opcodes:**
- Account access: `BALANCE`, `EXTCODESIZE`, `EXTCODECOPY`, `EXTCODEHASH`, `CALL`, `CALLCODE`, `DELEGATECALL`, `STATICCALL`, `SELFDESTRUCT`
- Storage access: `SLOAD`, `SSTORE`

**What this means for developers:**
- Contracts that touch many cold storage slots or call many external contracts will cost significantly more on Monad.
- Warm access is identical to Ethereum, so accessing the same slot/account repeatedly within a transaction has no extra cost.
- Batch operations that access a storage slot once (cold) and then reuse it (warm) are fine. But patterns that do single cold reads across many different slots will be more expensive.
- If your contract reads from many different storage slots in a single call, the gas estimate will be higher on Monad. Account for this when setting gas limits.

### Precompile Repricing

Cryptographic precompiles cost 2-5x more on Monad:

| Precompile | Address | Ethereum | Monad | Multiplier |
|------------|---------|----------|-------|------------|
| ecRecover | 0x01 | 3,000 | 6,000 | 2x |
| ecAdd | 0x06 | 150 | 300 | 2x |
| ecMul | 0x07 | 6,000 | 30,000 | 5x |
| ecPairing | 0x08 | 45,000 | 225,000 | 5x |
| blake2f | 0x09 | rounds x 1 | rounds x 2 | 2x |
| point evaluation | 0x0a | 50,000 | 200,000 | 4x |

**What this means for developers:**
- Contracts relying heavily on signature verification (`ecRecover`) will use 2x the gas for those operations.
- ZK-related operations (`ecMul`, `ecPairing`, point evaluation) are 4-5x more expensive. If your contract does on-chain ZK proof verification, gas estimates from Ethereum will be significantly off.
- Factor these higher precompile costs into gas limit calculations if your contract uses them.