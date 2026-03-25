"""
Polymarket Trading Helpers
Order building, posting, cancellation, balance/position queries
"""
import json
import time
import random
import requests as _requests
from .utils import (
    BASE,
    DATA_API,
    CTF_EXCHANGE,
    CTF_EXCHANGE_NEG,
    CHAIN_ID,
    EOA,
    WALLET as get_wallet,
    API_KEY as get_api_key,
    l2_headers,
    clob_get,
    clob_post,
    clob_delete,
)


def get_market_info(token_id):
    """
    Get market metadata including fee rate
    Returns dict with fee_bps, neg_risk, tick_size
    """
    r = clob_get(f"{BASE}/markets", params={"token_id": token_id})
    if r.status_code == 200:
        markets = r.json()
        if markets:
            market = markets[0] if isinstance(markets, list) else markets
            return {
                "fee_bps": market.get("maker_base_fee_rate", 1000),  # Default 10%
                "neg_risk": market.get("neg_risk", False),
                "tick_size": market.get("minimum_tick_size", "0.01"),
            }
    # Fallback defaults
    return {"fee_bps": 1000, "neg_risk": False, "tick_size": "0.01"}


def get_balance():
    """Get USDC balance and allowance"""
    r = clob_get(
        f"{BASE}/balance-allowance",
        headers=l2_headers("GET", "/balance-allowance"),
        params={"asset_type": "COLLATERAL", "signature_type": EOA},
    )
    r.raise_for_status()
    return r.json()


def get_open_orders():
    """Get all open orders"""
    r = clob_get(f"{BASE}/data/orders", headers=l2_headers("GET", "/data/orders"))
    r.raise_for_status()
    return r.json()


def get_trades(limit=20):
    """Get recent trades (from public Data API)"""
    wallet = get_wallet()
    r = _requests.get(
        f"{DATA_API}/trades",
        params={"user": wallet, "limit": limit},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def get_positions():
    """Get current positions (from public Data API)"""
    wallet = get_wallet()
    r = _requests.get(
        f"{DATA_API}/positions",
        params={"user": wallet},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def cancel_order(order_id):
    """Cancel a specific order"""
    body = json.dumps({"orderID": order_id})
    r = clob_delete(f"{BASE}/order", headers=l2_headers("DELETE", "/order", body), data=body)
    return r.status_code, r.json()


def cancel_all_orders():
    """Cancel all open orders"""
    r = clob_delete(f"{BASE}/cancel-all", headers=l2_headers("DELETE", "/cancel-all"))
    return r.status_code, r.json()


def build_order_payload(token_id, side, price, size, neg_risk=False, tick_size="0.01", fee_bps=None):
    """
    Build EIP-712 order payload for signing
    Returns: (domain, types, message, meta)

    Args:
        token_id: CLOB token ID
        side: "BUY" or "SELL"
        price: Order price (0.01-0.99)
        size: Order size in tokens
        neg_risk: Use neg-risk exchange contract
        tick_size: Price tick size (0.01 or 0.001)
        fee_bps: Fee rate in basis points (auto-queries from market if None)
    """
    wallet = get_wallet()

    # Query market info for fee rate if not provided
    if fee_bps is None:
        market_info = get_market_info(token_id)
        fee_bps = market_info["fee_bps"]

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


def post_signed_order(token_id, signature, meta):
    """
    Post a signed order to CLOB

    Args:
        token_id: CLOB token ID
        signature: EIP-712 signature from wallet
        meta: Metadata from build_order_payload

    Returns:
        (status_code, response_json)
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
            "feeRateBps": str(meta.get("fee_bps", 1000)),  # Use fee from meta or default
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
