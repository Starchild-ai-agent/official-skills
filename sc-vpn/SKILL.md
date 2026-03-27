---
name: sc-vpn
version: 1.0.0
description: Route outbound HTTP traffic through SC-VPN Gateway for geo-restricted access. Per-request proxy only — never set global proxy.
keywords: vpn, proxy, geo, region, blocked, restricted
triggers: [vpn, proxy through, different country, geo blocked, region restricted]
---

# SC-VPN Gateway

Internal VPN with exit nodes in **10 countries**. No credentials needed — internal network only.

**⚠️ Last resort only.** Most traffic goes through sc-proxy. Global VPN proxy breaks sc-proxy routing. Always use **per-request proxy**.

## Countries

`au` Australia | `ch` Switzerland | `de` Germany | `jp` Japan | `my` Malaysia | `mx` Mexico | `th` Thailand | `za` South Africa | `br` Brazil | `ar` Argentina

## Usage

### curl
```bash
curl -x "http://jp:x@sc-vpn.internal:8080" https://ifconfig.me
```

### Python requests
```python
import requests
proxy = {"https": "http://jp:x@sc-vpn.internal:8080", "http": "http://jp:x@sc-vpn.internal:8080"}
resp = requests.get("https://geo-restricted-api.example.com", proxies=proxy)
```

**❌ NEVER** set global `HTTP_PROXY`/`HTTPS_PROXY` env vars.

## REST API

Base: `http://sc-vpn.internal:8081`

| Endpoint | Purpose |
|----------|---------|
| `GET /api/tunnels` | All tunnel status |
| `GET /api/status` | Gateway overview |
| `GET /api/usage` | Traffic stats |
| `GET /health` | Health check |

## Limits

500 GB/month | 50 concurrent connections | 100 req/s

## Troubleshooting

| Error | Fix |
|-------|-----|
| `502 Unknown region` | Use valid code: au, ch, de, jp, my, mx, th, za, br, ar |
| `502 Tunnel not active` | Check `/api/status`, may need restart |
| DNS failure `sc-vpn.internal` | Only accessible from Starchild internal network |
| Other requests broken | You set global proxy — unset immediately |
