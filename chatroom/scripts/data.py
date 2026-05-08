#!/usr/bin/env python3
"""chatroom data <room_id>

Prints the path to this room's data.md.
"""
from __future__ import annotations

import argparse
import sys

import _common as C


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="chatroom data", description=__doc__)
    p.add_argument("room_id")
    args = p.parse_args(argv[1:])
    room_id = C.validate_room_id(args.room_id)
    d = C.ensure_room_workspace(room_id)
    path = d / "data.md"
    C.info(str(path))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
