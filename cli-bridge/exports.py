"""cli-bridge exports — wrapper functions for core.skill_tools.

Public surface for agents to mint / list / revoke CLI short-code bundles
without shelling out to the scripts manually. The three underlying CLI
scripts under ``scripts/`` remain the source of truth; this module just
turns their argv-style ``main()`` into kwargs-friendly callables that
return structured data.

Usage in a task script:

    from core.skill_tools import _modules
    cb = _modules["cli-bridge"]
    bundle = cb.cli_login_mint(label="my laptop")["bundle"]
    for b in cb.cli_list_bundles()["bundles"]:
        print(b["code"], b["label"])
    cb.cli_revoke_bundle("sc_xxxxxxxx")

The scripts run inside the platform process (importlib, not subprocess) so
the same ``CONTAINER_ID`` / ``CONTAINER_JWT`` / ``CHATROOM_PUBLIC_URL`` env
that the rest of the agent sees are what the skill sees.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import sys
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Module loading
# ---------------------------------------------------------------------------

_here = os.path.dirname(__file__)
_scripts_dir = os.path.join(_here, "scripts")


def _load_script(filename: str, alias: str):
    """Import a scripts/<file> under a unique module name.

    The scripts do ``import _common as C`` — a bare top-level import. When
    loaded via spec_from_file_location without a parent package, that
    import would fail. We temporarily put ``scripts/`` on ``sys.path`` so
    the bare import resolves to ``scripts/_common.py`` for the duration of
    the spec load, then restore sys.path.
    """
    path = os.path.join(_scripts_dir, filename)
    added = False
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)
        added = True
    try:
        spec = importlib.util.spec_from_file_location(alias, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        if added:
            try:
                sys.path.remove(_scripts_dir)
            except ValueError:
                pass
    return mod


_login_mod = _load_script("cli_login.py", "_cli_bridge_login")
_list_mod = _load_script("cli_list.py", "_cli_bridge_list")
_revoke_mod = _load_script("cli_revoke.py", "_cli_bridge_revoke")


# ---------------------------------------------------------------------------
# Internal: capture stdout/stderr of the script-style main() functions
# ---------------------------------------------------------------------------

class CliBridgeError(RuntimeError):
    """Raised when an underlying cli-bridge script returns non-zero."""


def _run_script(main, argv: List[str]) -> str:
    """Invoke a script's main(argv) with stdout/stderr captured.

    Returns the captured stdout. Raises CliBridgeError on non-zero exit
    so callers can ``try/except`` instead of inspecting a return code.
    """
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = main(["cli-bridge"] + argv) or 0
    if rc != 0:
        raise CliBridgeError(
            f"cli-bridge script failed (rc={rc}): {err.getvalue().strip()}"
        )
    return out.getvalue()


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

def cli_login_mint(
    label: str,
    ttl_days: int = 90,
    enable_shell: bool = False,
    enable_files: bool = False,
) -> Dict[str, Any]:
    """Mint a new CLI bundle. Returns the bundle string the user pastes
    into ``starchild login``, plus the captured stdout (which contains
    the install / pairing instructions for the user).

    ``label`` is the human reminder, e.g. ``"my laptop"`` or ``"codex-vm"``.
    ``ttl_days`` defaults to 90, max 365 (the script enforces it).
    ``enable_shell`` / ``enable_files`` mint a bundle that carries the
    matching capability for ``agent-shell`` (commands / file transfer on
    the user's machine). Both default off — a plain bundle is a chat
    bridge only.
    """
    if not label or not label.strip():
        raise ValueError("label is required and must be non-empty")
    argv = ["--label", label.strip(), "--ttl-days", str(int(ttl_days))]
    if enable_shell:
        argv.append("--enable-shell")
    if enable_files:
        argv.append("--enable-files")
    stdout = _run_script(_login_mod.main, argv)

    # Pull the bundle string out of the printed `  starchild login <bundle>`
    # line so callers can hand it to a UI without re-parsing all the prose.
    bundle = None
    for line in stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("starchild login "):
            parts = stripped.split(" ", 2)
            if len(parts) == 3:
                bundle = parts[2]
            break

    return {
        "ok": True,
        "bundle": bundle,
        "capabilities": _capabilities_from_flags(enable_shell, enable_files),
        "stdout": stdout,
    }


def cli_list_bundles(include_revoked: bool = False) -> Dict[str, Any]:
    """List CLI short codes this user has minted on sc-chatroom.

    Returns a parsed list of dicts (code / issued / expires / uses /
    label / revoked) plus the raw stdout for callers that want the
    formatted table. Empty list when the user has no bundles.
    """
    argv = ["--include-revoked"] if include_revoked else []
    stdout = _run_script(_list_mod.main, argv)
    bundles = _parse_list_table(stdout)
    return {"ok": True, "bundles": bundles, "stdout": stdout}


def cli_revoke_bundle(target: str, akm: bool = False) -> Dict[str, Any]:
    """Revoke a CLI short code (default) or the underlying AKM.

    ``target`` is an ``sc_…`` short code by default; with ``akm=True`` it
    is treated as an ``sk_…`` AKM prefix and the script will refuse if
    the matching key is not a ``chat:bridge:cli`` scope (so a fat-finger
    can't take out a chatroom room key).
    """
    if not target or not target.strip():
        raise ValueError("target is required and must be non-empty")
    argv = [target.strip()]
    if akm:
        argv.append("--akm")
    stdout = _run_script(_revoke_mod.main, argv)
    return {"ok": True, "revoked_akm": akm, "target": target.strip(),
            "stdout": stdout}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _capabilities_from_flags(enable_shell: bool, enable_files: bool) -> List[str]:
    caps = []
    if enable_shell:
        caps.append("shell")
    if enable_files:
        caps.append("files")
    return caps


def _parse_list_table(text: str) -> List[Dict[str, Any]]:
    """Best-effort parse of cli-list's fixed-width text table.

    Columns: CODE ISSUED EXPIRES USES LABEL (+ optional ``✗revoked`` tag).
    Returns [] if the shape changes — callers can always fall back to
    the ``stdout`` field.
    """
    rows: List[Dict[str, Any]] = []
    for line in text.splitlines():
        s = line.rstrip()
        if not s or s.startswith("-") or s.startswith("CODE") \
                or s.startswith("no CLI bundles"):
            continue
        parts = s.split(None, 4)
        if len(parts) < 5:
            continue
        code, issued, expires, uses, label = parts
        revoked = "✗revoked" in label
        if revoked:
            label = label.replace(" ✗revoked", "").strip()
        try:
            uses_int: Any = int(uses)
        except (TypeError, ValueError):
            uses_int = uses
        rows.append({
            "code": code,
            "issued": issued,
            "expires": expires,
            "uses": uses_int,
            "label": label,
            "revoked": revoked,
        })
    return rows
