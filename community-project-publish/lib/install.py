"""Type-specific install handlers."""
from __future__ import annotations
import json
import os
from typing import Any


def install_task(project_dir: str, manifest: dict[str, Any]) -> dict[str, Any]:
    schedule = manifest.get("schedule") or "0 * * * *"
    entry_rel = manifest.get("entry") or "src/run.py"
    entry_abs = os.path.join(project_dir, entry_rel)
    return {
        "next_step": (
            f"Task installed (paused). To activate as a scheduled job:\n"
            f"  scheduled_task(action='register', "
            f"title={json.dumps(manifest.get('description', 'Forked task'))}, "
            f"schedule={json.dumps(schedule)}, "
            f"description='Forked from community projects')\n"
            f"Then edit the generated run.py to invoke entry: {entry_abs}\n"
            f"Or activate directly if a job is already registered."
        ),
        "entry_abs": entry_abs,
        "schedule": schedule,
        "type": "task",
    }


def install_preview(project_dir: str, manifest: dict[str, Any]) -> dict[str, Any]:
    port = manifest.get("port")
    entry = manifest.get("entry") or "src/index.html"
    is_static = entry.endswith(".html")
    if is_static:
        return {
            "next_step": (
                f"Preview ready. Use:\n"
                f"  preview(action='serve', "
                f"title={json.dumps(manifest.get('description', 'Preview'))}, "
                f"dir={json.dumps(project_dir + '/' + os.path.dirname(entry))})"
            ),
            "type": "preview", "port": port, "is_static": True,
        }
    runtime = manifest.get("runtime") or {}
    cmd = (
        f"python {entry}" if runtime.get("python")
        else f"node {entry}" if runtime.get("node")
        else f"./{entry}"
    )
    return {
        "next_step": (
            f"Preview ready. Use:\n"
            f"  preview(action='serve', "
            f"title={json.dumps(manifest.get('description', 'Preview'))}, "
            f"dir={json.dumps(project_dir)}, command={json.dumps(cmd)}, port={port})"
        ),
        "type": "preview", "port": port, "command": cmd, "is_static": False,
    }


def install_service(project_dir: str, manifest: dict[str, Any]) -> dict[str, Any]:
    entry_rel = manifest.get("entry") or "src/server.py"
    entry_abs = os.path.join(project_dir, entry_rel)
    runtime = manifest.get("runtime") or {}
    cmd = (
        f"python {entry_abs}" if runtime.get("python")
        else f"node {entry_abs}" if runtime.get("node")
        else entry_abs
    )
    port = manifest.get("port")
    return {
        "next_step": (
            f"Service ready. To start in background:\n"
            f"  bash(command={json.dumps(cmd)}, background=True)\n"
            + (f"It will listen on port {port}.\n" if port else "")
            + "Track via bash_process(action='list')."
        ),
        "type": "service", "command": cmd, "port": port,
    }


def install_script(project_dir: str, manifest: dict[str, Any]) -> dict[str, Any]:
    entry_rel = manifest.get("entry") or "src/main.py"
    entry_abs = os.path.join(project_dir, entry_rel)
    runtime = manifest.get("runtime") or {}
    cmd = (
        f"python {entry_abs}" if runtime.get("python")
        else f"node {entry_abs}" if runtime.get("node")
        else entry_abs
    )
    return {
        "next_step": f"Script ready. Run with:\n  bash(command={json.dumps(cmd)})",
        "type": "script", "command": cmd,
    }


INSTALLERS = {"task": install_task, "preview": install_preview, "service": install_service, "script": install_script}


def install(project_dir: str, manifest: dict[str, Any]) -> dict[str, Any]:
    fn = INSTALLERS.get(manifest.get("type"))
    if not fn:
        return {"next_step": f"Unknown type: {manifest.get('type')}", "type": manifest.get("type")}
    return fn(project_dir, manifest)


def diff_env_required(manifest: dict[str, Any]) -> list[str]:
    """env names declared in manifest.env_required not present in workspace/.env."""
    env_required = manifest.get("env_required") or []
    if not isinstance(env_required, list):
        return []

    have: set[str] = set(os.environ.keys())
    for path in ("/data/workspace/.env",):
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key = line.split("=", 1)[0].strip()
                    if key:
                        have.add(key)

    return [e for e in env_required if e not in have]
