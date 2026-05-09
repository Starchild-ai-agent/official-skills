"""Remove DNS record + delete tunnel + clear state. Use when user wants to
disconnect a custom domain.

Does NOT kill the cloudflared background process — caller should do that
via bash_process(action='kill', session_id=state['cloudflared_session_id']).
"""
from __future__ import annotations

import sys

from cf_api import cf_request, load_state, save_state, STATE_PATH


def delete_dns(zone_id: str, hostname: str) -> int:
    r = cf_request("GET", f"/zones/{zone_id}/dns_records?name={hostname}")
    n = 0
    for rec in r.get("result", []):
        cf_request("DELETE", f"/zones/{zone_id}/dns_records/{rec['id']}")
        n += 1
    return n


def delete_tunnel(account_id: str, tunnel_id: str) -> bool:
    # Tunnel must have no active connections; cleanup first
    cf_request("DELETE", f"/accounts/{account_id}/cfd_tunnel/{tunnel_id}/connections")
    cf_request("DELETE", f"/accounts/{account_id}/cfd_tunnel/{tunnel_id}")
    return True


def main() -> int:
    state = load_state()
    if not state:
        print("Nothing to tear down — no .cf_state.json")
        return 0

    zone_id = state.get("zone_id")
    hostname = state.get("hostname")
    account_id = state.get("account_id")
    tunnel_id = state.get("tunnel_id")

    if zone_id and hostname:
        n = delete_dns(zone_id, hostname)
        print(f"✅ Deleted {n} DNS record(s) for {hostname}")

    if account_id and tunnel_id:
        try:
            delete_tunnel(account_id, tunnel_id)
            print(f"✅ Deleted tunnel {tunnel_id}")
        except Exception as e:
            print(f"⚠ Tunnel delete failed (you may need to stop cloudflared first): {e}")

    # Clear publishing state but keep account/zone for next run
    keep = {
        k: state[k]
        for k in ("account_id", "zone_id", "zone_name")
        if k in state
    }
    save_state(keep)
    print(f"→ State reset. Account/zone kept for next setup.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
