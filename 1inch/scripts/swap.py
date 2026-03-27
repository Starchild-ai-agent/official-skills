#!/usr/bin/env python3
"""Execute 1inch swap in script mode: optional auto-approve + swap tx broadcast."""

from __future__ import annotations

import argparse

from _oneinch_lib import (
    NATIVE_TOKEN,
    approve_tx,
    build_symbol_index,
    check_allowance,
    compact_token,
    fetch_tokens,
    from_wei,
    get_evm_wallet_address,
    print_json,
    quote,
    resolve_chain_id,
    resolve_token,
    swap_tx,
    to_wei,
    wallet_broadcast,
)


def main() -> None:
    p = argparse.ArgumentParser(description="1inch swap")
    p.add_argument("--chain", required=True)
    p.add_argument("--from", dest="src", required=True, help="Source token symbol/address")
    p.add_argument("--to", dest="dst", required=True, help="Destination token symbol/address")
    p.add_argument("--amount", required=True, help="Human amount in source token units")
    p.add_argument("--slippage", type=float, default=1.0, help="Slippage percent, default 1.0")
    p.add_argument("--auto-approve", action="store_true", help="If set, auto-send approve tx when allowance is insufficient")
    args = p.parse_args()

    chain_id = resolve_chain_id(args.chain)
    wallet = get_evm_wallet_address()

    token_map = fetch_tokens(chain_id)
    idx = build_symbol_index(token_map)
    src = resolve_token(args.src, token_map, idx)
    dst = resolve_token(args.dst, token_map, idx)

    src_dec = int(src.get("decimals", 18))
    dst_dec = int(dst.get("decimals", 18))
    amount_wei = to_wei(args.amount, src_dec)

    # Pre-quote for visibility
    q = quote(chain_id, src["address"], dst["address"], amount_wei)

    approval_result = None
    if src["address"].lower() != NATIVE_TOKEN.lower():
        allowance = check_allowance(chain_id, src["address"], wallet)
        if allowance < int(amount_wei):
            if not args.auto_approve:
                raise RuntimeError(
                    "insufficient allowance; re-run with --auto-approve or execute approve.py first"
                )
            a_tx = approve_tx(chain_id, src["address"], amount=None)
            a_resp = wallet_broadcast(
                chain_id=chain_id,
                to=a_tx["to"],
                data=a_tx["data"],
                value=str(a_tx.get("value", "0")),
            )
            approval_result = {
                "approve_tx_request": {
                    "to": a_tx.get("to"),
                    "value": str(a_tx.get("value", "0")),
                },
                "wallet_response": a_resp,
            }

    s = swap_tx(chain_id, src["address"], dst["address"], amount_wei, wallet, args.slippage)
    tx = s.get("tx") or {}
    if not tx:
        raise RuntimeError("1inch /swap returned no tx object")

    swap_resp = wallet_broadcast(
        chain_id=chain_id,
        to=tx["to"],
        data=tx["data"],
        value=str(tx.get("value", "0")),
    )

    out = {
        "ok": True,
        "action": "swap",
        "chain": args.chain,
        "chain_id": chain_id,
        "wallet": wallet,
        "src": compact_token(src),
        "dst": compact_token(dst),
        "amount_in_human": args.amount,
        "amount_in_wei": amount_wei,
        "quote": {
            "estimated_out_wei": q.get("dstAmount"),
            "estimated_out_human": from_wei(str(q.get("dstAmount", "0")), dst_dec),
            "gas": q.get("gas"),
        },
        "approval": approval_result,
        "swap_tx_request": {
            "to": tx.get("to"),
            "value": str(tx.get("value", "0")),
            "dstAmount": s.get("dstAmount"),
        },
        "wallet_response": swap_resp,
    }
    print_json(out)


if __name__ == "__main__":
    main()
