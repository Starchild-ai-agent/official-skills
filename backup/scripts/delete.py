#!/usr/bin/env python3
"""Delete a backup from sc-agent-backup storage.

Usage:
    python3 delete.py <backup_id> --confirm <backup_id>

Both positional `<backup_id>` and the `--confirm` value must match EXACTLY.
This is a tripwire, not a substitute for user confirmation — the SKILL.md
Flow C requires the agent to obtain TWO distinct user confirmations before
calling this script at all (see SKILL.md §C.3 and §C.4).

Before issuing DELETE, the script calls `GET /backups` to fetch the target
backup's metadata (label / created_at / size / sections). It prints that
metadata to stdout as JSON so the agent can tell the user what was deleted.

Environment:
    CONTAINER_JWT         Required.
    BACKUP_STORAGE_URL    Optional. Defaults to http://sc-agent-backup.internal:8080.

Exit codes:
    0   backup deleted (server returned 204). stdout has the deleted backup's
        metadata as JSON.
    1   network / auth / 404 / other HTTP failure. Error on stderr.
    2   --confirm value did NOT match backup_id (tripwire triggered —
        the agent likely skipped the double-confirm flow).
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request

DEFAULT_STORAGE = "http://sc-agent-backup.internal:8080"
TIMEOUT = 30
RETRY_BASE_DELAY = 1.0
RETRY_JITTER = 2.0

_BACKUP_ID_RE = re.compile(r"^bk_\d{8}_\d{6}_[a-z0-9]{4}$")


def _storage_url() -> str:
    return os.environ.get("BACKUP_STORAGE_URL", DEFAULT_STORAGE).rstrip("/")


def _jwt() -> str:
    token = os.environ.get("CONTAINER_JWT", "").strip()
    if not token:
        print("ERROR: CONTAINER_JWT env var is not set.", file=sys.stderr)
        sys.exit(1)
    return token


class _NetworkError(Exception):
    """Transient transport failure worth one jittered retry."""


def _with_retry(fn):
    last_err: _NetworkError | None = None
    for attempt in range(2):
        try:
            return fn()
        except _NetworkError as e:
            last_err = e
            if attempt == 0:
                delay = RETRY_BASE_DELAY + random.uniform(0, RETRY_JITTER)
                print(
                    f"WARN: transient network error ({e}); "
                    f"retrying once in {delay:.1f}s...",
                    file=sys.stderr,
                )
                time.sleep(delay)
    print(
        "ERROR: cannot reach backup storage over Fly internal network. "
        "This script must run inside a Fly machine.",
        file=sys.stderr,
    )
    print(f"DETAIL: {last_err}", file=sys.stderr)
    sys.exit(1)


def _fetch_backup_meta(backup_id: str) -> dict | None:
    """GET /backups, return the entry matching backup_id (or None).

    Using list-then-match instead of a direct HEAD/GET on /backups/{id}:
    listing already filters by JWT tenant, so we get the metadata + a
    no-match acts as the 'already gone' signal without an extra round trip.
    """
    def _do():
        req = urllib.request.Request(
            f"{_storage_url()}/backups",
            headers={"Authorization": f"Bearer {_jwt()}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()
        except (urllib.error.URLError, OSError) as e:
            raise _NetworkError(str(e)) from e

    status, body = _with_retry(_do)
    if status != 200:
        try:
            err = json.loads(body.decode("utf-8"))
        except Exception:
            err = {"raw": body.decode("utf-8", errors="replace")}
        if status == 401:
            print(f"ERROR: unauthorized — {err.get('message', 'bad JWT')}",
                  file=sys.stderr)
        elif status == 403:
            print("ERROR: forbidden — must run from Fly 6PN", file=sys.stderr)
        else:
            print(f"ERROR: list failed HTTP {status} — {err}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        print("ERROR: storage returned non-JSON for /backups", file=sys.stderr)
        sys.exit(1)

    for b in data.get("backups", []):
        if b.get("backup_id") == backup_id:
            return b
    return None


def _do_delete(backup_id: str) -> int:
    """Issue DELETE /backups/{id}. Returns HTTP status code."""
    def _do():
        req = urllib.request.Request(
            f"{_storage_url()}/backups/{backup_id}",
            headers={"Authorization": f"Bearer {_jwt()}"},
            method="DELETE",
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.status
        except urllib.error.HTTPError as e:
            return e.code
        except (urllib.error.URLError, OSError) as e:
            raise _NetworkError(str(e)) from e

    return _with_retry(_do)


def main() -> None:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
    )
    parser.add_argument("backup_id", type=str,
                        help="the backup_id to delete")
    parser.add_argument(
        "--confirm", type=str, required=True,
        help="MUST equal backup_id exactly — tripwire against the agent "
             "skipping the SKILL.md Flow C double-confirmation. Callers "
             "that pass `--confirm` without first getting two distinct "
             "user acknowledgements are violating the skill contract.",
    )
    args = parser.parse_args()

    # ── Pre-flight: id format ─────────────────────────────────────────────
    if not _BACKUP_ID_RE.match(args.backup_id):
        print(f"ERROR: malformed backup_id: {args.backup_id!r} "
              f"(expected bk_YYYYMMDD_HHMMSS_xxxx)", file=sys.stderr)
        sys.exit(1)

    # ── Tripwire: --confirm must match exactly ────────────────────────────
    if args.confirm != args.backup_id:
        print(
            f"ERROR: --confirm value ({args.confirm!r}) does not match "
            f"backup_id ({args.backup_id!r}).\n"
            "This tripwire guards against accidental deletes. Per SKILL.md "
            "Flow C, the agent must obtain TWO user confirmations before "
            "invoking delete.py, and pass the backup_id as --confirm only "
            "once the user has typed it back verbatim (Step C.4).",
            file=sys.stderr,
        )
        sys.exit(2)

    # ── Fetch metadata up-front so we can echo what got deleted ───────────
    meta = _fetch_backup_meta(args.backup_id)
    if meta is None:
        # Same response server-side returns 404 for cross-tenant and
        # genuinely missing — we treat both the same.
        print(
            f"ERROR: backup not found (already deleted, or does not belong "
            f"to this user): {args.backup_id}",
            file=sys.stderr,
        )
        sys.exit(1)

    # ── Issue the DELETE ─────────────────────────────────────────────────
    status = _do_delete(args.backup_id)
    if status == 204:
        result = {
            "deleted_backup_id": meta.get("backup_id"),
            "user_label": meta.get("user_label"),
            "created_at": meta.get("created_at"),
            "size_bytes": meta.get("size_bytes"),
            "sections": meta.get("sections"),
        }
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)

    if status == 404:
        # Race: someone else deleted it between our list and delete. Still a
        # success from the user's point of view (the backup is gone). But
        # we report it as an error so the flow is transparent.
        print(
            "ERROR: backup vanished between list and delete (race). "
            "Re-list to confirm it's gone.", file=sys.stderr,
        )
        sys.exit(1)
    if status == 401:
        print("ERROR: unauthorized — CONTAINER_JWT invalid or expired",
              file=sys.stderr)
    elif status == 403:
        print("ERROR: forbidden — must run from Fly 6PN", file=sys.stderr)
    else:
        print(f"ERROR: delete failed HTTP {status}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
