---
name: "woofi-bot"
version: 5.0.0
description: "Complete WOOFi bot — DEX analytics, swap quotes, swap execution — DEX analytics, swap quotes, swap execution with tx generation, pool states, protocol revenue across 16 chains. Updated from woonetwork/woofi-skills v1.1."
tags: [defi, analytics, woofi, dex, yield, trading, perps, swap, quote, execution, transaction]
author: "starchild"

metadata:
  starchild:
    emoji: "📊"
    skillKey: woofi-data

user-invocable: true
---

# 📊 WOOFi Data

Fetch WOOFi DEX metrics for market analysis, reporting, and DeFi research.

**Updated**: 2026-03-23 — Aligned with [woonetwork/woofi-skills](https://github.com/woonetwork/woofi-skills) v1.1 (2026-03-20)

**v4.0.0 adds complete swap functionality:**
- ✅ **Quote only** (`POST /v1/quote`) — Get exchange rates without executing
- ✅ **Swap execution** (`POST /v1/swap`) — Generate on-chain transaction data with approval steps
- ✅ **Wallet-ready** — Returns `tx_steps` array for sequential signing and broadcast

**What's New in v4.0.0:**
- Added `POST /v1/quote` — Token swap quotes with slippage protection (sapi.woofi.com)
- Added `POST /v1/swap` — Complete swap execution with tx step generation and approval handling
- Updated `/swap` endpoint documentation (legacy api.woofi.com)
- Renumbered all endpoint sections for clarity (17 total endpoints)
- Updated network support matrix with v1 API compatibility

## When to Use

- User asks about WOOFi trading volume on specific chains
- Comparing DEX activity across multiple chains
- Checking WOOFi Earn vault TVL and APYs
- Analyzing volume sources (1inch, 0x, Paraswap, etc.)
- Monitoring WOO staking metrics and APR
- Querying user portfolio data (balances, positions, staking)
- Checking WOOFi Pro perpetuals volume
- **Getting swap quotes for token exchanges** (NEW)
- **Checking pool liquidity and reserves** (NEW)
- **Tracking protocol revenue** (NEW)
- Building DeFi dashboards or reports

## API Overview

| Detail | Value |
|--------|-------|
| **Base URL** | `https://api.woofi.com` |
| **Auth** | None (fully public) |
| **Rate Limit** | 5 requests/second |
| **Chains** | bsc, avalanche, polygon, arbitrum, optimism, linea, base, mantle, sonic, berachain, hyperevm, monad, solana, fantom, zksync, polygon_zkevm, sei |

## Endpoints

### 1. Swap Support — `/swap_support`

Query supported networks, DEXs, and tokens for WOOFi swaps.

**Trigger phrases**: "swap support", "supported networks", "supported tokens", "which chains"

**Example:**
```bash
curl "https://api.woofi.com/swap_support"
```

**Response fields:**
- `dexs` — List of DEX integrations per chain (uni_swap, sushi_swap, curve, woofi, etc.)
- `network_infos` — Chain metadata (name, RPC URL, chain ID, explorer, bridge support)
- `token_infos` — Supported tokens with address, symbol, decimals, `swap_enable` flag
- `swap_enable` — Whether swapping is currently active for this token/network
- `bridge_enable` — Whether cross-chain bridging is supported

**⚠️ Note**: Paused networks (fantom, zksync, polygon_zkevm) have `swap_enable=false` for all tokens.

### 2. Swap Quote (v1) — `POST /v1/quote` 🆕

Get token exchange rates and expected receive amounts **without executing a trade**. Uses the new `sapi.woofi.com` API.

**Base URL**: `https://sapi.woofi.com`  
**Endpoint**: `POST /v1/quote`  
**Content-Type**: `application/json`

**Trigger phrases**: "quote", "price", "exchange rate", "token price", "how much will I get"

#### Parameters (QuoteRequest)

All parameters are passed in the JSON body.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `chain_id` | `integer` | Yes | — | Network chain ID (e.g., Base: `8453`, Arbitrum: `42161`, BSC: `56`, Polygon: `137`) |
| `sell_token` | `string` | Yes | — | Address or symbol of token to sell (Native ETH/BNB/etc is `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`) |
| `buy_token` | `string` | Yes | — | Address or symbol of token to buy |
| `sell_amount` | `string` | Yes | — | Human-readable amount to sell (e.g., `"1.5"`) |
| `slippage_pct` | `float` | No | `0.5` | Max allowed slippage percentage |
| `woofi_only` | `boolean` | No | `false` | If `true`, only sources quotes directly from WOOFi |

#### Response Fields (QuoteResponse)

| Field | Type | Description |
|-------|------|-------------|
| `chain_id` | `integer` | Chain ID |
| `sell_token` | `string` | Sell token address |
| `buy_token` | `string` | Buy token address |
| `sell_amount` | `string` | Sell amount requested |
| `buy_amount` | `string` | Expected buy amount |
| `price` | `string` | Current execution price |
| `guaranteed_price` | `string` | Minimum guaranteed price after considering slippage |

**Example:**
```bash
curl -X POST "https://sapi.woofi.com/v1/quote" \
  -H "Content-Type: application/json" \
  -d '{
    "chain_id": 42161,
    "sell_token": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
    "buy_token": "0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f",
    "sell_amount": "1000"
  }'
```

**Response:**
```json
{
  "chain_id": 42161,
  "sell_token": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
  "buy_token": "0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f",
  "sell_amount": "1000",
  "buy_amount": "0.01524300",
  "price": "0.000015243",
  "guaranteed_price": "0.000015167"
}
```

**⚠️ Important:**
- This is a **read-only quote** — no transaction is generated or executed
- Use this for price checking, slippage evaluation, and pre-trade verification
- Always perform a quote before initiating a `swap` execution to verify expectations
- Native assets (ETH, BNB, etc.) use address `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`

---

### 3. Swap Execution — `POST /v1/swap` 🆕

Generate **blockchain-ready transaction data** for swaps, including necessary token approvals.

**Base URL**: `https://sapi.woofi.com`  
**Endpoint**: `POST /v1/swap`  
**Content-Type**: `application/json`

**Trigger phrases**: "swap", "trade", "execute swap", "build transaction", "swap tokens"

#### Parameters (SwapRequest)

This endpoint inherits all parameters from the Quote endpoint, plus execution-specific ones:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chain_id` | `integer` | Yes | Network chain ID (e.g., Base: `8453`, Arbitrum: `42161`) |
| `sell_token` | `string` | Yes | Token address/symbol to sell (Native is `0xEeeeeE...`) |
| `buy_token` | `string` | Yes | Token address/symbol to buy |
| `sell_amount` | `string` | Yes | Human-readable amount to sell (e.g., `"1.5"`) |
| `to` | `string` | Yes | The wallet address that will receive the purchased tokens |
| `rebate_to` | `string` | Yes | Rebate receiving address (typically same as `to`) |
| `slippage_pct` | `float` | No | Max allowed slippage percentage (default: `0.5`) |
| `signer_address` | `string` | No | User's wallet address initiating the swap. Used to check if an `Approve` is required. |

#### Response Fields (SwapResponse)

| Field | Type | Description |
|-------|------|-------------|
| `needs_approve` | `boolean` | If `true`, user must approve the router contract before swapping |
| `tx_steps` | `array` | List of transaction steps to be signed and submitted on-chain |
| `buy_amount` | `string` | Expected buy amount |
| `price` | `string` | Current execution price |
| `guaranteed_price` | `string` | Minimum guaranteed price |

Each item in `tx_steps` represents an on-chain call:
- `to`: Target contract address for this step
- `data`: Hex string representing the transaction data payload
- `value`: Amount of native token to send in Wei
- `desc`: Human-readable description (e.g., "Approve USDC for WOOFi Router")

**Example:**
```bash
curl -X POST "https://sapi.woofi.com/v1/swap" \
  -H "Content-Type: application/json" \
  -d '{
    "chain_id": 42161,
    "sell_token": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
    "buy_token": "0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f",
    "sell_amount": "1000",
    "to": "0xYourWalletAddress",
    "rebate_to": "0xYourWalletAddress",
    "signer_address": "0xYourWalletAddress"
  }'
```

**Response:**
```json
{
  "chain_id": 42161,
  "sell_token": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
  "buy_token": "0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f",
  "sell_amount": "1000",
  "buy_amount": "0.01524300",
  "price": "0.000015243",
  "guaranteed_price": "0.000015167",
  "needs_approve": true,
  "tx_steps": [
    {
      "to": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
      "data": "0x095ea7b3...",
      "value": "0",
      "desc": "Approve USDC for WOOFi Router"
    },
    {
      "to": "0x4c4AF8DBc524681930a27b2F1Af5bcC8062E6fB7",
      "data": "0x...",
      "value": "0",
      "desc": "Swap 1000 USDC for WBTC via WOOFi"
    }
  ]
}
```

**⚠️ Critical:**
1. **Sequential Execution**: If `tx_steps` contains multiple items, they MUST be submitted to the blockchain in the exact order provided (Approve must confirm before Swap)
2. **Native Asset Routing**: When selling or buying native assets (ETH, BNB, etc.), use `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`
3. **Wallet Integration Required**: These transactions must be signed and broadcast by the user's wallet
4. **Check `needs_approve`**: If `true`, the approval transaction must be executed first

---

### 4. Swap Quote (Legacy) — `/swap`

Get swap quote for token exchange using the legacy `api.woofi.com` endpoint. Returns routing info, expected output amount, and price impact.

**Trigger phrases**: "swap quote", "quote ETH to USDC", "how much USDC for 1 ETH", "swap price"

**Parameters:**
- `from_token` (required): Source token contract address (or `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE` for native ETH)
- `to_token` (required): Destination token contract address
- `from_amount` (required): Amount in smallest unit (wei for ETH, 6 decimals for USDC)
- `network` (required): Chain name (e.g., "arbitrum", "bsc", "base")
- `slippage` (optional): Slippage tolerance in basis points (e.g., 50 = 0.5%, default: 50)

**Example:**
```bash
# Quote: 0.1 ETH → USDC on Arbitrum
curl "https://api.woofi.com/swap?from_token=0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE&to_token=0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8&from_amount=100000000000000000&network=arbitrum"
```

**Response structure:**
```json
{
  "status": "ok",
  "data": {
    "from_token": {...},
    "to_token": {...},
    "from_amount": "100000000000000000",
    "to_amount": "245000000",  # Expected output (in to_token decimals)
    "price_impact": "0.15",   # Price impact percentage
    "routing_info": {
      "sources": [
        {"name": "woofi", "percentage": "60.5"},
        {"name": "uni_swap", "percentage": "39.5"}
      ]
    },
    "gas_estimate": "150000"
  }
}
```

**⚠️ Important:**
- This endpoint returns a **quote only** — it does NOT execute the swap
- To execute, you need to integrate with WOOFi's smart contracts or use a wallet
- `from_amount` must be in the token's smallest unit (wei for 18-decimal tokens)
- `to_amount` will be in the destination token's decimal precision
- For native ETH, use address `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`

### 5. Total Stats — `/multi_total_stat`, `/total_stat`, `/cumulate_stat`

Cross-chain aggregated trading statistics.

**Trigger phrases**: "total volume", "total stats", "cross chain stats", "24h stats", "overall volume"

**Example:**
```bash
# Cross-chain total
curl "https://api.woofi.com/multi_total_stat"

# Single chain total
curl "https://api.woofi.com/total_stat?network=arbitrum"

# Cumulative stat
curl "https://api.woofi.com/cumulate_stat?network=bsc"
```

### 6. Trading Stats — `/stat`

Volume, trader count, and transaction count by period and chain.

**Trigger phrases**: "trading stats", "trading volume", "woofi stats", "how much volume", "trader count"

**Parameters:**
- `period` (required): `1d`, `1w`, `1m`, `3m`, `1y`, `all`
- `network` (required): chain name from list above

**⚠️ CRITICAL: `volume_usd` is in wei — divide by 10^18 to get USD value**

**Example:**
```bash
curl "https://api.woofi.com/stat?period=1d&network=arbitrum"
```

**Response:**
```json
{
  "status": "ok",
  "data": [
    {
      "timestamp": 1710892800,
      "volume_usd": "1234567890123456789012",
      "traders": 1523,
      "txns": 8942
    }
  ]
}
```

### 7. Source Stats — `/source_stat`

Volume breakdown by integrator/aggregator source.

**Trigger phrases**: "volume by source", "top integrators", "who is sending volume", "traffic source"

**Parameters:**
- `period` (required): `1d`, `1w`, `1m`, `3m`, `1y`, `all`
- `network` (required): chain name

**Example:**
```bash
curl "https://api.woofi.com/source_stat?period=1m&network=arbitrum"
```

**Response fields per source:**
- `name` — Source name (e.g. "1inch", "0x", "Paraswap", "WOOFi", "KyberSwap", "ODOS")
- `volume_usd` — Volume in wei (÷ 10^18 = USD)
- `percentage` — Share of total volume (string, e.g. "45.2")
- `traders`, `txs` — Unique wallets and tx count

**Known integrators:** 1inch, 0x, ODOS, KyberSwap, Paraswap, THORSwap, OKX, BitKeep, Firebird, Transit Swap, Hera Fireance, Yeti, Joy, ZetaFarm, Slingshot, unizen, 1delta, KALM, ONTO, Velora, Nativo, etc.

### 8. Token Stats — `/token_stat`

Per-token 24-hour trading statistics including TVL, volume, and turnover rate.

**Trigger phrases**: "token stats", "token volume", "token tvl", "top tokens"

**Parameters:**
- `network` (required): chain name

**Example:**
```bash
curl "https://api.woofi.com/token_stat?network=arbitrum"
```

### 9. Solana Pool Stats — `/solana_stat`

Solana-specific raw pool statistics.

**Trigger phrases**: "solana stats", "solana pool", "solana trading"

**Example:**
```bash
curl "https://api.woofi.com/solana_stat"
```

### 10. Earn Yields — `/yield`

Vault TVL, APY, and yield composition per chain.

**Trigger phrases**: "earn tvl", "earn vault", "yield farming", "woofi earn", "tvl", "apy"

**Parameters:**
- `network` (required): chain name

**Example:**
```bash
curl "https://api.woofi.com/yield?network=base"
```

**Response structure:**
- `auto_compounding` — Map of vault address → vault data
  - `total_deposit` — TVL in wei (÷ 10^18 = USD)
  - `apy` — Current APY (decimal, e.g. 0.045 = 4.5%)
  - `source_apy` — Breakdown of yield sources
- `total_deposit` — Chain-wide total TVL in wei

### 11. Earn Summary — `/earn_summary`

Supercharger vault APR summary across all networks, sorted by APR.

**Trigger phrases**: "earn summary", "supercharger", "earn apr", "best earn vault", "vault ranking"

**Example:**
```bash
curl "https://api.woofi.com/earn_summary"
```

**⚠️ Note**: Paused networks (`fantom`, `zksync`, `polygon_zkevm`) are excluded.

### 12. WOO Staking — `/stakingv2`

Global WOO token staking statistics including base APR and Multiplier Point boost.

**Trigger phrases**: "woo staking", "staking apr", "staked woo", "multiplier points"

**Example:**
```bash
curl "https://api.woofi.com/stakingv2"
```

**Response fields:**
- `total_woo_staked` — Total WOO staked in wei (÷ 10^18)
- `avg_apr` — Current average staking APR
- `base_apr` — Base APR component
- `mp_boosted_apr` — Multiplier-boosted APR component

### 13. User Portfolio — `/user_balances`, `/user_supercharger_infos`, `/user_stakingv2_infos`, `/boosted_apr_info`

User portfolio data including token balances, Supercharger positions, staking info, and boosted APR status.

**Trigger phrases**: "user balance", "user portfolio", "my position", "user staking", "boosted apr"

**Parameters:**
- `user` or `user_address` (required): User wallet address (checksummed for EVM)

**Example:**
```bash
curl "https://api.woofi.com/user_balances?user_address=0x..."
curl "https://api.woofi.com/user_supercharger_infos?user_address=0x..."
curl "https://api.woofi.com/user_stakingv2_infos?user_address=0x..."
curl "https://api.woofi.com/boosted_apr_info?user_address=0x..."
```

### 14. User Trading Volume — `/user_trading_volumes`, `/user_perp_volumes`

User swap and perpetual trading volume history.

**Trigger phrases**: "user trading volume", "my volume", "user perp volume", "trading history"

**Parameters:**
- `user` or `user_address` (required): User wallet address
- `period` (required): `7d`, `14d`, `30d` (different from stat endpoints!)

**Example:**
```bash
curl "https://api.woofi.com/user_trading_volumes?user_address=0x...&period=30d"
curl "https://api.woofi.com/user_perp_volumes?user_address=0x...&period=7d"
```

### 15. WOOFi Pro Perps — `/woofi_pro/perps_volume`

WOOFi Pro daily perpetual trading volume.

**Trigger phrases**: "perps volume", "woofi pro", "woofi dex", "perpetual volume"

**Example:**
```bash
curl "https://api.woofi.com/woofi_pro/perps_volume"
```

### 16. Integration Endpoints — `/integration/pairs`, `/integration/tickers`, `/integration/pool_states` 🆕

Trading pairs, 24-hour ticker data, and pool states for third-party integrations.

**Trigger phrases**: "trading pairs", "ticker data", "pool state", "integration pairs", "fee rate", "pool liquidity"

**Example:**
```bash
curl "https://api.woofi.com/integration/pairs?network=arbitrum"
curl "https://api.woofi.com/integration/tickers?network=arbitrum"
curl "https://api.woofi.com/integration/pool_states?network=arbitrum"
```

**Pool states response includes:**
- `reserve` — Token reserve in the WooPP pool
- `fee_rate` — Trading fee rate (in basis points)
- `max_gamma` — Maximum gamma parameter for sPMM pricing
- `max_notional_swap` — Maximum notional swap size
- `cap_bal` — Maximum balance cap for the token
- `price` — Current oracle price (18-decimal fixed point)
- `spread` — Price spread from the oracle

### 17. Protocol Revenue — `/analytics/daily_fee` 🆕

Daily net protocol revenue breakdown for WOOFi Swap and WOOFi Pro.

**Trigger phrases**: "protocol revenue", "daily fee", "woofi revenue", "fee breakdown"

**Parameters:**
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (required): End date in YYYY-MM-DD format

**Example:**
```bash
curl "https://api.woofi.com/analytics/daily_fee?start_date=2026-03-01&end_date=2026-03-20"
```

**Response:**
```json
{
  "status": "ok",
  "data": [
    {
      "date": "2026-03-20",
      "swap": 1732.845286,   # Swap revenue (USD)
      "pro": 845.123456      # Pro perps revenue (USD)
    }
  ]
}
```

## Network Support Matrix

### Legacy API (api.woofi.com)

| Network | /stat | /source_stat | /token_stat | /yield | /earn_summary | /stakingv2 | /user_* | /integration | /swap |
|---------|-------|--------------|-------------|--------|---------------|------------|---------|--------------|-------|
| BSC | Yes | Yes | Yes | Yes | Yes | — | Yes | Yes | Yes |
| Avalanche | Yes | Yes | Yes | Yes | Yes | — | Yes | Yes | Yes |
| Polygon | Yes | Yes | Yes | Yes | Yes | — | Yes | Yes | Yes |
| Arbitrum | Yes | Yes | Yes | Yes | Yes | — | Yes | Yes | Yes |
| Optimism | Yes | Yes | Yes | Yes | Yes | — | Yes | Yes | Yes |
| Linea | Yes | Yes | Yes | Yes | Yes | — | Yes | Yes | Yes |
| Base | Yes | Yes | Yes | Yes | Yes | — | Yes | Yes | Yes |
| Mantle | Yes | Yes | Yes | Yes | Yes | — | Yes | Yes | Yes |
| Sonic | Yes | Yes | Yes | Yes | Yes | — | Yes | Yes | Yes |
| Berachain | Yes | Yes | Yes | Yes | Yes | — | Yes | Yes | Yes |
| HyperEVM | Yes | Yes | Yes | No | — | — | Yes | Yes | Yes |
| Monad | Yes | Yes | Yes | No | — | — | Yes | Yes | Yes |
| Solana | Yes | Yes | Yes | No | — | — | No | No | Yes |
| Fantom | Yes | Yes | Yes | Yes | Paused | — | Yes | Yes | Paused |
| zkSync | Yes | Yes | Yes | Yes | Paused | — | Yes | Yes | Paused |
| Polygon zkEVM | Yes | Yes | Yes | Yes | Paused | — | Yes | Yes | Paused |
| Sei | — | — | — | — | — | — | — | — | Pro only |
| (global) | — | — | — | — | — | Yes | — | — | — |

### v1 API (sapi.woofi.com) — NEW

| Network | Chain ID | /v1/quote | /v1/swap |
|---------|----------|-----------|----------|
| BSC | 56 | Yes | Yes |
| Avalanche | 43114 | Yes | Yes |
| Polygon | 137 | Yes | Yes |
| Arbitrum | 42161 | Yes | Yes |
| Optimism | 10 | Yes | Yes |
| Linea | 59144 | Yes | Yes |
| Base | 8453 | Yes | Yes |
| Mantle | 5000 | Yes | Yes |
| Sonic | 146 | Yes | Yes |
| Berachain | 80094 | Yes | Yes |
| HyperEVM | 714 | Yes | Yes |
| Monad | 10143 | Yes | Yes |
| Fantom | 250 | Yes | Yes |
| Polygon zkEVM | 1101 | Yes | Yes |

**Note**: v1 API uses `chain_id` instead of network name. Solana and Sei are not yet supported on v1 API.

## Common Patterns

### Get v1 quote: 1000 USDC → WBTC on Arbitrum (NEW v1 API)

```python
import requests

# Get quote (read-only, no execution)
response = requests.post(
    "https://sapi.woofi.com/v1/quote",
    json={
        "chain_id": 42161,
        "sell_token": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",  # USDC
        "buy_token": "0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f",  # WBTC
        "sell_amount": "1000",
        "slippage_pct": 0.5
    }
).json()

print(f"Expected receive: {response['buy_amount']} WBTC")
print(f"Price: {response['price']}")
print(f"Guaranteed price: {response['guaranteed_price']}")
```

### Execute swap: 1000 USDC → WBTC with tx generation (NEW v1 API)

```python
import requests

# Build swap transaction
response = requests.post(
    "https://sapi.woofi.com/v1/swap",
    json={
        "chain_id": 42161,
        "sell_token": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "buy_token": "0x2f2a2543b76a4166549f7aab2e75bef0aefc5b0f",
        "sell_amount": "1000",
        "to": "0xYourWalletAddress",
        "rebate_to": "0xYourWalletAddress",
        "signer_address": "0xYourWalletAddress"
    }
).json()

# Check if approval needed
if response["needs_approve"]:
    print("⚠️ Approval required first!")
    approve_tx = response["tx_steps"][0]
    print(f"Approve: {approve_tx['desc']}")
    print(f"  To: {approve_tx['to']}")
    print(f"  Data: {approve_tx['data']}")

# Swap transaction
swap_tx = response["tx_steps"][-1]
print(f"\nSwap: {swap_tx['desc']}")
print(f"  To: {swap_tx['to']}")
print(f"  Data: {swap_tx['data']}")
print(f"  Expected: {response['buy_amount']} WBTC")
```

### Get legacy quote: 0.1 ETH → USDC on Arbitrum

```python
import requests

# First, get token addresses from swap_support
r = requests.get("https://api.woofi.com/swap_support").json()
arb_tokens = r["data"]["arbitrum"]["token_infos"]
eth_addr = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
usdc_addr = "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8"

# Get quote
r = requests.get(
    "https://api.woofi.com/swap",
    params={
        "from_token": eth_addr,
        "to_token": usdc_addr,
        "from_amount": "100000000000000000",  # 0.1 ETH in wei
        "network": "arbitrum"
    }
).json()

if r["status"] == "ok":
    to_amount = int(r["data"]["to_amount"]) / 1e6  # USDC has 6 decimals
    print(f"0.1 ETH → ${to_amount:,.2f} USDC")
    print(f"Price impact: {r['data']['price_impact']}%")
```

### Get total volume across all chains (last 30d)

Use the script in `scripts/total_volume.py`:

```bash
python skills/woofi-data/scripts/total_volume.py --period 1m
```

### Get total TVL across all earn vaults

Use the script in `scripts/total_tvl.py`:

```bash
python skills/woofi-data/scripts/total_tvl.py
```

### Get protocol revenue for a date range

```python
import requests

r = requests.get(
    "https://api.woofi.com/analytics/daily_fee",
    params={"start_date": "2026-03-01", "end_date": "2026-03-20"}
).json()

total_swap = sum(d["swap"] for d in r["data"])
total_pro = sum(d["pro"] for d in r["data"])
print(f"Swap revenue: ${total_swap:,.2f}")
print(f"Pro revenue: ${total_pro:,.2f}")
```

### Quick single-chain query

```python
import requests

# Trading stats
r = requests.get("https://api.woofi.com/stat?period=1d&network=arbitrum").json()
volume_usd = int(r["data"][0]["volume_usd"]) / 1e18
print(f"Arbitrum 24h volume: ${volume_usd:,.0f}")

# Earn yields
r = requests.get("https://api.woofi.com/yield?network=base").json()
tvl = int(r["data"]["total_deposit"]) / 1e18
print(f"Base Earn TVL: ${tvl:,.0f}")

# WOO staking
r = requests.get("https://api.woofi.com/stakingv2").json()
woo_staked = int(r["data"]["total_woo_staked"]) / 1e18
print(f"Total WOO staked: {woo_staked:,.0f} WOO")

# Pool states
r = requests.get("https://api.woofi.com/integration/pool_states?network=arbitrum").json()
print(f"Pool data: {r['data']}")
```

## Gotchas

### v1 API (sapi.woofi.com) — NEW
1. **Chain ID required** — v1 API uses numeric `chain_id` (e.g., 42161), not network names
2. **Human-readable amounts** — `sell_amount` uses decimal format (e.g., `"1.5"`), NOT wei
3. **Sequential tx execution** — If `tx_steps` has multiple items, execute in order (approve → swap)
4. **`needs_approve` check** — Always check this flag before attempting swap
5. **Wallet signing required** — v1/swap returns tx data but doesn't broadcast — you must sign and submit
6. **Native asset address** — Use `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE` for ETH, BNB, etc.

### Legacy API (api.woofi.com)
1. **Wei conversion** — ALL USD values (`volume_usd`, `total_deposit`) are in wei. Always divide by 10^18.
2. **Token decimals vary** — USDC has 6 decimals, ETH has 18. Adjust `from_amount` and parse `to_amount` accordingly.
3. **Chain names** — Use exact names from the supported list. "arbitrum" not "arb", "optimism" not "op".
4. **Period buckets** — `1m` returns 30 days of daily buckets, not a single aggregated value. Sum all buckets for total.
5. **Staking is global** — `/stakingv2` doesn't take a network param — it's the same across all chains.
6. **Trader counts** — Do NOT sum `trader_count` across time buckets — each bucket is independently unique-per-period.
7. **Period `1d`** — Returns hourly buckets. All other periods return daily buckets.
8. **User endpoints** — Period values are `7d`, `14d`, `30d` (different from stat endpoints).
9. **Cross-chain queries** — Require separate requests per network, then manual aggregation. Exception: `/multi_total_stat` and `/user_trading_volumes` aggregate automatically.
10. **Address format** — All EVM addresses should be checksummed.
11. **Paused networks** — `fantom`, `zksync`, `polygon_zkevm` are excluded from `/earn_summary` and have `swap_enable=false`.
12. **Native ETH** — Use `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE` as the token address for ETH.
14. **v1 API amounts** — `sell_amount` is human-readable (e.g., "1.5"), NOT wei. But `buy_amount` in response still needs decimal parsing based on token decimals.

## Related Resources

- API docs: `https://api.woofi.com/llms.txt`
- Official docs: `https://learn.woo.org`
- Original skill: `https://github.com/woonetwork/woofi-skills`
- Python SDK: `https://github.com/woonetwork/woofi-python-sdk`
