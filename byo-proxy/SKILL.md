---
name: byo-proxy
version: 0.2.0
description: |
  Bring-your-own proxy: per-skill country bindings (rotating + sticky sessions) and dedicated static IPs, opt-in routing.

  Use when the user wants paid residential/static IPs or per-skill geo routing (e.g. bind web-crawler to JP, add IPRoyal account, pin one fixed IP to a skill, route this scrape via DE).
delivery: script
metadata:
  starchild:
    emoji: "🌐"
    skillKey: byo-proxy
    requires:
      bins: [python3]
user-invocable: true
author: starchild
tags: [proxy, residential, static-ip, geo, byo, iproyal]

---

# byo-proxy — bring-your-own proxy

Users supply their own proxy account (currently **IPRoyal**); this skill stores
the credentials, maintains a `skill → provider` binding table, and exposes a tiny
Python API that other skills can opt into.

This skill **does not run a proxy server** and **does not intercept any traffic**.
It is a configuration center plus a URL builder. Other skills only behave differently
if they explicitly `import` from `exports.py`.

## Boundaries vs. existing proxy skills

| Skill | What it does | When |
|---|---|---|
| `sc-vpn` | Internal VPN gateway, 18 fixed countries, no auth | Last resort for geo-blocked requests inside Starchild |
| `transparent-proxy-maintenance` | Maintain the platform's billing proxy plugins | Ops work on `sc-proxy` |
| **`byo-proxy`** (this) | Manage user's own provider keys + per-skill bindings | User wants residential IPs, paid accounts, country granularity beyond sc-vpn's 18, or a dedicated fixed IP |

## Supported providers

| Provider | Kind | Endpoint | IP behaviour | Auth |
|---|---|---|---|---|
| `iproyal` | gateway | `geo.iproyal.com:12321` | rotates; sticky ≤ 7 days per session | account username + password |
| `iproyal-isp` | isp | **per-IP** `host:port` (e.g. `191.116.125.248:12323`) | **dedicated, never changes** | per-proxy username + password |

Two shapes of "fixed IP":

- **Sticky session** (`iproyal` + `--session` + `--sticky`) → same exit IP for up to
  **7 days**, then pool rotation can move it. Cheap (per GB).
- **Dedicated static IP** (`iproyal-isp`) → an IP reserved for you that **never
  changes**. Priced per IP, unlimited traffic. This is the "permanent fixed IP".

Adding more providers later: add an entry to `PROVIDERS` + a URL builder in
`exports.py`. See `references/iproyal.md` (residential) and
`references/iproyal-isp.md` (dedicated).

## Storage

- **Account credentials** (gateway providers) → `/data/workspace/.env` (same convention
  as `polymarket`, `birdeye`, `coingecko`). Keys: `IPROYAL_USERNAME`, `IPROYAL_PASSWORD`.
- **Bindings + ISP proxy inventory** → `/data/workspace/.byo-proxy.json`:
  ```json
  {
    "bindings": { "web-crawler": { "provider": "iproyal", "country": "jp",
                                   "session": "crawler-jp", "sticky_minutes": 360 } },
    "isp_proxies": { "jp-1": { "host": "191.116.125.248", "port": 12323,
                               "socks_port": 12324, "username": "…", "password": "…",
                               "label": "Tokyo ISP" } }
  }
  ```
  ISP credentials are per-IP, so they live here (keyed by local `proxy_id`) rather
  than in `.env`. Both files are edited only through scripts; agents should not
  hand-edit. Legacy bindings-only files are migrated automatically on next save.

## User workflow

```bash
SKILL=/data/workspace/skills/byo-proxy

# ── Residential gateway (rotating / sticky) ──────────────────────────────────
# 0. One-shot onboarding — prompts for creds only if missing, binds, live-tests:
python3 $SKILL/scripts/onboard.py web-crawler --provider iproyal --country jp

# 1. Register credentials (interactive — prompts for username/password)
python3 $SKILL/scripts/setup_provider.py iproyal

# 2. Bind a skill (long-term preference)
python3 $SKILL/scripts/bind_skill.py web-crawler --provider iproyal --country jp
#    Pin one exit IP for up to 7 days (sticky needs a session id):
python3 $SKILL/scripts/bind_skill.py web-crawler --provider iproyal --country jp \
    --session crawler-jp --sticky 360        # 6 hours

# ── Dedicated static IP (permanent) ─────────────────────────────────────────
# 3. Register a purchased ISP proxy (interactive if flags omitted), then bind:
python3 $SKILL/scripts/add_isp_proxy.py jp-1 \
    --host 191.116.125.248 --port 12323 --socks-port 12324 \
    --username <user> --password <pass> --label "Tokyo ISP"
python3 $SKILL/scripts/bind_skill.py web-crawler --provider iproyal-isp --proxy-id jp-1
#    Or one-shot: python3 $SKILL/scripts/onboard.py web-crawler --provider iproyal-isp

# ── Inspect / verify / clean up ────────────────────────────────────────────
python3 $SKILL/scripts/list_providers.py            # providers, ISP proxies, bindings
python3 $SKILL/scripts/test_proxy.py iproyal --country jp
python3 $SKILL/scripts/test_proxy.py iproyal-isp --proxy-id jp-1
python3 $SKILL/scripts/bind_skill.py web-crawler --unset
python3 $SKILL/scripts/add_isp_proxy.py --list
python3 $SKILL/scripts/add_isp_proxy.py --remove jp-1 [--force]
```

## How other skills consume it

Two patterns. Both raise `ProxyNotConfiguredError` on misconfiguration — never
silent fallback (a proxy user is debugging a geo/identity problem; silently falling
through to a direct connection makes that debugging much harder).

### Pattern A — explicit, one-off

```python
import sys, requests
sys.path.insert(0, "/data/workspace/skills/byo-proxy")
from exports import get_proxy_url

p = get_proxy_url(provider="iproyal", country="jp")            # rotating
p = get_proxy_url(provider="iproyal", country="jp",
                  session="crawler-jp", sticky_minutes=360)    # sticky 6h
p = get_proxy_url(provider="iproyal-isp", proxy_id="jp-1")     # dedicated IP
r = requests.get("https://example.com", proxies={"http": p, "https": p}, timeout=30)
```

### Pattern B — bound, long-term

Use when a skill always wants to route through whatever the user configured for it:

```python
import sys, requests
sys.path.insert(0, "/data/workspace/skills/byo-proxy")
from exports import get_proxy_for_skill, ProxyNotConfiguredError

try:
    p = get_proxy_for_skill("web-crawler")   # caller declares its own name
except ProxyNotConfiguredError as e:
    # The exception message IS a multi-line onboarding guide for the user —
    # surface it verbatim. It includes the signup URL, pricing note, and the
    # one-shot `onboard.py` command to fix the situation.
    raise SystemExit(str(e))

r = requests.get(url, proxies={"http": p, "https": p}, timeout=30)
```

`get_proxy_for_skill` is **provider-agnostic**: it returns the right URL whether the
user bound a rotating country, a sticky session, or a dedicated ISP IP. A skill that
does **not** import it is unaffected, even if the user has bindings configured.
Opt-in only.

### Onboarding for unconfigured skills

When `get_proxy_for_skill("X")` raises because nothing is configured for `X`, the
exception message is **already a complete onboarding script**: signup URL, pricing,
credential location, and the exact `onboard.py` command to run. Agents that surface
this error to a user will naturally walk them through registration and binding — no
extra logic needed in the calling skill.

If a calling skill wants to render its own onboarding UI (instead of relying on the
error message), it can import the same text directly:

```python
from exports import onboarding_guide
print(onboarding_guide("web-crawler", provider="iproyal", country="jp"))
print(onboarding_guide("web-crawler", provider="iproyal-isp"))
```

## Public API (`exports.py`)

| Function | Returns | Raises |
|---|---|---|
| `get_proxy_url(provider, country=None, sticky_minutes=None, session=None, proxy_id=None)` | `str` proxy URL | `ProxyNotConfiguredError` if creds/proxy missing; `ValueError` on bad provider/country/param |
| `get_proxy_for_skill(skill_name)` | `str` proxy URL | `ProxyNotConfiguredError` (multi-line onboarding guide) if unbound, provider gone, creds or ISP proxy missing |
| `onboarding_guide(skill_name, provider="iproyal", country="<cc>", proxy_id=None)` | `str` onboarding text | `ValueError` on bad provider |
| `list_providers()` | `list[dict]` — `{provider, kind, configured, …}` + `bound_skills` | never |
| `set_binding(skill_name, provider, country=None, sticky_minutes=None, session=None, proxy_id=None)` | `None` | `ValueError` on bad provider/country/param or unregistered ISP proxy |
| `unset_binding(skill_name)` | `None` | never |
| `add_isp_proxy(proxy_id, host, port, username, password, socks_port=None, label=None)` | `None` | `ValueError` on bad id/host/port |
| `remove_isp_proxy(proxy_id, force=False)` | `list` of still-bound skills | `ValueError` if bound and not `force` |
| `list_isp_proxies()` | `list[dict]` — `{proxy_id, endpoint, socks_endpoint, label, bound_skills}` (creds redacted) | never |
| `test_proxy(provider, country=None, proxy_id=None, timeout=15)` | `dict` — `{ok, exit_ip, geo_country, latency_ms}` | `ProxyNotConfiguredError` / `ValueError` |

Sticky bounds: `sticky_minutes` ∈ 1..10080 (7 days). `sticky_minutes` **requires**
`session` (IPRoyal's `lifetime-` only applies to a `session-`).

## Per-request only — no global proxy

Same rule as `sc-vpn`: never `export HTTP_PROXY=...` from this skill's URLs.
Pass `proxies=` to the specific request only. Setting global env vars will
break unrelated skills (notably `sc-proxy` traffic for paid APIs).

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `Skill 'X' has no proxy binding` | bindings has no entry for X | `python3 scripts/onboard.py X --provider iproyal --country <cc>` (or `--provider iproyal-isp`) |
| `... USERNAME / ... PASSWORD not found` | gateway creds never saved (or removed from `.env`) | `python3 scripts/setup_provider.py iproyal` (or re-run `onboard.py`) |
| `ISP proxy 'X' is not registered` | binding references an id absent from `.byo-proxy.json` | `python3 scripts/add_isp_proxy.py X --host … --port … --username … --password …` |
| `... bound to unknown provider` | bindings references a provider that no longer exists | rebind, or `bind_skill.py X --unset` |
| `sticky_minutes requires a session id` | `--sticky` without `--session` | add `--session <id>` (IPRoyal's `lifetime-` needs `session-`) |
| `sticky_minutes must be between 1 and 10080` | out of range | max is 7 days |
| `ValueError: Unknown country code 'XX'` | not in IPRoyal's supported list | see `references/iproyal.md` |
| `test_proxy` returns `ok=false` | wrong creds/host, expired account, network | check the dashboard; for ISP re-register the proxy string |

## Files

```
byo-proxy/
├── SKILL.md
├── exports.py                # public API for other skills
├── scripts/
│   ├── onboard.py            # one-shot: register (if needed) + bind + test
│   ├── setup_provider.py     # interactive gateway credential setup
│   ├── add_isp_proxy.py      # register/list/remove dedicated ISP proxies
│   ├── list_providers.py     # show providers + ISP proxies + bindings
│   ├── bind_skill.py         # set/unset skill→provider binding
│   └── test_proxy.py         # verify exit IP via ifconfig.co
└── references/
    ├── iproyal.md            # residential gateway: params, sticky sessions
    └── iproyal-isp.md        # dedicated static IPs: per-IP endpoint + auth
```