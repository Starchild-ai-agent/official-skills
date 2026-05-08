#!/usr/bin/env python3
"""Restore file-based components of an extracted backup to their original paths.

The backup bundle holds three kinds of state:

  1. File-based state under `files/workspace/**` — memory, prompt, config,
     tasks scripts, setup.sh, .env, opt-in dirs the user picked. This script
     handles those: copies to `/data/workspace/**` with overwrite detection.

  2. File-based state under `files/data/**` — scheduler registry,
     preview state. This script copies those to `/data/**`.

  3. API-managed state under `api/*.json` — agent_profile, user_settings,
     scheduled_tasks. These live in ai-agent's database, not on the container
     fs. They are applied by the `backup` SKILL's Flow B using Starchild
     native tools (memory, agent_profile, user_settings, scheduled_task).
     This script deliberately does NOT touch those; see SKILL.md.

Usage:
    python3 restore.py [--apply] [--force] [--extract-dir PATH]
                       [--workspace-dir PATH] [--data-dir PATH]

By default the script prints what WOULD happen and exits 0 without writing
anything (dry-run). Pass --apply to actually copy files. Overwrites of
non-identical files are refused unless --force is set.

Path mapping (bundle → live):
    extract/files/workspace/<rel>  →  {WORKSPACE}/<rel>
    extract/files/data/<rel>       →  {DATA}/<rel>
    extract/api/*                  →  (ignored here; agent applies via tools)
    extract/files/extra/<name>/**  →  not restored automatically (user must
                                      copy manually — original path is unknown)
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

WORKSPACE = Path(os.environ.get("WORKSPACE_DIR", "/data/workspace"))
DATA = Path(os.environ.get("DATA_DIR", "/data"))


def _digest(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_against_manifest(extract_dir: Path) -> None:
    """Pre-apply integrity check: re-hash every file listed in manifest.contents
    and compare against the recorded sha256. Mismatch anywhere → exit 1.

    This is defense-in-depth vs download.py's post-extract verification.
    Time may pass between download and apply (user deliberating, multi-turn
    confirmations), during which someone could edit the extract dir. We
    re-check right before we write anything to live workspace/data.
    """
    manifest_path = extract_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: no manifest.json at {manifest_path}. Was this dir "
              "produced by the `backup` skill?", file=sys.stderr)
        sys.exit(1)

    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        print(f"ERROR: manifest.json is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    contents = manifest.get("contents")
    if not isinstance(contents, dict):
        # Pre-v1.1 bundle — whole-bundle hash was already checked at download.
        # Print a notice and continue.
        print("WARN: bundle is pre-v1.1 (no manifest.contents). Skipping "
              "per-file verification. Whole-bundle sha256 was checked at "
              "download time.", file=sys.stderr)
        return

    expected: dict[str, dict] = {}
    for entry in (contents.get("files") or []) + (contents.get("api") or []):
        expected[entry["path"]] = entry

    bad: list[str] = []
    missing: list[str] = []
    for path, entry in expected.items():
        p = extract_dir / path
        if not p.exists():
            missing.append(path)
            continue
        if p.stat().st_size != entry.get("size"):
            bad.append(f"{path}  (size: "
                       f"got {p.stat().st_size}, expected {entry.get('size')})")
            continue
        digest = _digest(p)
        if digest != entry.get("sha256"):
            bad.append(f"{path}  (sha256: "
                       f"got {digest[:16]}…, expected "
                       f"{entry.get('sha256', '')[:16]}…)")

    if bad or missing:
        print("ERROR: pre-apply integrity check FAILED.", file=sys.stderr)
        if bad:
            print(f"  corrupted files ({len(bad)}):", file=sys.stderr)
            for b in bad[:20]:
                print(f"    {b}", file=sys.stderr)
            if len(bad) > 20:
                print(f"    ... ({len(bad) - 20} more)", file=sys.stderr)
        if missing:
            print(f"  manifest-listed files missing on disk ({len(missing)}):",
                  file=sys.stderr)
            for m in missing[:20]:
                print(f"    {m}", file=sys.stderr)
            if len(missing) > 20:
                print(f"    ... ({len(missing) - 20} more)", file=sys.stderr)
        print(
            "\nThe extracted bundle was modified between download and apply. "
            "Aborting — do NOT let the agent overwrite workspace/data with "
            "potentially-corrupted content. Re-download the backup (delete "
            f"{extract_dir} first) and try again. If the fresh download "
            "ALSO fails verification, the bundle on storage is corrupt; "
            "pick another backup.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Passed — emit a quiet note.
    print(f"Pre-apply integrity check: OK ({len(expected)} files verified)",
          file=sys.stderr)


def _print_diff(old: Path, new: Path) -> None:
    try:
        a = old.read_text(errors="replace").splitlines()
        b = new.read_text(errors="replace").splitlines()
    except Exception:
        print(f"    (binary diff; {old.stat().st_size} → {new.stat().st_size} bytes)")
        return
    diff = list(difflib.unified_diff(a, b, fromfile=str(old), tofile=str(new), n=2))
    if not diff:
        print("    (no textual diff)")
        return
    for line in diff[:40]:
        print(f"    {line.rstrip()}")
    if len(diff) > 40:
        print(f"    ... ({len(diff) - 40} more lines)")


def _collect_file_targets(extract_dir: Path, workspace: Path, data: Path
                          ) -> list[tuple[Path, Path, str]]:
    """Return [(source_in_bundle, destination_on_disk, origin_kind), ...].

    origin_kind is "workspace" or "data" — purely for the summary print.
    `files/extra/` is intentionally skipped: by the time we're here, we don't
    know where the user originally pulled those from.
    """
    out: list[tuple[Path, Path, str]] = []

    ws_root = extract_dir / "files" / "workspace"
    if ws_root.exists() and ws_root.is_dir():
        for src in ws_root.rglob("*"):
            if src.is_file():
                rel = src.relative_to(ws_root)
                out.append((src, workspace / rel, "workspace"))

    data_root = extract_dir / "files" / "data"
    if data_root.exists() and data_root.is_dir():
        for src in data_root.rglob("*"):
            if src.is_file():
                rel = src.relative_to(data_root)
                out.append((src, data / rel, "data"))

    return out


def _classify(src: Path, dst: Path) -> str:
    """Return one of: new, unchanged, modified."""
    if not dst.exists():
        return "new"
    try:
        if _digest(src) == _digest(dst):
            return "unchanged"
    except Exception:
        pass
    return "modified"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="actually write files (default: dry-run)")
    parser.add_argument("--force", action="store_true",
                        help="allow overwrite of existing, non-identical files")
    parser.add_argument("--backup-id", type=str, default=None,
                        help="the backup_id to restore; uses "
                             "/data/workspace/.restore/{backup_id}/ as the "
                             "extract dir. Mutually exclusive with --extract-dir.")
    parser.add_argument("--extract-dir", type=Path, default=None,
                        help="explicit path to the extracted bundle (override). "
                             "Defaults derive from --backup-id.")
    parser.add_argument("--workspace-dir", type=Path, default=WORKSPACE,
                        help="live workspace to restore into (default: /data/workspace)")
    parser.add_argument("--data-dir", type=Path, default=DATA,
                        help="live /data/ root to restore into")
    parser.add_argument("--skip-verify", action="store_true",
                        help="skip the pre-apply per-file sha256 check "
                             "(NOT recommended — only for debugging)")
    args = parser.parse_args()

    # Resolve the extract dir.
    if args.extract_dir is None:
        if args.backup_id is None:
            print("ERROR: supply either --backup-id or --extract-dir",
                  file=sys.stderr)
            sys.exit(1)
        args.extract_dir = WORKSPACE / ".restore" / args.backup_id

    if not args.extract_dir.exists():
        print(f"ERROR: extract dir does not exist: {args.extract_dir}",
              file=sys.stderr)
        print("Run `download.py <backup_id>` first.", file=sys.stderr)
        sys.exit(1)

    # ── Pre-apply defense-in-depth: rehash every file against manifest ──
    # download.py already did this right after extract, but time may have
    # passed between download and apply (user took a while to approve, or
    # interactive flow involves multiple turns). Re-verify so we don't
    # apply state that got clobbered in-between.
    if not args.skip_verify:
        _verify_against_manifest(args.extract_dir)

    pairs = _collect_file_targets(
        args.extract_dir, args.workspace_dir, args.data_dir
    )

    # Detect bundles from older skill versions (pre-layout-change).
    legacy_soul = args.extract_dir / "identity" / "soul.md"
    legacy_files = args.extract_dir / "files"
    if not pairs and (legacy_soul.exists() or (legacy_files.exists()
                      and not (legacy_files / "workspace").exists())):
        print("ERROR: this bundle uses the pre-v1 layout (no files/workspace/"
              " or files/data/ split).", file=sys.stderr)
        print("Upgrade to the current `backup` skill and re-take a backup, or"
              " manually map the old paths.", file=sys.stderr)
        sys.exit(1)

    if not pairs:
        print("No file-based components in this bundle (no files/workspace/, no files/data/).")
        print("Apply memory/identity/tasks/settings via Starchild APIs per SKILL.md.")
        return

    bucket: dict[str, list[tuple[Path, Path, str]]] = {
        "new": [], "unchanged": [], "modified": []
    }
    for src, dst, origin in pairs:
        bucket[_classify(src, dst)].append((src, dst, origin))

    # ---------------- summary ----------------
    print(f"Restore plan (workspace={args.workspace_dir}, data={args.data_dir})")
    print(f"  new       : {len(bucket['new'])} file(s)")
    print(f"  unchanged : {len(bucket['unchanged'])} file(s) (will skip)")
    print(f"  modified  : {len(bucket['modified'])} file(s) (will overwrite with --force)")
    print()

    if bucket["new"]:
        print("NEW:")
        for src, dst, origin in bucket["new"]:
            print(f"  + [{origin}] {dst}  ({src.stat().st_size} B)")
        print()

    if bucket["modified"]:
        print("MODIFIED (existing content differs):")
        for src, dst, origin in bucket["modified"]:
            print(f"  ~ [{origin}] {dst}")
            _print_diff(dst, src)
        print()

    if not args.apply:
        print("Dry-run only. Re-run with --apply to write, and --force if you")
        print("want to overwrite modified files.")
        return

    # ---------------- apply ----------------
    wrote = 0
    skipped_modified = 0
    errors = 0

    for src, dst, _origin in bucket["new"]:
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            wrote += 1
        except Exception as e:
            print(f"ERROR: could not write {dst}: {e}", file=sys.stderr)
            errors += 1

    for src, dst, _origin in bucket["modified"]:
        if not args.force:
            skipped_modified += 1
            continue
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            wrote += 1
        except Exception as e:
            print(f"ERROR: could not overwrite {dst}: {e}", file=sys.stderr)
            errors += 1

    print(f"Applied: wrote={wrote} skipped_modified={skipped_modified} errors={errors}")
    if skipped_modified:
        print("Re-run with --force to overwrite modified files.")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
