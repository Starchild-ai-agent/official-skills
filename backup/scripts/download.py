#!/usr/bin/env python3
"""Download a backup from sc-agent-backup and extract it into
/data/workspace/.restore/{backup_id}/.

Usage:
    python3 download.py <backup_id>

Environment:
    CONTAINER_JWT         Required.
    BACKUP_STORAGE_URL    Optional. Defaults to http://sc-agent-backup.internal:8080.
    WORKSPACE_DIR         Optional. Defaults to /data/workspace.

Three layers of integrity protection (belt + suspenders + airbag):
  1. X-Sha256 header: server returns the whole-bundle sha256; client streams
     the body to tmp while hashing, rejects on mismatch (catches transport /
     storage corruption).
  2. Tar member path audit: absolute paths and ".." are refused before extract.
  3. Per-file sha256 in manifest.contents: after extract, every file listed in
     manifest is rehashed and compared (catches tar format corruption, an
     edited/mismatched manifest, or post-extract tampering between download
     and apply).

Extraction lands under /data/workspace/.restore/{backup_id}/ so two
concurrent restores of different backups never stomp each other, and
retrying the same backup just re-extracts in place.

Exit codes:
    0   bundle downloaded, extracted, and integrity-verified. Prints a
        human summary to stdout.
    1   network / auth / bundle-corruption / manifest-mismatch. stderr has
        a detailed message.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import shutil
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_STORAGE = "http://sc-agent-backup.internal:8080"
MAX_SIZE = 500 * 1024 * 1024
DOWNLOAD_TIMEOUT = 600  # seconds; room for 500MB over slow links
READ_CHUNK = 64 * 1024
RETRY_BASE_DELAY = 1.0
RETRY_JITTER = 2.0  # jittered retry to avoid thundering-herd on recovery
WORKSPACE = Path(os.environ.get("WORKSPACE_DIR", "/data/workspace"))
RESTORE_ROOT = WORKSPACE / ".restore"

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
    """Transient transport failure worth one retry."""


def _stream_to_file(backup_id: str, dest: Path) -> str:
    """GET the bundle and stream it chunk-by-chunk to `dest`, returning the
    server's X-Sha256 header. Raises _NetworkError on transport-level failure.
    HTTP errors (401/403/404) call sys.exit(1) directly — not retryable."""
    req = urllib.request.Request(
        f"{_storage_url()}/backups/{backup_id}",
        headers={"Authorization": f"Bearer {_jwt()}"},
        method="GET",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        if e.code == 401:
            print("ERROR: unauthorized — CONTAINER_JWT invalid or expired", file=sys.stderr)
        elif e.code == 403:
            print("ERROR: forbidden — must run from Fly 6PN", file=sys.stderr)
        elif e.code == 404:
            print(f"ERROR: backup not found: {backup_id}", file=sys.stderr)
        elif e.code == 400:
            print(f"ERROR: bad backup_id: {body}", file=sys.stderr)
        else:
            print(f"ERROR: HTTP {e.code} — {body}", file=sys.stderr)
        sys.exit(1)
    except (urllib.error.URLError, OSError) as e:
        raise _NetworkError(str(e)) from e

    sha_header = resp.headers.get("X-Sha256", "")
    total = 0
    try:
        with open(dest, "wb") as f:
            while True:
                chunk = resp.read(READ_CHUNK)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_SIZE:
                    raise _NetworkError(f"bundle exceeds MAX_SIZE={MAX_SIZE}")
                f.write(chunk)
    except (urllib.error.URLError, OSError) as e:
        raise _NetworkError(str(e)) from e
    finally:
        resp.close()

    return sha_header


def _download_with_retry(backup_id: str, dest: Path) -> str:
    """One-shot, then one jittered retry on transport failure."""
    last_err: _NetworkError | None = None
    for attempt in range(2):
        try:
            return _stream_to_file(backup_id, dest)
        except _NetworkError as e:
            last_err = e
            # Clean up any partial data before retrying so we start from byte 0.
            try:
                dest.unlink(missing_ok=True)
            except Exception:
                pass
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


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(READ_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def download(backup_id: str) -> tuple[Path, str]:
    """Stream the bundle into a local tmp file. Returns (path, sha256_header).

    The caller is responsible for unlinking the returned path after use.
    Memory stays bounded at READ_CHUNK regardless of bundle size.
    """
    tmp = Path(tempfile.mkstemp(suffix=".tar.gz", prefix=f"{backup_id}.")[1])
    sha_header = _download_with_retry(backup_id, tmp)

    if sha_header:
        actual = _sha256_file(tmp)
        if actual != sha_header:
            tmp.unlink(missing_ok=True)
            print(
                f"ERROR: whole-bundle sha256 mismatch — got {actual}, "
                f"expected {sha_header}. Bundle may be corrupt in transit or "
                "on server disk. Pick another backup.",
                file=sys.stderr,
            )
            sys.exit(1)

    return tmp, sha_header


def extract(bundle_path: Path, extract_dir: Path) -> dict:
    """Extract bundle into extract_dir. Returns the parsed manifest.json.

    If extract_dir already exists it's wiped first — retrying the same
    backup replaces the prior extract atomically (from the user's POV).
    """
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    try:
        with tarfile.open(bundle_path, "r:gz") as tar:
            for member in tar.getmembers():
                if member.name.startswith("/") or ".." in member.name.split("/"):
                    print(f"ERROR: dangerous path in archive: {member.name}",
                          file=sys.stderr)
                    sys.exit(1)
            tar.extractall(extract_dir, filter="data")
    except tarfile.TarError as e:
        print(f"ERROR: invalid tar.gz: {e}", file=sys.stderr)
        sys.exit(1)

    manifest_path = extract_dir / "manifest.json"
    if not manifest_path.exists():
        print("ERROR: bundle has no manifest.json at root", file=sys.stderr)
        sys.exit(1)

    try:
        return json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid manifest.json: {e}", file=sys.stderr)
        sys.exit(1)


def verify_per_file(manifest: dict, extract_dir: Path) -> None:
    """Re-hash every file listed in manifest.contents and compare against the
    recorded sha256. On ANY mismatch, print the full list of bad files to
    stderr and exit 1 — do not let the caller proceed to apply.

    Also checks for files listed in manifest that are missing on disk, AND
    files on disk that aren't listed in manifest (extra files shouldn't be
    applied — they'd indicate a pre-v1.1 bundle or tampering).
    """
    contents = manifest.get("contents")
    if not isinstance(contents, dict):
        # Pre-v1.1 manifest — skip per-file check with a warning.
        print(
            "WARN: bundle manifest has no `contents` section (pre-v1.1 "
            "bundle). Skipping per-file hash verification. Whole-bundle "
            "sha256 was verified at download time.",
            file=sys.stderr,
        )
        return

    expected: dict[str, dict] = {}
    for entry in contents.get("files", []):
        expected[entry["path"]] = entry
    for entry in contents.get("api", []):
        expected[entry["path"]] = entry

    # Walk disk, compare each file.
    on_disk: dict[str, Path] = {}
    for p in extract_dir.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(extract_dir).as_posix()
        if rel == "manifest.json":
            continue
        on_disk[rel] = p

    bad: list[str] = []
    missing: list[str] = []
    for path, entry in expected.items():
        p = on_disk.get(path)
        if p is None:
            missing.append(path)
            continue
        if p.stat().st_size != entry.get("size"):
            bad.append(f"{path}  (size mismatch: "
                       f"got {p.stat().st_size}, expected {entry.get('size')})")
            continue
        digest = _sha256_file(p)
        if digest != entry.get("sha256"):
            bad.append(f"{path}  (sha256 mismatch: "
                       f"got {digest[:16]}…, expected {entry.get('sha256', '')[:16]}…)")

    extra = [p for p in on_disk if p not in expected]

    if bad or missing or extra:
        print("ERROR: bundle contents verification failed.", file=sys.stderr)
        if bad:
            print(f"  corrupted files ({len(bad)}):", file=sys.stderr)
            for b in bad[:20]:
                print(f"    {b}", file=sys.stderr)
            if len(bad) > 20:
                print(f"    ... ({len(bad) - 20} more)", file=sys.stderr)
        if missing:
            print(f"  missing files listed in manifest ({len(missing)}):",
                  file=sys.stderr)
            for m in missing[:20]:
                print(f"    {m}", file=sys.stderr)
            if len(missing) > 20:
                print(f"    ... ({len(missing) - 20} more)", file=sys.stderr)
        if extra:
            print(f"  extra files NOT in manifest ({len(extra)}):",
                  file=sys.stderr)
            for e in extra[:20]:
                print(f"    {e}", file=sys.stderr)
            if len(extra) > 20:
                print(f"    ... ({len(extra) - 20} more)", file=sys.stderr)
        print(
            "\nDo NOT proceed to restore. Pick another backup, or delete this "
            "one via Flow C and re-take a fresh backup.",
            file=sys.stderr,
        )
        sys.exit(1)


def summarize(manifest: dict, extract_dir: Path) -> None:
    print(f"Bundle extracted to {extract_dir}/")
    print(f"  source    : {manifest.get('source', 'unknown')}")
    print(f"  version   : {manifest.get('version')}")
    print(f"  label     : {manifest.get('label') or '(no label)'}")
    print(f"  created_at: {manifest.get('created_at')}")
    contents = manifest.get("contents", {}) or {}
    files = contents.get("files") or []
    api = contents.get("api") or []
    total_size = sum(e.get("size", 0) for e in files) + sum(e.get("size", 0) for e in api)
    print(f"  files     : {len(files)} (filesystem state) + {len(api)} (api state)")
    print(f"  total     : {total_size:,} bytes")
    print()

    # Group files by top-level section under files/ for a human-readable
    # breakdown (workspace/memory, workspace/prompt, data/, …).
    buckets: dict[str, list[dict]] = {}
    for entry in files:
        parts = entry["path"].split("/", 2)
        # path like "files/workspace/memory/MEMORY.md" → bucket "files/workspace"
        if len(parts) >= 2:
            key = "/".join(parts[:2])
        else:
            key = entry["path"]
        buckets.setdefault(key, []).append(entry)

    if buckets:
        print("Filesystem sections:")
        for key in sorted(buckets):
            items = buckets[key]
            size = sum(e.get("size", 0) for e in items)
            print(f"  {key:<30s} {len(items):>4d} files  {size:>10,} bytes")
        print()

    if api:
        print("API sections:")
        for entry in sorted(api, key=lambda e: e["path"]):
            print(f"  {entry['path']:<30s} {entry.get('size', 0):>10,} bytes")
        print()

    warnings = (manifest.get("plan_summary") or {}).get("warnings") or []
    if warnings:
        print("Pack-time warnings:")
        for w in warnings:
            print(f"  ⚠ {w}")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 download.py <backup_id>", file=sys.stderr)
        sys.exit(1)

    backup_id = sys.argv[1].strip()
    if not _BACKUP_ID_RE.match(backup_id):
        print(f"ERROR: invalid backup_id format: {backup_id!r}", file=sys.stderr)
        sys.exit(1)

    extract_dir = RESTORE_ROOT / backup_id

    print(f"Downloading {backup_id} ...")
    bundle_path, sha = download(backup_id)
    size = bundle_path.stat().st_size
    try:
        print(f"Downloaded {size:,} bytes (bundle sha256 verified: {bool(sha)})")
        manifest = extract(bundle_path, extract_dir)
        verify_per_file(manifest, extract_dir)
        print(f"Per-file hash verification: OK "
              f"({len((manifest.get('contents') or {}).get('files', []))} + "
              f"{len((manifest.get('contents') or {}).get('api', []))} files)")
        print()
        summarize(manifest, extract_dir)
    finally:
        bundle_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
