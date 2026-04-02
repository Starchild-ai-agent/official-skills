---
name: morpho
version: 1.0.0
description: "Morpho protocol integration — deposit into yield vaults, borrow against collateral, query market data via GraphQL API. Use when user mentions Morpho, Morpho vaults, or wants DeFi lending/borrowing on Ethereum/Base."

metadata:
  starchild:
    emoji: "🦋"
    skillKey: morpho

user-invocable: true
---

# Morpho — Lending & Yield Vaults

Morpho provides isolated lending markets and managed ERC4626 vaults across Ethereum, Base, Arbitrum, and other EVM chains. Two main products: **Earn** (deposit into curated vaults) and **Borrow** (collateralized lending).

## Prerequisites — Wallet Policy

Before any on-chain operation, load the **wallet-policy** skill and propose the standard wildcard policy (deny key export + allow `*`).

## Architecture

- **Morpho Markets** — Isolated lending pools with specific collateral/loan asset pairs, oracles, and IRMs
- **Morpho Vaults** — ERC4626 vaults managed by curators that allocate across multiple markets
- **Bundlers** — Batch multiple operations (approve + deposit) in a single tx
- **Public Allocator** — JIT liquidity reallocation across markets

## Key Contracts (Ethereum)

| Contract | Address |
|----------|---------|
| Morpho Core V2 | `0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb` |
| Bundler V2 | `0x4095F064B8D3c3548A3BeBfD0bBfD04750E30077` |
| Example USDC Vault | `0xBEEF01735c132Ada46AA9aA4c54623cAA92A64CB` |

Vault addresses vary — query the GraphQL API to find vaults by asset, APY, or curator.

## GraphQL API

**Endpoint**: `https://api.morpho.org/graphql`
Rate limit: 5000 requests / 5 minutes. No API key required.

### Find Vaults

```graphql
query {
  vaults(first: 10, orderBy: TotalAssetsUsd, orderDirection: Desc, where: { chainId_in: [1] }) {
    items {
      address
      name
      symbol
      asset { symbol decimals address }
      state {
        totalAssetsUsd
        apy
        netApy
        fee
      }
      metadata { curators { name } }
    }
  }
}
```

### Get User Position

```graphql
query {
  vaultPositions(where: { userAddress: "0x...", chainId: 1 }) {
    items {
      vault { address name asset { symbol } }
      supplyAssets
      supplyAssetsUsd
    }
  }
}
```

### Find Markets (for borrowing)

```graphql
query {
  markets(first: 10, orderBy: SupplyAssetsUsd, orderDirection: Desc, where: { chainId_in: [1] }) {
    items {
      uniqueKey
      loanAsset { symbol address }
      collateralAsset { symbol address }
      state {
        supplyAssetsUsd
        borrowAssetsUsd
        utilization
        supplyApy
        borrowApy
      }
      lltv
    }
  }
}
```

Use `scripts/morpho_ops.py` for data queries and calldata generation.

## Operations

### Deposit into Vault (Earn)

Morpho Vaults are standard ERC4626. Two transactions:

1. **Approve** the underlying asset for the vault
2. **Deposit** via `deposit(assets, receiver)`

```
# Step 1: Approve (e.g., USDC for a USDC vault)
wallet_transfer(to=<asset_address>, amount="0", chain_id=1, data=<approve calldata>)

# Step 2: Deposit into vault
wallet_transfer(to=<vault_address>, amount="0", chain_id=1, data=<deposit calldata>)
```

### Withdraw from Vault

Standard ERC4626 `withdraw(assets, receiver, owner)` or `redeem(shares, receiver, owner)`.

### Borrow (Supply Collateral + Borrow)

Requires direct Morpho Core interaction:
1. `supplyCollateral(marketParams, assets, onBehalf, data)` 
2. `borrow(marketParams, assets, shares, onBehalf, receiver)`

This is more complex — use the bundler for atomic multi-step operations.

## Gotchas

- **Vault addresses are NOT fixed** — always query API to find vaults. The example USDC vault above may change.
- **Bundlers** allow atomic approve+deposit but require multicall encoding.
- **Chain support**: Ethereum (1), Base (8453), Arbitrum (42161), Polygon (137), OP Mainnet (10), and many more.
- **No minimum deposit** for vaults. Withdrawals may fail if liquidity is fully utilized — check utilization first.
- **Permit support**: Many assets (USDC, DAI) support EIP-2612 permit for gasless approval.
