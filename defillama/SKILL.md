---
name: defillama
description: DefiLlama API - TVL, yields, fees, DEX volume, bridges, stablecoin data
version: 2.1.1
---

# DefiLlama API

Comprehensive DeFi data: TVL rankings, yield screening, protocol revenue, DEX volumes, chain flows.

## Quick Reference

| API | Base URL | Auth |
|-----|----------|------|
| **Free** | `https://api.llama.fi` | None |
| **Pro** | `https://pro-api.llama.fi/{API_KEY}` | Key in URL path |
| **Bridges** | `https://bridges.llama.fi` | None |

Env var: `DEFILLAMA_API_KEY` — used in pro URL path, NOT as HTTP header.

## Most Common Endpoints (Free — api.llama.fi)

| Task | Endpoint | Notes |
|------|----------|-------|
| TVL Top N | `GET /protocols` | Sort by `.tvl` |
| Protocol detail | `GET /protocol/{slug}` | e.g. `/protocol/aave` |
| Chain TVL history | `GET /v2/historicalChainTvl/{chain}` | `.date` + `.tvl` |
| All chains TVL | `GET /v2/chains` | Sum `.tvl` for global total |
| DEX volumes | `GET /overview/dexs?excludeChart=true` | `.total24h`, `.total7d` |
| Protocol fees | `GET /overview/fees?excludeChart=true` | `.total24h` |
| Stablecoins | `GET /stablecoins` | Market caps |
| Stablecoin flows | `GET /stablecoinchains` | By chain |
| Token prices | `GET /prices/current/{chain}:{addr}` | Batch: comma-separated |
| Historical prices | `GET /prices/historical/{ts}/{chain}:{addr}` | Unix timestamp |

## Pro Endpoints (require DEFILLAMA_API_KEY)

| Endpoint | Purpose |
|----------|---------|
| `/yields/pools` | All yield pools (APY, TVL, chain, project) |
| `/yields/chart/{pool_uuid}` | Historical APY for specific pool |

## Proxy Setup

```python
import os, requests
session = requests.Session()
host, port = os.getenv("PROXY_HOST"), os.getenv("PROXY_PORT")
if host and port:
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    proxy = f"http://{host}:{port}"
    session.proxies.update({"http": proxy, "https": proxy})

# Free
r = session.get("https://api.llama.fi/protocols", timeout=25)

# Pro
key = os.environ["DEFILLAMA_API_KEY"]
r = session.get(f"https://pro-api.llama.fi/{key}/yields/pools", timeout=25)
```

## Workflow Recipes

### DeFi TVL Top 10
```python
r = session.get("https://api.llama.fi/protocols", timeout=25)
protocols = sorted(r.json(), key=lambda x: x.get("tvl", 0), reverse=True)[:10]
for p in protocols:
    print(f"{p['name']}: ${p['tvl']/1e9:.2f}B")
```

### Stablecoin Yield Screening
```python
r = session.get(f"https://pro-api.llama.fi/{key}/yields/pools", timeout=25)
pools = [p for p in r.json()["data"]
         if p.get("stablecoin") and p.get("apy", 0) > 3 and p.get("tvlUsd", 0) > 1e6]
pools.sort(key=lambda x: x["apy"], reverse=True)
```

### DEX Volume Snapshot
```python
r = session.get("https://api.llama.fi/overview/dexs?excludeChart=true", timeout=25)
data = r.json()
print(f"Total 24h: ${data['total24h']/1e9:.2f}B")
```

## Gotchas

- **Free vs Pro URL**: Free = `api.llama.fi`, Pro = `pro-api.llama.fi/{KEY}`. Don't mix them.
- **`excludeChart=true`**: Always add for `/overview/*` endpoints — cuts response size 10x.
- **TVL nulls**: Some protocols return null TVL — filter with `if p.get("tvl")`.
- **Yield pool UUID**: Use `pool` field from `/yields/pools` for `/yields/chart/{uuid}`.
- **Stablecoin ≠ TVL**: Stablecoin endpoints are separate from TVL endpoints.
- **Number formatting**: TVL in raw USD (divide by 1e9 for billions). APY as percentage (3.5 = 3.5%).
