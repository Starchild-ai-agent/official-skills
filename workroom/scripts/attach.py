#!/usr/bin/env python3
"""workroom attach <room_id>

Register THIS agent as a fan-out target in a room where you're already a
member but don't yet have agent_endpoint + akm_key set. Covers two cases:

  1. You created the room before `workroom create` auto-attached owners.
     db.create_room inserts the owner with NULL endpoint/key, so sc-chatroom
     has nothing to fan out to. Running `attach <room_id>` fixes it.

  2. You cleared your endpoint somehow (manual PUT, external tooling) and
     want to re-arm fan-out without leaving + rejoining.

If you are not a member of the room yet, use `workroom join <invite_code>`
instead — `join` is the one-shot new-member flow.

Steps:
  1. GET /rooms/{id} → fail fast if the room doesn't exist or is archived
     (archived rooms are read-only; minting an AKM key for one would just
     leave an orphan secret behind)
  2. POST /api/keys → sign a fresh AKM key scoped to this room's thread
  3. PUT /rooms/{id}/members/{USER_ID}/endpoint with endpoint + key
  4. ensure /data/workspace/workroom/{room_id}/ rules.md + data.md
  5. Record AKM prefix in keys.json
"""
from __future__ import annotations

import argparse
import sys

import _common as C


DEFAULT_TTL_SECONDS = 90 * 24 * 3600    # 90 days; sliding-renewed by `workroom send`
DEFAULT_RATE_LIMIT = {"per_minute": 10}


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="workroom attach", description=__doc__)
    p.add_argument("room_id")
    args = p.parse_args(argv[1:])
    room_id = C.validate_room_id(args.room_id)
    C.require_env()

    # 0. Confirm room exists and is writable BEFORE any side-effects
    r = C.workroom_call("GET", f"/rooms/{room_id}")
    if r.status_code == 404:
        C.die(f"room {room_id} does not exist")
    if r.status_code != 200:
        C.die(f"sc-chatroom GET /rooms/{room_id} returned {r.status_code}: {r.text}")
    room = r.json()
    if room.get("archived"):
        C.die(
            f"room {room_id} is archived (read-only) — cannot attach. "
            "Owner must PATCH archived=false to re-open it."
        )

    # 1. Sign AKM key
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

    # 2. PUT endpoint + key (+ container_id for fly-force-instance-id routing)
    put_body: dict = {"agent_endpoint": C.AGENT_BASE_URL, "akm_key": secret}
    if C.CONTAINER_ID:
        put_body["container_id"] = C.CONTAINER_ID
    r = C.workroom_call(
        "PUT", f"/rooms/{room_id}/members/{C.USER_ID}/endpoint",
        json=put_body,
    )
    if r.status_code != 200:
        try:
            C.clawd_call("DELETE", f"/api/keys/{prefix}")
        except Exception:
            pass
        if r.status_code == 404:
            C.die(
                f"you are not a member of {room_id} — use "
                f"`workroom join <invite_code>` first (AKM key rolled back)"
            )
        C.die(
            f"sc-chatroom PUT /endpoint returned {r.status_code}: {r.text}  "
            "(AKM key rolled back)"
        )
    C.info(f"  ✓ attached as fan-out target at {C.AGENT_BASE_URL}")

    # 2b. If sc-chatroom was already holding a different AKM key for this
    #     member, it returns the prior key's prefix so we can revoke it
    #     locally. Otherwise the keystore accumulates orphan-active keys
    #     across re-attaches, and — far worse — that orphan can later get
    #     out-of-band revoked while sc-chatroom is still PUTting against
    #     it, leading to the silent 401-storm we just debugged. Best-
    #     effort: if the DELETE fails we keep going (the new key works
    #     either way).
    try:
        body = r.json()
    except ValueError:
        body = {}
    prior_prefix = body.get("prior_akm_prefix") if isinstance(body, dict) else None
    if isinstance(prior_prefix, str) and prior_prefix:
        try:
            rd = C.clawd_call("DELETE", f"/api/keys/{prior_prefix}")
            if rd.status_code in (200, 204, 404):
                C.info(f"  ✓ revoked previous AKM key ({prior_prefix}…)")
            else:
                C.info(
                    f"  ! could not revoke previous AKM key {prior_prefix}: "
                    f"HTTP {rd.status_code} (continuing — new key is active)"
                )
        except Exception as e:
            C.info(
                f"  ! could not revoke previous AKM key {prior_prefix}: "
                f"{e!r} (continuing — new key is active)"
            )

    # 3. Workspace (idempotent — safe on re-attach)
    d = C.ensure_room_workspace(room_id)
    C.info(f"  ✓ workspace ready at {d}")

    # 4. Record prefix
    C.set_key(room_id, prefix)

    C.info("")
    C.info(f"Room {room_id} is now wired up. Post a message as the user and")
    C.info("you should see fan-out reach this agent:")
    C.info(f"  fly logs -a sc-chatroom | grep 'fan-out room={room_id}'")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
