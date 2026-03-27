---
name: "woofi-bot"
version: 5.0.0
description: "WOOFi DEX analytics, swap quotes, swap execution, pool states, protocol revenue across 16 chains."
tags: [defi, analytics, woofi, dex, swap, quote, execution]
author: "starchild"
metadata:
  starchild:
    emoji: "📊"
    skillKey: woofi-data
user-invocable: true
---

# 📊 WOOFi Data

Fetch WOOFi DEX metrics, execute swaps, and analyze protocol data.

## Quick Reference

| Detail | Value |
|--------|-------|
| **Legacy API** | `https://api.woofi.com` |
| **v1 API (new)** | `https://sapi.woofi.com` |
| **Auth** | None (public) |
| **Rate Limit** | 5 req/s |
| **Active Chains** | bsc, avalanche, polygon, arbitrum, optimism, linea, base, mantle, sonic, berachain, hyperevm, monad, solana |
| **Paused Chains** | fantom, zksync, polygon_zkevm, sei |

## Endpoints

### Swap (v1 API — sapi.woofi.com)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/quote` | POST | Get swap quote without executing |
| `/v1/swap` | POST | Generate on-chain tx data for swap execution |

**Quote request** (JSON body):
- `chain_id` (required): Network chain ID (e.g., 42161=Arbitrum, 8453=Base, 56=BSC)
- `sell_token`, `buy_token` (required): Address or symbol. Native token = `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`
- `sell_amount` (required): Human-readable amount (e.g., "1.5")
- `slippage_pct`: default 0.5

**Swap request** = Quote params + `sender` (wallet address). Returns `tx_steps` array: approval tx (if needed) → swap tx. Execute sequentially with wallet tools.

### Analytics (Legacy API — api.woofi.com)

| Endpoint | Params | Notes |
|----------|--------|-------|
| `/swap_support` | — | Supported networks, DEXs, tokens |
| `/swap` | `network`, `sell_token`, `buy_token`, `sell_amount` | Legacy swap quote |
| `/stat` | `period`, `network` | Volume/traders. **⚠️ volume_usd in wei ÷ 10^18** |
| `/cumulate_stat` | `network` | Cumulative all-time stats |
| `/source_stat` | `period`, `network` | Volume by integrator (1inch, 0x, etc.) |
| `/token_stat` | `network` | Per-token 24h stats |
| `/yield` | `network` | Earn vault TVL/APY. **TVL in wei ÷ 10^18** |
| `/earn_summary` | — | Supercharger APR rankings |
| `/stakingv2` | — | WOO staking APR/stats |
| `/user_balances` | `user_address` | User token balances |
| `/user_trading_volumes` | `user_address`, `period` | User swap volume (period: 7d/14d/30d) |
| `/woofi_pro/perps_volume` | — | WOOFi Pro perps daily volume |
| `/integration/pairs` | `network` | Trading pairs |
| `/integration/tickers` | `network` | 24h ticker data |
| `/integration/pool_states` | `network` | Pool reserves, fees, oracle prices |
| `/analytics/daily_fee` | `network` | Protocol revenue |

**Periods for `/stat`, `/source_stat`**: 1d, 1w, 1m, 3m, 1y, all
**Periods for user endpoints**: 7d, 14d, 30d

## Common Patterns

### Get v1 quote
```bash
curl -X POST https://sapi.woofi.com/v1/quote \
  -H "Content-Type: application/json" \
  -d '{"chain_id":42161,"sell_token":"USDC","buy_token":"WBTC","sell_amount":"1000"}'
```

### Execute v1 swap
```bash
curl -X POST https://sapi.woofi.com/v1/swap \
  -H "Content-Type: application/json" \
  -d '{"chain_id":42161,"sell_token":"USDC","buy_token":"WBTC","sell_amount":"1000","sender":"0xYOUR_WALLET"}'
# Returns tx_steps[] → sign & broadcast each step sequentially
```

### Quick analytics
```bash
curl "https://api.woofi.com/stat?period=1d&network=arbitrum"
curl "https://api.woofi.com/yield?network=base"
```

## Gotchas

- **Wei values**: `volume_usd` and `total_deposit` are in wei (÷ 10^18 for USD)
- **v1 API base URL**: `sapi.woofi.com` (not `api.woofi.com`)
- **Token addresses**: Native tokens use `0xEeee...eEEeE` address
- **Paused chains**: fantom, zksync, polygon_zkevm have `swap_enable=false`
- **Solana quirks**: `/solana_stat` is a separate endpoint (raw pool data)
- **Checksum addresses**: EVM user queries require checksummed addresses
- **v1 swap flow**: Always process `tx_steps` sequentially (approve → swap)
