"""Shared helpers for workroom skill scripts.

Scripts are written as one-shot CLI commands; this module holds the small
amount of shared plumbing (env var resolution, HTTP calls against clawd
loopback + sc-chatroom, JSON persistence of per-room key prefixes).

The skill is named **workroom** but the underlying server is still
**sc-chatroom** — env vars, URLs, AKM scope strings, and the agent
thread_id prefix ``chatroom-{room_id}`` are wire protocol shared with
deployed agents/keys, so they're intentionally left as-is.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

import httpx

# ---------------------------------------------------------------------------
# Env
# ---------------------------------------------------------------------------

USER_ID = os.environ.get("USER_ID", "").strip()
CLAWD_BASE_URL = os.environ.get("CLAWD_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
CHATROOM_SERVER_URL = os.environ.get(
    "CHATROOM_SERVER_URL", "http://sc-chatroom.internal:8080",
).rstrip("/")
# Public URL for sc-chatroom — used when generating onboarding instructions
# (viewer links, CLI download URL) that will be shared outside the
# Fly private network. CHATROOM_SERVER_URL is the internal URL the skill
# uses for its own API calls; CHATROOM_PUBLIC_URL is what external
# consumers see.
CHATROOM_PUBLIC_URL = os.environ.get(
    "CHATROOM_PUBLIC_URL", "https://workroom.iamstarchild.com",
).rstrip("/")

# Resolve this agent's own reachable URL so sc-chatroom can call us for
# fan-out. IMPORTANT (matches starchild-telegram-client/lib/chat_service.py):
# we MUST use the PUBLIC Fly URL (https://<app>.fly.dev), NOT the
# .internal one — Fly's internal DNS resolves to IPv6 but clawd containers
# bind IPv4-only, so .internal never connects. Public URL + Fly proxy is
# the only reliable path, and sticky machine routing is done via the
# `fly-force-instance-id` HTTP header using CONTAINER_ID (= FLY_MACHINE_ID).
_agent_override = os.environ.get("AGENT_BASE_URL", "").strip()
if _agent_override:
    AGENT_BASE_URL = _agent_override.rstrip("/")
else:
    _fly_app = os.environ.get("FLY_APP_NAME", "").strip()
    AGENT_BASE_URL = f"https://{_fly_app}.fly.dev" if _fly_app else ""

# Fly-assigned machine id for this clawd container. Sent to sc-chatroom at
# join time and replayed as `fly-force-instance-id` header on every
# fan-out call so Fly's proxy routes to this specific machine even when
# the app has many machines (one per user).
CONTAINER_ID = (
    os.environ.get("CONTAINER_ID")
    or os.environ.get("FLY_MACHINE_ID")
    or ""
).strip()

WORKSPACE_DIR = Path(os.environ.get("WORKSPACE_DIR", "/data/workspace"))
WORKROOM_WORKSPACE = WORKSPACE_DIR / "workroom"
_LEGACY_WORKSPACE = WORKSPACE_DIR / "chatroom"   # pre-rename layout
KEYS_INDEX_PATH = WORKROOM_WORKSPACE / "keys.json"   # {room_id: akm_prefix}


def migrate_legacy_workspace() -> None:
    """One-shot, idempotent migration from the pre-rename layout.

    Old skill stored everything under ``/data/workspace/chatroom/`` —
    per-room dirs (``rules.md``, ``data.md``) plus the ``keys.json``
    index. After the rename to **workroom** we move each entry into
    ``/data/workspace/workroom/`` on first skill use. Anything that
    already exists in the new location wins (we never clobber).
    """
    if not _LEGACY_WORKSPACE.exists():
        return
    WORKROOM_WORKSPACE.mkdir(parents=True, exist_ok=True)
    for entry in _LEGACY_WORKSPACE.iterdir():
        target = WORKROOM_WORKSPACE / entry.name
        if target.exists():
            continue
        try:
            entry.rename(target)
        except OSError as e:
            print(
                f"warning: could not migrate {entry} → {target}: {e}",
                file=sys.stderr,
            )
    # Best-effort: drop the now-empty legacy dir so it doesn't keep
    # confusing future migration runs. Ignore if non-empty.
    try:
        _LEGACY_WORKSPACE.rmdir()
    except OSError:
        pass


# Run migration once on import — every script entry point pulls this
# module in, so this is the natural "on skill use" hook.
migrate_legacy_workspace()


def require_env():
    if not USER_ID:
        die("USER_ID env var is not set")
    if not AGENT_BASE_URL:
        die(
            "cannot determine this agent's .internal URL.\n"
            "  Either set AGENT_BASE_URL explicitly, or ensure FLY_APP_NAME "
            "is set (Fly automatically injects this on every machine — if "
            "it's missing you may be running outside Fly).\n"
            "  AGENT_BASE_URL should look like "
            "'http://<fly-app-name>.internal:8000'"
        )


def get_user_jwt() -> str:
    """Return the JWT clawd uses to identify itself to other Starchild
    internal services. This is the CONTAINER_JWT env var — injected by
    ai-agent at container creation, 10-year TTL, no refresh needed.

    Same mechanism used by services/base_client.py, services/models_client.py,
    etc. sc-chatroom's auth.py accepts it as a ``type=container`` user token.

    Fall back to USER_JWT env (explicit override, useful in dev) or a
    credential file in workspace (legacy) so scripts still work outside a
    clawd container for manual testing.
    """
    # Prefer explicit override
    override = os.environ.get("USER_JWT", "").strip()
    if override:
        return override
    # Production path: CONTAINER_JWT is what every clawd container has
    container = os.environ.get("CONTAINER_JWT", "").strip()
    if container:
        return container
    # Legacy fallback
    cred_path = WORKSPACE_DIR / ".credentials" / "user.jwt"
    if cred_path.exists():
        return cred_path.read_text().strip()
    die(
        "no identity JWT available — expected CONTAINER_JWT env (production) "
        "or USER_JWT env (dev). Checked credential file at "
        f"{cred_path} too."
    )
    return ""  # unreachable


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

def die(msg: str, code: int = 1) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def info(msg: str) -> None:
    print(msg)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

# server-minted ids are `rm_` + 6 url-safe chars; reserved rooms are
# rm_welcome / rm_feedback / rm_bugs (longer suffix). Allow any rm_-prefixed
# id of plausible length so future-format ids still pass.
_ROOM_ID_RE = re.compile(r"^rm_[A-Za-z0-9_-]{2,32}$")


def validate_room_id(value: str, *, arg_name: str = "room_id") -> str:
    """Reject obviously-bad room_id arguments (flags, blanks, wrong shape)
    before any side-effects (workspace mkdir, AKM key minting). Returns the
    stripped value on success; calls die() on failure."""
    if value is None:
        die(f"{arg_name} is required")
    v = value.strip()
    if not v:
        die(f"{arg_name} is empty")
    if v.startswith("-"):
        die(f"{arg_name} {v!r} looks like a flag — pass `--help` for usage")
    if not _ROOM_ID_RE.match(v):
        die(
            f"{arg_name} {v!r} is not a valid room id "
            "(expected `rm_` + 2-32 chars [A-Za-z0-9_-])"
        )
    return v


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def clawd_call(method: str, path: str, **kwargs) -> httpx.Response:
    """Loopback call to this agent's own clawd — no auth needed, middleware
    recognizes 127.0.0.1 and sets auth_type='internal'."""
    url = CLAWD_BASE_URL + path
    with httpx.Client(timeout=10.0) as c:
        r = c.request(method, url, **kwargs)
    return r


def workroom_call(
    method: str,
    path: str,
    *,
    user_jwt: Optional[str] = None,
    **kwargs,
) -> httpx.Response:
    """Call sc-chatroom server. Bearer is userJWT unless a kwarg overrides."""
    headers = dict(kwargs.pop("headers", {}))
    if "authorization" not in {k.lower() for k in headers}:
        jwt = user_jwt or get_user_jwt()
        headers["Authorization"] = f"Bearer {jwt}"
    url = CHATROOM_SERVER_URL + path
    with httpx.Client(timeout=30.0) as c:
        r = c.request(method, url, headers=headers, **kwargs)
    return r


def touch_key(prefix: str) -> bool:
    """Sliding-renewal: ask local clawd to extend an AKM key's lifetime
    if it's in the "near expiry" window. Idempotent and cheap; the server
    bumps ``expires_at = now + ttl`` only when the key is past 2/3 of its
    lifetime, so calling on every send is fine.

    404 means clawd doesn't yet implement /touch — we silently no-op so
    the skill keeps working against older clawd builds. Other failures
    are also swallowed: this is best-effort renewal, never fatal.

    Returns True iff clawd actually accepted the touch (200), False on
    any other status (404 / network / 4xx / 5xx).
    """
    if not prefix:
        return False
    try:
        r = clawd_call("POST", f"/api/keys/{prefix}/touch")
    except Exception:
        return False
    return r.status_code == 200


# ---------------------------------------------------------------------------
# Workspace key index
# ---------------------------------------------------------------------------

def load_key_index() -> dict[str, str]:
    if not KEYS_INDEX_PATH.exists():
        return {}
    try:
        return json.loads(KEYS_INDEX_PATH.read_text())
    except Exception as e:
        print(f"warning: could not parse {KEYS_INDEX_PATH}: {e}", file=sys.stderr)
        return {}


def save_key_index(idx: dict[str, str]) -> None:
    WORKROOM_WORKSPACE.mkdir(parents=True, exist_ok=True)
    KEYS_INDEX_PATH.write_text(json.dumps(idx, indent=2, sort_keys=True) + "\n")


def set_key(room_id: str, prefix: str) -> None:
    idx = load_key_index()
    idx[room_id] = prefix
    save_key_index(idx)


def pop_key(room_id: str) -> Optional[str]:
    idx = load_key_index()
    prefix = idx.pop(room_id, None)
    save_key_index(idx)
    return prefix


def get_key(room_id: str) -> Optional[str]:
    return load_key_index().get(room_id)


# ---------------------------------------------------------------------------
# Workspace files (rules.md)
# ---------------------------------------------------------------------------
#
# ``data.md`` was a per-agent local file in older skill versions (≤ 0.3.x).
# It was created here as a TODO template and meant for the room owner to
# edit by hand. In practice owners never SSH'd into agent containers to
# fill it, so every workroom shipped forever with placeholder content and
# agents stayed maximally conservative about referencing anything beyond
# raw chat. Workroom Awareness Plan §C moved the field to room-level
# state at ``GET /rooms/{id}/data``, editable from the viewer. This
# helper now only manages ``rules.md`` (still per-agent local notes —
# server-side ``room_rules`` lives at ``/rooms/{id}/rules`` and ships
# in the fan-out payload).

def room_workspace_dir(room_id: str) -> Path:
    return WORKROOM_WORKSPACE / room_id


def ensure_room_workspace(room_id: str) -> Path:
    d = room_workspace_dir(room_id)
    d.mkdir(parents=True, exist_ok=True)
    rules = d / "rules.md"
    if not rules.exists():
        rules.write_text(_rules_template(room_id))
    # NOTE: we deliberately do NOT create ``data.md`` anymore. Pre-0.4
    # agents that already have one on disk keep it; the agent runtime
    # (clawd) now reads room-level reference scope from the fan-out
    # payload's ``room_data`` block, not from this file.
    return d


def _rules_template(room_id: str) -> str:
    return (
        f"# Workroom Rules for {room_id}\n\n"
        "## Voice\n"
        "- Short, direct.\n\n"
        "## Reply policy\n"
        "- Always reply when @-mentioned.\n"
        "- Otherwise default to `[SILENT]`.\n\n"
        "## Don'ts\n"
        "- Do not reference facts outside the room's reference scope "
        "(see `workroom data <room_id>`, owner-curated).\n"
    )


# ---------------------------------------------------------------------------
# Invite code decoding (server-signed, we only peek at claims here)
# ---------------------------------------------------------------------------

def peek_invite(code: str) -> dict[str, Any]:
    """Decode the payload without verification. We cannot verify — we don't
    have the server's HMAC secret — so this is just convenience to surface
    the room_id for UX before calling /rooms/<id>/join. The real validation
    happens server-side."""
    import base64
    parts = code.split(".")
    if len(parts) != 3:
        die("invite_code is not a valid JWT (expected 3 parts)")
    payload_b64 = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception as e:
        die(f"failed to decode invite_code payload: {e}")
    for k in ("room_id", "created_by", "jti"):
        if k not in payload:
            die(f"invite_code missing required claim: {k}")
    return payload
