#!/usr/bin/env python3
"""Get a 1inch quote (script mode)."""

from __future__ import annotations

import argparse

from _oneinch_lib import (
    build_symbol_index,
    compact_token,
    fetch_tokens,
    from_wei,
    print_json,
    quote,
    resolve_chain_id,
    resolve_token,
    to_wei,
)


def main() -> None:
    p = argparse.ArgumentParser(description="1inch quote")
    p.add_argument("--chain", required=True, help="ethereum|arbitrum|base|optimism|polygon|bsc|avalanche|gnosis")
    p.add_argument("--from", dest="src", required=True, help="Source token symbol/address, e.g. USDC")
    p.add_argument("--to", dest="dst", required=True, help="Destination token symbol/address, e.g. POL")
    p.add_argument("--amount", required=True, help="Human amount in source token units, e.g. 1")
    args = p.parse_args()

    chain_id = resolve_chain_id(args.chain)
    token_map = fetch_tokens(chain_id)
    idx = build_symbol_index(token_map)

    src = resolve_token(args.src, token_map, idx)
    dst = resolve_token(args.dst, token_map, idx)

    src_dec = int(src.get("decimals", 18))
    dst_dec = int(dst.get("decimals", 18))

    amount_wei = to_wei(args.amount, src_dec)
    q = quote(chain_id, src["address"], dst["address"], amount_wei)

    out = {
        "ok": True,
        "action": "quote",
        "chain": args.chain,
        "chain_id": chain_id,
        "src": compact_token(src),
        "dst": compact_token(dst),
        "amount_in_human": args.amount,
        "amount_in_wei": amount_wei,
        "estimated_out_wei": q.get("dstAmount"),
        "estimated_out_human": from_wei(str(q.get("dstAmount", "0")), dst_dec),
        "gas": q.get("gas"),
        "protocols": q.get("protocols"),
    }
    print_json(out)


if __name__ == "__main__":
    main()
