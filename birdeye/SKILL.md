---
name: birdeye
version: 1.0.0
description: Token intelligence and wallet analytics for Solana and EVM chains. Use for token security checks, comprehensive token data, and wallet portfolio analysis.
tools:
  - birdeye_token_security
  - birdeye_token_overview
  - birdeye_wallet_networth

metadata:
  starchild:
    emoji: "👁️"
    skillKey: birdeye
    requires:
      env: [BIRDEYE_API_KEY]

user-invocable: false
disable-model-invocation: false
---

# Birdeye

Multi-chain token intelligence and wallet analytics. Covers Solana + EVM chains.

## Tools

| Tool | Use when |
|------|----------|
| `birdeye_token_security(address, chain?)` | "Is this token safe?" — security score, rug pull risk, contract vulnerabilities |
| `birdeye_token_overview(address, chain?)` | "Full rundown on this token" — price, volume, market cap, liquidity, price changes |
| `birdeye_wallet_networth(wallet, chain?)` | "What's this wallet worth?" — portfolio value and token breakdown |

**Chain options:** `solana` (default), `ethereum`, `arbitrum`, `base`, `optimism`, `polygon`, `bsc`, `avalanche`, `zksync`, `sui`

## Interpretation

### Security Scores

| Score | Risk | Action |
|-------|------|--------|
| 90-100 | Very Low | Safe, verified contract |
| 70-89 | Low | Generally safe |
| 50-69 | Medium | Caution, check issues |
| 30-49 | High | Investigate carefully |
| 0-29 | Very High | Likely scam — avoid |

**Red flags:** mint authority not renounced, freeze authority enabled, liquidity <$10k, top 10 holders >80% supply

### Liquidity Tiers

| Liquidity | Risk |
|-----------|------|
| <$10k | Very high, easy to manipulate |
| $10k-$100k | Moderate, watch large exits |
| $100k-$1M | Good for small/medium trades |
| >$1M | Strong, safer for larger positions |

## Common Workflows

**Token due diligence:** `birdeye_token_security` → `birdeye_token_overview`. Low score (<50) + low liquidity (<$10k) = rug pull risk.

**Wallet analysis:** `birdeye_wallet_networth`. Check concentration (>80% in one token = high risk).

## Notes

- Rate limits: wallet endpoints 5 req/s, 75 req/min
- Solana addresses are base58, EVM addresses are 0x...
- Security scores are automated — validate manually for high-value trades
- Use CoinGecko for broad market data/rankings; Birdeye for security checks and Solana-specific data
- **Limitations:** no trending tokens, no holder distribution, no trade history, no smart money signals
