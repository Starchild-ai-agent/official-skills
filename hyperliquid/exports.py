"""
Hyperliquid skill exports — read-only tools, sync via requests.

Bypasses the async client entirely. Uses direct POST to /info endpoint.

ADDRESS HANDLING (v1.8.0): every user-scoped function takes an optional
`address` argument. Omit it to query the agent's own wallet (resolved via
Fly OIDC -> wallet-service, cached); pass any 0x address to inspect a third
party. Before v1.8.0 these were hard-bound to the agent's own wallet, so
"analyse this wallet's Hyperliquid PnL" was impossible to answer.

Write operations (hl_order, hl_cancel, etc.) are NOT exported — they require
the agent's signing pipeline. Use HyperliquidClient for those.

Usage in task scripts:
    from core.skill_tools import hyperliquid
    account  = hyperliquid.hl_account()                      # agent's own
    other    = hyperliquid.hl_account(address="0x1f16...")   # someone else's
    pnl      = hyperliquid.hl_portfolio(address="0x1f16...") # PnL time series
    mids     = hyperliquid.hl_market()
    candles  = hyperliquid.hl_candles(coin="BTC", interval="1h", hours_back=24)
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
    """Get agent's own EVM wallet address (cached)."""
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


def _addr(address=None):
    """Resolve a target address: explicit arg wins, else the agent's own wallet.

    Validates shape early — an unchecked bad address makes Hyperliquid return
    an empty result rather than an error, which reads as "no positions" and
    is worse than a clear failure.
    """
    if address is None:
        return _get_address()
    a = str(address).strip()
    if not (a.startswith("0x") and len(a) == 42):
        raise ValueError(f"Invalid EVM address: {address!r} (expected 0x + 40 hex chars)")
    return a


def _info(req_type, **kwargs):
    """POST to Hyperliquid /info endpoint."""
    payload = {"type": req_type, **kwargs}
    r = requests.post(f"{HL_API}/info", json=payload, timeout=15)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and data.get("status") == "err":
        raise Exception(f"Hyperliquid error: {data.get('response', data)}")
    return data


def _ms_ago(hours=None, days=None):
    """Epoch-ms timestamp for N hours/days back from now."""
    secs = 0
    if hours:
        secs += hours * 3600
    if days:
        secs += days * 86400
    return int((time.time() - secs) * 1000)


# ── Account state ────────────────────────────────────────────────────────


def hl_account(address=None, dex=None):
    """Perp account state: positions, margin, unrealized PnL.

    Args:
        address: wallet to inspect (default: the agent's own)
        dex: HIP-3 builder dex name (default: the first perp dex)

    Unrealized PnL per position is in assetPositions[].position.unrealizedPnl.
    For realized PnL use hl_fills (closedPnl) or hl_portfolio (time series).
    """
    kw = {"user": _addr(address)}
    if dex:
        kw["dex"] = dex
    return _info("clearinghouseState", **kw)


def hl_balances(address=None):
    """Spot token balances."""
    return _info("spotClearinghouseState", user=_addr(address))


def hl_total_balance(address=None):
    """Total available balance across spot + perp, aware of abstraction mode.

    Use this for "how much can I trade with" checks — hl_account shows perp
    only (often $0 under unified account) and hl_balances shows spot only.

    Returns dict:
        totalAvailable: USDC available for trading (rounded 2dp)
        abstractionMode: "unifiedAccount" | "disabled" | "default" | ...
        note: human-readable explanation of how the total was derived
        breakdown: {spot:{usdc}, perp:{accountValue, marginUsed, available}}
    """
    addr = _addr(address)

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

    spot_usdc = 0.0
    for bal in spot_state.get("balances", []):
        if bal.get("coin") == "USDC":
            spot_usdc = float(bal.get("total", 0))
            break

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


def hl_user_role(address=None):
    """Account role: "user", "agent", "vault", "subAccount", "missing".

    "missing" means the address has never traded on Hyperliquid — check this
    before reporting "no positions", which otherwise looks identical.
    """
    return _info("userRole", user=_addr(address))


def hl_user_fees(address=None):
    """Fee schedule and 14-day volume."""
    return _info("userFees", user=_addr(address))


def hl_rate_limit(address=None):
    """Request rate-limit state: cumVlm, nRequestsUsed, nRequestsCap."""
    return _info("userRateLimit", user=_addr(address))


def hl_sub_accounts(address=None):
    """Sub-accounts owned by this address (None if it has none)."""
    return _info("subAccounts", user=_addr(address))


def hl_referral(address=None):
    """Referral state: referrer, code, cumVlm, builder/claimed rewards."""
    return _info("referral", user=_addr(address))


def hl_extra_agents(address=None):
    """Approved API agent wallets and their expiry."""
    return _info("extraAgents", user=_addr(address))


# ── PnL and history ──────────────────────────────────────────────────────


def hl_portfolio(address=None):
    """PnL and account-value time series — the direct answer to "what is this
    wallet's PnL over time".

    Returns a list of [period, data] pairs covering 8 windows:
        day, week, month, allTime, perpDay, perpWeek, perpMonth, perpAllTime
    Each data dict holds:
        accountValueHistory: [[epoch_ms, "value_usd"], ...]
        pnlHistory:          [[epoch_ms, "pnl_usd"], ...]
        vlm:                 traded volume for the window

    The bare "day"/"week"/... keys cover the whole account; the "perp*" keys
    are perps only. Note pnlHistory restarts at 0 at the start of each window,
    so allTime is the one to read for lifetime PnL.
    """
    return _info("portfolio", user=_addr(address))


def hl_fills(address=None):
    """Most recent trade fills (capped at 2000, newest last).

    Each fill carries closedPnl — realized PnL for that fill. For a bounded
    window or to page beyond 2000 fills, use hl_fills_by_time.
    """
    return _info("userFills", user=_addr(address))


def hl_fills_by_time(address=None, days_back=30, start=None, end=None,
                     aggregate_by_time=False):
    """Trade fills within a time range (max 2000 per call).

    Args:
        address: wallet to inspect (default: the agent's own)
        days_back: lookback window in days (default 30)
        start/end: explicit epoch-ms timestamps (override days_back)
        aggregate_by_time: merge partial fills of the same order

    To walk a long history, page forward: pass the last fill's `time` as the
    next `start` until fewer than 2000 fills come back.
    """
    if start is None:
        start = _ms_ago(days=days_back)
    kw = {"user": _addr(address), "startTime": int(start)}
    if end is not None:
        kw["endTime"] = int(end)
    if aggregate_by_time:
        kw["aggregateByTime"] = True
    return _info("userFillsByTime", **kw)


def hl_historical_orders(address=None):
    """Recent order history including cancelled and rejected orders.

    hl_open_orders shows only what is live now; this shows what happened.
    """
    return _info("historicalOrders", user=_addr(address))


def hl_ledger(address=None, days_back=30, start=None, end=None):
    """Non-funding ledger updates: deposits, withdrawals, transfers, liquidations.

    This is the money-in/money-out record. Cost basis for an all-time PnL
    calculation comes from here — trade fills alone cannot tell you how much
    capital entered the account.
    """
    if start is None:
        start = _ms_ago(days=days_back)
    kw = {"user": _addr(address), "startTime": int(start)}
    if end is not None:
        kw["endTime"] = int(end)
    return _info("userNonFundingLedgerUpdates", **kw)


def hl_funding_payments(address=None, days_back=30, start=None, end=None):
    """Funding payments this wallet paid or received (max 500 per call).

    Distinct from hl_funding, which is an asset's market-wide funding rate.
    """
    if start is None:
        start = _ms_ago(days=days_back)
    kw = {"user": _addr(address), "startTime": int(start)}
    if end is not None:
        kw["endTime"] = int(end)
    return _info("userFunding", **kw)


def hl_twap_fills(address=None):
    """Fills from TWAP orders (kept separate from ordinary fills)."""
    return _info("userTwapSliceFills", user=_addr(address))


def hl_vault_equities(address=None):
    """Vault deposits held by this address."""
    return _info("userVaultEquities", user=_addr(address))


# ── Orders ───────────────────────────────────────────────────────────────


def hl_open_orders(address=None):
    """Currently open orders (basic form)."""
    return _info("openOrders", user=_addr(address))


def hl_open_orders_full(address=None):
    """Open orders with trigger/TP-SL detail.

    Includes triggerCondition, isTrigger, triggerPx, isPositionTpsl and
    orderType — none of which hl_open_orders returns. Use this when stop
    losses or take profits matter.
    """
    return _info("frontendOpenOrders", user=_addr(address))


def hl_order_status(oid, address=None):
    """Look up a single order by oid (or cloid string)."""
    return _info("orderStatus", user=_addr(address), oid=oid)


# ── Market data ──────────────────────────────────────────────────────────


def hl_market(dex=None):
    """Current mid prices for all assets."""
    if dex:
        return _info("allMids", dex=dex)
    return _info("allMids")


def hl_orderbook(coin):
    """L2 orderbook snapshot for a coin."""
    return _info("l2Book", coin=coin)


def hl_candles(coin, interval="1h", hours_back=24, start=None, end=None):
    """OHLCV candlestick data.

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
    return _info("candleSnapshot", req={"coin": coin, "interval": interval,
                                        "startTime": start, "endTime": end})


def hl_funding(coin, hours_back=24, start=None):
    """An asset's market-wide historical funding rates.

    For what a specific wallet paid or received, use hl_funding_payments.
    """
    if start is None:
        start = _ms_ago(hours=hours_back)
    return _info("fundingHistory", coin=coin, startTime=start)


def hl_predicted_funding():
    """Predicted next funding rates across venues for all assets."""
    return _info("predictedFundings")


def hl_meta(dex=None):
    """Perp universe metadata: name, szDecimals, maxLeverage, margin tables.

    szDecimals is required to size an order correctly — a size with more
    decimals than the asset allows is rejected.
    """
    if dex:
        return _info("meta", dex=dex)
    return _info("meta")


def hl_meta_ctxs(dex=None):
    """Perp metadata plus live context per asset.

    Returns [meta, contexts] where each context has markPx, midPx, oraclePx,
    funding, openInterest, dayNtlVlm, premium, impactPxs, prevDayPx. This is
    the one call for a market-wide scan — hl_market gives only mid prices.
    """
    if dex:
        return _info("metaAndAssetCtxs", dex=dex)
    return _info("metaAndAssetCtxs")


def hl_spot_meta():
    """Spot universe metadata: tokens, pairs, indices, EVM contracts."""
    return _info("spotMeta")


def hl_spot_meta_ctxs():
    """Spot metadata plus live context (markPx, midPx, dayNtlVlm, prevDayPx)."""
    return _info("spotMetaAndAssetCtxs")


def hl_perp_dexs():
    """All perp dexes, including HIP-3 builder-deployed ones.

    Index 0 is null — that is the first/native perp dex. Named entries (e.g.
    "xyz") carry their own universe; their assets appear as "dex:SYMBOL" and
    need the dex argument on hl_account / hl_meta / hl_market.
    """
    return _info("perpDexs")


# ── Staking ──────────────────────────────────────────────────────────────


def hl_staking(address=None):
    """Staking summary: delegated, undelegated, pending withdrawals."""
    return _info("delegatorSummary", user=_addr(address))


def hl_staking_delegations(address=None):
    """Per-validator stake delegations."""
    return _info("delegations", user=_addr(address))


def hl_staking_rewards(address=None):
    """Staking reward history."""
    return _info("delegatorRewards", user=_addr(address))
