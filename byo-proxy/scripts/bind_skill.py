#!/usr/bin/env python3
"""Bind / unbind a skill to a proxy provider.

Gateway provider (country + optional sticky session):
    python3 bind_skill.py web-crawler --provider iproyal --country jp
    python3 bind_skill.py web-crawler --provider iproyal --country jp --session abc --sticky 60

Dedicated static IP (IPRoyal ISP, registered via add_isp_proxy.py):
    python3 bind_skill.py web-crawler --provider iproyal-isp --proxy-id jp-1

Unbind:
    python3 bind_skill.py web-crawler --unset
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from exports import (  # noqa: E402
    MAX_STICKY_MINUTES, MIN_STICKY_MINUTES, PROVIDERS,
    ProxyNotConfiguredError, set_binding, unset_binding, BINDINGS_FILE,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Bind a skill to a proxy provider.")
    ap.add_argument("skill", help="Skill name (caller's identifier in get_proxy_for_skill)")
    ap.add_argument("--provider", help=f"Provider name: {', '.join(sorted(PROVIDERS))}")
    ap.add_argument("--country", help="ISO-3166-1 alpha-2 country code, lowercase (gateway providers)")
    ap.add_argument("--proxy-id", dest="proxy_id", help="Registered ISP proxy id (isp providers)")
    ap.add_argument("--session", default=None,
                    help="Named session id (gateway providers). Lets requests reuse one IP.")
    ap.add_argument("--sticky", type=int, default=None,
                    help=f"Sticky-session lifetime in minutes "
                         f"({MIN_STICKY_MINUTES}..{MAX_STICKY_MINUTES}, 7 days). Requires --session.")
    ap.add_argument("--unset", action="store_true", help="Remove the binding for this skill")
    args = ap.parse_args()

    if args.unset:
        unset_binding(args.skill)
        print(f"Unbound {args.skill!r}.  ({BINDINGS_FILE})")
        return 0

    if not args.provider:
        ap.error("--provider is required (or pass --unset)")

    kind = PROVIDERS.get(args.provider, {}).get("kind")
    if kind == "isp":
        if not args.proxy_id:
            ap.error(f"--proxy-id is required for provider {args.provider!r}")
        if args.country or args.sticky or args.session:
            ap.error(f"{args.provider!r} serves one dedicated IP per proxy; "
                     f"--country/--sticky/--session do not apply")
    elif kind == "gateway":
        if not args.country:
            ap.error(f"--country is required for provider {args.provider!r} (or pass --unset)")

    try:
        set_binding(args.skill, args.provider, country=args.country,
                    sticky_minutes=args.sticky, session=args.session,
                    proxy_id=args.proxy_id)
    except (ValueError, ProxyNotConfiguredError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if kind == "isp":
        print(f"Bound {args.skill!r} → {args.provider}/{args.proxy_id}")
    else:
        sticky_note = f", sticky={args.sticky}m" if args.sticky else ""
        session_note = f", session={args.session}" if args.session else ""
        print(f"Bound {args.skill!r} → {args.provider}/{args.country}{sticky_note}{session_note}")
    print(f"  ({BINDINGS_FILE})")
    return 0


if __name__ == "__main__":
    sys.exit(main())