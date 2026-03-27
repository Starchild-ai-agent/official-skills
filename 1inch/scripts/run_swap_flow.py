#!/usr/bin/env python3
"""One-command 1inch swap flow: quote -> optional approve -> swap -> address-aware balance verification."""

from __future__ import annotations

import argparse
import re
import time
from decimal import Decimal
from typing import Any, Dict, List
from urllib.parse import quote_plus

import requests

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
    wallet_request,
)


_REQUEST_ID_RE = re.compile(r"requestId\s*:\s*([A-Za-z0-9-]+)", re.IGNORECASE)


def _extract_request_id(error_text: str) -> str:
    m = _REQUEST_ID_RE.search(error_text or "")
    return m.group(1) if m else ""


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _normalize_symbol(symbol: str) -> str:
    s = (symbol or "").upper().strip()
    if "_" in s:
        s = s.split("_", 1)[0]
    return s


def _asset_candidates(chain: str, token: Dict[str, Any]) -> List[str]:
    """Build wallet-service asset enum candidates for this token.

    Wallet service currently expects enums like usdc/usdc.e/eth/pol/usdt/eurc.
    We generate best-effort candidates and query until we can match by address/symbol.
    """
    chain_lc = chain.lower().strip()
    symbol = _normalize_symbol(str(token.get("symbol") or ""))
    addr = str(token.get("address") or "")

    native_by_chain = {
        "polygon": "pol",
        "ethereum": "eth",
        "arbitrum": "eth",
        "base": "eth",
        "optimism": "eth",
        "linea": "eth",
    }

    symbol_map = {
        "USDC": "usdc",
        "USDC.E": "usdc.e",
        "USDT": "usdt",
        "EURC": "eurc",
        "ETH": "eth",
        "WETH": "eth",
        "POL": "pol",
        "WMATIC": "pol",
        "MATIC": "pol",
        "NATIVE": native_by_chain.get(chain_lc, "eth"),
    }

    candidates: List[str] = []

    # 1) token symbol direct mapping
    mapped = symbol_map.get(symbol)
    if mapped:
        candidates.append(mapped)

    # 2) native token explicit mapping
    if addr.lower() == NATIVE_TOKEN.lower():
        candidates.append(native_by_chain.get(chain_lc, "eth"))

    # 3) broad fallbacks by chain (wallet often returns multiple tokens per query)
    if chain_lc == "polygon":
        candidates.extend(["usdc", "usdc.e", "pol", "usdt", "eurc"])
    else:
        candidates.extend([native_by_chain.get(chain_lc, "eth"), "usdc", "usdt", "eurc"])

    # dedupe while preserving order
    out: List[str] = []
    seen = set()
    for c in candidates:
        if not c:
            continue
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _row_matches_token(row: Dict[str, Any], token: Dict[str, Any], chain: str) -> bool:
    addr = str(token.get("address") or "").lower()
    want_symbol = _normalize_symbol(str(token.get("symbol") or ""))

    # Balance row can be in old schema (id/symbol) or new schema (asset)
    row_id = str(row.get("id") or row.get("address") or row.get("contract_address") or "").lower()
    row_symbol = _normalize_symbol(str(row.get("symbol") or ""))
    row_asset = str(row.get("asset") or "").lower().strip()

    # ERC20: prefer exact address match when available
    if addr and addr != NATIVE_TOKEN.lower() and addr.startswith("0x"):
        if row_id == addr:
            return True

    chain_lc = chain.lower().strip()

    # Native token matching (e.g., polygon native asset="pol")
    if addr == NATIVE_TOKEN.lower():
        if row_symbol and row_symbol == want_symbol:
            return True
        if chain_lc == "polygon" and (row_id in {"matic", "pol"} or row_asset == "pol"):
            return True
        if chain_lc != "polygon" and (row_id in {"eth", "ethereum"} or row_asset == "eth"):
            return True

    # For new wallet schema, accept canonical asset enum alignment
    symbol_to_asset = {
        "USDC": "usdc",
        "USDC.E": "usdc.e",
        "USDT": "usdt",
        "EURC": "eurc",
        "ETH": "eth",
        "WETH": "eth",
        "POL": "pol",
        "MATIC": "pol",
        "WMATIC": "pol",
        "NATIVE": "pol" if chain_lc == "polygon" else "eth",
    }
    mapped = symbol_to_asset.get(want_symbol)
    if mapped and row_asset == mapped:
        return True

    # fallback: normalized symbol match
    if want_symbol and row_symbol == want_symbol:
        return True

    return False


def _extract_amount_str(row: Dict[str, Any]) -> str:
    """Extract human-readable amount from heterogeneous wallet balance schemas."""
    # Legacy style fields
    val = row.get("amount")
    if val is None:
        val = row.get("balance_formatted")
    if val is None:
        val = row.get("balance")
    if val is not None:
        return str(val)

    # Current wallet-service schema: raw_value + raw_value_decimals
    raw_value = row.get("raw_value")
    raw_decimals = row.get("raw_value_decimals")
    if raw_value is not None and raw_decimals is not None:
        try:
            q = Decimal(str(raw_value)) / (Decimal(10) ** int(raw_decimals))
            return format(q, "f")
        except Exception:
            pass

    # Fallback: display_values map (prefer non-usd key)
    dv = row.get("display_values")
    if isinstance(dv, dict) and dv:
        for k, v in dv.items():
            if str(k).lower() != "usd":
                return str(v)
        # only usd present
        first_v = next(iter(dv.values()))
        return str(first_v)

    return "0"


def _row_identity(row: Dict[str, Any]) -> str:
    """Stable identity for a wallet balance row, to avoid before/after drift."""
    rid = str(row.get("id") or row.get("address") or row.get("contract_address") or "").strip().lower()
    if rid:
        return f"id:{rid}"
    asset = str(row.get("asset") or "").strip().lower()
    if asset:
        return f"asset:{asset}"
    sym = _normalize_symbol(str(row.get("symbol") or ""))
    if sym:
        return f"sym:{sym}"
    return ""


def _rpc_token_balance(chain: str, wallet: str, token: Dict[str, Any]) -> Dict[str, Any]:
    """Direct on-chain balance read fallback (ERC20 + native) for robust verification."""
    chain_to_rpc = {
        "ethereum": "https://ethereum-rpc.publicnode.com",
        "polygon": "https://polygon-bor-rpc.publicnode.com",
        "arbitrum": "https://arbitrum-one-rpc.publicnode.com",
        "base": "https://base-rpc.publicnode.com",
        "optimism": "https://optimism-rpc.publicnode.com",
        "linea": "https://linea-rpc.publicnode.com",
    }

    chain_lc = chain.lower().strip()
    rpc = chain_to_rpc.get(chain_lc)
    if not rpc:
        return {"ok": False, "error": f"unsupported chain for rpc fallback: {chain}"}

    addr = str(token.get("address") or "").lower()
    decimals = int(token.get("decimals", 18))

    try:
        if addr == NATIVE_TOKEN.lower():
            payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_getBalance", "params": [wallet, "latest"]}
            r = requests.post(rpc, json=payload, timeout=15)
            r.raise_for_status()
            data = r.json()
            if data.get("error"):
                return {"ok": False, "error": str(data.get("error"))}
            raw_hex = str(data.get("result") or "0x0")
            raw_int = int(raw_hex, 16)
            return {
                "ok": True,
                "amount": str(Decimal(raw_int) / (Decimal(10) ** decimals)),
                "raw_int": str(raw_int),
                "matched_by": "rpc_native",
                "row_identity": f"rpc:{chain_lc}:native",
                "rpc": rpc,
            }

        # ERC20 balanceOf
        method_selector = "70a08231"  # balanceOf(address)
        wallet_data = wallet.lower().replace("0x", "").rjust(64, "0")
        call_data = "0x" + method_selector + wallet_data
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_call",
            "params": [{"to": addr, "data": call_data}, "latest"],
        }
        r = requests.post(rpc, json=payload, timeout=15)
        r.raise_for_status()
        data = r.json()
        if data.get("error"):
            return {"ok": False, "error": str(data.get("error"))}
        raw_hex = str(data.get("result") or "0x0")
        raw_int = int(raw_hex, 16)
        return {
            "ok": True,
            "amount": str(Decimal(raw_int) / (Decimal(10) ** decimals)),
            "raw_int": str(raw_int),
            "matched_by": "rpc_erc20",
            "row_identity": f"rpc:{chain_lc}:{addr}",
            "rpc": rpc,
        }
    except Exception as e:
        return {"ok": False, "error": repr(e)}


def _fetch_token_balance(
    chain: str,
    token: Dict[str, Any],
    wallet: str,
    preferred_asset: str = "",
    preferred_row_identity: str = "",
) -> Dict[str, Any]:
    """Fetch token balance with stable selection.

    Strategy:
    1) Try wallet-service asset scans (fast, aligned with wallet tooling)
    2) If no reliable match or row is zero-like, fallback to direct RPC read
    """
    last_error = ""
    candidates = _asset_candidates(chain, token)
    if preferred_asset:
        candidates = [preferred_asset] + [c for c in candidates if c != preferred_asset]

    for asset in candidates:
        try:
            qs = f"?chain_type=ethereum&chain={quote_plus(chain)}&asset={quote_plus(asset)}"
            data = wallet_request("GET", f"/agent/balance{qs}")
            rows: List[Dict[str, Any]] = data.get("balances", []) if isinstance(data, dict) else []

            # 1) Strongest: same row identity as before snapshot
            if preferred_row_identity:
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    if _row_identity(row) == preferred_row_identity:
                        amt = _extract_amount_str(row)
                        if _to_dec(amt) != Decimal("0"):
                            return {
                                "asset_query": asset,
                                "amount": amt,
                                "raw": row,
                                "matched_by": "preferred_row_identity",
                                "row_identity": _row_identity(row),
                                "token": compact_token(token),
                            }

            # 2) Normal matching (address/native/symbol mapping)
            for row in rows:
                if isinstance(row, dict) and _row_matches_token(row, token, chain):
                    amt = _extract_amount_str(row)
                    if _to_dec(amt) != Decimal("0"):
                        return {
                            "asset_query": asset,
                            "amount": amt,
                            "raw": row,
                            "matched_by": "address_or_symbol",
                            "row_identity": _row_identity(row),
                            "token": compact_token(token),
                        }

                    # Matched but zero-like row; keep searching/fallback to avoid false 0->0
                    last_error = "matched_zero_row"

        except Exception as e:
            last_error = repr(e)
            continue

    # 3) RPC fallback (address-exact and chain state authoritative)
    rpc = _rpc_token_balance(chain, wallet, token)
    if rpc.get("ok"):
        return {
            "asset_query": "rpc",
            "amount": str(rpc.get("amount", "0")),
            "raw": {"rpc": rpc.get("rpc"), "raw_int": rpc.get("raw_int")},
            "matched_by": str(rpc.get("matched_by") or "rpc"),
            "row_identity": str(rpc.get("row_identity") or ""),
            "token": compact_token(token),
        }

    return {
        "asset_query": candidates[0] if candidates else "",
        "amount": "0",
        "raw": {},
        "matched_by": "not_found",
        "row_identity": "",
        "token": compact_token(token),
        "last_error": last_error,
        "rpc_error": rpc.get("error") if isinstance(rpc, dict) else "",
    }


def _to_dec(v: str) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def _diff(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    b = _to_dec(before.get("amount", "0"))
    a = _to_dec(after.get("amount", "0"))
    return {
        "before": str(b),
        "after": str(a),
        "delta": str(a - b),
        "before_source": before.get("asset_query"),
        "after_source": after.get("asset_query"),
        "matched_before": before.get("matched_by"),
        "matched_after": after.get("matched_by"),
    }


def _swap_tx_with_retry(
    *,
    chain_id: int,
    src: str,
    dst: str,
    amount_wei: str,
    from_addr: str,
    slippage: float,
    retries: int,
    backoff_sec: int,
) -> Dict[str, Any]:
    attempts = max(1, retries + 1)
    delay = max(1, backoff_sec)
    errors: List[Dict[str, Any]] = []

    for i in range(1, attempts + 1):
        try:
            data = swap_tx(chain_id, src, dst, amount_wei, from_addr, slippage)
            data["_swap_attempt"] = i
            if errors:
                data["_retry_errors"] = errors
            return data
        except Exception as e:
            err = str(e)
            req_id = _extract_request_id(err)
            err_item = {"attempt": i, "error": err}
            if req_id:
                err_item["request_id"] = req_id
            errors.append(err_item)

            is_server_side = ("1inch API 500" in err) or ("1inch API 502" in err) or ("1inch API 503" in err)
            if i < attempts and is_server_side:
                time.sleep(delay)
                delay *= 2
                continue

            raise RuntimeError(
                "1inch /swap failed after retries: " +
                "; ".join([f"attempt {x['attempt']}: {x['error']}" for x in errors])
            )

    raise RuntimeError("unreachable: swap retry loop exited unexpectedly")


def main() -> None:
    p = argparse.ArgumentParser(description="Run full 1inch swap flow with post-trade verification")
    p.add_argument("--chain", required=True)
    p.add_argument("--from", dest="src", required=True, help="Source token symbol/address")
    p.add_argument("--to", dest="dst", required=True, help="Destination token symbol/address")
    p.add_argument("--amount", required=True, help="Human amount in source token units")
    p.add_argument("--slippage", type=float, default=1.0, help="Slippage percent, default 1.0")
    p.add_argument("--auto-approve", action="store_true", help="If set, auto-send approve tx when allowance is insufficient")
    p.add_argument("--verify-timeout", type=int, default=120, help="Seconds to wait for balance change verification")
    p.add_argument("--poll-interval", type=int, default=8, help="Polling interval seconds")
    p.add_argument("--swap-retries", type=int, default=2, help="Retry count for transient 1inch /swap 5xx errors")
    p.add_argument("--swap-retry-backoff", type=int, default=2, help="Initial backoff seconds for /swap retries")
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

    before_src = _fetch_token_balance(args.chain, src, wallet)
    before_dst = _fetch_token_balance(args.chain, dst, wallet)

    q = quote(chain_id, src["address"], dst["address"], amount_wei)

    approval_result = None
    if src["address"].lower() != NATIVE_TOKEN.lower():
        allowance = check_allowance(chain_id, src["address"], wallet)
        if allowance < int(amount_wei):
            if not args.auto_approve:
                raise RuntimeError("insufficient allowance; re-run with --auto-approve or execute approve.py first")
            a_tx = approve_tx(chain_id, src["address"], amount=None)
            a_resp = wallet_broadcast(
                chain_id=chain_id,
                to=a_tx["to"],
                data=a_tx["data"],
                value=str(a_tx.get("value", "0")),
            )
            approval_result = {
                "approve_tx_request": {"to": a_tx.get("to"), "value": str(a_tx.get("value", "0"))},
                "wallet_response": a_resp,
            }

    s = _swap_tx_with_retry(
        chain_id=chain_id,
        src=src["address"],
        dst=dst["address"],
        amount_wei=amount_wei,
        from_addr=wallet,
        slippage=args.slippage,
        retries=_safe_int(args.swap_retries, 2),
        backoff_sec=_safe_int(args.swap_retry_backoff, 2),
    )
    tx = s.get("tx") or {}
    if not tx:
        raise RuntimeError("1inch /swap returned no tx object")

    swap_resp = wallet_broadcast(
        chain_id=chain_id,
        to=tx["to"],
        data=tx["data"],
        value=str(tx.get("value", "0")),
    )

    # Verify by polling balances for changed state.
    started = time.time()
    after_src = before_src
    after_dst = before_dst
    changed = False
    src_pref_asset = str(before_src.get("asset_query") or "")
    dst_pref_asset = str(before_dst.get("asset_query") or "")
    src_pref_row = str(before_src.get("row_identity") or "")
    dst_pref_row = str(before_dst.get("row_identity") or "")

    while time.time() - started <= max(0, args.verify_timeout):
        after_src = _fetch_token_balance(
            args.chain,
            src,
            wallet,
            preferred_asset=src_pref_asset,
            preferred_row_identity=src_pref_row,
        )
        after_dst = _fetch_token_balance(
            args.chain,
            dst,
            wallet,
            preferred_asset=dst_pref_asset,
            preferred_row_identity=dst_pref_row,
        )

        src_changed = (after_src.get("amount") != before_src.get("amount"))
        dst_changed = (after_dst.get("amount") != before_dst.get("amount"))
        if src_changed or dst_changed:
            changed = True
            break

        if args.verify_timeout <= 0:
            break
        time.sleep(max(1, args.poll_interval))

    out = {
        "ok": True,
        "action": "run_swap_flow",
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
            "attempt": s.get("_swap_attempt", 1),
            "retry_errors": s.get("_retry_errors", []),
        },
        "wallet_response": swap_resp,
        "verification": {
            "changed_detected": changed,
            "waited_seconds": int(time.time() - started),
            "source_asset": _diff(before_src, after_src),
            "dest_asset": _diff(before_dst, after_dst),
            "source_snapshot_before": before_src,
            "source_snapshot_after": after_src,
            "dest_snapshot_before": before_dst,
            "dest_snapshot_after": after_dst,
        },
    }
    print_json(out)


if __name__ == "__main__":
    main()
