#!/usr/bin/env python3
"""End-to-end onboarding for a skill that needs a proxy.

Runs whichever steps are still missing, in order, then always verifies.

Gateway provider (iproyal):
    1. (if no creds saved)  prompt for username/password and save them
    2. (if not bound)       create the skill -> provider/country binding
    3.                      test the proxy and report exit IP / country

Dedicated static IP (iproyal-isp):
    1. (if proxy not registered) prompt for host/port/username/password
    2. (if not bound)            bind the skill to that proxy
    3.                           test the proxy and report exit IP

This is the script that ProxyNotConfiguredError messages point at, so
re-running it after a partial failure should always be safe and idempotent.

Usage:
    python3 onboard.py web-crawler --provider iproyal --country jp
    python3 onboard.py web-crawler --provider iproyal --country jp --session abc --sticky 60
    python3 onboard.py web-crawler --provider iproyal-isp
"""
import argparse
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from exports import (  # noqa: E402
    BINDINGS_FILE, ENV_FILE, MAX_STICKY_MINUTES, MIN_STICKY_MINUTES, PROVIDERS,
    _cred, _load_bindings, _load_isp_proxies, _validate_proxy_id,
    add_isp_proxy, save_credentials, set_binding, test_proxy,
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


def _prompt_isp_proxy(proxy_id: str = None) -> str:
    cfg = PROVIDERS["iproyal-isp"]
    print()
    print("━━━ Step 1/3 — register your ISP proxy ━━━")
    print(f"  Don't own one yet? Buy a dedicated IP: {cfg['signup_url']}")
    print(f"  ({cfg['pricing_note']})")
    print(f"  Copy host:port + username:password from: {cfg['credential_hint']}")
    print()
    if not proxy_id:
        proxy_id = input("Local id for this IP (e.g. jp-1): ").strip()
    _validate_proxy_id(proxy_id)
    host = input("Proxy host (IP): ").strip()
    port = input("Proxy HTTP port: ").strip()
    socks_port = input("Proxy SOCKS5 port (optional, blank to skip): ").strip() or None
    username = input("Proxy username: ").strip()
    password = getpass.getpass("Proxy password: ").strip()
    add_isp_proxy(proxy_id, host=host, port=port, username=username,
                  password=password, socks_port=socks_port)
    return proxy_id


def main() -> int:
    ap = argparse.ArgumentParser(
        description="One-command onboarding: register provider (if needed), bind skill, test."
    )
    ap.add_argument("skill", help="Skill name that will call get_proxy_for_skill()")
    ap.add_argument("--provider", default="iproyal", choices=sorted(PROVIDERS.keys()))
    ap.add_argument("--country", help="ISO-3166-1 alpha-2 code, lowercase (gateway providers)")
    ap.add_argument("--proxy-id", dest="proxy_id", help="Registered ISP proxy id (isp providers)")
    ap.add_argument("--session", default=None, help="Named session id (gateway providers)")
    ap.add_argument("--sticky", type=int, default=None,
                    help=f"Sticky-session lifetime in minutes "
                         f"({MIN_STICKY_MINUTES}..{MAX_STICKY_MINUTES}). Requires --session.")
    ap.add_argument("--non-interactive", action="store_true",
                    help="Fail instead of prompting if setup is missing")
    args = ap.parse_args()

    cfg = PROVIDERS[args.provider]
    kind = cfg["kind"]

    if kind == "gateway" and not args.country:
        ap.error(f"--country is required for provider {args.provider!r}")
    if kind == "gateway" and args.sticky and not args.session:
        ap.error("--sticky requires --session (IPRoyal lifetime- applies to a session-)")
    if kind == "isp" and (args.country or args.sticky or args.session):
        ap.error(f"{args.provider!r} serves one dedicated IP per proxy; "
                 f"--country/--sticky/--session do not apply")

    # Step 1 — provider registration
    if kind == "isp":
        proxy_id = args.proxy_id
        if proxy_id and proxy_id in _load_isp_proxies():
            print(f"[1/3] ISP proxy {proxy_id!r} already registered  ✅")
        elif args.non_interactive:
            print(
                f"ERROR: ISP proxy {proxy_id!r} is not registered in {BINDINGS_FILE}. "
                f"Re-run without --non-interactive, or run add_isp_proxy.py.",
                file=sys.stderr,
            )
            return 2
        else:
            try:
                proxy_id = _prompt_isp_proxy(proxy_id)
            except ValueError as e:
                print(f"ERROR: {e}", file=sys.stderr)
                return 2
            print(f"[1/3] registered ISP proxy {proxy_id!r}  ✅")
        target_value = proxy_id
    else:
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
        target_value = args.country.lower()

    # Step 2 — binding
    bindings = _load_bindings()
    existing = bindings.get(args.skill)
    if kind == "isp":
        same = bool(existing) and (
            existing.get("provider") == args.provider
            and existing.get("proxy_id") == target_value
        )
    else:
        same = bool(existing) and (
            existing.get("provider") == args.provider
            and existing.get("country") == target_value
            and existing.get("sticky_minutes") == args.sticky
            and existing.get("session") == args.session
        )
    if existing and not same:
        print(
            f"[2/3] {args.skill!r} currently bound to "
            f"{existing.get('proxy_id') or existing.get('country')}; "
            f"overwriting with {target_value}"
        )
    try:
        set_binding(args.skill, args.provider, country=args.country,
                    sticky_minutes=args.sticky, session=args.session,
                    proxy_id=target_value if kind == "isp" else None)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    if same:
        print(f"[2/3] {args.skill!r} already bound  ✅")
    else:
        print(f"[2/3] bound {args.skill!r} → {args.provider}/{target_value}  ✅")
        print(f"      ({BINDINGS_FILE})")

    # Step 3 — verification
    print(f"[3/3] testing exit IP through {args.provider}/{target_value} …")
    result = test_proxy(args.provider, country=args.country,
                        proxy_id=target_value if kind == "isp" else None)
    if not result["ok"]:
        print(f"      FAIL ({result['latency_ms']}ms): {result.get('error')}", file=sys.stderr)
        if kind == "isp":
            print(
                "\nThe binding was saved but the test failed. Common causes:"
                f"\n  • Wrong host/port or credentials — re-register: "
                f"python3 {os.path.dirname(__file__)}/add_isp_proxy.py {target_value}"
                "\n  • ISP proxy expired or got reassigned — check the dashboard"
                "\n  • Network unreachable — try again from a machine with outbound HTTPS",
                file=sys.stderr,
            )
        else:
            print(
                "\nThe binding was saved but the test failed. Common causes:"
                "\n  • Wrong username/password — re-run: "
                f"python3 {os.path.dirname(__file__)}/setup_provider.py {args.provider}"
                "\n  • IPRoyal account out of credit — check the dashboard"
                "\n  • Network unreachable — try again from a machine with outbound HTTPS",
                file=sys.stderr,
            )
        return 1

    if kind == "isp":
        print(f"      OK  exit_ip={result['exit_ip']}  country={result['geo_country']}  "
              f"latency={result['latency_ms']}ms")
    else:
        requested = target_value
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