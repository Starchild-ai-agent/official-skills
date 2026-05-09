#!/usr/bin/env python3
"""End-to-end onboarding for a skill that needs a residential proxy.

Walks the user through whichever steps are still missing, in order:
    1. (if no creds saved)  prompt for provider username/password and save them
    2. (if not bound)       create the skill -> provider/country binding
    3. (always)             test the proxy and report exit IP / country

This is the script that ProxyNotConfiguredError messages point at, so
re-running it after a partial failure should always be safe and idempotent.

Usage:
    python3 onboard.py web-crawler --provider iproyal --country jp
    python3 onboard.py web-crawler --provider iproyal --country jp --sticky 30
"""
import argparse
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from exports import (  # noqa: E402
    PROVIDERS, _cred, _load_bindings, save_credentials,
    set_binding, test_proxy, ENV_FILE, BINDINGS_FILE,
)


def _prompt_credentials(provider: str) -> tuple[str, str]:
    cfg = PROVIDERS[provider]
    print()
    print(f"━━━ Step 1/3 — register {provider} credentials ━━━")
    print(f"  Don't have an account yet? Sign up: {cfg['signup_url']}")
    print(f"  ({cfg['pricing_note']})")
    print(f"  Then copy your proxy creds from: {cfg['credential_hint']}")
    print()
    username = input(f"{provider} proxy username: ").strip()
    if not username:
        print("ERROR: username is required", file=sys.stderr)
        sys.exit(2)
    password = getpass.getpass(f"{provider} proxy password: ").strip()
    if not password:
        print("ERROR: password is required", file=sys.stderr)
        sys.exit(2)
    return username, password


def main() -> int:
    ap = argparse.ArgumentParser(
        description="One-command onboarding: register creds (if needed), bind skill, test."
    )
    ap.add_argument("skill", help="Skill name that will call get_proxy_for_skill()")
    ap.add_argument("--provider", default="iproyal", choices=sorted(PROVIDERS.keys()))
    ap.add_argument("--country", required=True, help="ISO-3166-1 alpha-2 code, lowercase")
    ap.add_argument("--sticky", type=int, default=None,
                    help="Sticky-session lifetime in minutes (1..1440). Omit for rotating IPs.")
    ap.add_argument("--session", default=None, help="Optional named session id")
    ap.add_argument("--non-interactive", action="store_true",
                    help="Fail instead of prompting if creds are missing")
    args = ap.parse_args()

    cfg = PROVIDERS[args.provider]

    # Step 1 — credentials
    has_creds = bool(_cred(cfg["env_user"]) and _cred(cfg["env_pass"]))
    if has_creds:
        print(f"[1/3] {args.provider} credentials already in {ENV_FILE}  ✅")
    else:
        if args.non_interactive:
            print(
                f"ERROR: {cfg['env_user']} / {cfg['env_pass']} missing in {ENV_FILE}. "
                f"Re-run without --non-interactive to enter them.",
                file=sys.stderr,
            )
            return 2
        username, password = _prompt_credentials(args.provider)
        save_credentials(args.provider, username=username, password=password)
        print(f"[1/3] saved credentials to {ENV_FILE}  ✅")

    # Step 2 — binding
    bindings = _load_bindings()
    existing = bindings.get(args.skill)
    if existing:
        same = (
            existing.get("provider") == args.provider
            and existing.get("country") == args.country.lower()
            and existing.get("sticky_minutes") == args.sticky
            and existing.get("session") == args.session
        )
        if same:
            print(f"[2/3] {args.skill!r} already bound to {args.provider}/{args.country}  ✅")
        else:
            print(
                f"[2/3] {args.skill!r} is currently bound to "
                f"{existing.get('provider')}/{existing.get('country')}; "
                f"overwriting with {args.provider}/{args.country}"
            )
    try:
        set_binding(args.skill, args.provider, args.country,
                    sticky_minutes=args.sticky, session=args.session)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    if not existing:
        sticky_note = f", sticky={args.sticky}m" if args.sticky else ""
        print(f"[2/3] bound {args.skill!r} → {args.provider}/{args.country}{sticky_note}  ✅")
        print(f"      ({BINDINGS_FILE})")

    # Step 3 — verification
    print(f"[3/3] testing exit IP through {args.provider}/{args.country} …")
    result = test_proxy(args.provider, args.country)
    if not result["ok"]:
        print(f"      FAIL ({result['latency_ms']}ms): {result.get('error')}", file=sys.stderr)
        print(
            "\nThe binding was saved but the test failed. Common causes:"
            "\n  • Wrong username/password — re-run: "
            f"python3 {os.path.dirname(__file__)}/setup_provider.py {args.provider}"
            "\n  • IPRoyal account out of credit — check the dashboard"
            "\n  • Network unreachable — try again from a machine with outbound HTTPS",
            file=sys.stderr,
        )
        return 1

    requested = args.country.lower()
    geo_match = "✅" if result["geo_country"] == requested else "⚠️ "
    print(
        f"      OK  exit_ip={result['exit_ip']}  "
        f"country={result['geo_country']} (requested {requested}) {geo_match}  "
        f"latency={result['latency_ms']}ms"
    )
    if result["geo_country"] != requested:
        print(
            f"      Note: requested {requested!r} but got {result['geo_country']!r}. "
            f"IPRoyal may have rotated to a nearby country if the {requested} pool is depleted.",
        )

    print(f"\nDone. {args.skill!r} can now call get_proxy_for_skill({args.skill!r}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
