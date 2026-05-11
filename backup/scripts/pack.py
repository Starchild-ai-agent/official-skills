#!/usr/bin/env python3
"""Deterministically assemble a backup bundle from a live Starchild agent.

Usage:
    python3 pack.py \\
        --api-dir   $WORK/api/ \\
        --out       $WORK/bundle.tar.gz \\
        [--mode default|full] \\
        [--extra-exclude <rel-path>] [--extra-path <abs-path>] \\
        [--label "升级前"] [--dry-run]

The "what to pack" model is a blacklist, not a whitelist:

  --mode default   walk /data/, pack everything EXCEPT logs, caches, derived
                   indexes (ChromaDB), transient runtime state, and this skill's
                   own scratch/markers. This is what you want 99% of the time.

  --mode full      walk /data/, pack literally everything. Only skip paths
                   that would create a self-reference loop (our own in-progress
                   bundle scratch, our own restore extract dirs).

Both modes always skip `__pycache__/` and `*.pyc` inside any copied directory.

Path arguments:
  --extra-exclude REL    additional path to skip, interpreted relative to
                         /data/ (e.g. "workspace/output" or "sessions").
                         Repeat for multiple.
  --extra-path ABS       extra absolute path to include, outside /data/
                         (e.g. some user-owned dir on another mount).

`--api-dir` must contain agent-supplied JSON written before pack.py runs:
    api-dir/profile.json            agent_profile(action="get") output
    api-dir/settings.json           user_settings(action="get") output
    api-dir/scheduled_tasks.json    scheduled_task(action="list"), normalized to
                                    [{title, schedule, description, channels}]

Convention: the agent allocates a per-run workdir (e.g. `mktemp -d
/tmp/backup-XXXXXX`), creates `$WORK/api/`, writes the three JSONs there, then
calls `pack.py --api-dir $WORK/api --out $WORK/bundle.tar.gz`. After upload
succeeds it `rm -rf $WORK`. Each backup attempt stays isolated.

With --dry-run, nothing is written; a plan (JSON) is printed to stdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tarfile
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Blacklists — the authoritative "what to skip" spec. Adding defaults here
# is the right place (keep in sync with SKILL.md's "what's excluded" table).
# ---------------------------------------------------------------------------

# Top-level children of /data/workspace/ we skip in DEFAULT mode.
# In FULL mode we keep ALL of these except the SELF_LOOP ones below.
DEFAULT_SKIP_WORKSPACE_TOP: set[str] = {
    ".active-upload.json",   # client upload-resume state; transient
    ".restore.log",          # restore progress marker; see SKILL.md Step 0
}

# Top-level children of /data/ we skip in DEFAULT mode.
# In FULL mode we keep ALL of these.
DEFAULT_SKIP_DATA_TOP: set[str] = {
    # Logs
    "logs",
    "auto_update.log",
    "skills-install.log",

    # Transient runtime state (resets on restart anyway)
    ".bash_processes",
    ".startup-tasks",
    "hibernation_state.json",

    # Derived / cache / reconstructable
    "memory",            # ChromaDB + FTS indexes; rebuilds from workspace/memory/**
    ".npm-cache",        # npm cache
    ".agents",           # npx skills lock-file shadow; real registry is in workspace/skills/.skill-lock.json
}

# ALWAYS skipped (even in FULL mode) — avoids packaging the backup of itself.
ALWAYS_SKIP_WORKSPACE_TOP: set[str] = {
    ".backup",           # our own pack scratch (where this run lives while running)
    ".restore",          # our own restore extract dirs (per-backup_id subdirs)
}

# Files / dir names to prune INSIDE any copied directory at any depth.
# We exclude these in both default and full mode — they're universally noise.
UNIVERSAL_PRUNE: set[str] = {
    "__pycache__",
}
UNIVERSAL_PRUNE_SUFFIXES: tuple[str, ...] = (".pyc",)

# API JSONs the agent must supply.
REQUIRED_API_FILES: list[str] = [
    "profile.json",
    "settings.json",
    "scheduled_tasks.json",
]


# ---------------------------------------------------------------------------
# Plan construction
# ---------------------------------------------------------------------------

def _copy_ignore(src: str, names: list[str]) -> list[str]:
    """shutil.copytree ignore fn: prune __pycache__ and *.pyc at every depth."""
    skip: list[str] = []
    for n in names:
        if n in UNIVERSAL_PRUNE:
            skip.append(n)
            continue
        if any(n.endswith(suf) for suf in UNIVERSAL_PRUNE_SUFFIXES):
            skip.append(n)
    return skip


def _path_summary(p: Path) -> tuple[bool, int, int]:
    """Return (exists, size_bytes, file_count) with __pycache__/*.pyc ignored."""
    if not p.exists():
        return False, 0, 0
    if p.is_file():
        return True, p.stat().st_size, 1
    total = 0
    count = 0
    for sub in p.rglob("*"):
        if not sub.is_file():
            continue
        # Skip pruned dirs/files in the summary to match what we'll actually pack.
        if UNIVERSAL_PRUNE.intersection(sub.parts):
            continue
        if any(sub.name.endswith(suf) for suf in UNIVERSAL_PRUNE_SUFFIXES):
            continue
        try:
            total += sub.stat().st_size
            count += 1
        except OSError:
            continue
    return True, total, count


def build_plan(
    workspace_dir: Path,
    data_dir: Path,
    api_dir: Path,
    mode: str,
    extra_excludes: set[str],
    extra_paths: list[Path],
    label: str,
) -> dict[str, Any]:
    """Produce a structured plan describing what will be packed.

    Exclusions are resolved in this order (highest priority first):
      1. ALWAYS_SKIP_WORKSPACE_TOP (self-loop guard — can't be overridden)
      2. --extra-exclude user-supplied list (any path under /data/)
      3. DEFAULT_SKIP_* lists (only applied when mode == 'default')
    """
    if mode not in ("default", "full"):
        raise ValueError(f"mode must be 'default' or 'full', got {mode!r}")

    plan: dict[str, Any] = {
        "label": label,
        "mode": mode,
        "workspace_dir": str(workspace_dir),
        "data_dir": str(data_dir),
        "created_at_unix": int(time.time()),
        "items": [],
        "api": [],
        "extra_paths": [],
        "warnings": [],
        "total_files": 0,
        "total_size_bytes": 0,
    }

    # Normalize extra-excludes to paths-relative-to-/data/.
    # "sessions" → /data/sessions, "workspace/output" → /data/workspace/output
    extra_excl_set: set[str] = set()
    for e in extra_excludes:
        e = e.strip().lstrip("/")
        if e:
            extra_excl_set.add(e)

    def _include(src: Path, bundle_rel: str, rel_key: str, kind: str,
                 section: str) -> None:
        exists, size, count = _path_summary(src)
        status = "ok" if exists else "absent"
        plan["items"].append({
            "section": section,
            "kind": kind,
            "src": str(src),
            "bundle": bundle_rel,
            "rel": rel_key,
            "status": status,
            "size_bytes": size,
            "files": count,
        })
        if exists:
            plan["total_files"] += count
            plan["total_size_bytes"] += size

    def _skip(src: Path, bundle_rel: str, rel_key: str, kind: str,
              section: str, reason: str) -> None:
        plan["items"].append({
            "section": section,
            "kind": kind,
            "src": str(src),
            "bundle": bundle_rel,
            "rel": rel_key,
            "status": f"excluded_{reason}",
            "size_bytes": 0,
            "files": 0,
        })

    # ---------- /data/workspace/* ----------
    if workspace_dir.exists():
        for child in sorted(workspace_dir.iterdir()):
            name = child.name
            rel_key = f"workspace/{name}"
            bundle_rel = f"files/workspace/{name}"
            kind = "workspace_dir" if child.is_dir() else "workspace_file"

            # 1. Always-skip (self-loop guard) — cannot be overridden even in full mode.
            if name in ALWAYS_SKIP_WORKSPACE_TOP:
                _skip(child, bundle_rel, rel_key, kind, "workspace", "self_loop")
                continue

            # 2. User override
            if rel_key in extra_excl_set:
                _skip(child, bundle_rel, rel_key, kind, "workspace", "user_rule")
                continue

            # 3. Default-mode skips
            if mode == "default" and name in DEFAULT_SKIP_WORKSPACE_TOP:
                _skip(child, bundle_rel, rel_key, kind, "workspace", "default_rule")
                continue

            _include(child, bundle_rel, rel_key, kind, "workspace")
    else:
        plan["warnings"].append(f"workspace_dir does not exist: {workspace_dir}")

    # ---------- /data/* (everything NOT under workspace/) ----------
    if data_dir.exists():
        for child in sorted(data_dir.iterdir()):
            name = child.name
            if name == "workspace":
                continue  # handled above
            rel_key = name
            bundle_rel = f"files/data/{name}"
            kind = "data_dir" if child.is_dir() else "data_file"

            # 1. User override
            if rel_key in extra_excl_set:
                _skip(child, bundle_rel, rel_key, kind, "data", "user_rule")
                continue

            # 2. Default-mode skips
            if mode == "default" and name in DEFAULT_SKIP_DATA_TOP:
                _skip(child, bundle_rel, rel_key, kind, "data", "default_rule")
                continue

            _include(child, bundle_rel, rel_key, kind, "data")
    else:
        plan["warnings"].append(f"data_dir does not exist: {data_dir}")

    # ---------- Extra user-specified paths (outside /data/) ----------
    for p in extra_paths:
        if not p.is_absolute():
            plan["warnings"].append(f"--extra-path must be absolute: {p}")
            continue
        if p.is_relative_to(workspace_dir):
            bundle_rel = f"files/workspace/{p.relative_to(workspace_dir)}"
        elif p.is_relative_to(data_dir):
            bundle_rel = f"files/data/{p.relative_to(data_dir)}"
        else:
            bundle_rel = f"files/extra/{p.name}"
        exists, size, count = _path_summary(p)
        kind = "workspace_dir" if p.is_dir() else "workspace_file"
        plan["extra_paths"].append({
            "src": str(p),
            "bundle": bundle_rel,
            "status": "ok" if exists else "missing",
            "size_bytes": size,
            "files": count,
        })
        if exists:
            plan["total_files"] += count
            plan["total_size_bytes"] += size

    # ---------- API files ----------
    for name in REQUIRED_API_FILES:
        p = api_dir / name
        if p.exists() and p.is_file():
            plan["api"].append({
                "file": name,
                "status": "ok",
                "size_bytes": p.stat().st_size,
            })
            plan["total_files"] += 1
            plan["total_size_bytes"] += p.stat().st_size
        else:
            plan["api"].append({"file": name, "status": "missing", "size_bytes": 0})
            plan["warnings"].append(
                f"required api file missing: {p} — agent must write this "
                "before pack.py runs"
            )

    return plan


# ---------------------------------------------------------------------------
# Plan execution (actual tar build)
# ---------------------------------------------------------------------------

def execute_plan(plan: dict[str, Any], api_dir: Path, out_path: Path) -> dict[str, Any]:
    """Copy everything the plan says 'ok' into a staging dir, write manifest
    (with per-file sha256), tar.gz to out_path, cleanup.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    staging = out_path.parent / f".{out_path.name}.staging.{os.getpid()}"
    if staging.exists():
        shutil.rmtree(staging)
    root = staging / "backup"
    root.mkdir(parents=True)

    def _copy_into_bundle(src: Path, bundle_rel: str) -> None:
        if not src.exists():
            return
        dst = root / bundle_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_file():
            shutil.copy2(src, dst)
        else:
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(
                src, dst,
                symlinks=False,
                ignore_dangling_symlinks=True,
                ignore=_copy_ignore,
            )

    for item in plan["items"]:
        if item["status"] != "ok":
            continue
        _copy_into_bundle(Path(item["src"]), item["bundle"])
    for extra in plan["extra_paths"]:
        if extra["status"] != "ok":
            continue
        _copy_into_bundle(Path(extra["src"]), extra["bundle"])

    # API dir
    api_bundle_dir = root / "api"
    api_bundle_dir.mkdir(parents=True, exist_ok=True)
    for entry in plan["api"]:
        if entry["status"] != "ok":
            continue
        shutil.copy2(api_dir / entry["file"], api_bundle_dir / entry["file"])

    # Per-file sha256 inventory.
    contents_files: list[dict[str, Any]] = []
    contents_api: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel == "manifest.json":
            continue
        entry = {
            "path": rel,
            "size": path.stat().st_size,
            "sha256": _sha256_file(path),
        }
        if rel.startswith("api/"):
            contents_api.append(entry)
        else:
            contents_files.append(entry)

    manifest = {
        "version": "1.1",
        "source": "starchild",
        "mode": plan["mode"],
        "created_at_unix": plan["created_at_unix"],
        "created_at": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(plan["created_at_unix"])
        ),
        "label": plan["label"],
        "sections": sorted({
            item["bundle"].split("/")[0] + "/" + item["bundle"].split("/")[1]
            for item in plan["items"]
            if item["status"] == "ok" and "/" in item["bundle"]
        }),
        "contents": {
            "files": contents_files,
            "api": contents_api,
        },
        "exclusions": [
            {"section": item["section"], "rel": item["rel"], "reason": item["status"]}
            for item in plan["items"]
            if item["status"].startswith("excluded_")
        ],
        "plan_summary": {
            "total_files": plan["total_files"],
            "total_size_bytes": plan["total_size_bytes"],
            "warnings": plan["warnings"],
        },
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if out_path.exists():
        out_path.unlink()
    with tarfile.open(out_path, "w:gz") as tar:
        tar.add(root, arcname=".")

    shutil.rmtree(staging)

    return {
        "bundle_path": str(out_path),
        "size_bytes": out_path.stat().st_size,
        "manifest": manifest,
    }


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _default_out_path() -> Path:
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return Path(f"/tmp/backup-{ts}-{os.getpid()}/bundle.tar.gz")


def main() -> None:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
    )
    parser.add_argument("--workspace-dir", type=Path,
                        default=Path(os.environ.get("WORKSPACE_DIR", "/data/workspace")))
    parser.add_argument("--data-dir", type=Path, default=Path("/data"))
    parser.add_argument("--api-dir", type=Path, required=True,
                        help="directory where the agent wrote profile.json, "
                             "settings.json, scheduled_tasks.json")
    parser.add_argument("--out", type=Path, default=None,
                        help="output bundle path (default: /tmp/backup-{ts}-{pid}/bundle.tar.gz)")
    parser.add_argument("--mode", choices=("default", "full"), default="default",
                        help="default (skip logs/caches/derived/scratch) or "
                             "full (pack everything except self-reference loops)")
    parser.add_argument("--label", type=str, default="",
                        help="user-facing label (≤64 chars)")
    parser.add_argument("--extra-exclude", action="append", default=[],
                        help="extra path to skip, relative to /data/ "
                             "(e.g. 'workspace/output' or 'sessions'). "
                             "Repeat for multiple.")
    parser.add_argument("--extra-path", action="append", default=[],
                        help="absolute path to an extra dir/file to include "
                             "(outside /data/); repeat for multiple.")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan as JSON to stdout; don't build a bundle")
    args = parser.parse_args()

    if args.out is None:
        args.out = _default_out_path()

    # ── Early validation: fail loud and specific on the common pitfalls ──
    # Agents sometimes split the flow across multiple bash tool calls; shell
    # vars like $WORK don't persist between calls, so --api-dir can expand
    # to something nonsensical. Detect this before building any plan.
    if not args.api_dir.exists():
        print(
            f"ERROR: --api-dir does not exist: {args.api_dir}\n\n"
            "This usually means one of:\n"
            "  (1) You passed a shell variable like $WORK that wasn't set in "
            "this bash invocation — bash variables do NOT persist across "
            "separate tool calls. Use a literal path string.\n"
            "  (2) You forgot to create the directory and write the three "
            "API JSONs (profile.json, settings.json, scheduled_tasks.json) "
            "before invoking pack.py.\n"
            "\n"
            "Fix: pick a literal timestamped path, create it, write the "
            "JSONs, then pass that exact string to --api-dir. Example:\n"
            "  WORK=/tmp/backup-20260427T164500Z\n"
            "  mkdir -p $WORK/api\n"
            "  # (write the 3 JSONs to $WORK/api/ via your native file tools)\n"
            "  python3 skills/backup/scripts/pack.py \\\n"
            f"      --api-dir {args.api_dir} \\\n"
            "      --out $WORK/bundle.tar.gz \\\n"
            "      ...",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.api_dir.is_dir():
        print(
            f"ERROR: --api-dir exists but is not a directory: {args.api_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Out path: ensure parent is writable. We don't require --out to exist
    # (pack.py creates it), but we DO need the parent directory to be
    # writable — catching this early saves the agent from a confusing
    # traceback halfway through plan building.
    out_parent = args.out.parent
    try:
        out_parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(
            f"ERROR: cannot create --out parent directory {out_parent}: {e}",
            file=sys.stderr,
        )
        sys.exit(1)
    if not os.access(out_parent, os.W_OK):
        print(
            f"ERROR: --out parent is not writable: {out_parent}",
            file=sys.stderr,
        )
        sys.exit(1)

    extra_paths = [Path(p) for p in args.extra_path]
    extra_excludes = set(args.extra_exclude)

    plan = build_plan(
        workspace_dir=args.workspace_dir.resolve(),
        data_dir=args.data_dir.resolve(),
        api_dir=args.api_dir.resolve(),
        mode=args.mode,
        extra_excludes=extra_excludes,
        extra_paths=extra_paths,
        label=args.label,
    )

    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    missing_api = [a["file"] for a in plan["api"] if a["status"] != "ok"]
    if missing_api:
        print(
            "ERROR: required API files not found in --api-dir: "
            f"{', '.join(missing_api)}.\nAgent must call profile / settings / "
            "scheduled_tasks tools and write the results there before pack.py.",
            file=sys.stderr,
        )
        sys.exit(1)

    result = execute_plan(plan, args.api_dir.resolve(), args.out.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
