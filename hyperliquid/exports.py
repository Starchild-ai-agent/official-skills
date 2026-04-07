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
