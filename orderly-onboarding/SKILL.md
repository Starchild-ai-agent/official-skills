---
name: orderly-onboarding
version: 1.0.0
description: Agent onboarding for Orderly Network - omnichain perpetual futures infrastructure
---

# Orderly Network: Agent Onboarding

Orderly is an omnichain orderbook-based trading infrastructure providing perpetual futures liquidity. No official front end — builders create DEXes on top.

## Quick Reference

| Feature | Detail |
|---------|--------|
| **Type** | Omnichain CLOB + perp futures |
| **Leverage** | Up to 50x |
| **Trading** | Gasless, one-click (trading key per session) |
| **Custody** | Self-custody, on-chain settlement |
| **EVM Chains** | Arbitrum, Optimism, Base, Ethereum, Polygon, Mantle |
| **Non-EVM** | Solana |
| **Docs** | https://orderly.network/docs/introduction |
| **API** | https://orderly.network/docs/build-on-evm/building-on-evm |

## Key Advantages

- Unified orderbook across all chains with shared liquidity
- CEX-level matching engine + on-chain settlement
- Revenue sharing for builders
- Launch a DEX in days with SDKs

## Getting Started: AI Agent Tools

### MCP Server (Recommended)

```bash
npx @orderly.network/mcp-server init --client <client>
```

Supported clients: `cursor`, `windsurf`, `claude`, `vscode`, `cline`

Provides 8 tools: `search_docs`, `get_sdk_patterns`, `get_contract_addresses`, `get_api_reference`, `get_integration_workflow`, `get_code_examples`, `get_troubleshooting`, `search_github`

### Skills (from skills.sh)

```bash
npx skills add orderly-network/orderly-ai-skills --yes
```

Skills: `orderly-api-authentication`, `orderly-trading-orders`, `orderly-positions-tpsl`, `orderly-websocket-streaming`, `orderly-deposit-withdraw`

## For Builders (SDK)

```bash
# React
npx @nicegoodthings/create-orderly-app@latest

# Multi-framework (React, Next, Vue, Nuxt)
npx degit nicegoodthings/orderly-web-example my-app
```

SDK packages: `@orderly.network/hooks`, `@orderly.network/ui-scaffold`, `@orderly.network/ui-connector`

## For API/Bot Developers

1. Generate API key pair: `ed25519` keypair (public key registered on-chain)
2. Create trading key: Session-based, no repeated signatures
3. Auth headers: `orderly-timestamp`, `orderly-account-id`, `orderly-key`, `orderly-signature`
4. REST base: `https://api-evm.orderly.org`
5. WebSocket: `wss://ws-evm.orderly.org/ws/stream/{account_id}`

See `orderly-api-authentication` skill for complete auth flow.

## $ORDER Token

- Governance + staking token
- Staking portal: https://app.orderly.network/staking
- Revenue sharing for stakers

## Common Issues

| Issue | Solution |
|-------|---------|
| Auth fails | Check ed25519 signing, timestamp within 300s |
| Orders rejected | Verify sufficient collateral and valid trading key |
| Missing positions | Ensure correct `account_id` format: `0x...` + broker_id hash |
| WebSocket disconnect | Implement ping/pong every 10s |

## Related Skills

**API**: orderly-api-authentication, orderly-trading-orders, orderly-positions-tpsl, orderly-websocket-streaming, orderly-deposit-withdraw

**SDK**: orderly-sdk-react-hooks, orderly-ui-components, orderly-sdk-dex-architecture, orderly-sdk-theming
