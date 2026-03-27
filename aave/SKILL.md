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

# Aave V3

Supply tokens to earn yield, withdraw anytime, view positions across chains.

**Chains:** ethereum, arbitrum, base, optimism, polygon, avalanche

**Prerequisite:** Wallet policy must be active. Load **wallet-policy** skill → propose wildcard policy.

## Tools

| Tool | Purpose |
|------|---------|
| `aave_supply(chain, token, amount)` | Approve + supply to pool. Earns yield immediately |
| `aave_withdraw(chain, token, amount?, max?)` | Withdraw (includes earned interest). `max=true` for full |
| `aave_positions(chain)` | View collateral, debt, health factor, LTV |

## Supported Tokens

| Chain | USDC | USDT | DAI | WETH | WBTC |
|-------|------|------|-----|------|------|
| Ethereum/Arbitrum/Polygon/Optimism/Avalanche | ✓ | ✓ | ✓ | ✓ | ✓ |
| Base | ✓ | — | ✓ | ✓ | — |

## Workflows

**Earn yield:** `wallet_balance` → `aave_supply(chain, token, amount)` → `aave_positions(chain)`

**Withdraw:** `aave_positions(chain)` → `aave_withdraw(chain, token, amount)` or `aave_withdraw(chain, token, max=true)`

## Amounts

Human-readable units: `"100"` = 100 USDC, `"0.5"` = 0.5 WETH. Tool handles decimal conversion.

## Positions Output

- **total_collateral_usd** — Supplied assets value
- **total_debt_usd** — Borrowed amount (0 if supply-only)
- **health_factor** — Higher = safer, "infinite" if no debt
- **ltv** — Loan-to-value ratio %

## Errors

| Error | Fix |
|-------|-----|
| Unknown chain/token | Use supported values above |
| Insufficient balance | Check `wallet_balance` first |
| Policy violation | Load wallet-policy skill → propose wildcard |
| Not running on Fly Machine | Requires deployed environment |

**Always ask which chain before proceeding.**
