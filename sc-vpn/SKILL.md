---
name: sc-vpn
version: 1.0.1
description: Route outbound HTTP traffic through SC-VPN Gateway for geo-restricted access. Use when a script or request is blocked by region restrictions and needs to appear from a specific country. Do NOT set global proxy — use per-request proxy only.
keywords: vpn, proxy, geo, region, ip, country, blocked, restricted, geo-restricted
triggers:
  - vpn
  - proxy through
  - different country
  - appear from
  - geo region
  - IP address from
  - access from japan
  - need a VPN
  - route through
  - geo blocked
  - region restricted
---

# SC-VPN Gateway

Internal VPN service for the Starchild platform. Provides exit nodes in **18 fixed countries** — accessible only from within the Starchild internal network. No credentials or setup needed.

## ⚠️ When to Use

**SC-VPN is a last resort, not a default.** Most agent HTTP traffic already goes through `sc-proxy` (the platform's transparent billing proxy for paid APIs). Setting a global VPN proxy will **break sc-proxy routing**.

Use SC-VPN **only** when:
- A specific request is **geo-blocked** or returns a region error
- You need to appear from a **specific country** for a particular API call
- A target website/API **refuses connections** from the default exit

**Always use per-request proxy** (pass `proxies=` to `requests.get()` or `-x` to `curl`). **Never set global `HTTP_PROXY` / `HTTPS_PROXY` environment variables**

## Available Countries

| Country | Code | Example Cities |
|---------|------|---------------|
| 🇦🇺 Australia | `au` | Adelaide, Sydney, Melbourne |
| 🇨🇭 Switzerland | `ch` | Zürich |
| 🇩🇪 Germany | `de` | Berlin, Frankfurt |
| 🇯🇵 Japan | `jp` | Tokyo, Osaka |
| 🇲🇾 Malaysia | `my` | Kuala Lumpur |
| 🇲🇽 Mexico | `mx` | Querétaro |
| 🇹🇭 Thailand | `th` | Bangkok |
| 🇿🇦 South Africa | `za` | Johannesburg |
| 🇧🇷 Brazil | `br` | São Paulo, Fortaleza |
| 🇦🇷 Argentina | `ar` | Buenos Aires |
| 🇸🇬 Singapore | `sg` | Singapore |
| 🇭🇰 Hong Kong | `hk` | Hong Kong |
| 🇬🇧 United Kingdom | `gb` | London, Manchester |
| 🇳🇱 Netherlands | `nl` | Amsterdam |
| 🇫🇷 France | `fr` | Paris, Marseille |
| 🇸🇪 Sweden | `se` | Stockholm, Malmö |
| 🇪🇸 Spain | `es` | Madrid |
| 🇮🇹 Italy | `it` | Milan, Rome |

**Only these 18 countries.** Requests for other regions are rejected (502). The specific server per country is auto-selected daily based on latency.

## Quick Start

### curl (per-request proxy)

```bash
# Route ONE request through Japan
curl -x "http://jp:x@sc-vpn.internal:8080" https://ifconfig.me

# Route ONE request through Brazil
curl -x "http://br:x@sc-vpn.internal:8080" https://example.com/api
```

### Python requests (per-request proxy)

```python
import requests

def vpn_proxy(region: str) -> dict:
    """Return proxy dict for a given region code."""
    return {
        "https": f"http://{region}:x@sc-vpn.internal:8080",
        "http":  f"http://{region}:x@sc-vpn.internal:8080",
    }

# Only the geo-blocked request goes through VPN
resp = requests.get("https://geo-restricted-api.example.com", proxies=vpn_proxy("jp"))

# All other requests go through normal sc-proxy routing (no proxies= arg)
resp2 = requests.get("https://api.coingecko.com/...")
```

### ❌ Do NOT do this

```bash
# WRONG — may influence other requests
export HTTP_PROXY="http://jp:x@sc-vpn.internal:8080"
export HTTPS_PROXY="http://jp:x@sc-vpn.internal:8080"
```

## Region Selection

The **username** in the proxy URL selects the exit country:

| Input | Resolves To |
|-------|-------------|
| `jp` or `japan` | Japan |
| `au` or `australia` | Australia |
| `de` or `germany` | Germany |
| `ch` or `switzerland` | Switzerland |
| `th` or `thailand` | Thailand |
| `br` or `brazil` | Brazil |
| `ar` or `argentina` | Argentina |
| `mx` or `mexico` | Mexico |
| `my` or `malaysia` | Malaysia |
| `za` or `south_africa` | South Africa |
| `sg` or `singapore` | Singapore |
| `hk` or `hong_kong` | Hong Kong |
| `gb` or `uk` or `united_kingdom` | United Kingdom |
| `nl` or `netherlands` | Netherlands |
| `fr` or `france` | France |
| `se` or `sweden` | Sweden |
| `es` or `spain` | Spain |
| `it` or `italy` | Italy |

## REST API

Base URL: `http://sc-vpn.internal:8081`

| Endpoint | Description |
|----------|-------------|
| `GET /api/tunnels` | Status of all 18 tunnels (region, latency, uptime) |
| `GET /api/status` | Gateway overview |
| `GET /api/usage` | Your traffic stats (identified by source IP) |
| `GET /health` | Health check |

## Rate Limits

| Limit | Default |
|-------|---------|
| Monthly quota per client | 500 GB |
| Max concurrent connections | 50 |
| Requests per second | 100 |

Clients identified by source IP. No API keys needed — internal network only.

## Verify It Works

```bash
# Your real exit IP
curl https://ifconfig.me

# VPN exit IP (should be different, from Japan)
curl -x "http://jp:x@sc-vpn.internal:8080" https://ifconfig.me
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `502 Bad Gateway: Unknown region` | Use one of: au, ch, de, jp, my, mx, th, za, br, ar, sg, hk, gb, nl, fr, se, es, it |
| `502 Bad Gateway: Tunnel not active` | Gateway may need restart — check `/api/status` |
| `400 Bad Request: No region specified` | Add username to proxy URL: `http://jp:x@sc-vpn.internal:8080` |
| DNS failure for `sc-vpn.internal` | Only accessible from Starchild internal network |
| Other requests broken after using VPN | You set global `HTTP_PROXY` — unset it immediately |