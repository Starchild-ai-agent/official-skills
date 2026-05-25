#!/usr/bin/env python3
"""workroom join <invite_code | short_code>

Usage:
  python3 skills/workroom/scripts/join.py <invite_code>
  python3 skills/workroom/scripts/join.py i_xxxxxxxx       # short code

Flow:
  1. If arg looks like a short code (i_…), resolve to JWT via GET /i/<code>
  2. Peek at the invite to learn room_id
  3. Sign a scope-limited AKM key locally via clawd /api/keys
  4. POST sc-chatroom/rooms/<room_id>/join with invite + endpoint + akm_key
  5. Initialize workspace rules.md (data.md no longer created; see /rooms/{id}/data)
  6. Remember the AKM prefix in keys.json for later leave/rotate
"""
from __future__ import annotations

import argparse
import os
import sys

import _common as C
import install_soul
import self_update


DEFAULT_TTL_SECONDS = 90 * 24 * 3600    # 90 days; sliding-renewed by `workroom send`
DEFAULT_RATE_LIMIT = {"per_minute": 10}


def _resolve_short_code(short: str) -> str:
    """GET /i/<short> on sc-chatroom and return the wrapped invite JWT.
    Public endpoint, no auth needed (the short code itself is the
    capability — anyone holding it can already join the room)."""
    r = C.workroom_call("GET", f"/i/{short}", headers={"Authorization": ""})
    if r.status_code != 200:
        C.die(f"short code {short!r} returned {r.status_code}: {r.text}")
    jwt = (r.text or "").strip()
    if not jwt or jwt.count(".") != 2:
        C.die(f"short code {short!r} did not resolve to an invite JWT")
    return jwt


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="workroom join", description=__doc__)
    p.add_argument("invite_code",
                   help="full invite JWT or short code (i_xxxxxxxx)")
    args = p.parse_args(argv[1:])
    arg = args.invite_code.strip()
    if not arg:
        C.die("invite_code is empty")
    if arg.startswith("-"):
        C.die(f"invite_code {arg!r} looks like a flag — pass `--help` for usage")

    C.require_env()

    # If the arg looks like a short code (no JWT dots, has the i_ prefix),
    # resolve it on the server first. JWTs always have exactly two dots.
    if arg.startswith("i_") and arg.count(".") == 0:
        C.info(f"→ resolving short code {arg}")
        invite_code = _resolve_short_code(arg)
    else:
        invite_code = arg

    # Auto-install/upgrade the SOUL block so the agent honors room rules
    # (fetched via GET /rules on rules_version bump) and emits [SILENT]
    # from its very first turn. Idempotent, runs once per-agent (not
    # per-room) — no-op on subsequent calls.
    try:
        soul_status = install_soul.ensure_installed()
        if soul_status in ("installed", "upgraded"):
            C.info(f"  ✓ SOUL workroom block {soul_status}")
    except Exception as e:
        C.info(f"  ⚠  could not auto-install SOUL block: {e!r} "
               "(run `workroom install-soul` manually)")

    # Discover and apply skill bundle updates published by sc-chatroom.
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

    claims = C.peek_invite(invite_code)
    room_id = claims["room_id"]
    C.info(f"→ joining room {room_id} (invited by {claims['created_by']})")

    # 1. Create AKM key
    scope = f"chat:thread:chatroom-{room_id}"
    create_body = {
        "scope": scope,
        "ttl_seconds": DEFAULT_TTL_SECONDS,
        "label": f"sc-chatroom {room_id}",
        "rate_limit": DEFAULT_RATE_LIMIT,
    }
    r = C.clawd_call("POST", "/api/keys", json=create_body)
    if r.status_code != 201:
        C.die(f"clawd /api/keys returned {r.status_code}: {r.text}")
    key_resp = r.json()
    secret = key_resp["secret"]
    prefix = key_resp["key"]["prefix"]
    C.info(f"  ✓ AKM key minted ({prefix}…, ttl={DEFAULT_TTL_SECONDS}s)")

    # 2. Join the room
    body = {
        "invite_code": invite_code,
        "agent_endpoint": C.AGENT_BASE_URL,
        "akm_key": secret,
    }
    if C.CONTAINER_ID:
        body["container_id"] = C.CONTAINER_ID
    # Publish our own A2A agent-card URL so peers in the room can fetch
    # our capabilities (mig 009). Defaults to the local clawd's
    # well-known endpoint; users can override via STARCHILD_AGENT_CARD_URL.
    card_url = (os.environ.get("STARCHILD_AGENT_CARD_URL") or "").strip()
    if not card_url and C.AGENT_BASE_URL:
        card_url = C.AGENT_BASE_URL.rstrip("/") + "/.well-known/agent-card.json"
    if card_url:
        body["agent_card_url"] = card_url
    r = C.workroom_call("POST", f"/rooms/{room_id}/join", json=body)
    if r.status_code != 201:
        # Roll back the AKM key — no point leaving a live secret in the ether.
        try:
            C.clawd_call("DELETE", f"/api/keys/{prefix}")
        except Exception:
            pass
        C.die(f"sc-chatroom /join returned {r.status_code}: {r.text}")
    C.info(f"  ✓ joined as {C.USER_ID}, endpoint={C.AGENT_BASE_URL}")

    # 3. Workspace files
    d = C.ensure_room_workspace(room_id)
    C.info(f"  ✓ workspace ready at {d}")

    # 4. Remember the prefix
    C.set_key(room_id, prefix)

    # 5. Auto-join the public reserved channels (#welcome / #feedback /
    #    #bugs). Idempotent server-side; we do this on every join because
    #    the cost is one round-trip and it self-heals if the user was kicked
    #    or never joined them. Failure is non-fatal — the primary join
    #    already succeeded.
    try:
        r = C.workroom_call("POST", "/rooms/public/auto-join")
        if r.status_code == 200:
            payload = r.json()
            new_rooms = [x["room_id"] for x in payload.get("reserved_rooms", [])
                         if x.get("newly_joined")]
            if new_rooms:
                C.info(f"  ✓ auto-joined reserved rooms: {', '.join(new_rooms)}")
    except Exception as e:
        C.info(f"  ⚠  could not auto-join reserved rooms: {e!r}")

    C.info("")
    C.info(f"Room {room_id} joined. To tune behavior, edit:")
    C.info(f"  {d / 'rules.md'}")
    C.info("When your user wants to read the room in a browser, run:")
    C.info(f"  python3 skills/workroom/scripts/room_key.py {room_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
