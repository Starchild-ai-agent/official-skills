---
name: ethena
version: 1.0.0
description: "Ethena protocol integration — stake USDe for sUSDe yield, unstake with cooldown, check staking rates. Use when user mentions Ethena, USDe, sUSDe, or wants stablecoin yield."

metadata:
  starchild:
    emoji: "🟣"
    skillKey: ethena

user-invocable: true
---

# Ethena — USDe Staking

Ethena lets users stake USDe to receive sUSDe, an ERC4626 yield-bearing token. Rewards accrue from ETH staking + funding rate delta-hedging. sUSDe value only increases or stays flat — never decreases.

## Prerequisites — Wallet Policy

Before any on-chain operation, load the **wallet-policy** skill and propose the standard wildcard policy (deny key export + allow `*`).

## Key Contracts (Ethereum Mainnet)

| Contract | Address |
|----------|---------|
| USDe | `0x4c9EDD5852cd905f086C759E8383e09bff1E68B3` |
| sUSDe (StakedUSDe) | `0x9D39A5DE30e57443BfF2A8307A4256c8797A3497` |
| USDeSilo (cooldown) | `0x7FC7c91D556B400AFa565013E3F32055a0713425` |
| Staking Rewards Distributor | `0xf2fa332BD83149c66b09B45670bCe64746C6b439` |

## How Staking Works

1. **Stake**: Transfer USDe → sUSDe contract → receive sUSDe shares (ERC4626 `deposit`)
2. **Yield**: Protocol transfers USDe rewards every 8h, linearly vested over 8h (anti-sandwich)
3. **Unstake**: Burn sUSDe → 7-day cooldown → USDe sent to USDeSilo → withdraw after cooldown

sUSDe/USDe exchange rate only goes up. No minimum staking period. Rewards = staked ETH yield + funding/basis spread.

## Operations

### Check sUSDe Rate

Read `totalAssets()` and `totalSupply()` on the sUSDe contract to get the current exchange rate:

```python
# rate = totalAssets / totalSupply
# Example: if totalAssets=1.05B USDe and totalSupply=1B sUSDe → 1 sUSDe = 1.05 USDe
```

Use `web_fetch` to query Etherscan or use the script in `scripts/ethena_ops.py`.

### Stake USDe → sUSDe

Two transactions required:
1. **Approve** USDe spend by sUSDe contract
2. **Deposit** via ERC4626 `deposit(assets, receiver)`

```
# Step 1: Approve USDe
wallet_transfer(
    to="0x4c9EDD5852cd905f086C759E8383e09bff1E68B3",  # USDe
    amount="0",
    chain_id=1,
    data=<approve calldata for sUSDe address>
)

# Step 2: Deposit
wallet_transfer(
    to="0x9D39A5DE30e57443BfF2A8307A4256c8797A3497",  # sUSDe
    amount="0",
    chain_id=1,
    data=<deposit(amount, receiver) calldata>
)
```

Use `scripts/ethena_ops.py` to generate the correct calldata.

### Unstake sUSDe → USDe

1. Call `cooldownAssets(assets)` or `cooldownShares(shares)` on sUSDe — starts 7-day cooldown
2. After cooldown: call `unstake(receiver)` on sUSDe to receive USDe from USDeSilo

### Check Balance

```
wallet_balance(chain="ethereum")  # Check USDe and sUSDe balances
```

## Gotchas

- **7-day cooldown** on unstaking — user must wait. Check `cooldownEnd` in the contract.
- **No negative rewards** — sUSDe value can only go up or stay flat.
- **Rewards every 8h** — linearly vested, so no sandwich opportunities.
- sUSDe can be sold on DEXes without cooldown if liquidity exists.
- **EU/EEA restriction** — sUSDe acquisition not offered in EU/EEA.
