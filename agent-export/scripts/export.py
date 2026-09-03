#!/usr/bin/env python3
"""Guard for the SC Agent Migration Relay upload step.

Migration means moving INTO Starchild from another platform. Uploading a
bundle produced inside a Starchild instance is not a migration, and is what
the migration-reward abuse relied on, so the relay upload is refused there.

Building a bundle locally (backup, hand-off, archival) stays allowed
everywhere — this guard only gates the relay upload.
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
    # `--check-relay` is the documented entry point used by SKILL.md
    # (`--check-env` kept as a compatibility alias). Any other argument set is
    # rejected so the guard can never be silently skipped by a typo.
    if sys.argv[1:] not in ([], ["--check-relay"], ["--check-env"]):
        print(f"usage: {sys.argv[0]} [--check-relay]", file=sys.stderr)
        sys.exit(2)

    if is_running_inside_starchild():
        print(
            "ERROR: Refusing to upload this bundle to the migration relay.\n"
            "This is a Starchild instance, and the relay only accepts bundles from\n"
            "external agent platforms (OpenClaw, Claude Code, Cursor, etc.).\n"
            "To use your agent in another Starchild session, just log in with the same account.\n"
            "The bundle itself is already built — keep it as a local backup if you need one.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Environment verified: external agent platform, relay upload allowed.")


if __name__ == "__main__":
    main()
