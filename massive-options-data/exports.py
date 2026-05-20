"""
Massive (formerly Polygon) Options data — script-mode skill exports.

Usage from a bash block:
    python3 - <<'EOF'
    import sys
    sys.path.insert(0, "/data/workspace/skills/massive-options-data")
    from exports import massive_option_chain_snapshot
    print(massive_option_chain_snapshot("SPY", limit=5))
    EOF

Imports from sidecar.proxy_client (NOT core.http_client) so this skill
stays runnable without the agent platform's core/* modules on PYTHONPATH.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional

try:
    from sidecar.proxy_client import proxied_get
except ImportError:
    # Local dev / outside the deployed image.
    from core.http_client import proxied_get


BASE = "https://api.polygon.io"
API_KEY = os.environ.get("MASSIVE_API_KEY", "")


# ---------------------------------------------------------------------------
# Low-level
# ---------------------------------------------------------------------------

def _headers(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    h = {"Accept": "application/json"}
    if extra:
        h.update(extra)
    return h


def _get(path: str, params: Optional[Dict[str, Any]] = None,
         caller_id: Optional[str] = None) -> Dict[str, Any]:
    params = dict(params or {})
    if API_KEY and "apikey" not in params and "apiKey" not in params:
        params["apikey"] = API_KEY
    headers = _headers({"SC-CALLER-ID": caller_id} if caller_id else None)
    url = path if path.startswith("http") else f"{BASE}{path}"
    r = proxied_get(url, params=params, headers=headers)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

def massive_option_chain_snapshot(
    underlying: str,
    *,
    strike_price: Optional[float] = None,
    strike_price_gte: Optional[float] = None,
    strike_price_lte: Optional[float] = None,
    expiration_date: Optional[str] = None,
    expiration_date_gte: Optional[str] = None,
    expiration_date_lte: Optional[str] = None,
    contract_type: Optional[str] = None,  # "call" | "put"
    order: Optional[str] = None,
    limit: int = 250,
    sort: Optional[str] = None,
    caller_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Full option chain snapshot for an underlying."""
    params: Dict[str, Any] = {"limit": limit}
    if strike_price is not None:
        params["strike_price"] = strike_price
    if strike_price_gte is not None:
        params["strike_price.gte"] = strike_price_gte
    if strike_price_lte is not None:
        params["strike_price.lte"] = strike_price_lte
    if expiration_date:
        params["expiration_date"] = expiration_date
    if expiration_date_gte:
        params["expiration_date.gte"] = expiration_date_gte
    if expiration_date_lte:
        params["expiration_date.lte"] = expiration_date_lte
    if contract_type:
        params["contract_type"] = contract_type
    if order:
        params["order"] = order
    if sort:
        params["sort"] = sort
    return _get(f"/v3/snapshot/options/{underlying.upper()}",
                params=params, caller_id=caller_id)


def massive_option_contract_snapshot(
    underlying: str,
    option_ticker: str,
    *,
    caller_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Snapshot for a single option contract.

    `option_ticker` is the OPRA-style ticker like `O:SPY260619C00500000`.
    """
    return _get(
        f"/v3/snapshot/options/{underlying.upper()}/{option_ticker}",
        caller_id=caller_id,
    )


# ---------------------------------------------------------------------------
# Reference
# ---------------------------------------------------------------------------

def massive_list_contracts(
    *,
    underlying_ticker: Optional[str] = None,
    contract_type: Optional[str] = None,  # "call" | "put"
    expiration_date: Optional[str] = None,
    expiration_date_gte: Optional[str] = None,
    expiration_date_lte: Optional[str] = None,
    strike_price: Optional[float] = None,
    strike_price_gte: Optional[float] = None,
    strike_price_lte: Optional[float] = None,
    expired: Optional[bool] = None,
    as_of: Optional[str] = None,
    order: Optional[str] = None,
    limit: int = 1000,
    sort: Optional[str] = None,
    caller_id: Optional[str] = None,
) -> Dict[str, Any]:
    """List option contracts (active or expired)."""
    params: Dict[str, Any] = {"limit": limit}
    if underlying_ticker:
        params["underlying_ticker"] = underlying_ticker.upper()
    if contract_type:
        params["contract_type"] = contract_type
    if expiration_date:
        params["expiration_date"] = expiration_date
    if expiration_date_gte:
        params["expiration_date.gte"] = expiration_date_gte
    if expiration_date_lte:
        params["expiration_date.lte"] = expiration_date_lte
    if strike_price is not None:
        params["strike_price"] = strike_price
    if strike_price_gte is not None:
        params["strike_price.gte"] = strike_price_gte
    if strike_price_lte is not None:
        params["strike_price.lte"] = strike_price_lte
    if expired is not None:
        params["expired"] = "true" if expired else "false"
    if as_of:
        params["as_of"] = as_of
    if order:
        params["order"] = order
    if sort:
        params["sort"] = sort
    return _get("/v3/reference/options/contracts",
                params=params, caller_id=caller_id)


# ---------------------------------------------------------------------------
# Ticks
# ---------------------------------------------------------------------------

def massive_option_trades(
    option_ticker: str,
    *,
    timestamp_gte: Optional[str] = None,
    timestamp_lte: Optional[str] = None,
    order: str = "desc",
    limit: int = 1000,
    sort: str = "timestamp",
    caller_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Historical trade ticks for an option contract."""
    params: Dict[str, Any] = {"order": order, "limit": limit, "sort": sort}
    if timestamp_gte:
        params["timestamp.gte"] = timestamp_gte
    if timestamp_lte:
        params["timestamp.lte"] = timestamp_lte
    return _get(f"/v3/trades/{option_ticker}",
                params=params, caller_id=caller_id)


def massive_option_quotes(
    option_ticker: str,
    *,
    timestamp_gte: Optional[str] = None,
    timestamp_lte: Optional[str] = None,
    order: str = "desc",
    limit: int = 1000,
    sort: str = "timestamp",
    caller_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Historical NBBO quote ticks for an option contract."""
    params: Dict[str, Any] = {"order": order, "limit": limit, "sort": sort}
    if timestamp_gte:
        params["timestamp.gte"] = timestamp_gte
    if timestamp_lte:
        params["timestamp.lte"] = timestamp_lte
    return _get(f"/v3/quotes/{option_ticker}",
                params=params, caller_id=caller_id)


# ---------------------------------------------------------------------------
# Aggregates
# ---------------------------------------------------------------------------

def massive_option_aggregates(
    option_ticker: str,
    multiplier: int,
    timespan: str,  # "minute" | "hour" | "day" | "week" | "month" | "quarter" | "year" | "second"
    from_: str,     # "YYYY-MM-DD" or ms timestamp
    to: str,
    *,
    adjusted: bool = True,
    sort: str = "asc",
    limit: int = 50000,
    caller_id: Optional[str] = None,
) -> Dict[str, Any]:
    """OHLCV aggregate bars for an option contract."""
    params: Dict[str, Any] = {
        "adjusted": "true" if adjusted else "false",
        "sort": sort,
        "limit": limit,
    }
    path = f"/v2/aggs/ticker/{option_ticker}/range/{multiplier}/{timespan}/{from_}/{to}"
    return _get(path, params=params, caller_id=caller_id)


# ---------------------------------------------------------------------------
# Pagination helper
# ---------------------------------------------------------------------------

def massive_paginate(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    *,
    max_pages: int = 20,
    caller_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Walk `next_url` until exhausted or `max_pages` reached.

    Returns a flat list of `results` items.
    """
    out: List[Dict[str, Any]] = []
    next_url: Optional[str] = url
    next_params: Optional[Dict[str, Any]] = dict(params or {})
    pages = 0
    while next_url and pages < max_pages:
        pages += 1
        data = _get(next_url, params=next_params, caller_id=caller_id)
        out.extend(data.get("results") or [])
        nu = data.get("next_url")
        if not nu:
            break
        next_url = nu
        next_params = None  # next_url already contains query string
    return out
