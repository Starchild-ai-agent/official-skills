---
name: where-is-my-ip
version: 0.1.0
description: "Look up the current outbound exit IP and its geolocation (country, city, ISP, ASN). Compare what you look like with the proxy on vs. off — useful for confirming a residential proxy is actually routing through the country you think it is. Use when the user asks 'what's my IP', 'where am I appearing from', 'is my proxy working', 'check my exit', or wants to verify a byo-proxy binding before scraping."
delivery: script
metadata:
  starchild:
    emoji: "📍"
    skillKey: where-is-my-ip
    requires:
      bins: [python3]
user-invocable: true
author: starchild
tags: [ip, geo, proxy, debug, byo-proxy, example]
---

# where-is-my-ip — exit-IP geolocator + byo-proxy demo

Tiny utility: queries `ifconfig.co/json` and prints what the world sees as your
outbound IP — country, city, ASN, latency. Doubles as the canonical example of
how to consume **`byo-proxy`** from another skill (both opt-in patterns).

## Three modes

```bash
SKILL=/data/workspace/skills/where-is-my-ip

# 1. Direct — no proxy, just check the raw exit
python3 $SKILL/scripts/check.py

# 2. Pattern A (explicit): route this single check through a specific provider/country
python3 $SKILL/scripts/check.py --via iproyal:jp
python3 $SKILL/scripts/check.py --via iproyal:de --sticky 30

# 3. Pattern B (bound): use whatever the user has configured for THIS skill
python3 $SKILL/scripts/check.py --use-binding

# Bonus: side-by-side — show direct exit vs proxied exit in one shot
python3 $SKILL/scripts/check.py --compare iproyal:jp
```

When `--use-binding` is passed and `where-is-my-ip` isn't bound yet, byo-proxy's
`ProxyNotConfiguredError` fires with a multi-line onboarding guide that already
tells the user exactly what to run. The script just prints it and exits non-zero.

## Why this skill exists

Two reasons:

1. **Sanity-check residential proxies.** Before kicking off a long scrape, run
   `--via iproyal:jp` to confirm the exit really is in Japan. IPRoyal occasionally
   rotates to a nearby country if the requested pool is depleted; this surfaces
   that immediately instead of failing 200 requests in.
2. **Reference implementation for byo-proxy.** `scripts/check.py` is short
   (~120 lines) and demonstrates both consumption patterns. New skills that need
   geo-routing should copy its proxy-acquisition block.

## Output (single check)

```
📍 exit  198.51.100.42
   country  JP (Japan)
   city     Tokyo, Tokyo
   asn      AS17676  SoftBank Corp.
   latency  234 ms
   via      iproyal/jp (sticky 30m)
```

## Output (--compare)

```
                  exit_ip          country     city          asn
direct            203.0.113.5      CN          Beijing       AS4134 China Telecom
iproyal/jp        198.51.100.42    JP          Tokyo         AS17676 SoftBank Corp.   ✅ matches request
```

## Integration with byo-proxy

`scripts/check.py` does this and nothing else to acquire a proxy:

```python
import sys
sys.path.insert(0, "/data/workspace/skills/byo-proxy")
from exports import get_proxy_url, get_proxy_for_skill, ProxyNotConfiguredError
```

If you're writing a new skill that needs residential routing, the same two
imports are enough. byo-proxy never auto-attaches — it only acts when you call
one of those functions, and it raises (with onboarding guidance) instead of
silently falling back to direct connection.

## Files

```
where-is-my-ip/
├── SKILL.md
└── scripts/
    └── check.py     # the entire skill — single-file demo
```
