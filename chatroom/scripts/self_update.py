#!/usr/bin/env python3
"""chatroom self-update [--check | --force]

Discover and apply skill updates published by sc-chatroom.

Each running Starchild agent has its skill bundles installed under
``/data/workspace/skills/<name>/`` (chatroom, cli-bridge, …). The
sc-chatroom server publishes the canonical version + tarball of every
bundle at ``GET /skills/index.json``. This script compares each local
``VERSION`` file to the server's index and, when they differ, downloads
the tarball, verifies its sha256, and atomically replaces the local
skill folder.

Modes:
  (default)   discover + apply for every bundled skill
  --check     report what's stale, don't change anything
  --force     re-download even if local VERSION matches remote

Failures are reported but never raise (the primary verb that called us —
``chatroom create`` / ``chatroom join`` — must still succeed even if the
self-update server is unreachable). The CLI mode exits 0 on success / no-
op, 1 if any skill failed to update.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import os
import re
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Optional

import _common as C


SKILLS_ROOT = Path(os.environ.get("SKILLS_ROOT", "/data/workspace/skills"))
_SKILL_MD_VERSION_RE = re.compile(r"^version:\s*([^\s#]+)", re.MULTILINE)


def _local_version(skill_dir: Path) -> str:
    """Read ``version:`` from the skill's SKILL.md frontmatter — the
    single source of truth shared with the server's index. Returns ""
    if the file is missing or has no version directive.
    """
    sm = skill_dir / "SKILL.md"
    if not sm.exists():
        return ""
    text = sm.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return ""
    fm_end = text.find("\n---", 3)
    block = text[:fm_end] if fm_end > 0 else text
    m = _SKILL_MD_VERSION_RE.search(block)
    if not m:
        return ""
    return m.group(1).strip().strip('"').strip("'")


def _fetch_index() -> list[dict]:
    """Pull /skills/index.json. Auth is not required for the index — it's
    public metadata about what the deployment ships."""
    r = C.chatroom_call("GET", "/skills/index.json", headers={"Authorization": ""})
    if r.status_code != 200:
        raise RuntimeError(
            f"GET /skills/index.json returned {r.status_code}: {r.text[:200]}"
        )
    body = r.json()
    items = body.get("skills") or []
    if not isinstance(items, list):
        raise RuntimeError("/skills/index.json: expected {skills: [...]}")
    return items


def _download_and_verify(skill_name: str, expect_sha256: str) -> bytes:
    # Skill bundles are public assets — strip the bearer header so we don't
    # ship the agent's JWT to a CDN cache. Always go through the internal
    # server URL (``chatroom_call`` already routes there); the absolute
    # ``url`` field in the index is for external consumers.
    path = f"/skills/{skill_name}.tar.gz"
    r = C.chatroom_call("GET", path, headers={"Authorization": ""})
    if r.status_code != 200:
        raise RuntimeError(f"GET {path} returned {r.status_code}")
    body = r.content
    digest = hashlib.sha256(body).hexdigest()
    if expect_sha256 and digest != expect_sha256:
        raise RuntimeError(
            f"sha256 mismatch on {path}: expected {expect_sha256}, got {digest}"
        )
    return body


def _atomic_swap(skill_name: str, tarball: bytes) -> None:
    """Extract ``tarball`` into a sibling temp dir, then atomically swap
    the live folder out. Layout produced by the server tar:

        <skill_name>/SKILL.md
        <skill_name>/VERSION
        <skill_name>/scripts/...

    so we extract into ``SKILLS_ROOT`` directly (it'll create
    ``<tmp>/<skill_name>/``), then rename.
    """
    SKILLS_ROOT.mkdir(parents=True, exist_ok=True)
    target = SKILLS_ROOT / skill_name

    staging = Path(tempfile.mkdtemp(prefix=f".{skill_name}.new-", dir=str(SKILLS_ROOT)))
    try:
        with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as tar:
            # Defense-in-depth: refuse anything outside ``<skill_name>/``
            for m in tar.getmembers():
                top = m.name.split("/", 1)[0]
                if top != skill_name or ".." in Path(m.name).parts:
                    raise RuntimeError(
                        f"tarball member {m.name!r} escapes {skill_name}/"
                    )
            tar.extractall(str(staging))
        new_dir = staging / skill_name
        if not new_dir.is_dir():
            raise RuntimeError(f"tarball missing top-level {skill_name}/ dir")

        backup: Optional[Path] = None
        if target.exists():
            backup = SKILLS_ROOT / f".{skill_name}.old-{os.getpid()}"
            os.rename(target, backup)
        try:
            os.rename(new_dir, target)
        except Exception:
            # Roll back if the rename failed
            if backup is not None and not target.exists():
                os.rename(backup, target)
            raise
        if backup is not None:
            shutil.rmtree(backup, ignore_errors=True)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def ensure_latest(verbose: bool = False) -> dict[str, str]:
    """Discover every skill in the server index and update any whose local
    VERSION differs from the remote VERSION.

    Returns a ``{skill_name: status}`` map where status is ``up-to-date``,
    ``updated``, ``installed`` (no local copy existed), or
    ``error: <msg>``. Designed to be called from ``create`` / ``join`` —
    callers should treat any error status as non-fatal.
    """
    out: dict[str, str] = {}
    try:
        index = _fetch_index()
    except Exception as e:
        if verbose:
            C.info(f"  ⚠  skill self-update: cannot reach index: {e!r}")
        return {"_index": f"error: {e!r}"}

    for entry in index:
        name = entry.get("name") or ""
        remote_version = entry.get("version") or ""
        sha256 = entry.get("sha256") or ""
        if not name:
            continue

        skill_dir = SKILLS_ROOT / name
        local_version = _local_version(skill_dir) if skill_dir.exists() else ""
        had_local = skill_dir.exists()

        if had_local and local_version == remote_version and remote_version:
            out[name] = "up-to-date"
            continue

        try:
            body = _download_and_verify(name, sha256)
            _atomic_swap(name, body)
            out[name] = "updated" if had_local else "installed"
            if verbose:
                C.info(f"  ✓ skill {name}: {local_version or '∅'} → "
                       f"{remote_version} ({out[name]})")
        except Exception as e:
            out[name] = f"error: {e!r}"
            if verbose:
                C.info(f"  ⚠  skill {name}: update failed: {e!r}")
    return out


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="chatroom self-update", description=__doc__)
    p.add_argument("--check", action="store_true",
                   help="report stale skills; do not download or modify")
    p.add_argument("--force", action="store_true",
                   help="re-download even if local VERSION matches remote")
    args = p.parse_args(argv[1:])
    C.require_env()

    try:
        index = _fetch_index()
    except Exception as e:
        C.die(f"could not fetch /skills/index.json: {e!r}")

    if not index:
        C.info("server has no skills published")
        return 0

    if args.check:
        any_stale = False
        for entry in index:
            name = entry.get("name") or "?"
            remote = entry.get("version") or "?"
            local = _local_version(SKILLS_ROOT / name)
            if not local:
                C.info(f"  · {name}: not installed (remote {remote})")
                any_stale = True
            elif local == remote:
                C.info(f"  · {name}: up-to-date ({local})")
            else:
                C.info(f"  · {name}: STALE (local {local} → remote {remote})")
                any_stale = True
        return 0 if not any_stale else 0  # check is informational only

    failures = 0
    for entry in index:
        name = entry.get("name") or ""
        remote_version = entry.get("version") or ""
        sha256 = entry.get("sha256") or ""
        if not name:
            continue
        skill_dir = SKILLS_ROOT / name
        local = _local_version(skill_dir) if skill_dir.exists() else ""
        had_local = skill_dir.exists()
        if not args.force and had_local and local == remote_version and remote_version:
            C.info(f"  · {name}: up-to-date ({local})")
            continue
        try:
            body = _download_and_verify(name, sha256)
            _atomic_swap(name, body)
            tag = "updated" if had_local else "installed"
            C.info(f"  ✓ {name}: {local or '∅'} → {remote_version} ({tag})")
        except Exception as e:
            C.info(f"  ⚠  {name}: {e!r}")
            failures += 1
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
