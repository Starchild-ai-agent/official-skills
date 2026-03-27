#!/usr/bin/env python3
"""Check ERC20 allowance for 1inch router (script mode)."""

from __future__ import annotations

import argparse

from _oneinch_lib import (
    NATIVE_TOKEN,
    build_symbol_index,
    check_allowance,
    compact_token,
    fetch_tokens,
    get_evm_wallet_address,
    print_json,
    resolve_chain_id,
    resolve_token,
)


def main() -> None:
    p = argparse.ArgumentParser(description="Check allowance for 1inch")
    p.add_argument("--chain", required=True)
    p.add_argument("--token", required=True, help="Token symbol/address to check")
    p.add_argument("--required", default="0", help="Optional required amount in wei for needs_approval check")
    args = p.parse_args()

    chain_id = resolve_chain_id(args.chain)
    wallet = get_evm_wallet_address()

    token_map = fetch_tokens(chain_id)
    idx = build_symbol_index(token_map)
    t = resolve_token(args.token, token_map, idx)

    allowance = check_allowance(chain_id, t["address"], wallet)
    required = int(args.required)

    out = {
        "ok": True,
        "action": "check_allowance",
        "chain": args.chain,
        "chain_id": chain_id,
        "wallet": wallet,
        "token": compact_token(t),
        "allowance": str(allowance),
        "needs_approval": (allowance < required) if required > 0 else (allowance == 0 and t["address"].lower() != NATIVE_TOKEN.lower()),
    }
    print_json(out)


if __name__ == "__main__":
    main()
