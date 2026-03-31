---
name: defillama
description: "DefiLlama DeFi analytics — TVL, fees, DEX volume, yields, stablecoins via native Python tools"
version: "2.0.0"
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

Native Python tools for DefiLlama DeFi analytics. No API key required.

## Tool Selection Guide

| Question type | Tool | NOT this |
|---|---|---|
| Top protocols by TVL | `defillama_tvl_rank(top_n=10)` | ❌ web_fetch |
| Specific protocol TVL & history | `defillama_protocol(slug="aave")` | ❌ web_search |
| Chain TVL comparison | `defillama_chains()` | ❌ cg_global |
| Chain TVL trend over time | `defillama_chain_history(chain="Ethereum")` | ❌ coin_chart |
| Top fees/revenue protocols | `defillama_fees(top_n=10)` | ❌ web_fetch |
| DEX volume ranking | `defillama_dex_volume(top_n=10)` | ❌ web_fetch |
| Yield pool discovery | `defillama_yields(min_apy=5, min_tvl=50000000)` | ❌ web_search |
| Stablecoin market caps | `defillama_stablecoins()` | ❌ cg_coins_markets |

## Common Slugs

Protocol slugs for `defillama_protocol()`:
- `aave`, `lido`, `makerdao`, `uniswap`, `compound-finance`
- `curve-dex`, `rocket-pool`, `eigenlayer`, `jito`, `raydium`

## Composite Queries

For "DeFi market snapshot" or multi-aspect questions, combine tools:
```
defillama_tvl_rank(top_n=5)      # Top protocols
defillama_fees(top_n=5)          # Top fee earners
defillama_dex_volume(top_n=5)    # Top DEXes
```

For protocol comparison (e.g. "Lido vs Rocket Pool"):
```
defillama_protocol(slug="lido")
defillama_protocol(slug="rocket-pool")
```
