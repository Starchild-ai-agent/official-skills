---
name: abstract
version: 1.0.2
description: "Abstract L2 — Master skill hub for all Abstract blockchain capabilities. Provides a directory of 7 specialized skills for building on Abstract: connecting, deploying contracts, wallet integration, agent wallets, multisig, prediction markets, and onchain agent identity. Use when the user wants to build on Abstract, deploy contracts, set up wallets, create multisigs, integrate prediction markets, register agents onchain, or any Abstract L2 development task."
metadata:
  starchild:
    emoji: "🔷"
    skillKey: abstract
user-invocable: true
disable-model-invocation: false
---

# Abstract L2 — Skills Directory

Abstract is an Ethereum Layer 2 ZK rollup (ZK Stack) focused on consumer crypto applications. This master skill provides a directory of all Abstract-related capabilities and helps you pick the right one.

![Abstract](assets/logo.png)

---

## Skills by Category

### 🔗 Infrastructure & Setup

#### 1. connecting-to-abstract
Network configuration — chain IDs, RPC endpoints, WebSocket URLs, block explorers, and deployed contract addresses for Abstract mainnet and testnet.

**Use when:** Configuring clients, wallets, or dev environments. Questions about Abstract RPC URLs, chain IDs (2741/11124), testnet config, Abscan explorer, or importing `abstract`/`abstractTestnet` from `viem/chains`.

**Key info:**
| Property | Mainnet | Testnet |
|----------|---------|---------|
| Chain ID | `2741` | `11124` |
| Explorer | https://abscan.org | https://sepolia.abscan.org |

---

#### 2. deploying-contracts-on-abstract
Deploy smart contracts using Foundry (default) or Hardhat. Covers `zksolc` compilation, deployment, Abscan verification, and testnet faucets.

**Use when:** Deploying or compiling contracts on Abstract, using `forge build --zksync`, `forge create --zksync`, anvil-zksync, or working with the zkSync compiler.

**Key note:** Abstract uses ZK Stack VM — must compile with `zksolc`, not standard `solc`. All `forge` commands need `--zksync` flag. Compiled output goes to `zkout/`.

---

### 💰 Wallets & Transactions

#### 3. abstract-global-wallet
Integrate Abstract Global Wallet (AGW) into React applications — email/social/passkey login, smart contract wallet, session keys, gas sponsorship.

**Use when:** Building a React app where end users log in and transact. Working with `AbstractWalletProvider`, `useLoginWithAbstract`, `useAbstractClient`, `useWriteContractSponsored`, `agw-react`, `agw-client`, or `create-abstract-app`.

**Quick start:** `npx @abstract-foundation/create-abstract-app@latest my-app`

---

#### 4. using-agw-mcp
AI agent wallet capabilities via the Abstract Global Wallet MCP server — read chain data, check balances, and send transactions on behalf of users.

**Use when:** Setting up `agw-mcp` for AI agent access to Abstract, giving agents wallet capabilities, or building MCP-powered agent workflows that interact with Abstract chain data.

**Decision guide:**
| Scenario | Use |
|----------|-----|
| End-user facing React app with login | `abstract-global-wallet` |
| AI agent needs to read/transact on-chain | `using-agw-mcp` |

---

#### 5. safe-multisig-on-abstract
Safe multi-signature wallets — deploy Safes, configure owners and thresholds, propose and execute multi-sig transactions.

**Use when:** Creating multisig wallets on Abstract, managing shared custody (treasury, team, DAO), working with Safe Protocol Kit, SafeL2, SafeProxyFactory, or the [safe.abs.xyz](https://safe.abs.xyz) web interface.

---

### 📡 Protocols & Identity

#### 6. myriad-on-abstract
Myriad Protocol prediction markets — REST API for market data, polkamarkets-js SDK for trading outcome shares, builder revenue sharing via referralBuy.

**Use when:** Working with Myriad API, prediction markets on Abstract, trading/buying/selling prediction shares, builder codes, referralBuy, claiming winnings, or Myriad contract addresses.

**Architecture:**
| Layer | Tool | Use For |
|-------|------|---------|
| Read-only data | REST API V2 | Market listings, prices, charts, portfolio |
| Trading | polkamarkets-js SDK | Buy/sell shares, claim winnings, ERC-20 approvals |

---

#### 7. erc8004-on-abstract
ERC-8004 onchain identity and reputation — register AI agents, track reputation, discover agents on Abstract.

**Use when:** Registering an agent onchain, querying agent reputation, giving feedback, working with IdentityRegistry or ReputationRegistry on Abstract, or onchain agent identity.

---

## Skill Selection Guide

| Task | Recommended Skill |
|------|-------------------|
| Connect a wallet/app to Abstract | `connecting-to-abstract` |
| Deploy a smart contract | `deploying-contracts-on-abstract` |
| Build a React app with user login | `abstract-global-wallet` |
| Give an AI agent wallet access | `using-agw-mcp` |
| Set up a team multisig | `safe-multisig-on-abstract` |
| Integrate prediction markets | `myriad-on-abstract` |
| Register an agent onchain | `erc8004-on-abstract` |
| Scaffold a new Abstract project | Start here → choose from above |

---

## Quickstart

For a brand new project, ask the user what they're building:
- **React app with user login** → `abstract-global-wallet` (use `create-abstract-app`)
- **Smart contracts only** → `deploying-contracts-on-abstract` (Foundry with zksync)
- **Full stack** → Both of the above

---

## Resources

- **Repository**: [Abstract-Foundation/abstract-skills](https://github.com/Abstract-Foundation/abstract-skills)
- **Documentation**: [docs.abs.xyz](https://docs.abs.xyz)
- **Explorer**: [abscan.org](https://abscan.org)
- **Safe UI**: [safe.abs.xyz](https://safe.abs.xyz)
- **Testnet Faucets**: [docs.abs.xyz/tooling/faucets](https://docs.abs.xyz/tooling/faucets)
