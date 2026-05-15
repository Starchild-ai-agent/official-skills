#!/usr/bin/env python3
"""workroom rules <room_id>

Prints the path to this room's rules.md — intended to be piped into
`$EDITOR` or simply shown to the user so they can edit the file.
"""
from __future__ import annotations

import argparse
import sys

import _common as C


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="workroom rules", description=__doc__)
    p.add_argument("room_id")
    args = p.parse_args(argv[1:])
    room_id = C.validate_room_id(args.room_id)
    d = C.ensure_room_workspace(room_id)
    path = d / "rules.md"
    C.info(str(path))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
