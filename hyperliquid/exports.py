"""
Hyperliquid skill exports — read-only tools, sync via requests.

Bypasses the async client entirely. Uses direct POST to /info endpoint.
Wallet address resolved via Fly OIDC → wallet-service.

Write operations (hl_order, hl_cancel, etc.) are NOT exported — they require
the agent's signing pipeline. Use /chat/stream to invoke those from task scripts.

Usage in task scripts:
    from core.skill_tools import hyperliquid
    account = hyperliquid.hl_account()
    mids = hyperliquid.hl_market()
    candles = hyperliquid.hl_candles(coin="BTC", interval="1h", hours_back=24)
"""
import os
import json
import time
import http.client
import socket
import requests

HL_API = os.environ.get("HYPERLIQUID_API_URL", "https://api.hyperliquid.xyz")
FLY_API_SOCKET = "/.fly/api"
WALLET_SERVICE_URL = os.environ.get("WALLET_SERVICE_URL", "https://wallet-service-dev.fly.dev")
OIDC_AUDIENCE = os.environ.get("WALLET_OIDC_AUDIENCE", WALLET_SERVICE_URL)

_cached_address = None


def _get_oidc_token():
    """Get OIDC token from Fly unix socket."""
    conn = http.client.HTTPConnection("localhost")
    conn.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    conn.sock.connect(FLY_API_SOCKET)
    body = json.dumps({"aud": OIDC_AUDIENCE}).encode()
    conn.request("POST", "/v1/tokens/oidc", body=body,
                 headers={"Host": "localhost", "Content-Type": "application/json"})
    resp = conn.getresponse()
    token = resp.read().decode().strip()
    conn.close()
    return token


def _get_address():
    """Get agent's EVM wallet address (cached)."""
    global _cached_address
    if _cached_address:
        return _cached_address
    if not os.path.exists(FLY_API_SOCKET):
        raise RuntimeError("Not on Fly machine — wallet unavailable")
    token = _get_oidc_token()
    r = requests.get(f"{WALLET_SERVICE_URL}/agent/wallet",
                     headers={"Authorization": f"Bearer {token}"}, timeout=15)
    r.raise_for_status()
    data = r.json()
    for w in (data if isinstance(data, list) else data.get("wallets", [])):
        if w.get("chain_type") == "ethereum":
            _cached_address = w["wallet_address"]
            return _cached_address
    raise RuntimeError("No ethereum wallet found")


def _info(req_type, **kwargs):
    """POST to Hyperliquid /info endpoint."""
    payload = {"type": req_type, **kwargs}
    r = requests.post(f"{HL_API}/info", json=payload, timeout=15)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and data.get("status") == "err":
        raise Exception(f"Hyperliquid error: {data.get('response', data)}")
    return data


# ── Exported read-only tools (names match SKILL.md) ──


def hl_account(dex=None):
    """Get perp account state: positions, margin, PnL."""
    addr = _get_address()
    if dex:
        return _info("clearinghouseState", user=addr, dex=dex)
    return _info("clearinghouseState", user=addr)


def hl_balances():
    """Get spot token balances."""
    return _info("spotClearinghouseState", user=_get_address())


def hl_total_balance():
    """Get total available balance across spot + perp, aware of abstraction mode.

    Mirrors the `hl_total_balance` runtime tool. Use this for "how much can I
    trade with" checks — hl_account shows perp only (often $0 under unified
    account) and hl_balances shows spot only.

    Returns dict:
        totalAvailable: USDC available for trading (rounded 2dp)
        abstractionMode: "unifiedAccount" | "disabled" | "default" | ...
        note: human-readable explanation of how the total was derived
        breakdown: {spot:{usdc}, perp:{accountValue, marginUsed, available}}
    """
    addr = _get_address()

    # Abstraction mode — tolerate string or dict shapes, default on any error.
    try:
        abstraction_result = _info("userAbstraction", user=addr)
        if isinstance(abstraction_result, str):
            abstraction_mode = abstraction_result
        elif isinstance(abstraction_result, dict):
            abstraction_mode = abstraction_result.get(
                "type", abstraction_result.get("state", "default")
            )
        else:
            abstraction_mode = "default"
    except Exception:
        abstraction_mode = "default"

    spot_state = _info("spotClearinghouseState", user=addr)
    perp_state = _info("clearinghouseState", user=addr)

    # Spot USDC
    spot_usdc = 0.0
    for bal in spot_state.get("balances", []):
        if bal.get("coin") == "USDC":
            spot_usdc = float(bal.get("total", 0))
            break

    # Perp margin
    perp_margin = perp_state.get("marginSummary", {})
    perp_value = float(perp_margin.get("accountValue", 0))
    perp_used = float(perp_margin.get("totalMarginUsed", 0))
    perp_available = perp_value - perp_used

    if abstraction_mode == "unifiedAccount":
        total_available = spot_usdc + perp_available
        note = "Unified account: funds are shared across spot/perp/builder-dexes"
    else:
        total_available = perp_available
        note = "Disabled mode: perp and spot are separate"

    return {
        "totalAvailable": round(total_available, 2),
        "abstractionMode": abstraction_mode,
        "note": note,
        "breakdown": {
            "spot": {"usdc": round(spot_usdc, 2)},
            "perp": {
                "accountValue": round(perp_value, 2),
                "marginUsed": round(perp_used, 2),
                "available": round(perp_available, 2),
            },
        },
    }


def hl_open_orders():
    """Get all open orders."""
    return _info("openOrders", user=_get_address())


def hl_market(dex=None):
    """Get current mid prices for all assets."""
    if dex:
        return _info("allMids", dex=dex)
    return _info("allMids")


def hl_orderbook(coin):
    """Get L2 orderbook snapshot for a coin."""
    return _info("l2Book", coin=coin)


def hl_fills():
    """Get recent trade fills for this wallet."""
    return _info("userFills", user=_get_address())


def hl_candles(coin, interval="1h", hours_back=24, start=None, end=None):
    """Get OHLCV candlestick data.
    
    Args:
        coin: e.g. "BTC", "ETH"
        interval: "1m","5m","15m","1h","4h","1d"
        hours_back: lookback period in hours (default 24)
        start/end: explicit timestamps in ms (override hours_back)
    """
    if end is None:
        end = int(time.time() * 1000)
    if start is None:
        start = end - hours_back * 3600 * 1000
    return _info("candleSnapshot", req={"coin": coin, "interval": interval, "startTime": start, "endTime": end})


def hl_funding(coin, hours_back=24, start=None):
    """Get historical funding rates for a coin.
    
    Args:
        coin: e.g. "BTC"
        hours_back: lookback in hours (default 24)
        start: explicit start timestamp in ms (overrides hours_back)
    """
    if start is None:
        start = int((time.time() - hours_back * 3600) * 1000)
    return _info("fundingHistory", coin=coin, startTime=start)


def hl_predicted_funding():
    """Get predicted next funding rates for all assets."""
    return _info("predictedFundings")


def hl_order_status(oid):
    """Look up a single order by oid."""
    return _info("orderStatus", user=_get_address(), oid=oid)


def hl_user_fees():
    """Get user fee schedule."""
    return _info("userFees", user=_get_address())
