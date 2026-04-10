---
name: defillama
description: DefiLlama API integration for DeFi analytics - TVL, stablecoin yields, vault/APY ranking, protocol revenue, fees, DEX volume, chain flows, bridges, and treasury data. Best for DeFi research, stablecoin farming, yield strategy screening, and protocol/chain market intelligence.
version: 2.1.2
tools:
  - defillama_tvl_rank
  - defillama_protocol
  - defillama_chains
  - defillama_chain_history
  - defillama_fees
  - defillama_dex_volume
  - defillama_yields
  - defillama_stablecoins
---

# DefiLlama Skill

Native Python tools for DefiLlama DeFi analytics. No API key required for most endpoints.

## Matching Keywords (intent triggers)

Use this skill when users ask about any of the following:

- **TVL**: TVL ranking, protocol TVL, chain TVL, TVL changes, DeFi market share
- **Stablecoin yield**: stablecoin yield, USDC/USDT APY, low-risk yield pools, safe yield
- **Yield / Farming**: APY ranking, yield pool screening, vault yield, lending APY, borrow rates, LSD/LRT yield
- **DEX / Fees / Revenue**: DEX volume, protocol fees, protocol revenue, revenue growth
- **Flows / Rotation**: capital flows, chain inflow/outflow, stablecoin netflow, liquidity rotation
- **Protocol Research**: protocol fundamentals, multi-protocol comparison, sector comparison, DeFi snapshot

Typical user prompts:
- "Which DEX has seen the strongest revenue growth recently?"
- "Find me some low-risk stablecoin yield options with decent returns."
- "Create a DeFi market snapshot for today (TVL / volume / fees)."
- "Compare ETH vs SOL on-chain flow changes over the last 30 days."

---

## Tool Selection Guide

> **ROOT CAUSE of all failures:** The model ignores defillama_* tools and falls back to web_search/web_fetch/CoinGecko. Every DeFi analytics question has a defillama_* tool. Use it. Do not search the web.

### Decision Tree — Pick Your Tool in 3 Steps

**STEP 1: Is the question about DeFi data?**
- TVL, fees, DEX volume, yields, stablecoins, chain capital flows → **GO TO STEP 2**
- Crypto price, market cap of a non-DeFi token → use coingecko tools

**STEP 2: What is the subject?**

| Subject | Keyword Triggers | CALL THIS TOOL |
|---|---|---|
| Protocol ranking | "top protocols", "TVL ranking", "biggest DeFi", "前10协议" | `defillama_tvl_rank(top_n=N)` |
| One specific protocol | "Aave TVL", "Lido", "Uniswap details", protocol name + "how much" | `defillama_protocol(slug="...")` |
| Chain comparison | "which chain", "ETH vs SOL TVL", "all chains", "链TVL排名" | `defillama_chains()` |
| Chain TVL over time | "30-day trend", "TVL history", "net inflow", "以太坊TVL趋势" | `defillama_chain_history(chain=X, days=N)` |
| Fees / revenue | "fees", "revenue", "协议手续费", "earns most", "24h fees" | `defillama_fees(top_n=N)` |
| DEX volume | "DEX volume", "trading volume", "top DEX", "Uniswap vs Raydium volume" | `defillama_dex_volume(top_n=N)` |
| Yields / APY | "yield", "APY", "best returns", "farming", "stablecoin pool" | `defillama_yields(min_apy=X, min_tvl=Y)` |
| Stablecoin market | "USDT", "USDC", "stablecoin market cap", "稳定币总市值" | `defillama_stablecoins()` |

**STEP 3: Multi-topic questions → call multiple tools**

- "DeFi market snapshot" → `defillama_tvl_rank` + `defillama_dex_volume` + `defillama_fees`
- "Solana DeFi analysis" → `defillama_chains()` + `defillama_dex_volume(chain="Solana")` + `defillama_yields(chain="Solana")`
- "Compare Lido vs Rocket Pool" → `defillama_protocol(slug="lido")` + `defillama_protocol(slug="rocket-pool")`

---

## Common Mistakes — Explicit Corrections

**❌ MISTAKE 1: Using `web_search` for any DeFi data**
```
WRONG:  web_search("Aave TVL 2024")
RIGHT:  defillama_protocol(slug="aave")
```
web_search returns stale articles. defillama_protocol returns live on-chain data.

**❌ MISTAKE 2: Using `web_fetch` for protocol or chain data**
```
WRONG:  web_fetch("https://defillama.com/chain/Ethereum")
RIGHT:  defillama_chain_history(chain="Ethereum", days=30)
```

**❌ MISTAKE 3: Using `cg_global_defi` INSTEAD OF defillama tools for DEX volume or TVL**
```
WRONG:  cg_global_defi() alone  ← returns aggregate stats only, not DEX rankings
RIGHT:  defillama_dex_volume(top_n=10)
OK:     defillama_dex_volume() + cg_global_defi()  ← combining is fine for context
```

**❌ MISTAKE 4: Using `cg_global` INSTEAD OF defillama tools for chain TVL**
```
WRONG:  cg_global() alone  ← returns total crypto market cap, not chain TVL
RIGHT:  defillama_chains()
OK:     defillama_chains() + cg_global()  ← combining for market context is fine
```

**❌ MISTAKE 5: Using `cg_coins_markets` for stablecoin data**
```
WRONG:  cg_coins_markets(ids="tether,usd-coin")
RIGHT:  defillama_stablecoins()
```
DefiLlama tracks stablecoins cross-chain with accurate supply data. CoinGecko does not.

**❌ MISTAKE 6: Using `cg_derivatives_exchanges` for DEX volume**
```
WRONG:  cg_derivatives_exchanges()   ← this is CEX derivatives (Binance futures, etc.)
RIGHT:  defillama_dex_volume()
```
These are completely different markets. DEX ≠ derivatives exchange.

**❌ MISTAKE 7: Not calling defillama_yields at all**
```
WRONG:  "I don't have data on DeFi yields."
RIGHT:  defillama_yields(min_apy=5, min_tvl=50000000, stablecoin_only=True)
```

**❌ MISTAKE 8: Using `coin_chart` for chain TVL trends**
```
WRONG:  coin_chart(coin_id="ethereum", days=30)  ← price chart, not TVL
RIGHT:  defillama_chain_history(chain="Ethereum", days=30)
```

---

## Quick-Reference: Do NOT Substitute

| If you're tempted to call... | Call this FIRST (primary) | OK to add for context |
|---|---|---|
| `web_search` for any DeFi question | Any `defillama_*` tool matching the subject | — |
| `web_fetch` on defillama.com | Any `defillama_*` tool matching the subject | — |
| `cg_global_defi` alone | `defillama_tvl_rank` or `defillama_dex_volume` | `cg_global_defi` as supplement |
| `cg_global` alone | `defillama_chains` | `cg_global` for market cap context |
| `cg_coins_markets` for stablecoins | `defillama_stablecoins` | — |
| `cg_derivatives_exchanges` | `defillama_dex_volume` | — |
| `coin_chart` for TVL history | `defillama_chain_history` | — |

---

## ⚠️ CRITICAL: Always Use DefiLlama Tools FIRST

**For any DeFi analytics question, use the defillama_* tools as PRIMARY data source. Do NOT use web_search, web_fetch as substitutes.**

## Tool Decision Table

| Question / Intent | CORRECT Tool | WRONG (never use) |
|---|---|---|
| Top protocols by TVL | `defillama_tvl_rank(top_n=10)` | web_search, cg_global_defi |
| Specific protocol TVL (Aave, Lido…) | `defillama_protocol(slug="aave")` | web_search, web_fetch |
| Chain TVL comparison (ETH, SOL, BSC…) | `defillama_chains()` | cg_global, cg_global_defi |
| Chain TVL trend / 30-day history | `defillama_chain_history(chain="Ethereum", days=30)` | web_search, coin_chart |
| Chain net inflow / outflow | `defillama_chain_history(chain=X, days=7)` | web_search, cg_global |
| Protocol fees / revenue (24h, 7d) | `defillama_fees(top_n=10)` | web_search, web_fetch |
| DEX trading volume | `defillama_dex_volume(top_n=10)` | cg_global_defi, cg_derivatives_exchanges |
| Yield pool discovery (APY, stablecoins) | `defillama_yields(min_apy=5, min_tvl=50000000)` | web_search |
| Stablecoin market caps | `defillama_stablecoins()` | cg_coins_markets |

---

## Key Rules

1. **DEX volume** → always `defillama_dex_volume`. CoinGecko returns CEX derivatives data, not DEX volume.
2. **Protocol fees/revenue** → always `defillama_fees`. Real-time on-chain fee data.
3. **Chain capital flows** → `defillama_chain_history` for multiple chains; compare TVL start vs end.
4. **Protocol comparison** → `defillama_protocol(slug=X)` for each, then compare.
5. **Never use web_search as primary** for any data defillama tools cover.
6. **Cross-skill OK** — combine defillama + coingecko for complex reports; defillama stays primary.

---

## Tool Reference

### defillama_tvl_rank(top_n=10)
Returns top N DeFi protocols by TVL with name, TVL in USD, chain, category.

### defillama_protocol(slug="aave")
Returns detailed data for one protocol: TVL, 7d/30d change, chain breakdown, category.
Protocol slugs: aave, lido, makerdao, uniswap, compound-finance, curve-dex, rocket-pool, eigenlayer, jito, raydium, pancakeswap

### defillama_chains()
Returns all chains ranked by TVL: name, TVL, 1d/7d/30d pct change.
Use for "which chain has most TVL?" or chain TVL comparison.

### defillama_chain_history(chain="Ethereum", days=30)
Returns daily TVL history for a specific chain over N days.
Use for "30-day trend", "TVL change over time", "net inflow/outflow last 7 days".
For chain flows: call for each chain (Ethereum, Solana, BSC, Arbitrum, Base…), compare start vs end TVL.

### defillama_fees(top_n=10)
Returns top protocols by fee revenue: 24h fees, 7d fees, protocol name.
Use for "which protocols earn most fees", "fee revenue ranking", "protocol income".

### defillama_dex_volume(top_n=10)
Returns DEX trading volume: 24h volume, 7d volume, protocol name, chain.
First row is usually the aggregate total across all DEXes.

### defillama_yields(min_apy=5, min_tvl=50000000, stable_only=True)
Returns yield pools meeting criteria: APY%, TVL, protocol, token, chain.

### defillama_stablecoins()
Returns stablecoin data: name, market cap, 24h change, peg price.
Use for "total stablecoin market cap", "USDT vs USDC dominance".

---

## Composite Queries

**DeFi market snapshot:**
```
defillama_tvl_rank(top_n=5)      # Top protocols by TVL
defillama_fees(top_n=5)          # Top fee earners (24h revenue)
defillama_dex_volume(top_n=5)    # Top DEXes by volume
```

**Protocol comparison (e.g. Lido vs Rocket Pool):**
```
defillama_protocol(slug="lido")
defillama_protocol(slug="rocket-pool")
defillama_fees(top_n=20)   # to get fee data for both
```

**Chain capital flows (past 7 days):**
```
defillama_chains()                              # current TVL snapshot with 7d pct change
defillama_chain_history(chain="Ethereum", days=7)
defillama_chain_history(chain="Solana", days=7)
# Compare TVL[0] vs TVL[-1] to get net inflow/outflow
```

**Solana ecosystem DeFi analysis:**
```
defillama_chain_history(chain="Solana", days=30)   # TVL trend
defillama_dex_volume(top_n=20)                      # filter for Solana DEXes
defillama_yields(min_apy=5)                          # Solana yield pools
```

---

## Common Protocol Slugs

| Protocol | Slug |
|---|---|
| Aave | `aave` |
| Lido | `lido` |
| MakerDAO | `makerdao` |
| Uniswap | `uniswap` |
| Compound | `compound-finance` |
| Curve | `curve-dex` |
| Rocket Pool | `rocket-pool` |
| EigenLayer | `eigenlayer` |
| Jito | `jito` |
| Raydium | `raydium` |
| PancakeSwap | `pancakeswap` |
