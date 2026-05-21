---
name: defillama
description: |
  DeFi analytics: protocol TVL, stablecoin yields, fees, DEX volume, bridges, treasuries.

  Use when screening yield strategies, comparing protocols, or tracking chain flows (e.g. best USDC yield, Uniswap fees, Arbitrum TVL).
version: 2.2.3
delivery: script

---


# DefiLlama API

> **Script-mode skill (PoC).** This skill is NOT registered as Anthropic
> tools. To use it, read this file, then run `python` in `bash` and import
> from `exports.py`. See **Script Usage** section below.

## Script Usage

This skill ships a single `exports.py` with all functions. Call it from a
`bash` block like this:

```bash
python3 - <<'EOF'
import sys, json
sys.path.insert(0, "/data/workspace/skills/defillama")
from exports import protocols, chains, yield_pools, dex_overview, fees_overview

# Top 10 protocols by TVL
data = protocols()
top = sorted(data, key=lambda p: p.get("tvl") or 0, reverse=True)[:10]
print(json.dumps([{"name": p["name"], "tvl": p["tvl"]} for p in top], indent=2))
EOF
```

Available functions in `exports.py`: `protocols`, `chains`, `protocol_tvl`,
`yield_pools`, `dex_overview`, `fees_overview`, `revenue_overview`,
`stablecoins`, `bridges`, `treasury`. Read `exports.py` directly for
signatures.

**Trit**: -1 (MINUS - Validator/Data Source)
**Color**: #4A90D9 (Cold blue, 210°)

Comprehensive DeFi data from DefiLlama's API ecosystem.


## Function Reference (signatures)

All functions are in `exports.py`. Call from a `bash` block after
`sys.path.insert(0, "/data/workspace/skills/defillama")`.

### Protocols & TVL
| Function | Description |
|---|---|
| `protocols()` | List all protocols with current TVL, chain breakdown, category. Returns list of dicts. |
| `protocol(slug)` | Detailed history for one protocol (slug from `protocols()`). |
| `chains()` | All supported chains with current TVL. |
| `chain_tvl_history(chain)` | Daily TVL series for one chain. |
| `global_tvl_history()` | Global daily TVL series. |

### Stablecoins
| Function | Description |
|---|---|
| `stablecoins(include_prices=True)` | All stablecoins with circulating supply per chain. |
| `stablecoin_chains()` | Per-chain stablecoin totals. |

### Yields
| Function | Description |
|---|---|
| `yield_pools()` | All yield pools with APY, TVL, project, chain. |
| `yield_chart(pool_id)` | Historical APY/TVL for one pool (pool_id from `yield_pools()`). |

### Volume / Fees / Revenue
| Function | Description |
|---|---|
| `dex_overview(exclude_chart=True)` | Aggregated DEX volume across all chains. |
| `dex_overview_chain(chain, exclude_chart=True)` | DEX volume for one chain. |
| `fees_overview(exclude_chart=True)` | Aggregated fees+revenue across all protocols. |
| `fees_overview_chain(chain, exclude_chart=True)` | Per-chain fees breakdown. |

### Bridges
| Function | Description |
|---|---|
| `bridges()` | List all bridges with volume stats. |
| `bridge_chain_volume(chain)` | Bridge volume by chain. |
| `bridge_volume(bridge_id, start_timestamp=None, end_timestamp=None)` | Time series for one bridge. |

### Prices
| Function | Description |
|---|---|
| `current_prices(coins)` | Current prices. `coins` = list/string like `"ethereum:0x...,coingecko:bitcoin"`. |
| `historical_prices(coins, timestamp)` | Prices at a specific unix timestamp. |

## Matching Keywords (intent triggers)

Use this skill when users ask about any of the following:

- **TVL**: TVL ranking, protocol TVL, chain TVL, TVL changes, DeFi market share
- **Stablecoin yield**: stablecoin yield, USDC/USDT APY, low-risk yield pools, safe yield, fixed-income-like DeFi
- **Yield / Farming**: APY ranking, yield pool screening, vault yield, lending APY, borrow rates, LSD/LRT yield
- **DEX / Fees / Revenue**: DEX volume, protocol fees, protocol revenue, revenue growth, which DEX revenue is growing fastest
- **Flows / Rotation**: capital flows, chain inflow/outflow, stablecoin netflow, liquidity rotation
- **Protocol Research**: protocol fundamentals, multi-protocol comparison, sector comparison, DeFi snapshot/report

Typical user prompts this skill should match:
- “Which DEX has seen the strongest revenue growth recently?”
- “Find me some low-risk stablecoin yield options with decent returns.”
- “Create a DeFi market snapshot for today (TVL / volume / fees).”
- “Compare ETH vs SOL on-chain flow changes over the last 30 days.”

## Base URLs

| API | Base URL | Auth |
|-----|----------|------|
| **Free API** | `https://api.llama.fi` | None (no key needed) |
| Pro API | `https://pro-api.llama.fi/{API_KEY}` | Key in path `/API_KEY/endpoint` |
| Bridge API | `https://bridges.llama.fi` | None |

> **Key rule**: Use `https://api.llama.fi` for all **free endpoints** (TVL, chains, DEX, fees, prices).
> Use `https://pro-api.llama.fi/{API_KEY}` ONLY for **pro endpoints** (yields, derivatives, emissions).
> Env var: `DEFILLAMA_API_KEY` — used in pro URL path, NOT as HTTP header.

## Most Common Endpoints (Start Here)

For 90% of DeFi analytics tasks, use these free endpoints (`api.llama.fi`):

| Task | Endpoint | Example |
|------|----------|---------|
| TVL Top N protocols | `GET /protocols` | Sort by `.tvl` field |
| Single protocol detail | `GET /protocol/{slug}` | e.g. `/protocol/aave` |
| Chain TVL history | `GET /v2/historicalChainTvl/{chain}` | `.date` + `.tvl` fields |
| DEX volumes | `GET /overview/dexs?excludeChart=true` | `.total24h`, `.total7d` |
| Protocol fees | `GET /overview/fees?excludeChart=true` | `.total24h` |
| All chains TVL | `GET /v2/chains` | Sum `.tvl` for global total |

> ⚠️ **Pro endpoints** (`/yields/*`, `/emissions`, etc.) require `DEFILLAMA_API_KEY` in the URL path.

## Proxy Requirement (sc-proxy)

When using fake API keys (for example `fake-defillama-key-12345`), requests **must** go through sc-proxy so the key can be replaced upstream.

- Env key name: `DEFILLAMA_API_KEY`
- Auto proxy detection envs: `PROXY_HOST`, `PROXY_PORT`
- If `HTTP_PROXY` / `HTTPS_PROXY` are unset, direct requests may hit upstream and return key errors.

### Python template (recommended)

```python
import os
import requests

host = os.getenv("PROXY_HOST")
port = os.getenv("PROXY_PORT")
session = requests.Session()
if host and port:
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"  # IPv6-safe
    proxy = f"http://{host}:{port}"
    session.proxies.update({"http": proxy, "https": proxy})

# Free endpoint (no key needed):
r_free = session.get("https://api.llama.fi/protocols", timeout=25)
print("Free:", r_free.status_code)

# Pro endpoint (key in URL path):
api_key = os.environ["DEFILLAMA_API_KEY"]
r_pro = session.get(f"https://pro-api.llama.fi/{api_key}/yields/pools", timeout=25)
print("Pro:", r_pro.status_code)
```

### Quick test commands

```bash
set -a && source .env && set +a
python3 - << 'PY'
import os, requests
s = requests.Session()
host, port = os.getenv('PROXY_HOST'), os.getenv('PROXY_PORT')
if host and port:
    if ':' in host and not host.startswith('['):
        host = f'[{host}]'
    p = f'http://{host}:{port}'
    s.proxies.update({'http': p, 'https': p})

# Free endpoint
r1 = s.get('https://api.llama.fi/protocols', timeout=25)
print('free /protocols:', r1.status_code)

# Pro endpoint
k = os.environ['DEFILLAMA_API_KEY']
r2 = s.get(f'https://pro-api.llama.fi/{k}/yields/pools', timeout=25)
print('pro /yields/pools:', r2.status_code)
PY
```

## Quick Reference

### TVL & Protocols
```bash
# All protocols with TVL
GET /protocols

# Single protocol detail
GET /protocol/{slug}

# Chain TVL
GET /v2/chains
GET /v2/historicalChainTvl/{chain}
```

### Prices
```bash
# Current prices (chain:address format)
GET /coins/prices/current/{coins}

# Historical
GET /coins/prices/historical/{timestamp}/{coins}

# Chart data
GET /coins/chart/{coins}?period=30d
```

### Yields (Pro)
```bash
GET /yields/pools           # All yield pools
GET /yields/chart/{pool}    # Pool history
GET /yields/poolsBorrow     # Borrow rates
GET /yields/perps           # Perp funding
GET /yields/lsdRates        # LSD rates
```

### Volume
```bash
GET /overview/dexs?excludeChart=true              # DEX volumes (recommended)
GET /overview/dexs/{chain}?excludeChart=true      # Chain DEX
GET /summary/dexs/{protocol}                       # Protocol detail
GET /overview/options?excludeChart=true           # Options
GET /overview/derivatives?excludeChart=true       # Derivatives (Pro)
```

### Fees & Revenue
```bash
GET /overview/fees?excludeChart=true              # All fees/revenue (recommended)
GET /overview/fees/{chain}?excludeChart=true      # Chain fees
GET /summary/fees/{protocol}                      # Protocol fees
# dataType: dailyFees | dailyRevenue | dailyHoldersRevenue
```

### Bridges
```bash
# Base: https://bridges.llama.fi
GET /bridges                        # All bridges
GET /bridge/{id}                    # Bridge detail
GET /bridgevolume/{chain}           # Volume by chain
GET /transactions/{id}              # Bridge txs
```

### DAT (Digital Asset Treasury)
```bash
GET /dat/institutions               # All institutions
GET /dat/institutions/{symbol}      # e.g., MSTR
```

## Usage Script

```clojure
;; See scripts/defillama.bb for full implementation
(require '[defillama :as dl])

;; TVL
(dl/protocols)
(dl/protocol "aave")
(dl/chain-tvl "Ethereum")

;; Prices
(dl/price "ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")
(dl/price-chart "coingecko:ethereum" {:period "30d"})

;; Yields
(dl/yield-pools)
(dl/pool-chart "747c1d2a-c668-4682-b9f9-296708a3dd90")

;; Volumes
(dl/dex-overview)
(dl/dex-protocol "uniswap")

;; Fees
(dl/fees-overview)
(dl/fees-protocol "hyperliquid")
```

## Endpoint Categories

### Free Endpoints
- `/protocols`, `/protocol/{slug}`, `/tvl/{slug}`
- `/v2/chains`, `/v2/historicalChainTvl`
- `/coins/prices/*`, `/coins/chart/*`
- `/overview/dexs`, `/overview/options`
- `/overview/fees`, `/summary/fees/*`

### Pro Endpoints (API Key Required)
- `/yields/*` - All yield endpoints (stablecoin pools, APY ranking, borrow/perps/LSD)
- `/overview/derivatives`
- `/tokenProtocols/{symbol}`
- `/inflows/{protocol}/{timestamp}`
- `/chainAssets`
- `/emissions`, `/emission/{protocol}`
- `/categories`, `/forks`, `/oracles`
- `/entities`, `/treasuries`
- `/hacks`, `/raises`
- `/etfs/*`, `/dat/*`
- Bridge endpoints on bridges.llama.fi

## Response Patterns

### TVL Response
```json
{"id": "2269", "name": "Aave", "tvl": 5200000000, "chains": ["Ethereum"]}
```

### Price Response
```json
{"coins": {"ethereum:0x...": {"price": 0.999, "symbol": "USDC", "confidence": 0.99}}}
```

### Yield Pool Response
```json
{"pool": "uuid", "chain": "Ethereum", "project": "aave-v3", "apy": 3.5, "tvlUsd": 1500000000}
```

## GF(3) Integration

This skill serves as MINUS (-1) validator in triads:
- Provides authoritative DeFi data
- Validates protocol metrics
- Constrains analysis with real data

Compose with:
- `aptos-agent` (+1): Execute based on data
- `exa-search` (0): Enrich with web context
## Output Format Guidelines (Chinese/English Queries)

Always format DeFi data responses as human-readable markdown. Support both Chinese and English queries.

### Number Formatting
- TVL ≥ $1B → `$X.XXB`; TVL ≥ $1M → `$XXXM`
- APY → `XX.X%`
- 24h changes → `+X.X%` or `-X.X%`
- Always include units: `$`, `%`, `B` (billion), `M` (million)

### Recommended Output Templates

**TVL Leaderboard**:
```markdown
| # | Protocol | TVL | Chains |
|---|--------------|-----|-----------|
| 1 | Aave V3      | $24.7B | Ethereum, Arbitrum |
```

**Yield Pools**:
```markdown
| Pool | APY | TVL | Risk |
|---------|-----|-----|---------|
| USDC    | 5.2% | $500M | ✅ Low risk |
```

**Market Snapshot**:
```markdown
| Metric | Value |
|------------|-----------|
| Total TVL       | $96B       |
| DEX 24h volume  | $5.7B      |
| Fees 24h        | $49M       |
```

### Risk Labels
Always include risk indicators for yield pools:
- `✅ Low risk` — stable APY < 20%, no IL risk
- `⚠️ Medium risk` — APY 20-100%, or IL risk present
- `🔴 High risk` — APY > 100% (likely incentive-driven, unsustainable)

### Tip: excludeChart Parameter
For volume/fee overview endpoints, always add `?excludeChart=true` to reduce response size:
```bash
GET /overview/dexs?excludeChart=true    # DEX volumes (much faster)
GET /overview/fees?excludeChart=true    # Fee data (much faster)
```

## Common Pitfalls & Gotchas

### 1. Wrong Base URL for Free Endpoints
❌ WRONG: `https://pro-api.llama.fi/protocols` → returns 404 "Path needs to start with /yields/..."
✅ CORRECT: `https://api.llama.fi/protocols`

Free endpoints NEVER go through `pro-api.llama.fi`.

### 2. Pro Endpoint Without API Key
❌ WRONG: `https://pro-api.llama.fi/yields/pools` → 401 or wrong route
✅ CORRECT: `https://pro-api.llama.fi/{DEFILLAMA_API_KEY}/yields/pools`

The API key is in the **URL path**, not in a header.

### 3. Missing `excludeChart=true` for Volume/Fee Endpoints
Without this param, `/overview/dexs` returns large chart history arrays.
Always add `?excludeChart=true` for summary queries.

### 4. Handling TVL Null Values
When sorting protocols by TVL, filter first:
```python
valid = [p for p in protocols if isinstance(p.get('tvl'), (int, float)) and p['tvl'] > 0]
```

### 5. Stablecoins vs TVL
DefiLlama's chain TVL includes ALL DeFi assets, not just stablecoins.
For stablecoin-specific flows, use the `stablecoins.llama.fi` API (separate from pro-api).
When asked about "stablecoin flows", the chain TVL change is a reasonable proxy.

### 6. Yields Pool UUID
The `pool` field in `/yields/pools` is a UUID like `"747c1d2a-c668-4682-b9f9-296708a3dd90"`.
Use this UUID (not token address) for `/yields/chart/{pool}` history.

### 7. Stablecoin Yield Screening Baseline
For “conservative stablecoin yield” requests, start with this baseline filter:
- `stablecoin == true`
- `tvlUsd >= 50_000_000`
- `apy` between `2` and `20` (drop extreme incentive spikes)
- `ilRisk == "no"`
- Prefer `exposure == "single"` for conservative profiles

## Workflow Examples (Agent Recipes)

### Recipe 1: DeFi TVL Top 10 (1 call)
```python
r = requests.get("https://api.llama.fi/protocols")
protocols = r.json()
top10 = sorted([p for p in protocols if p.get('tvl',0) > 0], key=lambda x: x['tvl'], reverse=True)[:10]
# Output: markdown table with | # | Protocol | TVL | Chain |
```

### Recipe 2: ETH vs SOL 30-day TVL comparison (2 calls)
```python
r1 = requests.get("https://api.llama.fi/v2/historicalChainTvl/Ethereum")
r2 = requests.get("https://api.llama.fi/v2/historicalChainTvl/Solana")
# Filter last 30d: [d for d in r1.json() if d['date'] >= time.time() - 30*86400]
# Output: | Chain | TVL 30d ago | TVL today | Change % |
```

### Recipe 3: Stablecoin yield shortlist (1 call)
```python
r = requests.get(f"https://pro-api.llama.fi/{API_KEY}/yields/pools")
raw = r.json()
pools = raw.get('data', raw) if isinstance(raw, dict) else raw
safe = [p for p in pools
        if p.get('stablecoin') is True
        and (p.get('tvlUsd') or 0) >= 50_000_000
        and (p.get('apy') or 0) >= 2
        and (p.get('apy') or 0) <= 20
        and p.get('ilRisk') == 'no']
top = sorted(safe, key=lambda x: x.get('apy', 0), reverse=True)[:10]
# Output: | Project | Chain | Symbol | APY | TVL | Risk |
```

### Recipe 4: DeFi Market Snapshot (3 calls)
```python
chains = requests.get("https://api.llama.fi/v2/chains").json()
dexs   = requests.get("https://api.llama.fi/overview/dexs?excludeChart=true").json()
fees   = requests.get("https://api.llama.fi/overview/fees?excludeChart=true").json()
# total_tvl = sum(c['tvl'] for c in chains if isinstance(c.get('tvl'), (int,float)))
# Output: snapshot table with TVL, DEX 24h vol, Fee 24h
```

### Recipe 5: Protocol TVL spike analysis (2 calls)
```python
r1 = requests.get("https://api.llama.fi/protocols")  # find protocol with big change_1d
r2 = requests.get(f"https://api.llama.fi/protocol/{slug}")  # get chainTvls detail
# Output: | Hypothesis | Explanation | How to verify | (table + step-by-step verification)
```

## Stablecoin Data

For stablecoin-specific analytics (distinct from general TVL), use the stablecoins API:

```bash
# Stablecoins overview (separate from pro-api)
GET https://stablecoins.llama.fi/stablecoins?includePrices=true

# Chain-specific stablecoin data
GET https://stablecoins.llama.fi/stablecoincharts/{chain}
# chain = "Ethereum", "Solana", "BSC", etc.

# All chains stablecoin summary
GET https://stablecoins.llama.fi/stablecoinchains
```

When users ask about "stablecoin net flows" or "stablecoin inflows":
1. Use `stablecoincharts/{chain}` for 30-day stablecoin TVL change (more accurate than general TVL)
2. Or use `/v2/historicalChainTvl/{chain}` as proxy if stablecoin API is unavailable

## Yields Pool Data Handling

The `/yields/pools` response is `{"data": [...], "status": "success"}`:

```python
r = session.get(f"https://pro-api.llama.fi/{api_key}/yields/pools")
raw = r.json()
pools = raw.get('data', raw) if isinstance(raw, dict) else raw
# Filter example: TVL > $50M and APY > 0
filtered = [p for p in pools if p.get('tvlUsd', 0) >= 50_000_000 and (p.get('apy') or 0) > 0]
```

**Key pool fields**:
| Field | Type | Description |
|-------|------|-------------|
| `pool` | UUID string | Unique pool identifier |
| `chain` | string | Chain name |
| `project` | string | Protocol name |
| `symbol` | string | Token pair (e.g. "USDC-WETH") |
| `tvlUsd` | number | TVL in USD |
| `apy` | number | Current APY % |
| `apyBase` | number | Base APY (lending/trading fees) |
| `apyReward` | number | Incentive APY (token rewards) |
| `ilRisk` | "yes"/"no" | Impermanent loss risk |
| `exposure` | "single"/"multi" | Single vs multi-asset exposure |
| `apyPct7D` | number | APY change past 7 days |
