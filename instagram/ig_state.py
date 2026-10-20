"""Local, non-secret state: the 30-hashtag-per-7-days ledger.

Meta enforces this server-side, but a local ledger avoids burning the quota on
duplicate probes and lets us return a precise reset time before the API says
"quota exceeded".
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

from ig_errors import QuotaExceeded

HASHTAG_WINDOW_SECONDS = 7 * 24 * 60 * 60
HASHTAG_LIMIT = 30


def state_dir() -> Path:
    path = Path(
        os.environ.get(
            "INSTAGRAM_STATE_DIR",
            str(Path.home() / ".starchild" / "instagram"),
        )
    )
    path.mkdir(parents=True, exist_ok=True)
    try:
        path.chmod(0o700)
    except OSError:
        pass
    return path


def _ledger_path() -> Path:
    return state_dir() / "hashtag_usage.json"


def _read() -> Dict[str, Any]:
    path = _ledger_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _write(data: Dict[str, Any]) -> None:
    path = _ledger_path()
    fd, tmp = tempfile.mkstemp(prefix="hashtag-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _prune(entries: List[Dict[str, Any]], now: float) -> List[Dict[str, Any]]:
    return [e for e in entries if now - float(e.get("ts", 0)) < HASHTAG_WINDOW_SECONDS]


def check_hashtag(account: str, tag: str) -> None:
    """Raise QuotaExceeded when querying ``tag`` would exceed Meta's limit."""
    now = time.time()
    ledger = _read()
    entries = _prune(ledger.get(account, []), now)
    normalized = tag.strip().lower().lstrip("#")
    if any(e.get("tag") == normalized for e in entries):
        return
    unique = {e.get("tag") for e in entries}
    if len(unique) >= HASHTAG_LIMIT:
        oldest = min(entries, key=lambda e: float(e.get("ts", now)))
        reset_at = int(float(oldest.get("ts", now)) + HASHTAG_WINDOW_SECONDS)
        raise QuotaExceeded(
            f"Hashtag search quota exhausted for account {account!r}: "
            f"{HASHTAG_LIMIT} unique hashtags per rolling 7 days.",
            hint="Wait for the oldest hashtag to age out, or use a different account.",
            details={"limit": HASHTAG_LIMIT, "reset_at_epoch": reset_at, "used": sorted(unique)},
        )


def record_hashtag(account: str, tag: str) -> None:
    now = time.time()
    ledger = _read()
    entries = _prune(ledger.get(account, []), now)
    normalized = tag.strip().lower().lstrip("#")
    if not any(e.get("tag") == normalized for e in entries):
        entries.append({"tag": normalized, "ts": now})
    ledger[account] = entries
    _write(ledger)


def usage(account: str) -> Dict[str, Any]:
    now = time.time()
    entries = _prune(_read().get(account, []), now)
    return {
        "used": len({e.get("tag") for e in entries}),
        "limit": HASHTAG_LIMIT,
        "window_seconds": HASHTAG_WINDOW_SECONDS,
        "hashtags": sorted(
            (
                {
                    "tag": e.get("tag"),
                    "expires_at_epoch": int(float(e.get("ts", now)) + HASHTAG_WINDOW_SECONDS),
                }
                for e in entries
            ),
            key=lambda item: item["expires_at_epoch"],
        ),
    }
