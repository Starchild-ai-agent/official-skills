#!/usr/bin/env python3
"""Print configured providers, registered ISP proxies, and skill bindings."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from exports import list_isp_proxies, list_providers, _load_bindings  # noqa: E402


def main() -> int:
    providers = list_providers()
    proxies = list_isp_proxies()
    bindings = _load_bindings()

    print("Providers:")
    for p in providers:
        status = "✅ configured" if p["configured"] else "⚪ not configured"
        if p["kind"] == "isp":
            detail = f"proxies={p['proxy_count']}"
        else:
            detail = f"endpoint={p['endpoint']}  countries={p['supported_country_count']}"
        print(f"  {p['provider']:12s}  [{p['kind']:7s}]  {status}  {detail}")
        for b in p["bound_skills"]:
            print(f"      • {b}")

    print()
    if proxies:
        print(f"ISP proxies ({len(proxies)}):")
        for p in proxies:
            label = f"  {p['label']}" if p.get("label") else ""
            socks = f"  socks={p['socks_endpoint']}" if p.get("socks_endpoint") else ""
            print(f"  {p['proxy_id']:12s}  {p['endpoint']}{socks}{label}")
    else:
        print("ISP proxies: (none)")

    print()
    if bindings:
        print(f"Bindings ({len(bindings)}):")
        for skill, b in sorted(bindings.items()):
            if b.get("provider") == "iproyal-isp":
                target = b.get("proxy_id")
            else:
                target = b.get("country")
            extras = []
            if b.get("sticky_minutes"):
                extras.append(f"sticky={b['sticky_minutes']}m")
            if b.get("session"):
                extras.append(f"session={b['session']}")
            tail = f"  [{', '.join(extras)}]" if extras else ""
            print(f"  {skill}  →  {b['provider']}/{target}{tail}")
    else:
        print("Bindings: (none)")

    if "--json" in sys.argv:
        print()
        print(json.dumps(
            {"providers": providers, "isp_proxies": proxies, "bindings": bindings},
            indent=2,
        ))
    return 0


if __name__ == "__main__":
    sys.exit(main())