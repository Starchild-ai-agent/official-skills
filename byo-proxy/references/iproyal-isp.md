# IPRoyal ISP (static residential) proxy reference

Loaded by `byo-proxy` when the user is configuring a **dedicated, permanent IP**.
Source of truth: <https://docs.iproyal.com/proxies/isp>.

## What this is

ISP proxies ("static residential") are IPs hosted at a premium ISP. Unlike the
residential pool, each IP is **dedicated to you** and **never rotates**.

| | Residential pool (`iproyal`) | ISP (`iproyal-isp`) |
|---|---|---|
| IP stability | rotates; sticky ≤ 7 days per session | permanent, never changes |
| Sharing | shared pool | dedicated to you |
| Billing | per GB (pay-as-you-go) | per IP, unlimited traffic |
| Endpoint | one gateway `geo.iproyal.com:12321` | **per-IP** `host:port` |
| Selection | `country-`/`state-`/`city-` param | which IP you bought |
| Sessions | `session-`/`lifetime-` params | unlimited, no params |

## Connecting

Each purchased proxy comes as a **proxy string**: `host:port` + `username:password`.

```bash
# HTTP/HTTPS
curl -x http://191.116.125.248:12323 --proxy-user aea1bcf5cb3:e8c6a622fe https://ifconfig.co/json

# SOCKS5 (separate port)
curl --socks5 191.116.125.248:12324 --proxy-user aea1bcf5cb3:e8c6a622fe https://ifconfig.co/json
```

So a URL is simply `http://<username>:<password>@<host>:<port>` — no `country-`,
`session-` or `lifetime-` parameters. This is why ISP credentials live per proxy in
`byo-proxy`, not as a single account pair in `.env`.

> Geo targeting alternative: IPRoyal also exposes ISP proxies through the gateway
> `geo.iproyal.com` (HTTP `12321`, SOCKS5 `32325`) with `_country-/_state-/_city-/_isp-`
> in the password. `byo-proxy` does **not** use this path — `iproyal` is the
> residential gateway and `iproyal-isp` is per-IP dedicated. Pick per-IP for a
> guaranteed fixed address.

## Registering in byo-proxy

```bash
python3 scripts/add_isp_proxy.py jp-1 \
    --host 191.116.125.248 --port 12323 --socks-port 12324 \
    --username aea1bcf5cb3 --password e8c6a622fe --label "Tokyo ISP"

python3 scripts/bind_skill.py web-crawler --provider iproyal-isp --proxy-id jp-1
python3 scripts/test_proxy.py iproyal-isp --proxy-id jp-1
```

`proxy_id` is a local nickname (letters, digits, `.`, `_`, `-`) — it is what bindings
reference, so the raw IP never appears in a binding.

## Pricing (informational)

Dedicated static IPs from **$2.00/IP**; term pricing 24h $1.80, 30d $2.70,
60d $2.55, 90d $2.40. Unlimited traffic per IP. 31+ locations, mostly US/EU.

## Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `ERR_PROXY_CONNECTION_FAILED` / timeout | wrong host/port, or proxy expired/reassigned | re-check the proxy string in the dashboard; re-run `add_isp_proxy.py` |
| `407 Proxy Authentication Required` | wrong username/password | re-register with the credentials from the ISP order |
| Auth works, site still blocks | that IP is burned for the site | different IP (buy another) — ISP IPs cannot rotate |
| `ISP proxy 'X' is not registered` | binding references an id not in `.byo-proxy.json` | `add_isp_proxy.py X ...`, or rebind |
| Connection succeeds but `exit_ip` differs from the bought IP | you hit the geo gateway, not the dedicated host | use the per-IP `host:port` from the proxy string |