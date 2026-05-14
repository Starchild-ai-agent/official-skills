#!/usr/bin/env python3
"""workroom list

List every room this agent's user is a member of. The source of truth is
sc-chatroom server (GET /rooms). The local `keys.json` index is used
only to annotate each row with the AKM key's prefix + TTL.

For each room you'll see:
  - role (owner / member)
  - archived flag
  - whether the server has an agent_endpoint + akm_key on file
  - whether the server has flagged the key stale (past fan-out failures)
  - the AKM key's prefix + expiry from local storage, if any
  - an actionable hint when a row isn't set up for agent participation
"""
from __future__ import annotations

import datetime
import sys

import _common as C


def _ts(v):
    if v is None:
        return "-"
    return datetime.datetime.fromtimestamp(v).isoformat(timespec="minutes")


def main(argv: list[str]) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="workroom list", description=__doc__)
    p.parse_args(argv[1:])
    C.require_env()

    # 1. Server-authoritative membership
    r = C.workroom_call("GET", "/rooms")
    if r.status_code != 200:
        C.die(f"sc-chatroom GET /rooms returned {r.status_code}: {r.text}")
    rooms = r.json().get("rooms", [])
    if not rooms:
        C.info("not a member of any rooms")
        return 0

    # 2. Local AKM metadata (for prefix + expiry annotation)
    local_prefixes = C.load_key_index()
    clawd_keys_by_prefix: dict[str, dict] = {}
    kr = C.clawd_call("GET", "/api/keys?include_expired=true")
    if kr.status_code == 200:
        for k in kr.json().get("keys", []):
            clawd_keys_by_prefix[k["prefix"]] = k

    # 3. Render
    hdr = f"{'ROOM ID':<16} {'ROLE':<7} {'STATE':<10} {'AKM KEY':<12} {'EXPIRES':<18} NAME"
    C.info(hdr)
    C.info("-" * len(hdr))
    hints: list[str] = []

    for room in rooms:
        rid = room["room_id"]
        role = room["role"]
        archived = room["archived"]
        has_ep = bool(room.get("agent_endpoint"))
        has_key = room.get("has_akm_key")
        stale = room.get("key_stale")

        state = (
            "archived"       if archived
            else "stale"     if stale
            else "no-agent"  if not (has_ep and has_key)
            else "active"
        )

        local_prefix = local_prefixes.get(rid, "")
        if local_prefix:
            local_key = clawd_keys_by_prefix.get(local_prefix)
            exp_col = _ts(local_key["expires_at"]) if local_key else "-"
            key_col = local_prefix
        else:
            exp_col = "-"
            key_col = "(none)"

        C.info(
            f"{rid:<16} {role:<7} {state:<10} {key_col:<12} {exp_col:<18} "
            f"{room.get('name') or ''}"
        )

        if state == "no-agent":
            hints.append(
                f"  • {rid}: no agent attached — run "
                f"`workroom attach {rid}` to enable fan-out to this agent"
            )
        elif state == "stale":
            hints.append(
                f"  • {rid}: AKM key stale — run "
                f"`workroom rotate-key {rid}` to push a fresh key"
            )

    if hints:
        C.info("")
        C.info("Hints:")
        for h in hints:
            C.info(h)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
