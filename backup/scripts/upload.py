#!/usr/bin/env python3
"""Upload a backup bundle to sc-agent-backup storage.

Usage:
    python3 upload.py <bundle.tar.gz> [--label LABEL] [--sections A,B,C]
                                      [--replace <backup_id>] [--resume]

Environment:
    CONTAINER_JWT         Required. Injected into clawd containers by ai-agent.
    BACKUP_STORAGE_URL    Optional. Defaults to http://sc-agent-backup.internal:8080.
    WORKSPACE_DIR         Optional. Where to store .active-upload.json. Default /workspace.

Exit codes:
    0  Either the upload succeeded, OR the quota is full and the existing
       backups are printed to stdout as JSON. The caller inspects stdout to
       tell the two apart:
         - success      → {"backup_id": "...", "size_bytes": ..., "sha256": ..., ...}
         - quota full   → {"error": "quota_exceeded", "current": [...]}
       Keeping quota-full at exit 0 avoids the harness flagging it as ✗ —
       it's an actionable outcome, not a failure.
    1  Network / auth / size / protocol failure. Error on stderr.

Transport strategy:
    * < RESUMABLE_THRESHOLD  : one-shot POST /backups (streamed from disk,
                               bounded memory).
    * >= RESUMABLE_THRESHOLD : reserve session → chunked POST per
                               CHUNK_SIZE → server auto-finalizes on last
                               chunk. A client-side state file lets a later
                               invocation resume at the server's current
                               offset after crashes / agent restarts.

This script never picks which backup to replace. That choice belongs to the
user — see SKILL.md §4.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_STORAGE = "http://sc-agent-backup.internal:8080"
MAX_UPLOAD_SIZE = 500 * 1024 * 1024       # mirror storage's cap
RESUMABLE_THRESHOLD = 10 * 1024 * 1024    # bundles >= 10MB use the resumable path
CHUNK_SIZE = 10 * 1024 * 1024             # 10 MB per chunk
UPLOAD_TIMEOUT = 600                      # per-request timeout, seconds
RETRY_BASE_DELAY = 1.0
RETRY_JITTER = 2.0                        # delay = BASE + uniform(0, JITTER)
STATE_FILENAME = ".active-upload.json"


def _storage_url() -> str:
    return os.environ.get("BACKUP_STORAGE_URL", DEFAULT_STORAGE).rstrip("/")


def _jwt() -> str:
    token = os.environ.get("CONTAINER_JWT", "").strip()
    if not token:
        print("ERROR: CONTAINER_JWT env var is not set.", file=sys.stderr)
        sys.exit(1)
    return token


def _workspace() -> Path:
    return Path(os.environ.get("WORKSPACE_DIR", "/workspace"))


def _state_path() -> Path:
    return _workspace() / STATE_FILENAME


def _load_state() -> dict | None:
    p = _state_path()
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _save_state(state: dict) -> None:
    p = _state_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False))
        os.replace(tmp, p)
    except Exception as e:
        # Best-effort — losing resume state just means we fall back to
        # restarting from the beginning. Don't crash the upload.
        print(f"WARN: could not persist resume state: {e}", file=sys.stderr)


def _clear_state() -> None:
    try:
        _state_path().unlink(missing_ok=True)
    except Exception:
        pass


def _build_manifest(label: str | None, sections: list[str] | None) -> dict:
    m: dict = {}
    if label:
        m["user_label"] = label
    if sections:
        m["sections"] = sections
    return m


def _check_bundle(path: Path) -> int:
    if not path.exists():
        print(f"ERROR: bundle not found: {path}", file=sys.stderr)
        sys.exit(1)
    size = path.stat().st_size
    if size == 0:
        print("ERROR: bundle is empty", file=sys.stderr)
        sys.exit(1)
    if size > MAX_UPLOAD_SIZE:
        print(
            f"ERROR: bundle too large ({size:,} B, max {MAX_UPLOAD_SIZE:,} B)",
            file=sys.stderr,
        )
        sys.exit(1)
    return size


class _NetworkError(Exception):
    """Transient transport failure worth one jittered retry."""


def _with_retry(fn):
    """Run fn once; on _NetworkError, sleep jittered and try once more.

    fn returns (status, body_bytes). HTTP errors are NOT retried — only
    transport-layer failures (DNS/connect/reset/timeout).
    """
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


# --- HTTP helpers ----------------------------------------------------------


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {_jwt()}"}


def _do_request(req: urllib.request.Request) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(req, timeout=UPLOAD_TIMEOUT) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except UnicodeEncodeError as e:
        # Usually a non-ASCII header slipped through. Surface a clean message
        # rather than a stack trace. Headers now default to ensure_ascii=True;
        # if this fires, someone added a header the old way.
        print(
            f"ERROR: non-ASCII byte in an HTTP header ({e}). "
            "Check that all header values are ASCII-safe.",
            file=sys.stderr,
        )
        sys.exit(1)
    except (urllib.error.URLError, OSError) as e:
        raise _NetworkError(str(e)) from e


def _post_json(url: str, body: dict) -> tuple[int, bytes]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            **_auth_headers(),
            "Content-Type": "application/json",
            "Content-Length": str(len(data)),
        },
        method="POST",
    )
    return _do_request(req)


def _get(url: str) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers=_auth_headers(), method="GET")
    return _do_request(req)


# --- One-shot streaming POST /backups -------------------------------------


def _one_shot_upload(
    url: str, path: Path, size: int, manifest: dict
) -> tuple[int, bytes]:
    headers = {
        **_auth_headers(),
        "Content-Type": "application/octet-stream",
        "Content-Length": str(size),
    }
    if manifest:
        # HTTP header values go through latin-1 encoding in http.client,
        # which rejects CJK and other non-ASCII chars. Use ensure_ascii=True
        # so "升级前" etc. become \uXXXX escapes in the JSON — still valid
        # JSON, server-side json.loads decodes them back.
        headers["X-Manifest"] = json.dumps(manifest, ensure_ascii=True)

    def _do():
        with open(path, "rb") as f:
            req = urllib.request.Request(url, data=f, headers=headers, method="POST")
            return _do_request(req)

    return _with_retry(_do)


# --- Resumable path -------------------------------------------------------


def _progress(upload_id: str, offset: int, total: int) -> None:
    pct = (offset / total * 100) if total else 0.0
    print(
        f"[upload] {upload_id}  "
        f"{offset // (1024 * 1024)}/{total // (1024 * 1024)} MB ({pct:.1f}%)",
        file=sys.stderr,
    )


def _reserve_session(manifest: dict, total: int, replace_id: str | None) -> dict:
    """POST /uploads/reserve → {upload_id, offset}. Exits on non-201."""
    body: dict = {"total": total}
    if manifest:
        body["manifest"] = manifest
    if replace_id:
        body["replace"] = replace_id

    def _do():
        return _post_json(f"{_storage_url()}/uploads/reserve", body)

    status, resp_body = _with_retry(_do)
    if status == 201:
        return json.loads(resp_body.decode("utf-8"))

    # Surface quota / replace errors through the same exit codes as the
    # one-shot path so the skill's handling logic is unchanged.
    try:
        err = json.loads(resp_body.decode("utf-8"))
    except Exception:
        err = {"raw": resp_body.decode("utf-8", errors="replace")}

    if status == 409:
        # Quota full — stdout JSON includes the 5 existing backups. Exit 0
        # so the harness doesn't flag it as a failure; the agent branches on
        # the presence of "error": "quota_exceeded" in stdout.
        print(json.dumps(err, ensure_ascii=False, indent=2))
        sys.exit(0)
    if status == 413:
        print(
            f"ERROR: declared total exceeds the storage's "
            f"{MAX_UPLOAD_SIZE // (1024 * 1024)}MB limit",
            file=sys.stderr,
        )
    elif status == 401:
        print(f"ERROR: unauthorized — {err.get('message')}", file=sys.stderr)
    elif status == 403:
        print("ERROR: forbidden — this upload must originate from Fly 6PN",
              file=sys.stderr)
    elif status == 404 and replace_id:
        print(f"ERROR: replace target not found: {replace_id}", file=sys.stderr)
    else:
        print(f"ERROR: reserve failed HTTP {status} — {err}", file=sys.stderr)
    sys.exit(1)


def _query_offset(upload_id: str) -> int | None:
    """GET /uploads/{id} → current offset, or None if the session is gone."""
    status, body = _with_retry(lambda: _get(f"{_storage_url()}/uploads/{upload_id}"))
    if status == 200:
        return json.loads(body.decode("utf-8"))["offset"]
    if status == 404:
        return None
    print(f"ERROR: status query failed HTTP {status} — {body!r}", file=sys.stderr)
    sys.exit(1)


def _send_chunk(
    upload_id: str, offset: int, chunk: bytes, total: int
) -> tuple[int, dict]:
    """Send one chunk. Returns (status, parsed_body)."""
    end = offset + len(chunk) - 1
    headers = {
        **_auth_headers(),
        "Content-Type": "application/octet-stream",
        "Content-Range": f"bytes {offset}-{end}/{total}",
        "Content-Length": str(len(chunk)),
    }

    def _do():
        req = urllib.request.Request(
            f"{_storage_url()}/uploads/{upload_id}/chunk",
            data=chunk,
            headers=headers,
            method="POST",
        )
        return _do_request(req)

    status, body = _with_retry(_do)
    try:
        parsed = json.loads(body.decode("utf-8"))
    except Exception:
        parsed = {"raw": body.decode("utf-8", errors="replace")}
    return status, parsed


def _resumable_upload(
    path: Path, size: int, manifest: dict, replace_id: str | None
) -> dict:
    """Drive a resumable upload to completion. Returns the final backup
    metadata dict (backup_id, size_bytes, sha256, remaining_slots, ...).
    """
    # Resume from prior state if the state file matches this bundle.
    state = _load_state()
    session: dict | None = None
    if state and state.get("bundle_path") == str(path.resolve()) and state.get("size") == size:
        uid = state["upload_id"]
        off = _query_offset(uid)
        if off is not None:
            print(
                f"[upload] resuming session {uid} from offset "
                f"{off}/{size} ({off / size * 100:.1f}%)",
                file=sys.stderr,
            )
            session = {"upload_id": uid, "offset": off}
        else:
            # Server forgot the session (TTL expired, aborted, or a new
            # deploy wiped /data/sessions). Discard local state and reserve
            # fresh.
            print(
                f"[upload] prior session {uid} expired on server; starting fresh",
                file=sys.stderr,
            )
            _clear_state()

    if session is None:
        reserved = _reserve_session(manifest, size, replace_id)
        session = {"upload_id": reserved["upload_id"], "offset": reserved["offset"]}
        _save_state({
            "upload_id": session["upload_id"],
            "bundle_path": str(path.resolve()),
            "size": size,
            "started_at": int(time.time()),
        })

    upload_id: str = session["upload_id"]
    offset: int = session["offset"]

    with open(path, "rb") as f:
        while offset < size:
            f.seek(offset)
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break

            status, parsed = _send_chunk(upload_id, offset, chunk, size)

            if status == 202:
                offset = parsed["offset"]
                _progress(upload_id, offset, size)
                continue
            if status == 201:
                _progress(upload_id, size, size)
                _clear_state()
                return parsed
            if status == 409:
                # Server offset is elsewhere (e.g. an old retry actually
                # succeeded). Seek to server's truth and retry from there.
                server_offset = parsed.get("offset", 0)
                print(
                    f"[upload] offset mismatch; server says {server_offset}, "
                    f"resuming from there",
                    file=sys.stderr,
                )
                offset = server_offset
                continue
            if status == 404:
                # Session vanished mid-upload (TTL / server wipe). Drop state
                # and bail — caller may retry the whole thing.
                _clear_state()
                print(
                    "ERROR: upload session expired on server mid-transfer. "
                    "Run the upload again to start over.",
                    file=sys.stderr,
                )
                sys.exit(1)
            if status == 413:
                _clear_state()
                print(f"ERROR: chunk rejected: {parsed.get('message')}",
                      file=sys.stderr)
                sys.exit(1)

            # Anything else — give up.
            print(f"ERROR: chunk HTTP {status} — {parsed}", file=sys.stderr)
            sys.exit(1)

    # If we got here, we wrote all bytes but the last response wasn't 201.
    # That's a protocol bug — surface it loudly.
    print("ERROR: upload finished sending but server did not finalize",
          file=sys.stderr)
    sys.exit(1)


# --- CLI entry point -------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path, help="path to backup tar.gz")
    parser.add_argument("--label", type=str, default=None,
                        help="optional user-facing label, ≤64 chars")
    parser.add_argument("--sections", type=str, default=None,
                        help="comma-separated list of sections included")
    parser.add_argument("--replace", type=str, default=None,
                        help="backup_id to replace atomically")
    parser.add_argument("--force-resumable", action="store_true",
                        help="force the resumable path regardless of size "
                             "(for tests)")
    args = parser.parse_args()

    size = _check_bundle(args.bundle)
    sections = None
    if args.sections:
        sections = [s.strip() for s in args.sections.split(",") if s.strip()]
    manifest = _build_manifest(args.label, sections)

    if size >= RESUMABLE_THRESHOLD or args.force_resumable:
        resp = _resumable_upload(args.bundle, size, manifest, args.replace)
        print(json.dumps(resp, ensure_ascii=False))
        sys.exit(0)

    # One-shot path for small bundles.
    url = f"{_storage_url()}/backups"
    if args.replace:
        url += f"?replace={args.replace}"
    status, body = _one_shot_upload(url, args.bundle, size, manifest)

    if status == 201:
        print(body.decode("utf-8"))
        sys.exit(0)

    try:
        err = json.loads(body.decode("utf-8"))
    except Exception:
        err = {"raw": body.decode("utf-8", errors="replace")}

    if status == 409:
        # Quota full — stdout JSON lists the 5 existing backups. Exit 0
        # so the harness doesn't flag it as a failure; the agent branches on
        # the "error": "quota_exceeded" marker in stdout.
        print(json.dumps(err, ensure_ascii=False, indent=2))
        sys.exit(0)

    if status == 401:
        print(f"ERROR: unauthorized — {err.get('message', 'bad or missing JWT')}",
              file=sys.stderr)
    elif status == 403:
        print("ERROR: forbidden — this upload must originate from Fly 6PN",
              file=sys.stderr)
    elif status == 413:
        print(
            f"ERROR: bundle exceeds the storage's "
            f"{MAX_UPLOAD_SIZE // (1024 * 1024)}MB limit",
            file=sys.stderr,
        )
    elif status == 400:
        print(f"ERROR: bad request — {err.get('message', body)}",
              file=sys.stderr)
    elif status == 404 and args.replace:
        print(f"ERROR: replace target not found: {args.replace}",
              file=sys.stderr)
    else:
        print(f"ERROR: HTTP {status} — {err}", file=sys.stderr)

    sys.exit(1)


if __name__ == "__main__":
    main()
