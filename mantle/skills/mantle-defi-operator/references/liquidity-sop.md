# Liquidity SOP

Use this flow for LP operations on Mantle (V3: Agni/Fluxion, LB: Merchant Moe).

## CRITICAL: Use CLI for All LP Operations

**ALWAYS use `mantle-cli` to build LP transactions and query positions.** The CLI handles pool resolution, tick range calculation, ABI encoding, and position enumeration.

```bash
# Read operations (no signing needed)
mantle-cli lp find-pools --token-a USDC --token-b USDe --json  # Discover ALL pools across ALL DEXes
mantle-cli lp positions --owner 0x... --json          # List all V3 positions
mantle-cli lp pool-state --token-a USDC --token-b WMNT --fee-tier 10000 --provider agni --json
mantle-cli lp suggest-ticks --token-a USDC --token-b WMNT --fee-tier 10000 --provider agni --json
mantle-cli lp analyze --token-a USDC --token-b WMNT --fee-tier 10000 --provider agni --investment-usd 1000 --json
mantle-cli defi lb-state --token-a USDC --token-b USDT0 --bin-step 1 --json

# Write operations (returns unsigned_tx)
mantle-cli lp add --provider agni --token-a USDC --token-b WMNT --amount-a 10 --amount-b 15 --recipient 0x... --json
mantle-cli lp add --provider agni --token-a USDC --token-b WMNT --amount-usd 1000 --recipient 0x... --json  # USD mode
mantle-cli lp remove --provider agni --token-id 12345 --liquidity 1000000 --recipient 0x... --json
mantle-cli lp remove --provider agni --token-id 12345 --percentage 50 --recipient 0x... --json  # Remove 50%
mantle-cli lp collect-fees --provider agni --token-id 12345 --recipient 0x... --json
```

## Step 1: Pool Discovery — ALWAYS Start Here

**Before any LP operation, use `find-pools` to discover ALL available pools across ALL DEXes.** This queries factory contracts on-chain — the authoritative source. Do NOT rely on DexScreener, subgraphs, or hardcoded pair lists.

```bash
mantle-cli lp find-pools --token-a USDC --token-b USDe --json
```

This returns every pool with its DEX provider, fee tier/bin step, pool address, and liquidity status. Example output for USDC/USDe:
- Agni fee=100 (0.01%) — $1.7M liquidity
- Merchant Moe bin=1 — active

**Use the results to pick the best pool**, then proceed with pool analysis.

## Step 2: Pool Analysis — ALWAYS Before Adding Liquidity

**After picking a pool, run `lp analyze` to understand APR, risk, and optimal range.**

```bash
mantle-cli lp analyze --token-a USDC --token-b WMNT --fee-tier 10000 --provider agni --investment-usd 5000 --json
```

The analysis returns:
- **Fee APR** based on 24h volume / TVL (base and concentrated across 10 range brackets)
- **Risk assessment**: TVL risk, volatility risk, concentration risk
- **Investment projections**: daily/weekly/monthly fee income for your investment amount
- **Recommended range**: auto-selected based on recent volatility (±3× daily movement)
- **Multi-range comparison**: ±1% through ±50% with APR, concentration factor, and rebalance risk

Use this data to make an informed range decision. Do NOT skip analysis and guess a tick range.

## Step 3: Pool State & Tick Suggestions

After analysis, get exact tick bounds:

### V3 Pools (Agni/Fluxion)
```bash
# 1. Check pool state — get current tick, price, liquidity
mantle-cli lp pool-state --token-a USDC --token-b WMNT --fee-tier 10000 --provider agni --json

# 2. Get tick range suggestions (pre-calculated wide/moderate/tight)
mantle-cli lp suggest-ticks --token-a USDC --token-b WMNT --fee-tier 10000 --provider agni --json

# 3. List existing positions
mantle-cli lp positions --owner 0x... --json
```

### Merchant Moe LB Pairs
```bash
# Check LB pair state — get active bin, nearby bin reserves
mantle-cli defi lb-state --token-a USDC --token-b USDT0 --bin-step 1 --json
```

## Step 4: Tick/Bin Range Selection

### V3 (Agni/Fluxion)
Use data from `lp analyze` (recommended range) and `lp suggest-ticks` to pick a range:
- **tight (±1-3%)**: stablecoins or low-volatility pairs — highest APR but frequent rebalancing
- **moderate (±5-10%)**: balanced risk/reward for most pairs
- **wide (±15-50%)**: volatile pairs, less rebalancing needed

Do NOT manually calculate ticks — use the CLI tools.

### Merchant Moe LB
Use `defi lb-state` to get the `active_id`, then:
- For stablecoins: use `delta_ids: [-2,-1,0,1,2]` centered on active bin
- For volatile: use wider range `delta_ids: [-5,-4,...,4,5]`
- Distribution: uniform `[1e18, 1e18, ...]` for even, or custom weights

## Step 5: Add Liquidity

### Amount modes

**Token amounts** (explicit control):
```bash
mantle-cli lp add --provider agni \
  --token-a USDC --token-b WMNT \
  --amount-a 10 --amount-b 15 \
  --tick-lower <from_analyze> --tick-upper <from_analyze> \
  --fee-tier 10000 --recipient 0x... --json
```

**USD amount** (automatic sizing — recommended for user-facing flows):
```bash
mantle-cli lp add --provider agni \
  --token-a USDC --token-b WMNT \
  --amount-usd 1000 \
  --tick-lower <from_analyze> --tick-upper <from_analyze> \
  --fee-tier 10000 --recipient 0x... --json
```

The `--amount-usd` mode:
- Fetches live token prices from DexScreener/DefiLlama
- Reads pool state to compute the correct token ratio for the target tick range (not a naive 50/50 split)
- Reports the computed amounts and prices in the response warnings
- Falls back to 50/50 for full-range positions or if pool read fails

### Merchant Moe
```bash
mantle-cli lp add --provider merchant_moe \
  --token-a USDC --token-b USDT0 \
  --amount-a 100 --amount-b 100 \
  --bin-step 1 --active-id <from_lb_state> \
  --delta-ids '[-2,-1,0,1,2]' \
  --distribution-x '[200000000000000000,200000000000000000,200000000000000000,200000000000000000,200000000000000000]' \
  --distribution-y '[200000000000000000,200000000000000000,200000000000000000,200000000000000000,200000000000000000]' \
  --recipient 0x... --json
```

## Step 6: Fee Collection (V3)

```bash
# Check accrued fees first
mantle-cli lp positions --owner 0x... --json
# Look for tokens_owed0 / tokens_owed1 > 0

# Collect fees
mantle-cli lp collect-fees --provider agni --token-id 12345 --recipient 0x... --json
```

## Step 7: Remove Liquidity

### V3 — Exact amount
```bash
mantle-cli lp remove --provider agni \
  --token-id 12345 --liquidity <amount> \
  --recipient 0x... --json
```

### V3 — Percentage mode (recommended for user-facing flows)
```bash
# Remove 50% of position
mantle-cli lp remove --provider agni \
  --token-id 12345 --percentage 50 \
  --recipient 0x... --json

# Remove all
mantle-cli lp remove --provider agni \
  --token-id 12345 --percentage 100 \
  --recipient 0x... --json
```

The `--percentage` mode reads the position's current liquidity on-chain and calculates the exact amount to remove. No need to manually query `lp positions` for the raw liquidity number.

### Merchant Moe
```bash
mantle-cli lp remove --provider merchant_moe \
  --token-a USDC --token-b USDT0 \
  --bin-step 1 \
  --ids '[8388608,8388609,8388610]' \
  --amounts '[1000000,1000000,1000000]' \
  --recipient 0x... --json
```

## Step 8: Post-operation Verification

- Re-read positions: `lp positions --owner 0x... --json`
- Check token balances changed as expected
- For V3: verify `in_range` status if market moved
- For Moe: verify bin balances via `defi lb-state`

## Common Pitfalls

- **Skipping pool analysis**: ALWAYS run `lp analyze` before adding liquidity — it shows APR, risk, and recommended range
- **Skipping pool discovery**: ALWAYS run `lp find-pools` first — it finds pools DexScreener misses (e.g. Agni fee=0.01% stablecoin pools)
- **Full-range V3 LP**: extremely capital-inefficient — always use analysis + tick suggestions to pick a range
- **Wrong active_id for Moe**: always read fresh from `defi lb-state`, never hardcode
- **Missing approve**: both tokens must be approved for the router/position manager before adding
- **Manual amount calculation**: use `--amount-usd` instead of manually computing token splits from prices
- **Manual liquidity lookup for removal**: use `--percentage` instead of manually reading position liquidity
- **`from` field**: NEVER add to unsigned_tx
- **V3 position enumeration**: `lp positions` discovers all positions across both Agni and Fluxion
- **Fee harvesting**: use `lp collect-fees` standalone — no need to remove liquidity to collect fees
