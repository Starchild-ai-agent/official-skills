#!/usr/bin/env python3
"""Register / remove / list dedicated IPRoyal ISP proxies.

A dedicated (static) IP is a permanent IP, so setup is per-proxy: register each
purchased IP with a local id, then bind skills to that id.

Register (interactive if flags are omitted):
    python3 add_isp_proxy.py jp-1 --host 191.116.125.248 --port 12323 \
        --username aea1bcf5cb3 --password e8c6a622fe --socks-port 12324 --label "Tokyo"

List:
    python3 add_isp_proxy.py --list

Remove:
    python3 add_isp_proxy.py --remove jp-1 [--force]
"""
import argparse
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from exports import (  # noqa: E402
    BINDINGS_FILE, PROVIDERS, add_isp_proxy, list_isp_proxies, remove_isp_proxy,
)


def _print_proxies() -> None:
    proxies = list_isp_proxies()
    if not proxies:
        print("ISP proxies: (none)")
        return
    print(f"ISP proxies ({len(proxies)}):")
    for p in proxies:
        label = f"  {p['label']}" if p.get("label") else ""
        socks = f"  socks={p['socks_endpoint']}" if p.get("socks_endpoint") else ""
        bound = f"  [{', '.join(p['bound_skills'])}]" if p["bound_skills"] else ""
        print(f"  {p['proxy_id']:12s}  {p['endpoint']}{socks}{label}{bound}")


def _prompt(missing: dict) -> dict:
    cfg = PROVIDERS["iproyal-isp"]
    print(f"Register an ISP proxy  ({cfg['pricing_note']})")
    print(f"  Buy one at: {cfg['signup_url']}")
    print(f"  Credentials at: {cfg['credential_hint']}")
    print()
    if "host" in missing:
        missing["host"] = input("Proxy host (IP): ").strip()
    if "port" in missing:
        missing["port"] = input("Proxy HTTP port: ").strip()
    if "username" in missing:
        missing["username"] = input("Proxy username: ").strip()
    if "password" in missing:
        missing["password"] = getpass.getpass("Proxy password: ").strip()
    if "socks_port" not in missing:
        missing["socks_port"] = input("Proxy SOCKS5 port (optional, blank to skip): ").strip() or None
    return missing


def main() -> int:
    ap = argparse.ArgumentParser(description="Manage dedicated IPRoyal ISP proxies.")
    ap.add_argument("proxy_id", nargs="?", help="Local id for this IP (e.g. jp-1)")
    ap.add_argument("--host", help="Proxy host / IP")
    ap.add_argument("--port", help="Proxy HTTP port")
    ap.add_argument("--socks-port", dest="socks_port", help="Proxy SOCKS5 port (optional)")
    ap.add_argument("--username", help="Proxy username")
    ap.add_argument("--password", help="Proxy password (omit to be prompted securely)")
    ap.add_argument("--label", help="Human-friendly note (e.g. 'Tokyo ISP')")
    ap.add_argument("--list", action="store_true", help="List registered proxies")
    ap.add_argument("--remove", metavar="PROXY_ID", help="Remove a registered proxy")
    ap.add_argument("--force", action="store_true",
                    help="With --remove: remove even if skills are bound to it")
    args = ap.parse_args()

    if args.list:
        _print_proxies()
        return 0

    if args.remove:
        try:
            bound = remove_isp_proxy(args.remove, force=args.force)
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        note = f" (was bound to: {', '.join(bound)})" if bound else ""
        print(f"Removed ISP proxy {args.remove!r}.{note}  ({BINDINGS_FILE})")
        return 0

    if not args.proxy_id:
        ap.error("proxy_id is required (or pass --list / --remove)")

    # Non-interactive when every required field is supplied.
    provided = {
        "host": args.host,
        "port": args.port,
        "username": args.username,
        "password": args.password,
        "socks_port": args.socks_port,
    }
    missing = [k for k in ("host", "port", "username", "password") if not provided[k]]
    if missing:
        try:
            provided = _prompt(provided)
        except EOFError:
            print("ERROR: cannot prompt in a non-interactive shell; pass the flags", file=sys.stderr)
            return 2

    try:
        add_isp_proxy(
            args.proxy_id,
            host=provided["host"],
            port=provided["port"],
            username=provided["username"],
            password=provided["password"],
            socks_port=provided["socks_port"] or None,
            label=args.label,
        )
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    print(f"Registered ISP proxy {args.proxy_id!r}  "
          f"(host {provided['host']}:{provided['port']})  ({BINDINGS_FILE})")
    print(f"\nNext: python3 scripts/bind_skill.py <skill> "
          f"--provider iproyal-isp --proxy-id {args.proxy_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())