"""Verify CLOUDFLARE_API_TOKEN, fetch account_id, list zones.

Output is human-readable so the agent can show it directly to the user.
Side effect: writes account_id (and the first zone if only one) to .cf_state.json.
"""
from __future__ import annotations

import sys

from cf_api import cf_request, update_state, load_state


def main() -> int:
    # 1. Verify token is valid
    try:
        v = cf_request("GET", "/user/tokens/verify")
    except Exception as e:
        print(f"❌ Token verification failed: {e}")
        return 1
    if not v.get("success"):
        print(f"❌ Token invalid: {v}")
        return 1
    print("✅ Token valid")

    # 2. Fetch zones first — each zone embeds account.id, so we can derive
    #    account_id even if /accounts isn't visible to this token (the
    #    Cloudflare-Tunnel:Edit perm doesn't include account-listing).
    zones = cf_request("GET", "/zones?per_page=50")
    zone_list = zones.get("result", [])
    if not zone_list:
        print("⚠ No domains found. Add a domain to Cloudflare first.")
        return 0

    # Derive account_id from zones
    account_ids = {z["account"]["id"] for z in zone_list}
    if len(account_ids) > 1:
        print("⚠ Zones span multiple accounts — using the first zone's account.")
    acct = zone_list[0]["account"]
    account_id = acct["id"]
    print(f"✅ Account: {acct.get('name', '(name hidden)')} ({account_id})")

    print(f"\n✅ Domains on this account ({len(zone_list)}):")
    for i, z in enumerate(zone_list, 1):
        status_flag = "✓" if z["status"] == "active" else f"⚠ {z['status']}"
        print(f"  {i}. {z['name']}  [{status_flag}]  zone_id={z['id']}")

    # If exactly one active zone, auto-select it
    active = [z for z in zone_list if z["status"] == "active"]
    state_update = {"account_id": account_id}
    if len(active) == 1:
        z = active[0]
        state_update.update(zone_id=z["id"], zone_name=z["name"])
        print(f"\n→ Auto-selected the only active zone: {z['name']}")
    update_state(**state_update)

    print(f"\nState saved to /data/workspace/.cf_state.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
