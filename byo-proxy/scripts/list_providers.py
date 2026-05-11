#!/usr/bin/env python3
"""Print configured providers and skill bindings."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from exports import list_providers, _load_bindings  # noqa: E402


def main() -> int:
    providers = list_providers()
    bindings = _load_bindings()

    print("Providers:")
    for p in providers:
        status = "✅ configured" if p["configured"] else "⚪ not configured"
        print(f"  {p['provider']:10s}  {status}  endpoint={p['endpoint']}  "
              f"countries={p['supported_country_count']}")
        if p["bound_skills"]:
            for b in p["bound_skills"]:
                print(f"      • {b}")

    print()
    if bindings:
        print(f"Bindings ({len(bindings)}):")
        for skill, b in sorted(bindings.items()):
            extras = []
            if b.get("sticky_minutes"):
                extras.append(f"sticky={b['sticky_minutes']}m")
            if b.get("session"):
                extras.append(f"session={b['session']}")
            tail = f"  [{', '.join(extras)}]" if extras else ""
            print(f"  {skill}  →  {b['provider']}/{b['country']}{tail}")
    else:
        print("Bindings: (none)")

    if "--json" in sys.argv:
        print()
        print(json.dumps({"providers": providers, "bindings": bindings}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
