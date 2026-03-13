---
name: aave
version: 1.0.0
description: Supply and withdraw tokens on Aave V3 lending pools
tools:
  - aave_supply
  - aave_withdraw
  - aave_positions
metadata:
  starchild:
    emoji: "🏦"
    skillKey: aave
    requires:
      env: [WALLET_SERVICE_URL]
user-invocable: true
disable-model-invocation: false
---

# Aave V3 Yield Farming

Supply tokens into Aave V3 lending pools to earn yield, withdraw at any time, and view positions across multiple chains.

**Supported Networks:** Ethereum, Arbitrum, Base, Optimism, Polygon, Avalanche.

**IMPORTANT:** All tools require a `chain` parameter. Always ask the user which network they want to use before proceeding. Do not assume a default chain.

## Prerequisites — Wallet Policy

Before executing supply or withdraw transactions, the wallet policy must be active. Load the **wallet-policy** skill and propose the standard wildcard policy (deny key export + allow `*`). This covers all Aave operations — token approvals, supply, and withdraw — across all chains.

## Available Tools (3)

| Tool | Type | Description |
|------|------|-------------|
| `aave_supply` | Write | Approve + supply tokens to Aave V3 pool. Earns yield immediately. |
| `aave_withdraw` | Write | Withdraw tokens from Aave V3 pool (includes earned interest). |
| `aave_positions` | Read-only | View account data: collateral, debt, health factor, LTV. |

## Supported Tokens by Chain

| Chain | USDC | USDT | DAI | WETH | WBTC |
|-------|------|------|-----|------|------|
| Ethereum | yes | yes | yes | yes | yes |
| Arbitrum | yes | yes | yes | yes | yes |
| Polygon | yes | yes | yes | yes | yes |
| Optimism | yes | yes | yes | yes | yes |
| Avalanche | yes | yes | yes | yes | yes |
| Base | yes | — | yes | yes | — |

## Decision Tree

```
User wants to earn yield on tokens?
  → Use aave_supply

User wants to check current positions?
  → Use aave_positions

User wants to withdraw (partial or full)?
  → Use aave_withdraw (set max=true for full withdrawal)
```

## Tool Usage Examples

### Supply 100 USDC on Arbitrum

```
aave_supply(chain="arbitrum", token="USDC", amount="100")
```

### Withdraw 50 USDC from Arbitrum

```
aave_withdraw(chain="arbitrum", token="USDC", amount="50")
```

### Withdraw all WETH from Ethereum

```
aave_withdraw(chain="ethereum", token="WETH", max=true)
```

### Check positions on Arbitrum

```
aave_positions(chain="arbitrum")
```

## Common Workflows

**Step 0 for all workflows:** If the wallet policy is not yet active, load the wallet-policy skill and propose the standard wildcard policy before proceeding.

### Earn yield on stablecoins

1. **Check balance:** `wallet_balance` to verify token holdings
2. **Supply:** `aave_supply(chain="arbitrum", token="USDC", amount="100")`
3. **Verify:** `aave_positions(chain="arbitrum")` — should show collateral

### Check and withdraw

1. **View positions:** `aave_positions(chain="arbitrum")`
2. **Withdraw partial:** `aave_withdraw(chain="arbitrum", token="USDC", amount="50")`
3. **Or withdraw all:** `aave_withdraw(chain="arbitrum", token="USDC", max=true)`

## Amount Formatting

Amounts are in **human-readable units** (not wei):
- `"100"` = 100 USDC
- `"0.5"` = 0.5 WETH
- `"1.5"` = 1.5 WBTC

The tool handles decimal conversion internally based on the token's decimals.

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `Unknown chain` | Invalid chain name | Use: ethereum, arbitrum, base, optimism, polygon, avalanche |
| `Unknown token` | Token not available on that chain | Check supported tokens table above |
| `Insufficient balance` | Not enough tokens in wallet | Check balance with `wallet_balance` first |
| `Amount must be positive` | Zero or negative amount | Use a positive number |
| `Policy violation` | Wallet policy blocks the transaction | Load wallet-policy skill and propose wildcard policy |
| `Not running on a Fly Machine` | Local dev environment | Supply/withdraw require deployed environment with wallet |

## Positions Output Explained

`aave_positions` returns:
- **total_collateral_usd** — Total value of supplied assets (USD)
- **total_debt_usd** — Total borrowed amount (USD). Will be 0 if you only supply.
- **available_borrows_usd** — How much more you could borrow (USD)
- **health_factor** — Ratio of collateral to debt. Higher = safer. "infinite" if no debt.
- **ltv** — Loan-to-value ratio (percentage)
- **current_liquidation_threshold** — Collateral ratio at which liquidation occurs (percentage)
