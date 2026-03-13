---
name: orderly-one
version: 1.0.0
description: Create and manage your own DEX on Orderly Network
tools:
  - orderly_one_networks
  - orderly_one_leaderboard
  - orderly_one_stats
  - orderly_one_dex_get
  - orderly_one_dex_create
  - orderly_one_dex_update
  - orderly_one_dex_delete
  - orderly_one_social_card
  - orderly_one_domain
  - orderly_one_visibility
  - orderly_one_deploy_status
  - orderly_one_theme
  - orderly_one_graduation
metadata:
  starchild:
    emoji: "🏗️"
    skillKey: orderly-one
    requires:
      env: [WALLET_SERVICE_URL]
user-invocable: true
disable-model-invocation: false
---

# Orderly One — DEX Builder

Build, customize, and manage your own decentralized exchange (DEX) on Orderly Network using the Orderly One DEX-as-a-Service platform. Your DEX inherits Orderly's shared liquidity, central limit orderbook, and cross-chain settlement infrastructure — you focus on branding, community, and growth.

## Prerequisites

- **Wallet**: Agent must be running on Fly.io with `WALLET_SERVICE_URL` configured (EIP-191 signing via Privy)
- **No API keys needed**: Authentication uses the agent's EVM wallet address + JWT tokens

## How It Works

Orderly One lets you launch a white-label DEX with:
- **Shared orderbook liquidity** from the entire Orderly Network
- **Multi-chain deployment** (Arbitrum, Optimism, Base, Polygon, etc.)
- **Custom branding** — name, logo, colors, domain
- **AI-powered theming** — generate themes from text prompts
- **Graduation path** — move from sandbox to production with your own broker ID

Authentication uses JWT tokens obtained via EIP-191 personal_sign (different from the Ed25519 auth used for Orderly trading).

## Tool Reference

| Tool | Auth | Purpose |
|------|------|---------|
| `orderly_one_networks` | None | List supported chains for DEX deployment |
| `orderly_one_leaderboard` | None | DEX rankings, broker stats by volume/users |
| `orderly_one_stats` | None | Platform-wide aggregate statistics |
| `orderly_one_dex_get` | JWT | Get your DEX config or a specific DEX by ID |
| `orderly_one_dex_create` | JWT | Create a new DEX (name, chains, branding) |
| `orderly_one_dex_update` | JWT | Update DEX configuration |
| `orderly_one_dex_delete` | JWT | Delete a DEX (destructive) |
| `orderly_one_social_card` | JWT | Update social links and OG metadata |
| `orderly_one_domain` | JWT | Set or remove a custom domain |
| `orderly_one_visibility` | JWT | Toggle leaderboard visibility |
| `orderly_one_deploy_status` | JWT | Check deployment status, trigger upgrades |
| `orderly_one_theme` | JWT | AI theme generation and fine-tuning |
| `orderly_one_graduation` | JWT | Graduate DEX to production |

## Workflows

### Build a DEX

1. Check available networks: `orderly_one_networks`
2. Create your DEX: `orderly_one_dex_create` with broker name and chain IDs
3. Check deployment: `orderly_one_deploy_status` (action: "status")
4. Configure branding: `orderly_one_social_card` with social links
5. Generate a theme: `orderly_one_theme` (action: "generate", prompt: "your style")

### Customize Your DEX

- **Theme**: Use `orderly_one_theme` with action "generate" for full themes or "fine_tune" for specific elements
- **Domain**: Use `orderly_one_domain` to set a custom domain (requires DNS CNAME setup)
- **Social**: Use `orderly_one_social_card` to configure Twitter, Discord, Telegram links and OG image
- **Visibility**: Use `orderly_one_visibility` to show/hide on the public leaderboard

### Graduate to Production

1. Check eligibility: `orderly_one_graduation` (action: "status")
2. Review fee options: `orderly_one_graduation` (action: "fees")
3. Make payment and verify: `orderly_one_graduation` (action: "verify", tx_hash, chain_id)
4. Finalize with admin wallet: `orderly_one_graduation` (action: "finalize", admin_wallet)

### Monitor & Upgrade

- Check deployment status: `orderly_one_deploy_status` (action: "status")
- Check for upgrades: `orderly_one_deploy_status` (action: "upgrade_check")
- Trigger upgrade: `orderly_one_deploy_status` (action: "upgrade")
- View workflow run details: `orderly_one_deploy_status` (action: "workflow", run_id)

## Supported Chains

Use `orderly_one_networks` for the current list. Commonly supported:

| Chain | Chain ID |
|-------|----------|
| Arbitrum | 42161 |
| Optimism | 10 |
| Base | 8453 |
| Polygon | 137 |
| Mantle | 5000 |
| Sei | 1329 |

## Error Handling

- **401 Unauthorized**: JWT expired — automatically refreshed on retry
- **403 Forbidden**: Wallet not authorized for this DEX
- **404 Not Found**: DEX ID doesn't exist
- **429 Rate Limited**: Too many requests — check `orderly_one_deploy_status` rate limit status

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WALLET_SERVICE_URL` | Required | Privy wallet service URL |
| `ORDERLY_ONE_API_URL` | `https://api.dex.orderly.network` | API base URL |
