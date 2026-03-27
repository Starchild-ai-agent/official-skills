#!/usr/bin/env python3
"""Broadcast ERC20 approve tx for 1inch router (script mode)."""

from __future__ import annotations

import argparse

from _oneinch_lib import (
    approve_tx,
    build_symbol_index,
    compact_token,
    fetch_tokens,
    print_json,
    resolve_chain_id,
    resolve_token,
    wallet_broadcast,
)


def main() -> None:
    p = argparse.ArgumentParser(description="Approve token for 1inch router")
    p.add_argument("--chain", required=True)
    p.add_argument("--token", required=True, help="Token symbol/address")
    p.add_argument("--amount", default="", help="Optional approval amount in wei; empty = unlimited")
    args = p.parse_args()

    chain_id = resolve_chain_id(args.chain)
    token_map = fetch_tokens(chain_id)
    idx = build_symbol_index(token_map)
    t = resolve_token(args.token, token_map, idx)

    tx = approve_tx(chain_id, t["address"], amount=args.amount or None)
    resp = wallet_broadcast(chain_id=chain_id, to=tx["to"], data=tx["data"], value=str(tx.get("value", "0")))

    out = {
        "ok": True,
        "action": "approve",
        "chain": args.chain,
        "chain_id": chain_id,
        "token": compact_token(t),
        "tx_request": {
            "to": tx.get("to"),
            "value": str(tx.get("value", "0")),
        },
        "wallet_response": resp,
    }
    print_json(out)


if __name__ == "__main__":
    main()
