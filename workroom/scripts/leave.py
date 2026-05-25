#!/usr/bin/env python3
"""workroom leave <room_id>

Drops membership server-side first, then revokes the local AKM key.

The order matters: if we revoked the key first and the server-side leave
then failed (network blip, 5xx), we'd land in an unrecoverable state —
the agent would still be in the room but every fan-out would 401, AND
the agent has no easy handle to retry (the key prefix is already gone
from keys.json). After this reorder, a failed leave just leaves both
membership AND key intact, and re-running ``workroom leave`` is safe.
Conversely, if the server drops us but the local DELETE /api/keys
fails, the membership is already gone so the orphan key is harmless —
it stays in the keystore until it expires (or gets cleaned up by
``workroom list-keys``).
"""
from __future__ import annotations

import argparse
import sys

import _common as C


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="workroom leave", description=__doc__)
    p.add_argument("room_id")
    args = p.parse_args(argv[1:])
    room_id = C.validate_room_id(args.room_id)
    C.require_env()

    # 1. Remove membership server-side. Until this returns 200/404 we leave
    #    the local AKM key alone so fan-out keeps working (and a retry of
    #    `workroom leave` stays safe).
    r = C.workroom_call("DELETE", f"/rooms/{room_id}/members/{C.USER_ID}")
    if r.status_code == 200:
        C.info(f"  ✓ left room {room_id}")
    elif r.status_code == 404:
        C.info(f"  · not a member of {room_id} anyway")
    else:
        C.die(
            f"sc-chatroom DELETE /members returned {r.status_code}: {r.text} "
            "(local AKM key left intact so retry stays safe)"
        )

    # 2. Membership is gone — now we can revoke the AKM key. The local
    #    prefix is removed first so that even if the DELETE call below
    #    fails, a future `workroom leave` won't try to revoke again (the
    #    key is now orphaned in the keystore, but nothing points at it).
    prefix = C.pop_key(room_id)
    if prefix:
        try:
            rd = C.clawd_call("DELETE", f"/api/keys/{prefix}")
            if rd.status_code in (200, 404):
                C.info(f"  ✓ local AKM key revoked ({prefix}…)")
            else:
                C.info(
                    f"  ! clawd /api/keys DELETE returned {rd.status_code}: "
                    f"{rd.text} (membership already removed; orphan key "
                    "will expire on its own)"
                )
        except Exception as e:
            C.info(
                f"  ! could not revoke local AKM key {prefix}: {e!r} "
                "(membership already removed; orphan key will expire on its own)"
            )
    else:
        C.info(f"  · no local AKM key recorded for {room_id}")

    ws = C.room_workspace_dir(room_id)
    if ws.exists():
        C.info(f"  · workspace at {ws} left intact (delete manually to forget)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
