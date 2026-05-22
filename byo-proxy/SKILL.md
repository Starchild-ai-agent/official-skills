---
name: byo-proxy
version: 0.1.1
description: |
  Bring-your-own residential proxy: per-skill country bindings, opt-in routing.

  Use when the user wants paid residential IPs or per-skill geo routing (e.g. bind web-crawler to JP, add IPRoyal account, route this scrape via DE).
delivery: script
metadata:
  starchild:
    emoji: "🌐"
    skillKey: byo-proxy
    requires:
      bins: [python3]
user-invocable: true
author: starchild
tags: [proxy, residential, geo, byo, iproyal]

---

# byo-proxy — bring-your-own residential proxy

Users supply their own residential proxy account (currently **IPRoyal**); this skill stores
the credentials in the workspace `.env`, maintains a `skill → provider/country` binding
table, and exposes a tiny Python API that other skills can opt into.

This skill **does not run a proxy server** and **does not intercept any traffic**.
It is a configuration center plus a URL builder. Other skills only behave differently
if they explicitly `import` from `exports.py`.

## Boundaries vs. existing proxy skills

| Skill | What it does | When |
|---|---|---|
| `sc-vpn` | Internal VPN gateway, 18 fixed countries, no auth | Last resort for geo-blocked requests inside Starchild |
| `transparent-proxy-maintenance` | Maintain the platform's billing proxy plugins | Ops work on `sc-proxy` |
| **`byo-proxy`** (this) | Manage user's own residential provider keys + per-skill bindings | User wants residential IPs, paid accounts, country granularity beyond sc-vpn's 18 |

## Supported providers

| Provider | Status | Endpoint | Auth |
|---|---|---|---|
| IPRoyal | ✅ supported | `geo.iproyal.com:12321` | username + password |

Adding more providers later: drop a new `providers/<name>.py` adapter and update
`PROVIDERS` in `exports.py`. See `references/iproyal.md` for the IPRoyal username
parameter format.

## Storage

- **Credentials** → `/data/workspace/.env` (same convention as `polymarket`, `birdeye`,
  `coingecko`). Keys: `IPROYAL_USERNAME`, `IPROYAL_PASSWORD`.
- **Bindings + provider metadata** → `/data/workspace/.byo-proxy.json`. Edited only
  through scripts; agents should not hand-edit.

## User workflow

```bash
SKILL=/data/workspace/skills/byo-proxy

# 0. One-shot onboarding (recommended for first-time setup) — does 1+3+5 in sequence:
#    prompts for credentials only if missing, creates the binding, runs a live test.
python3 $SKILL/scripts/onboard.py web-crawler --provider iproyal --country jp

# 1. Register a provider (interactive — prompts for username/password)
python3 $SKILL/scripts/setup_provider.py iproyal

# 2. List configured providers + bindings
python3 $SKILL/scripts/list_providers.py

# 3. Bind a skill to a provider/country (long-term preference)
python3 $SKILL/scripts/bind_skill.py web-crawler --provider iproyal --country jp
python3 $SKILL/scripts/bind_skill.py web-crawler --provider iproyal --country jp --sticky 30   # 30-min sticky session

# 4. Unbind
python3 $SKILL/scripts/bind_skill.py web-crawler --unset

# 5. Verify exit IP/country actually works
python3 $SKILL/scripts/test_proxy.py iproyal --country jp
```

## How other skills consume it

Two patterns. Both raise `ProxyNotConfiguredError` on misconfiguration — never
silent fallback (a residential-proxy user is debugging a geo problem; silently
falling through to direct connection makes that debugging much harder).

### Pattern A — explicit, one-off

Use when a skill needs a specific country for a specific request:

```python
import sys, requests
sys.path.insert(0, "/data/workspace/skills/byo-proxy")
from exports import get_proxy_url

p = get_proxy_url(provider="iproyal", country="jp")
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

A skill that does **not** import `get_proxy_for_skill()` is unaffected, even if
the user has bindings configured. Opt-in only.

### Onboarding for unconfigured skills

When `get_proxy_for_skill("X")` raises because nothing is configured for `X`,
the exception message is **already a complete onboarding script**: signup URL,
pricing, credential location, and the exact `onboard.py` command to run. Agents
that surface this error to a user will naturally walk them through registration
and binding — no extra logic needed in the calling skill.

If a calling skill wants to render its own onboarding UI (instead of relying
on the error message), it can import the same text directly:

```python
from exports import onboarding_guide
print(onboarding_guide("web-crawler", provider="iproyal", country="jp"))
```

## Public API (`exports.py`)

| Function | Returns | Raises |
|---|---|---|
| `get_proxy_url(provider, country, sticky_minutes=None, session=None)` | `str` proxy URL | `ProxyNotConfiguredError` if creds missing or country invalid |
| `get_proxy_for_skill(skill_name)` | `str` proxy URL | `ProxyNotConfiguredError` (multi-line onboarding guide) if no binding, binding's provider has no creds, or country invalid |
| `onboarding_guide(skill_name, provider="iproyal", country="<cc>")` | `str` onboarding text (signup URL, pricing, command) | `ValueError` on bad provider |
| `list_providers()` | `list[dict]` — `{provider, configured, default_country, bound_skills}` | never |
| `set_binding(skill_name, provider, country, sticky_minutes=None)` | `None` | `ValueError` on bad provider/country |
| `unset_binding(skill_name)` | `None` | never |
| `test_proxy(provider, country)` | `dict` — `{ok, exit_ip, geo_country, latency_ms}` | `ProxyNotConfiguredError` |

## Per-request only — no global proxy

Same rule as `sc-vpn`: never `export HTTP_PROXY=...` from this skill's URLs.
Pass `proxies=` to the specific request only. Setting global env vars will
break unrelated skills (notably `sc-proxy` traffic for paid APIs).

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `ProxyNotConfiguredError: Skill 'X' has no proxy binding` | bindings.json has no entry for X | one-shot: `python3 scripts/onboard.py X --provider iproyal --country <cc>` |
| `ProxyNotConfiguredError: ...USERNAME / ...PASSWORD not found` | provider creds were never saved (or removed from `.env`) | `python3 scripts/setup_provider.py iproyal` (or re-run `onboard.py`) |
| `ProxyNotConfiguredError: ... bound to unknown provider` | bindings.json references a provider that no longer exists | `python3 scripts/bind_skill.py X --unset` then rebind |
| `ValueError: Unknown country code 'XX'` | not in IPRoyal's supported list | see `references/iproyal.md` for valid codes |
| `test_proxy` returns `ok=false` | wrong creds, expired account, network | log into IPRoyal dashboard, check balance / re-register |

## Files

```
byo-proxy/
├── SKILL.md
├── exports.py                # public API for other skills
├── scripts/
│   ├── onboard.py            # one-shot: setup creds (if needed) + bind + test
│   ├── setup_provider.py     # interactive credential setup
│   ├── list_providers.py     # show configured providers + bindings
│   ├── bind_skill.py         # set/unset skill→provider/country binding
│   └── test_proxy.py         # verify exit IP via ifconfig.co
└── references/
    └── iproyal.md            # IPRoyal-specific endpoint + parameter docs
```
