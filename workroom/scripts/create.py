#!/usr/bin/env python3
"""workroom create <name>

Create a new room AND attach this agent as a fan-out target so web
messages the user sends will reach its own agent (via=web messages no
longer exclude the sender's agent).

Steps:
  1. POST /rooms → get room_id; server auto-adds you as owner
     (but with NULL agent_endpoint / akm_key)
  2. Sign a local AKM key via POST /api/keys
  3. PUT /rooms/{id}/members/{USER_ID}/endpoint → register agent_endpoint
     + akm_key so you become an eligible fan-out target
  4. Initialize /data/workspace/workroom/<room_id>/rules.md + data.md
  5. Remember AKM prefix in keys.json

Use `workroom invite <room_id>` after this to hand out join codes.
"""
from __future__ import annotations

import sys

import _common as C
import install_soul
import self_update


DEFAULT_TTL_SECONDS = 90 * 24 * 3600    # 90 days; sliding-renewed by `workroom send`
DEFAULT_RATE_LIMIT = {"per_minute": 10}


def main(argv: list[str]) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="workroom create")
    p.add_argument("name", nargs="+", help="room display name")
    p.add_argument("--public", action="store_true",
                   help="make the room visibility=public — anyone can browse "
                        "the message history without an invite. Joining (post "
                        "messages) still requires a starchild user or an invite.")
    args = p.parse_args(argv[1:])
    name = " ".join(args.name).strip()
    if not name:
        C.die("name is empty")
    # Server allows up to 200 chars but the viewer's room header truncates
    # awkwardly past ~80. Reject early with a clear message rather than
    # letting the user discover it after the room is live.
    if len(name) > 80:
        C.die(f"name too long ({len(name)} chars); please use ≤ 80 chars")
    visibility = "public" if args.public else "private"
    C.require_env()

    # 0. Auto-install/upgrade the SOUL block so the agent honors room
    # rules (fetched via GET /rules on rules_version bump) and emits
    # [SILENT] from its very first turn. Idempotent, runs once per-agent
    # (not per-room) — no-op on subsequent calls.
    try:
        soul_status = install_soul.ensure_installed()
        if soul_status in ("installed", "upgraded"):
            C.info(f"  ✓ SOUL workroom block {soul_status}")
    except Exception as e:
        C.info(f"  ⚠  could not auto-install SOUL block: {e!r} "
               "(run `workroom install-soul` manually)")

    # 0b. Discover and apply skill bundle updates published by sc-chatroom.
    # Non-fatal — the next ``workroom`` invocation picks up the new files.
    try:
        results = self_update.ensure_latest(verbose=False)
        changed = [n for n, s in results.items()
                   if s in ("installed", "updated")]
        if changed:
            C.info(f"  ✓ skill bundle updated: {', '.join(changed)} "
                   "(takes effect on next workroom invocation)")
    except Exception as e:
        C.info(f"  ⚠  could not check for skill updates: {e!r}")

    # 1. Create the room
    r = C.workroom_call("POST", "/rooms",
                        json={"name": name, "visibility": visibility})
    if r.status_code != 201:
        C.die(f"sc-chatroom POST /rooms returned {r.status_code}: {r.text}")
    body = r.json()
    room_id = body["room_id"]
    C.info(f"  ✓ created room {room_id}  '{body.get('name') or ''}'  "
           f"({body.get('visibility') or 'private'})")

    # 2. Sign an AKM key scoped to this room's thread
    scope = f"chat:thread:chatroom-{room_id}"
    r = C.clawd_call("POST", "/api/keys", json={
        "scope": scope,
        "ttl_seconds": DEFAULT_TTL_SECONDS,
        "label": f"sc-chatroom {room_id}",
        "rate_limit": DEFAULT_RATE_LIMIT,
    })
    if r.status_code != 201:
        C.die(f"clawd POST /api/keys returned {r.status_code}: {r.text}")
    key_resp = r.json()
    secret = key_resp["secret"]
    prefix = key_resp["key"]["prefix"]
    C.info(f"  ✓ AKM key minted ({prefix}…)")

    # 3. Register endpoint + key on the server so fan-out can reach this agent
    put_body: dict = {"agent_endpoint": C.AGENT_BASE_URL, "akm_key": secret}
    if C.CONTAINER_ID:
        put_body["container_id"] = C.CONTAINER_ID
    r = C.workroom_call(
        "PUT", f"/rooms/{room_id}/members/{C.USER_ID}/endpoint",
        json=put_body,
    )
    if r.status_code != 200:
        # Roll back the AKM key — don't leave a live secret that no one uses
        try:
            C.clawd_call("DELETE", f"/api/keys/{prefix}")
        except Exception:
            pass
        C.die(
            f"sc-chatroom PUT /endpoint returned {r.status_code}: {r.text}  "
            "(AKM key rolled back)"
        )
    C.info(f"  ✓ attached as fan-out target at {C.AGENT_BASE_URL}")

    # 4. Workspace
    d = C.ensure_room_workspace(room_id)
    C.info(f"  ✓ workspace ready at {d}")

    # 5. Remember the prefix for leave/rotate
    C.set_key(room_id, prefix)

    C.info("")
    C.info(f"Room {room_id} ready.")
    C.info(f"  Edit {d / 'rules.md'} to tune behavior.")
    C.info(f"  Invite someone:  python3 skills/workroom/scripts/invite.py {room_id}")
    C.info(f"  Open as a user:  python3 skills/workroom/scripts/room_key.py {room_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
