---
name: tooling-and-infra
description: Monad tooling and infrastructure provider support directory. Use this skill whenever a developer asks which tools, services, or infrastructure providers support Monad (mainnet or testnet), or needs to find an RPC provider, block explorer, oracle, bridge, indexer, wallet, onramp, custody solution, analytics tool, toolkit, or wallet infrastructure provider for Monad. Also use when a developer asks "does X support Monad?" or "what providers are available for Y on Monad?". Covers all categories from the official Monad docs tooling page.
---

# Monad Tooling & Infrastructure

Quick reference for which tooling and infrastructure providers support Monad mainnet, testnet, or both.

## How to use this skill

1. If the developer asks about a **specific provider** (e.g. "does Alchemy support Monad?"), search the reference files below for that provider name.
2. If the developer asks about a **category** (e.g. "what oracles support Monad testnet?"), read the relevant reference file and filter by network.

## Categories

Each category has a reference file with the full provider list, network support, and documentation links. Read only the file(s) relevant to the developer's question.

| Category | Reference File | What it covers |
|----------|---------------|----------------|
| Analytics | [analytics.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/tooling-and-infra/references/analytics.md) | On-chain monitoring, portfolio tracking, DeFi analytics, dashboards |
| Block Explorers | [block-explorers.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/tooling-and-infra/references/block-explorers.md) | Transaction explorers, contract verification, UserOp explorers |
| Cross-Chain | [cross-chain.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/tooling-and-infra/references/cross-chain.md) | Bridges, bridge aggregators, liquidity layers, AMBs, chain abstraction |
| Custody | [custody.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/tooling-and-infra/references/custody.md) | Institutional-grade custody solutions |
| Indexers | [indexers.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/tooling-and-infra/references/indexers.md) | Common data APIs and indexing frameworks (subgraphs, data pipelines) |
| Onramps | [onramps.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/tooling-and-infra/references/onramps.md) | Fiat-to-crypto conversion, payment gateways |
| Oracles | [oracles.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/tooling-and-infra/references/oracles.md) | Price feeds, VRF, data feeds |
| RPC Providers | [rpc-providers.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/tooling-and-infra/references/rpc-providers.md) | RPC endpoints for interacting with Monad |
| Toolkits | [toolkits.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/tooling-and-infra/references/toolkits.md) | Development frameworks (Foundry, Hardhat) |
| Wallets | [wallets.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/tooling-and-infra/references/wallets.md) | Software wallets, hardware wallets, institutional wallets, multisig wallets |
| Wallet Infrastructure | [wallet-infra.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/tooling-and-infra/references/wallet-infra.md) | Embedded wallets, account abstraction, smart accounts |

## Quick lookup: Provider to category

If the developer names a provider and you're not sure which category it falls under, here's a quick cross-reference of commonly asked-about providers:

- **Alchemy** — RPC Providers, Embedded Wallets, Account Abstraction
- **thirdweb** — RPC Providers, Embedded Wallets, Account Abstraction, Indexers (Common Data)
- **Sequence** — Embedded Wallets, Account Abstraction, Indexers (Common Data)
- **Quicknode** — RPC Providers, Indexers (Common Data)
- **Tenderly** — Analytics, Block Explorers (Transaction Analyzer)
- **Goldsky** — Indexers (Common Data), Indexing Frameworks
- **Chainlink** — Oracles, Cross-Chain (CCIP)
- **Pimlico** — Account Abstraction, Smart Accounts
- **ZeroDev** — Account Abstraction, Smart Accounts
- **Biconomy** — Account Abstraction, Smart Accounts
- **Phantom** — Software Wallets, Embedded Wallets
- **MetaMask** — Software Wallets, Embedded Wallets, Smart Accounts
- **Safepal** — Software Wallets, Hardware Wallets
- **Coinbase** — Onramps, Custody, Embedded Wallets

## Important notes

- Provider support can change. If the developer needs certainty, suggest they check the provider's own docs or the official Monad docs page.
- Some providers listed as mainnet-only may add testnet support later (and vice versa).
- "Pending" status (marked with a clock icon) means the provider has announced support but it's not yet live.
