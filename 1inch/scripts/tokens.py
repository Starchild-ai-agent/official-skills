#!/usr/bin/env python3
"""Search/list 1inch tokens on a chain (script mode)."""

from __future__ import annotations

import argparse

from _oneinch_lib import fetch_tokens, print_json, resolve_chain_id


def main() -> None:
    p = argparse.ArgumentParser(description="List/search 1inch tokens")
    p.add_argument("--chain", required=True)
    p.add_argument("--search", default="", help="Symbol/name contains")
    p.add_argument("--limit", type=int, default=20)
    args = p.parse_args()

    chain_id = resolve_chain_id(args.chain)
    token_map = fetch_tokens(chain_id)
    rows = list(token_map.values())

    if args.search:
        q = args.search.lower()
        rows = [
            t for t in rows
            if q in str(t.get("symbol", "")).lower() or q in str(t.get("name", "")).lower()
        ]

    out = {
        "ok": True,
        "action": "tokens",
        "chain": args.chain,
        "chain_id": chain_id,
        "count": min(len(rows), args.limit),
        "tokens": [
            {
                "address": t.get("address"),
                "symbol": t.get("symbol"),
                "name": t.get("name"),
                "decimals": t.get("decimals"),
            }
            for t in rows[: args.limit]
        ],
    }
    print_json(out)


if __name__ == "__main__":
    main()
