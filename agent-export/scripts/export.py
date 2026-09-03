#!/usr/bin/env python3
"""Export agent migration bundle and upload to SC Agent Migration Relay.

Security safeguard:
Prevents "self-migration" abuse where an attacker runs this export script
inside a Starchild instance to falsely trigger migration rewards.
"""

import os
import sys
from pathlib import Path


def is_running_inside_starchild() -> bool:
    """Detect if the current environment is a Starchild agent container.

    Checks:
    1. STARCHILD_* environment variables
    2. Starchild-specific workspace directory (/data/workspace)
    3. Hosts / Fly app environment pointing to starchild
    """
    for key in os.environ:
        if key.startswith("STARCHILD_") or key in ("SC_CALLER_ID", "SC_GATEWAY_URL"):
            return True

    # Starchild container standard layout
    if Path("/data/workspace").is_dir() and Path("/data/.starchild").is_dir():
        return True

    # Container hostname or Fly app
    fly_app = os.environ.get("FLY_APP_NAME", "").lower()
    if "starchild" in fly_app or "sc-agent" in fly_app:
        return True

    return False


def main():
    if is_running_inside_starchild():
        print(
            "ERROR: Migration export cannot be executed inside a Starchild instance.\n"
            "This tool is designed to export from external agent platforms (OpenClaw, Claude Code, Cursor, etc.).\n"
            "To transfer or use your agent across Starchild sessions, simply log in with the same account.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Environment verified: External agent platform detected.")


if __name__ == "__main__":
    main()
