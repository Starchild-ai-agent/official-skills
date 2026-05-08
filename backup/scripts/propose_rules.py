#!/usr/bin/env python3
"""Scan /data/workspace/ and /data/ top-level entries, classify each, and
emit a JSON proposal for the agent to discuss with the user.

Runs on the FIRST backup (when /data/workspace/config/backup_rules.md is
absent). The agent uses the output to show the user what's actually on disk,
discuss the ambiguous items, and compose the final rules file based on their
decisions.

Output JSON shape:
    {
      "workspace": [
        {"name": ..., "path": ..., "is_dir": ..., "size_bytes": ...,
         "file_count": ..., "category": ..., "reason": ...},
        ...
      ],
      "data": [ ... same shape, path under /data/ ... ],
      "summary": {"total_size_bytes": ..., "core_count": N, "skip_count": N,
                  "ask_count": N, "unknown_count": N}
    }

Categories:
    core     — definitely back up (core user state; stock default includes)
    skip     — definitely skip (logs/cache/derived/runtime; stock default
               already excludes; shown for transparency)
    ask      — default includes, user might want to skip (large or optional)
    unknown  — path not on any list; user decides

Exit codes:
    0   ok, JSON on stdout
    1   workspace or data dir missing / unreadable
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Classification sets — keep in sync with pack.py's DEFAULT_SKIP/ALWAYS_SKIP.
# The "reason" strings are what the agent surfaces to the user.
# ---------------------------------------------------------------------------

# Always-backup under workspace/
CORE_WORKSPACE: dict[str, str] = {
    "memory": "agent memory (MEMORY.md + daily/ + topics/)",
    "prompt": "agent identity (SOUL.md + USER.md + optionally AGENTS.md)",
    "config": "per-agent config (agent.yaml / custom_models.yaml / backup_rules.md itself)",
    "tasks": "scheduled task scripts",
    "skills": "installed skills (including .skill-lock.json manifest)",
    "setup.sh": "startup hook (apt/pip install steps)",
    ".env": "secrets (API keys, tokens, bot credentials)",
}

# Always-skip under workspace/ — stock default blacklist + self-loop guards
SKIP_WORKSPACE: dict[str, str] = {
    ".backup": "pack scratch — self-loop guard",
    ".restore": "restore extract — self-loop guard",
    ".active-upload.json": "upload resume state — transient",
    ".restore.log": "restore progress marker — transient",
}

# Always-backup directly under /data/
CORE_DATA: dict[str, str] = {
    "scheduled_jobs.json": "scheduler registry (task definitions)",
    "preview_history.json": "permanent preview service history",
    "previews.json": "active preview registry",
    "sessions": "chat history SQLite family (state.db + -wal + -shm)",
}

# Always-skip directly under /data/ — stock default blacklist
SKIP_DATA: dict[str, str] = {
    "logs": "logs, regenerated",
    "memory": "ChromaDB + FTS + embedding cache (derivable from workspace/memory/**)",
    ".npm-cache": "npm cache",
    ".bash_processes": "process registry — resets on container restart",
    ".startup-tasks": "startup transient status",
    "hibernation_state.json": "container runtime state",
    "auto_update.log": "logs",
    "skills-install.log": "logs",
    "workspace": "sub-tree handled separately",  # placeholder; not actually skipped
}

# Default backs up, but user often wants to decide — "ask" category
ASK_WORKSPACE: dict[str, str] = {
    "output": "agent-generated reports (could be large or sensitive)",
    "scripts": "user-authored custom scripts",
}

ASK_DATA: dict[str, str] = {
    "scheduled_jobs.db": "job execution history (definitions live in scheduled_jobs.json; this is the run log)",
    "tasks.json": "subagent spawn history",
    ".user-packages": "pip/npm --user installs; often large; THEORETICALLY rebuildable via setup.sh",
    ".local": "typically user-installed binaries + app data; varies by agent",
    ".agents": "npx skills shadow lock-file (real registry is workspace/skills/.skill-lock.json)",
}


def _size_and_count(p: Path) -> tuple[int, int]:
    """Return (size_bytes, file_count) for a path (file or dir, recursive).

    Skips __pycache__ and *.pyc to match what pack.py will actually pack.
    """
    if p.is_file():
        try:
            return p.stat().st_size, 1
        except OSError:
            return 0, 0
    total = 0
    count = 0
    for sub in p.rglob("*"):
        if not sub.is_file():
            continue
        if "__pycache__" in sub.parts or sub.name.endswith(".pyc"):
            continue
        try:
            total += sub.stat().st_size
            count += 1
        except OSError:
            continue
    return total, count


def classify_child(name: str, is_dir: bool, base: str) -> tuple[str, str]:
    """Return (category, reason) for a top-level child under workspace or data.

    base is "workspace" or "data".
    """
    if base == "workspace":
        if name in CORE_WORKSPACE:
            return "core", CORE_WORKSPACE[name]
        if name in SKIP_WORKSPACE:
            return "skip", SKIP_WORKSPACE[name]
        if name in ASK_WORKSPACE:
            return "ask", ASK_WORKSPACE[name]
    else:  # data
        if name == "workspace":
            return "core", "the workspace directory (enumerated separately above)"
        if name in CORE_DATA:
            return "core", CORE_DATA[name]
        if name in SKIP_DATA:
            return "skip", SKIP_DATA[name]
        if name in ASK_DATA:
            return "ask", ASK_DATA[name]

    # Unrecognized — punt to user.
    kind = "directory" if is_dir else "file"
    return "unknown", f"unrecognized {kind} under {base}/; user must decide"


def _scan_children(base_dir: Path, label: str) -> list[dict]:
    entries: list[dict] = []
    for child in sorted(base_dir.iterdir()):
        # Under /data/, skip 'workspace' — emitted as its own section.
        if label == "data" and child.name == "workspace":
            continue
        size, count = _size_and_count(child)
        cat, reason = classify_child(child.name, child.is_dir(), label)
        entries.append({
            "name": child.name,
            "path": str(child),
            "is_dir": child.is_dir(),
            "size_bytes": size,
            "file_count": count,
            "category": cat,
            "reason": reason,
        })
    return entries


def propose(workspace_dir: Path, data_dir: Path) -> dict:
    if not workspace_dir.exists():
        print(f"ERROR: workspace dir does not exist: {workspace_dir}",
              file=sys.stderr)
        sys.exit(1)
    if not data_dir.exists():
        print(f"ERROR: data dir does not exist: {data_dir}",
              file=sys.stderr)
        sys.exit(1)

    ws = _scan_children(workspace_dir, "workspace")
    dt = _scan_children(data_dir, "data")

    counts = {"core": 0, "skip": 0, "ask": 0, "unknown": 0}
    total = 0
    for e in ws + dt:
        counts[e["category"]] += 1
        total += e["size_bytes"]

    return {
        "workspace": ws,
        "data": dt,
        "summary": {
            "total_size_bytes": total,
            "core_count": counts["core"],
            "skip_count": counts["skip"],
            "ask_count": counts["ask"],
            "unknown_count": counts["unknown"],
        },
    }


def main() -> None:
    workspace = Path(os.environ.get("WORKSPACE_DIR", "/data/workspace"))
    data = Path(os.environ.get("DATA_DIR", "/data"))
    print(json.dumps(propose(workspace, data), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
