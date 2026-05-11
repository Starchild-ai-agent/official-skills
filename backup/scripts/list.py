#!/usr/bin/env python3
"""List this user's backups via GET /backups on sc-agent-backup.

Usage:
    python3 list.py [--json]

By default prints a human-readable menu intended for an agent to surface to
the user as the pick list. With --json, prints the raw storage JSON for
programmatic consumption.

Environment:
    CONTAINER_JWT     Required.
    BACKUP_STORAGE_URL  Optional. Defaults to http://sc-agent-backup.internal:8080.

Exit codes:
    0   request succeeded. Prints the menu (or "（无备份）" if the user has
        no backups yet). The agent reads stdout to decide whether to ask
        "pick one" or "run /backup first".
    1   network / auth / protocol failure (error on stderr)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_STORAGE = "http://sc-agent-backup.internal:8080"


def _storage_url() -> str:
    return os.environ.get("BACKUP_STORAGE_URL", DEFAULT_STORAGE).rstrip("/")


def _jwt() -> str:
    token = os.environ.get("CONTAINER_JWT", "").strip()
    if not token:
        print("ERROR: CONTAINER_JWT env var is not set.", file=sys.stderr)
        sys.exit(1)
    return token


def _fetch() -> dict:
    req = urllib.request.Request(
        f"{_storage_url()}/backups",
        headers={"Authorization": f"Bearer {_jwt()}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        print(f"ERROR: HTTP {e.code} — {detail}", file=sys.stderr)
        sys.exit(1)
    except (urllib.error.URLError, OSError) as e:
        print(
            "ERROR: cannot reach backup storage over Fly internal network. "
            "This script must run inside a Fly machine.",
            file=sys.stderr,
        )
        print(f"DETAIL: {e}", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        print(f"ERROR: storage returned non-JSON: {body[:200]}", file=sys.stderr)
        sys.exit(1)


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _relative_age(ts: int) -> str:
    now = int(time.time())
    d = max(0, now - ts)
    if d < 60:
        return f"{d} 秒前"
    if d < 3600:
        return f"{d // 60} 分钟前"
    if d < 86400:
        return f"{d // 3600} 小时前"
    if d < 30 * 86400:
        return f"{d // 86400} 天前"
    return f"{d // (30 * 86400)} 个月前"


def _format_menu(data: dict) -> str:
    backups = data.get("backups", [])
    quota = data.get("quota", "?")
    if not backups:
        return "（无备份）"

    lines = [f"您的备份（{len(backups)} / {quota}，按时间倒序）："]
    for i, b in enumerate(backups, 1):
        label = b.get("user_label") or "（无标签）"
        ts = b.get("created_at", 0)
        when = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(ts)) if ts else "?"
        age = _relative_age(ts) if ts else "?"
        size = _human_size(int(b.get("size_bytes", 0)))
        sections = b.get("sections") or []
        bid = b.get("backup_id", "?")

        lines.append("")
        lines.append(f"[{i}] {bid}")
        lines.append(f"    标签: {label}")
        lines.append(f"    时间: {when}  ({age})")
        lines.append(f"    大小: {size}")
        if sections:
            lines.append(f"    内容: {', '.join(sections)}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true",
                        help="emit raw storage JSON instead of a menu")
    args = parser.parse_args()

    data = _fetch()

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(_format_menu(data))

    # Empty isn't an error — exit 0 and let the agent read stdout to decide
    # what to say. Non-zero is reserved for genuine failures (network/auth).


if __name__ == "__main__":
    main()
