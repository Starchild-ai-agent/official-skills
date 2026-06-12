"""Create (or reuse) a remotely-managed Cloudflare Tunnel, configure ingress,
create the DNS CNAME, and save everything to .cf_state.json.

Usage:
  python3 setup.py --hostname app.example.com --port 8080
  python3 setup.py --hostname app.example.com --port 8080 --service-host 127.0.0.1

  # Recommended: record how to (re)start the local app so keepalive.sh can bring
  # the WHOLE site back by itself after a container restart or an app crash:
  python3 setup.py --hostname app.example.com --port 8080 \
      --app-cmd "python3 server.py" --app-dir projects/myapp

setup.py is CONFIG-TIME, not start-time. It calls the Cloudflare API to
create/reuse the tunnel + DNS and writes .cf_state.json. Run it ONCE per domain
(or again only when reconfiguring). NEVER put setup.py in workspace/setup.sh —
on every restart it would re-hit the API and may rotate the run_token. Boot and
self-heal are handled by keepalive.sh, which only READS .cf_state.json.
"""
from __future__ import annotations

import argparse
import base64
import os
import secrets
import sys

from cf_api import cf_request, load_state, update_state


def find_existing_tunnel(account_id: str, name: str) -> dict | None:
    """List tunnels and return one with matching name (not deleted)."""
    r = cf_request("GET", f"/accounts/{account_id}/cfd_tunnel?is_deleted=false&name={name}")
    for t in r.get("result", []):
        if t.get("name") == name and not t.get("deleted_at"):
            return t
    return None


def create_tunnel(account_id: str, name: str) -> dict:
    """Create a remotely-managed tunnel (config_src=cloudflare).

    Note: API also requires `tunnel_secret` — a 32-byte base64 string. Even for
    config_src=cloudflare, supplying a secret keeps the API happy and lets
    locally-managed mode work as fallback.
    """
    secret = base64.b64encode(secrets.token_bytes(32)).decode()
    body = {"name": name, "config_src": "cloudflare", "tunnel_secret": secret}
    r = cf_request("POST", f"/accounts/{account_id}/cfd_tunnel", body=body)
    return r["result"]


def fetch_run_token(account_id: str, tunnel_id: str) -> str:
    r = cf_request("GET", f"/accounts/{account_id}/cfd_tunnel/{tunnel_id}/token")
    # `result` is the token string (already a JSON-encoded string)
    return r["result"]


def put_ingress_config(
    account_id: str, tunnel_id: str, hostname: str, service_url: str
) -> None:
    body = {
        "config": {
            "ingress": [
                {"hostname": hostname, "service": service_url},
                {"service": "http_status:404"},
            ]
        }
    }
    cf_request(
        "PUT",
        f"/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations",
        body=body,
    )


def upsert_dns_cname(zone_id: str, hostname: str, target: str) -> dict:
    """Create or update a proxied CNAME record."""
    # Look for an existing record at this name
    existing = cf_request("GET", f"/zones/{zone_id}/dns_records?name={hostname}")
    body = {
        "type": "CNAME",
        "name": hostname,
        "content": target,
        "proxied": True,
        "ttl": 1,  # 1 = automatic
        "comment": "Managed by cloudflare-tunnel-publish skill",
    }
    if existing.get("result"):
        rec = existing["result"][0]
        r = cf_request(
            "PUT", f"/zones/{zone_id}/dns_records/{rec['id']}", body=body
        )
    else:
        r = cf_request("POST", f"/zones/{zone_id}/dns_records", body=body)
    return r["result"]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--hostname", required=True, help="Public hostname, e.g. app.example.com")
    p.add_argument("--port", required=True, type=int, help="Local port to expose")
    p.add_argument("--service-host", default="localhost", help="Local host (default: localhost)")
    p.add_argument("--app-cmd", default="", help="Command to (re)start the local app, e.g. 'python3 server.py'. "
                                                 "Recorded in state so keepalive.sh can restart the app after a "
                                                 "restart/crash. Omit if the app is managed elsewhere.")
    p.add_argument("--app-dir", default="", help="Working dir for --app-cmd, relative to /data/workspace "
                                                 "(default: workspace root).")
    args = p.parse_args()

    state = load_state()
    account_id = state.get("account_id")
    zone_id = state.get("zone_id")
    zone_name = state.get("zone_name")

    if not account_id or not zone_id:
        print("❌ Missing account_id / zone_id in .cf_state.json — run verify.py first.")
        return 2

    if not args.hostname.endswith(zone_name):
        print(f"❌ Hostname {args.hostname} is not in zone {zone_name}")
        return 2

    tunnel_name = "starchild-" + args.hostname.replace(".", "-")
    service_url = f"http://{args.service_host}:{args.port}"

    # 1. Reuse or create tunnel
    existing = find_existing_tunnel(account_id, tunnel_name)
    if existing:
        tunnel = existing
        print(f"↻ Reusing existing tunnel: {tunnel_name} ({tunnel['id']})")
    else:
        tunnel = create_tunnel(account_id, tunnel_name)
        print(f"✅ Created tunnel: {tunnel_name} ({tunnel['id']})")

    # 2. Run token (refetch every time in case of rotation)
    run_token = fetch_run_token(account_id, tunnel["id"])
    print(f"✅ Fetched run token (length {len(run_token)})")

    # 3. Ingress config
    put_ingress_config(account_id, tunnel["id"], args.hostname, service_url)
    print(f"✅ Set ingress: {args.hostname} → {service_url}")

    # 4. DNS CNAME
    cname_target = f"{tunnel['id']}.cfargotunnel.com"
    upsert_dns_cname(zone_id, args.hostname, cname_target)
    print(f"✅ DNS: {args.hostname} CNAME {cname_target} (proxied)")

    # 5. Persist
    app_dir = args.app_dir.strip()
    if app_dir and not app_dir.startswith("/"):
        app_dir = f"/data/workspace/{app_dir}"
    update_state(
        hostname=args.hostname,
        port=args.port,
        service_url=service_url,
        tunnel_id=tunnel["id"],
        tunnel_name=tunnel_name,
        run_token=run_token,
        app_cmd=args.app_cmd.strip(),
        app_dir=app_dir,
    )
    if args.app_cmd.strip():
        print(f"✅ Recorded app_cmd → keepalive.sh can auto-restart the app")
    else:
        print("ℹ️  No --app-cmd given: keepalive.sh will guard the tunnel only "
              "(it can't restart your app if it dies). Re-run with --app-cmd to enable full self-heal.")
    print(f"\n→ State saved. Start (and self-heal) the whole site with ONE script:")
    print(f"    bash skills/cloudflare-tunnel-publish/scripts/keepalive.sh")
    print(f"→ After ~15s, check: curl -I https://{args.hostname}")
    print(f"→ For durability, add keepalive.sh to workspace/setup.sh AND schedule it. See SKILL.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
