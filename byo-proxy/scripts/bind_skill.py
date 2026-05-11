#!/usr/bin/env python3
"""Bind / unbind a skill to a residential-proxy provider/country.

Examples:
    python3 bind_skill.py web-crawler --provider iproyal --country jp
    python3 bind_skill.py web-crawler --provider iproyal --country jp --sticky 30
    python3 bind_skill.py web-crawler --unset
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from exports import set_binding, unset_binding, BINDINGS_FILE  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Bind a skill to a residential-proxy provider/country.")
    ap.add_argument("skill", help="Skill name (caller's identifier in get_proxy_for_skill)")
    ap.add_argument("--provider", help="Provider name, e.g. iproyal")
    ap.add_argument("--country", help="ISO-3166-1 alpha-2 country code, lowercase")
    ap.add_argument("--sticky", type=int, default=None,
                    help="Sticky-session lifetime in minutes (1..1440). Omit for rotating IPs.")
    ap.add_argument("--session", default=None,
                    help="Optional named session id (any short string). Lets multiple bindings share an IP.")
    ap.add_argument("--unset", action="store_true", help="Remove the binding for this skill")
    args = ap.parse_args()

    if args.unset:
        unset_binding(args.skill)
        print(f"Unbound {args.skill!r}.  ({BINDINGS_FILE})")
        return 0

    if not args.provider or not args.country:
        ap.error("--provider and --country are required (or pass --unset)")

    try:
        set_binding(args.skill, args.provider, args.country,
                    sticky_minutes=args.sticky, session=args.session)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    sticky_note = f", sticky={args.sticky}m" if args.sticky else ""
    session_note = f", session={args.session}" if args.session else ""
    print(f"Bound {args.skill!r} → {args.provider}/{args.country}{sticky_note}{session_note}")
    print(f"  ({BINDINGS_FILE})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
