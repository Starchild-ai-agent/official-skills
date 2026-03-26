---
name: okx
version: 1.0.0
description: OKX OnChainOS - Complete on-chain operations suite with 11 specialized skills for trading, analytics, security, and wallet management across 20+ blockchains
metadata:
  starchild:
    emoji: "⛓️"
    skillKey: okx-onchainos
    requires:
      bins:
        - npx
        - node
user-invocable: true
disable-model-invocation: false
---

# OKX OnChainOS Skills Directory

OKX OnChainOS is a comprehensive suite of 11 specialized skills that provide on-chain trading, analytics, security, and wallet management capabilities across 20+ blockchains including Ethereum, Solana, Base, BSC, Arbitrum, Polygon, XLayer, and TRON.

## Overview

All OKX OnChainOS skills use the `onchainos` CLI tool and can be installed via npx from the [okx/onchainos-skills](https://github.com/okx/onchainos-skills) repository.

**Supported Chains**: Ethereum, Solana, XLayer, Base, BSC, Arbitrum, Polygon, Optimism, Avalanche, Fantom, TRON, and 10+ more.

---

## Skills by Category

### 📊 Market Data & Analytics

#### 1. okx-dex-market
Real-time token prices, K-line charts, index prices, and wallet PnL analysis on-chain.

**Capabilities:**
- Single and batch token price queries
- K-line/candlestick chart data with customizable timeframes
- Index price aggregation from multiple sources
- Wallet portfolio analysis (win rate, top performers, transaction history)
- Address tracking for smart money and KOL trading activities

**Installation:**
```bash
npx skills add https://github.com/okx/onchainos-skills --skill okx-dex-market
```

---

#### 2. okx-dex-token
Token discovery, analytics, and holder insights for DEX trading.

**Capabilities:**
- Token search by name, symbol, or contract address
- Detailed pricing metrics including market cap, liquidity, and volume
- Risk identification (honeypots, developer rug-pull history)
- Holder filtering by wallet type (whales, smart money, KOLs, snipers, bundlers)
- Top trader identification and liquidity pool inspection
- Holder cluster analysis for concentration assessment

**Installation:**
```bash
npx skills add https://github.com/okx/onchainos-skills --skill okx-dex-token
```

---

#### 3. okx-dex-signal
Real-time tracking of smart money, whale, and KOL buy signals across multiple blockchains.

**Capabilities:**
- Lists supported chains for signal tracking
- Fetches buy-direction signals filtered by wallet type, trade size, and token
- Displays signal metadata including USD amount, wallet type, trigger count
- Ranks top traders across markets with customizable sorting

**Installation:**
```bash
npx skills add https://github.com/okx/onchainos-skills --skill okx-dex-signal
```

---

#### 4. okx-dex-trenches
Meme token discovery, developer reputation checks, bundle detection, and co-investor tracking for pump.fun and similar launchpads.

**Capabilities:**
- Scan new token launches across Solana, BSC, X Layer, and TRON
- Analyze creator credibility through rug pull history
- Detect bundler and sniper activity on tokens
- Identify wallets that co-invested in the same launches
- Find similar tokens by the same developer

**Installation:**
```bash
npx skills add https://github.com/okx/onchainos-skills --skill okx-dex-trenches
```

---

### 💼 Portfolio & Wallet Management

#### 5. okx-wallet-portfolio
Query wallet balances, token holdings, and portfolio value across 20+ blockchains.

**Capabilities:**
- Total portfolio value across all chains
- All token balances with USD valuations
- Specific token holdings lookup
- Supports both EVM (0x...) and Solana (Base58) addresses
- Integration with swap workflows for balance verification

**Installation:**
```bash
npx skills add https://github.com/okx/onchainos-skills --skill okx-wallet-portfolio
```

---

#### 6. okx-agentic-wallet
Authentication, balance queries, token transfers, transaction history, and smart contract calls.

**Capabilities:**
- Account management (login, add wallets, switch accounts)
- Balance queries across chains
- Token transfers and native asset sends
- Smart contract interactions
- Transaction history browsing
- MEV protection for high-value transactions
- TEE signing for secure transaction execution

**Installation:**
```bash
npx skills add https://github.com/okx/onchainos-skills --skill okx-agentic-wallet
```

**Important Notes:**
- Requires authentication via email or API key
- Uses numeric chain IDs (e.g., 1 for Ethereum, 501 for Solana)
- Amounts must be specified in UI units, not base units

---

### 🔄 Trading & Swaps

#### 7. okx-dex-swap
Multi-chain DEX swap aggregation with quote, approval, and execution across 500+ liquidity sources.

**Capabilities:**
- Quote generation across 20+ blockchains
- Token approval handling
- Swap execution with built-in security features
- Automatic chain name resolution
- AutoSlippage optimization and MEV protection
- Merged approve+swap flow for EVM tokens
- Security checks including honeypot detection and tax rate disclosure

**Installation:**
```bash
npx skills add https://github.com/okx/onchainos-skills --skill okx-dex-swap
```

**Core Commands:**
```bash
onchainos swap chains          # List supported blockchains
onchainos swap quote           # Get price estimates
onchainos swap approve         # Generate ERC-20 approval data
onchainos swap swap            # Execute swaps with transaction data
onchainos swap liquidity       # View available DEX sources
```

---

### 🔐 Security & Safety

#### 8. okx-security
Token risk analysis, DApp phishing detection, transaction pre-execution security, signature safety, and approval management.

**Capabilities:**
- Token risk detection and honeypot scanning across all chains
- DApp phishing threat identification
- Transaction safety analysis before execution (EVM + Solana)
- Message signature validation (EVM only)
- Token authorization and Permit2 status queries (EVM only)

**Installation:**
```bash
npx skills add https://github.com/okx/onchainos-skills --skill okx-security
```

**Core Commands:**
```bash
onchainos security token-scan    # Detect token risks and honeypots
onchainos security dapp-scan     # Identify phishing threats
onchainos security tx-scan       # Analyze transaction safety
onchainos security sig-scan      # Validate message signatures
onchainos security approvals     # Query token authorizations
```

**Important:** If any security scan fails, the agent MUST block the associated operation rather than proceed.

---

### ⚙️ Infrastructure & Operations

#### 9. okx-onchain-gateway
Gas estimation, transaction simulation, broadcasting, and order tracking across 25+ blockchains.

**Capabilities:**
- Gas price lookups with Gwei and USD cost estimates
- Transaction simulation (dry-run) before broadcasting
- Signed transaction broadcasting
- Order status tracking
- MEV protection on Ethereum, BSC, and Solana
- Batch broadcast support for approve+swap workflows

**Installation:**
```bash
npx skills add https://github.com/okx/onchainos-skills --skill okx-onchain-gateway
```

**Primary Commands:**
```bash
onchainos gateway gas           # Current gas prices
onchainos gateway gas-limit     # Estimate transaction gas
onchainos gateway simulate      # Test transactions before broadcasting
onchainos gateway broadcast     # Send signed transactions
onchainos gateway orders        # Track transaction status
```

---

#### 10. okx-x402-payment
Sign x402 payment authorizations and return payment proof for accessing payment-gated resources.

**Capabilities:**
- X402 HTTP payment protocol support
- TEE signing via wallet session
- Local signing with private key
- Access payment-required API resources
- Support for EVM chains using CAIP-2 format

**Installation:**
```bash
npx skills add https://github.com/okx/onchainos-skills --skill okx-x402-payment
```

---

#### 11. okx-audit-log
Provide the audit log file path for developers to troubleshoot issues offline.

**Capabilities:**
- Access audit log file for debugging
- JSON Lines format with detailed event logging
- Automatic log rotation (max 10,000 lines)
- Timestamp, command, success status, duration, and error tracking

**Installation:**
```bash
npx skills add https://github.com/okx/onchainos-skills --skill okx-audit-log
```

**Log Location:**
- Default: `~/.onchainos/audit.jsonl`
- Custom: `$ONCHAINOS_HOME/audit.jsonl` (if environment variable is set)

**Log Format:**
```json
{"timestamp":"2025-01-15T10:30:45Z","source":"cli","command":"market price","success":true,"duration":1234,"args":"[REDACTED]"}
```

---

## Installation Workflow

### Install All Skills at Once
```bash
# Install all 11 OKX OnChainOS skills
npx skills add https://github.com/okx/onchainos-skills --skill okx-dex-market
npx skills add https://github.com/okx/onchainos-skills --skill okx-wallet-portfolio
npx skills add https://github.com/okx/onchainos-skills --skill okx-dex-token
npx skills add https://github.com/okx/onchainos-skills --skill okx-dex-swap
npx skills add https://github.com/okx/onchainos-skills --skill okx-onchain-gateway
npx skills add https://github.com/okx/onchainos-skills --skill okx-dex-signal
npx skills add https://github.com/okx/onchainos-skills --skill okx-dex-trenches
npx skills add https://github.com/okx/onchainos-skills --skill okx-agentic-wallet
npx skills add https://github.com/okx/onchainos-skills --skill okx-security
npx skills add https://github.com/okx/onchainos-skills --skill okx-audit-log
npx skills add https://github.com/okx/onchainos-skills --skill okx-x402-payment
```

---

## Important Notes

### Chain Identifiers
- Supports both human-readable names (`ethereum`, `solana`, `xlayer`) and numeric chain IDs
- Use `onchainos swap chains` or `onchainos gateway chains` to view all supported chains

### Authentication
- **okx-agentic-wallet** requires authentication via email or API key
- Other skills work without authentication for read-only operations
- TEE signing available for enhanced security

### Pre-flight Checks
- All skills include automatic pre-flight checks
- CLI binary is installed/updated automatically
- Integrity verification before command execution

### Security Best Practices
1. Always run `okx-security` scans before executing transactions
2. Verify token contracts for honeypots and high taxes
3. Check DApp URLs for phishing before connecting wallets
4. Review transaction simulations before broadcasting
5. Monitor token approvals and revoke unnecessary permissions

### Gas & MEV Protection
- MEV protection available on Ethereum, BSC, and Solana
- AutoSlippage optimization for large trades
- Gas price estimates include USD cost calculations
- Merged approve+swap reduces transaction steps and costs

---

## Troubleshooting

### Common Issues
- **Binary not found**: Run `npx onchainos --version` to trigger installation
- **Chain not supported**: Use `onchainos swap chains` to view supported chains
- **Authentication required**: Use `okx-agentic-wallet` login flow for wallet operations
- **Rate limits**: Check API rate limits and wait between requests

---

## Resources

- **Repository**: [okx/onchainos-skills](https://github.com/okx/onchainos-skills)
- **Documentation**: [OKX OnChainOS Docs](https://www.okx.com/web3/build/docs/onchain-os/introduction)
- **Skills Registry**: [skills.sh/okx/onchainos-skills](https://skills.sh/okx/onchainos-skills)

---

## Skill Selection Guide

Choose the right skill for your task:

| Task | Recommended Skill |
|------|-------------------|
| Check token price | okx-dex-market |
| Find new tokens | okx-dex-token or okx-dex-trenches |
| Track smart money | okx-dex-signal |
| View wallet balances | okx-wallet-portfolio |
| Execute swaps | okx-dex-swap |
| Security analysis | okx-security |
| Wallet operations | okx-agentic-wallet |
| Gas estimates | okx-onchain-gateway |
| Transaction tracking | okx-onchain-gateway |
| Payment gating | okx-x402-payment |
| Debugging | okx-audit-log |

