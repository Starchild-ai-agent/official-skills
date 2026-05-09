"""Cloudflare API helpers — shared by verify.py / setup.py / teardown.py.

Uses the user's CLOUDFLARE_API_TOKEN from workspace/.env. All calls go direct
to api.cloudflare.com (Cloudflare's own endpoint, not via sc-proxy — this is
the user's own credential, not a platform-billed API).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import urllib.request
import urllib.error

WORKSPACE = Path("/data/workspace")
STATE_PATH = WORKSPACE / ".cf_state.json"
ENV_PATH = WORKSPACE / ".env"
API_BASE = "https://api.cloudflare.com/client/v4"


def _load_env() -> None:
    """Load workspace/.env into os.environ (very small parser)."""
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def get_token() -> str:
    _load_env()
    tok = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not tok:
        print("ERROR: CLOUDFLARE_API_TOKEN not set in workspace/.env", file=sys.stderr)
        sys.exit(2)
    return tok


def cf_request(method: str, path: str, body: dict | None = None) -> dict[str, Any]:
    """Call Cloudflare API. Returns parsed JSON. Raises on HTTP error."""
    token = get_token()
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        print(f"HTTP {e.code} on {method} {path}\n{body_text}", file=sys.stderr)
        raise


def load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {}


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2))


def update_state(**kwargs) -> dict[str, Any]:
    s = load_state()
    s.update(kwargs)
    save_state(s)
    return s
