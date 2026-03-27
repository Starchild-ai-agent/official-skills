---
name: okx
version: 1.0.0
description: "OKX OnChainOS - 11 specialized on-chain skills for trading, analytics, security, and wallet management across 20+ blockchains"
metadata:
  starchild:
    emoji: "⛓️"
    skillKey: okx-onchainos
    requires:
      bins: [npx, node]
user-invocable: true
---

# OKX OnChainOS Skills Directory

Suite of 11 skills for on-chain operations via `onchainos` CLI. Install any skill via npx from [okx/onchainos-skills](https://github.com/okx/onchainos-skills).

**Chains**: Ethereum, Solana, Base, BSC, Arbitrum, Polygon, Optimism, XLayer, TRON, Avalanche, Fantom, 10+ more.

## Skills

### Market Data & Analytics

| Skill | Purpose | Install |
|-------|---------|---------|
| **okx-dex-market** | Token prices, K-lines, index prices, wallet PnL analysis | `npx skills add ...okx-dex-market` |
| **okx-dex-token** | Token discovery, risk detection (honeypots/rugs), holder analytics, top traders | `npx skills add ...okx-dex-token` |
| **okx-dex-signal** | Smart money/whale/KOL buy signals, trader rankings | `npx skills add ...okx-dex-signal` |
| **okx-dex-trenches** | Meme token launches, dev reputation, bundler/sniper detection | `npx skills add ...okx-dex-trenches` |

### Portfolio & Wallet

| Skill | Purpose | Install |
|-------|---------|---------|
| **okx-wallet-portfolio** | Multi-chain balances + USD valuations (EVM + Solana) | `npx skills add ...okx-wallet-portfolio` |
| **okx-agentic-wallet** | Auth, transfers, tx history, contract interaction | `npx skills add ...okx-agentic-wallet` |

### Trading

| Skill | Purpose | Install |
|-------|---------|---------|
| **okx-dex-swap** | Cross-chain token swaps with best-route aggregation | `npx skills add ...okx-dex-swap` |

### Infrastructure

| Skill | Purpose | Install |
|-------|---------|---------|
| **okx-onchain-gateway** | Gas estimation, tx tracking, chain info | `npx skills add ...okx-onchain-gateway` |
| **okx-security** | Token risk scoring, address risk, approval scanning | `npx skills add ...okx-security` |
| **okx-x402-payment** | HTTP 402 payment-gated content via x-402 protocol | `npx skills add ...okx-x402-payment` |
| **okx-audit-log** | Debug skill execution, trace tool calls | `npx skills add ...okx-audit-log` |

All install commands: `npx skills add https://github.com/okx/onchainos-skills --skill <name>`

## Skill Selection Guide

| Task | Skill |
|------|-------|
| Token price | okx-dex-market |
| Find new tokens | okx-dex-token / okx-dex-trenches |
| Track smart money | okx-dex-signal |
| Wallet balances | okx-wallet-portfolio |
| Execute swaps | okx-dex-swap |
| Security analysis | okx-security |
| Wallet operations | okx-agentic-wallet |
| Gas/tx tracking | okx-onchain-gateway |
| Payment gating | okx-x402-payment |
| Debugging | okx-audit-log |

## Usage Pattern

```bash
# Install a skill
npx skills add https://github.com/okx/onchainos-skills --skill okx-dex-swap --yes --copy --agent openclaw

# Tools become available after install — read the installed SKILL.md for tool names and parameters
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| "npx not found" | Install Node.js (`apt install nodejs npm`) |
| "skill not found" | Check exact name: `okx-dex-swap`, not `okx-swap` |
| Chain not supported | Verify chain name matches OKX format |
| Rate limits | Add delays between API requests |

## Resources

- [GitHub](https://github.com/okx/onchainos-skills) · [Docs](https://www.okx.com/web3/build/docs/onchain-os/introduction) · [skills.sh](https://skills.sh/okx/onchainos-skills)
