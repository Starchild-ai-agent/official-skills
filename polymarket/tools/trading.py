"""
Polymarket Trading — order building, posting, cancellation, balance/position queries.
Privy-only: orders built as EIP-712 payloads → signed via wallet_sign_typed_data → posted to CLOB.
"""
import json
import time
import random
import requests as _requests
from .utils import (
    BASE, DATA_API, GAMMA,
    CTF_EXCHANGE, CTF_EXCHANGE_NEG, CHAIN_ID, EOA,
    WALLET as get_wallet, API_KEY as get_api_key,
    l2_headers, clob_get, clob_post, clob_delete,
)


def get_market_info(token_id):
    """
    Get market metadata (tick size, fee, neg-risk) for a token.
    1) Gamma lookup by clob_token_ids → get conditionId
    2) CLOB lookup by conditionId → get market-level metadata
    """
    out = {
        "fee_bps": 0,
        "neg_risk": False,
        "tick_size": "0.01",
        "minimum_order_size": 5,
        "condition_id": None,
    }

    condition_id = None

    # Step 1: map token → condition via Gamma
    try:
        rg = _requests.get(
            f"{GAMMA}/markets",
            params={"clob_token_ids": str(token_id)},
            timeout=20,
        )
        if rg.status_code == 200:
            arr = rg.json()
            if isinstance(arr, list) and arr:
                m0 = arr[0]
                condition_id = m0.get("conditionId") or m0.get("condition_id")
                if m0.get("orderMinSize") is not None:
                    try:
                        out["minimum_order_size"] = float(m0["orderMinSize"])
                    except Exception:
                        pass
    except Exception:
        pass

    out["condition_id"] = condition_id

    # Step 2: fetch authoritative metadata from CLOB
    if condition_id:
        try:
            rc = clob_get(f"{BASE}/markets/{condition_id}")
            if rc.status_code == 200:
                mk = rc.json()
                if isinstance(mk, dict):
                    if mk.get("minimum_tick_size") is not None:
                        out["tick_size"] = str(mk["minimum_tick_size"])
                    if mk.get("taker_base_fee") is not None:
                        out["fee_bps"] = int(mk["taker_base_fee"])
                    elif mk.get("maker_base_fee") is not None:
                        out["fee_bps"] = int(mk["maker_base_fee"])
                    if mk.get("neg_risk") is not None:
                        out["neg_risk"] = bool(mk["neg_risk"])
                    if mk.get("minimum_order_size") is not None:
                        try:
                            out["minimum_order_size"] = float(mk["minimum_order_size"])
                        except Exception:
                            pass
        except Exception:
            pass

    return out


# ── Read endpoints ──

def get_balance():
    """Get USDC.e balance and allowance."""
    r = clob_get(
        f"{BASE}/balance-allowance",
        headers=l2_headers("GET", "/balance-allowance"),
        params={"asset_type": "COLLATERAL", "signature_type": EOA},
    )
    r.raise_for_status()
    return r.json()


def get_open_orders():
    """Get all open orders."""
    r = clob_get(f"{BASE}/data/orders", headers=l2_headers("GET", "/data/orders"))
    r.raise_for_status()
    return r.json()


def get_trades(limit=20):
    """Get recent trades."""
    wallet = get_wallet()
    r = _requests.get(
        f"{DATA_API}/trades",
        params={"user": wallet, "limit": limit},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def get_positions():
    """Get current positions."""
    wallet = get_wallet()
    r = _requests.get(
        f"{DATA_API}/positions",
        params={"user": wallet},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


# ── Order building ──

def build_order_payload(token_id, side, price, size, neg_risk=False, tick_size="0.01", fee_bps=None):
    """
    Build EIP-712 order payload for signing.
    Returns: (domain, types, message, meta)

    Auto-queries market info for fee_bps if not provided.
    """
    wallet = get_wallet()

    if fee_bps is None:
        market_info = get_market_info(token_id)
        fee_bps = market_info["fee_bps"]
        neg_risk = market_info["neg_risk"]
        tick_size = market_info["tick_size"]

    exchange = CTF_EXCHANGE_NEG if neg_risk else CTF_EXCHANGE
    tick = float(tick_size)
    price = round(round(price / tick) * tick, 4)
    size = round(size, 2)

    if side.upper() == "BUY":
        taker_amount = int(round(size, 2) * 1_000_000)
        raw_maker = round(round(size, 2) * round(price, 2), 4)
        maker_amount = round(raw_maker * 1_000_000)
        order_side = 0
    else:
        maker_amount = int(size * 1_000_000)
        taker_amount = int(price * size * 1_000_000)
        order_side = 1

    salt = round(time.time() * random.random())

    domain = {
        "name": "Polymarket CTF Exchange",
        "version": "1",
        "chainId": CHAIN_ID,
        "verifyingContract": exchange,
    }

    types = {
        "Order": [
            {"name": "salt", "type": "uint256"},
            {"name": "maker", "type": "address"},
            {"name": "signer", "type": "address"},
            {"name": "taker", "type": "address"},
            {"name": "tokenId", "type": "uint256"},
            {"name": "makerAmount", "type": "uint256"},
            {"name": "takerAmount", "type": "uint256"},
            {"name": "expiration", "type": "uint256"},
            {"name": "nonce", "type": "uint256"},
            {"name": "feeRateBps", "type": "uint256"},
            {"name": "side", "type": "uint8"},
            {"name": "signatureType", "type": "uint8"},
        ]
    }

    message = {
        "salt": str(salt),
        "maker": wallet,
        "signer": wallet,
        "taker": "0x0000000000000000000000000000000000000000",
        "tokenId": str(token_id),
        "makerAmount": str(maker_amount),
        "takerAmount": str(taker_amount),
        "expiration": "0",
        "nonce": "0",
        "feeRateBps": str(fee_bps),
        "side": order_side,
        "signatureType": EOA,
    }

    meta = {
        "salt": salt,
        "maker_amount": maker_amount,
        "taker_amount": taker_amount,
        "maker": wallet,
        "signer": wallet,
        "order_side": order_side,
        "exchange": exchange,
        "price": price,
        "size": size,
        "side_str": side.upper(),
        "neg_risk": neg_risk,
        "fee_bps": fee_bps,
    }

    return domain, types, message, meta


# ── Order posting ──

def post_signed_order(token_id, signature, meta):
    """
    Post a signed order to CLOB.
    Returns: (status_code, response_json)
    """
    wallet = get_wallet()
    api_key = get_api_key()
    side_str = "BUY" if meta["order_side"] == 0 else "SELL"

    order_body = {
        "order": {
            "salt": meta["salt"],
            "maker": wallet,
            "signer": wallet,
            "taker": "0x0000000000000000000000000000000000000000",
            "tokenId": str(token_id),
            "makerAmount": str(meta["maker_amount"]),
            "takerAmount": str(meta["taker_amount"]),
            "expiration": "0",
            "nonce": "0",
            "feeRateBps": str(meta.get("fee_bps", 0)),
            "side": side_str,
            "signatureType": EOA,
            "signature": signature,
        },
        "owner": api_key,
        "orderType": "GTC",
    }

    body_str = json.dumps(order_body, separators=(",", ":"))
    headers = l2_headers("POST", "/order", body_str)
    r = clob_post(f"{BASE}/order", headers=headers, data=body_str)
    return r.status_code, r.json()


# ── Cancellation ──

def cancel_order(order_id):
    """Cancel a specific order."""
    body = json.dumps({"orderID": order_id})
    r = clob_delete(f"{BASE}/order", headers=l2_headers("DELETE", "/order", body), data=body)
    return r.status_code, r.json()


def cancel_all_orders():
    """Cancel all open orders."""
    r = clob_delete(f"{BASE}/cancel-all", headers=l2_headers("DELETE", "/cancel-all"))
    return r.status_code, r.json()
