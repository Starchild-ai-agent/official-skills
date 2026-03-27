"""
Polymarket Market Data — search, lookup, orderbook, R/R analysis.
Primary search uses Gamma search-v2 with /markets fallback.
"""
import json
import requests as _requests
from .utils import (
    GAMMA, BASE, DATA_API,
    gamma_get, clob_get,
    parse_polymarket_url, enrich_market,
    get_orderbook, get_midpoint, get_price,
)


# ── Search (primary: search-v2, fallback: /markets) ──

def search_v2(query, limit=10):
    """
    Primary discovery via Gamma search-v2.
    Higher recall for thematic/event searches.
    Returns list of events with nested markets.
    """
    q = (query or "").strip()
    if not q:
        return []
    lim = max(1, min(50, int(limit or 10)))
    r = gamma_get(
        f"{GAMMA}/search-v2",
        params={
            "q": q,
            "optimized": "true",
            "limit_per_type": lim,
            "type": "events",
            "search_tags": "true",
            "search_profiles": "true",
            "cache": "true",
        },
    )
    if r.status_code >= 400:
        return []
    data = r.json() if r.text.strip() else {}
    events = data.get("events", []) if isinstance(data, dict) else []
    return events if isinstance(events, list) else []


def search_markets_legacy(query, limit=5):
    """Fallback search via /markets endpoint."""
    q = (query or "").strip()
    if not q:
        return []
    lim = max(1, min(50, int(limit or 5)))
    r = gamma_get(
        f"{GAMMA}/markets",
        params={"q": q, "limit": lim, "active": "true", "closed": "false"},
    )
    if r.status_code >= 400:
        return []
    data = r.json() if r.text.strip() else []
    return data if isinstance(data, list) else []


def search(query, limit=10):
    """
    Unified search: search-v2 first, fallback to /markets if no results.
    Returns dict with events and/or markets.
    """
    events = search_v2(query, limit)

    # Extract flat market rows from events
    markets = []
    for ev in events:
        for m in ev.get("markets", []):
            markets.append(m)

    if events:
        return {"source": "search-v2", "events": events, "markets": markets}

    # Fallback
    legacy = search_markets_legacy(query, limit)
    return {"source": "markets-fallback", "events": [], "markets": legacy}


# ── Lookup ──

def lookup_event(slug):
    """Look up event by slug."""
    r = gamma_get(f"{GAMMA}/events", params={"slug": slug, "limit": 1})
    if r.status_code >= 400:
        return None
    data = r.json() if r.text.strip() else []
    return data[0] if isinstance(data, list) and data else None


def lookup_market_by_slug(slug):
    """Look up single market by slug."""
    r = gamma_get(f"{GAMMA}/markets", params={"slug": slug, "limit": 1})
    if r.status_code >= 400:
        return None
    data = r.json() if r.text.strip() else []
    return data[0] if isinstance(data, list) and data else None


def full_lookup(url_or_slug):
    """
    Full market lookup from URL or slug.
    Returns enriched event/market data with live prices.
    """
    event_slug, market_slug = parse_polymarket_url(url_or_slug)
    event = lookup_event(event_slug)

    if not event:
        market = lookup_market_by_slug(event_slug)
        if market:
            return {"type": "single_market", "market": enrich_market(market)}
        return {"error": f"Not found: {event_slug}"}

    result = {
        "type": "event",
        "title": event.get("title"),
        "slug": event.get("slug"),
        "description": (event.get("description") or "")[:500],
        "end_date": event.get("endDate"),
        "volume": event.get("volume"),
        "neg_risk": event.get("negRisk", False),
        "neg_risk_market_id": event.get("negRiskMarketID"),
        "markets": [],
    }

    for m in event.get("markets", []):
        enriched = enrich_market(m)
        result["markets"].append(enriched)
        if market_slug and m.get("slug") == market_slug:
            result["focused_market"] = enriched

    return result


# ── Orderbook Analysis ──

def analyze_orderbook(token_id):
    """Analyze orderbook depth and spread."""
    book = get_orderbook(token_id)
    mid = get_midpoint(token_id)
    bids = sorted(book.get("bids", []), key=lambda x: float(x["price"]), reverse=True)
    asks = sorted(book.get("asks", []), key=lambda x: float(x["price"]))

    best_bid = float(bids[0]["price"]) if bids else 0
    best_ask = float(asks[0]["price"]) if asks else 1
    spread = best_ask - best_bid
    mp = mid or ((best_bid + best_ask) / 2)
    spread_pct = (spread / mp * 100) if mp else 0

    def depth_within(levels, mp, band, side):
        total = 0
        for lvl in levels:
            p, s = float(lvl["price"]), float(lvl["size"])
            if side == "bid" and p >= mp - band:
                total += p * s
            elif side == "ask" and p <= mp + band:
                total += p * s
        return total

    return {
        "token_id": token_id,
        "best_bid": best_bid,
        "best_ask": best_ask,
        "midpoint": mid,
        "spread": round(spread, 4),
        "spread_pct": round(spread_pct, 2),
        "bid_levels": len(bids),
        "ask_levels": len(asks),
        "bid_depth_2c": round(depth_within(bids, mp, 0.02, "bid"), 2),
        "ask_depth_2c": round(depth_within(asks, mp, 0.02, "ask"), 2),
        "bid_depth_5c": round(depth_within(bids, mp, 0.05, "bid"), 2),
        "ask_depth_5c": round(depth_within(asks, mp, 0.05, "ask"), 2),
        "top_bids": [{"price": b["price"], "size": b["size"]} for b in bids[:5]],
        "top_asks": [{"price": a["price"], "size": a["size"]} for a in asks[:5]],
    }


# ── Risk/Reward Analysis ──

def rr_analysis(token_id, side, size_usd):
    """Risk/reward analysis for a potential trade."""
    ob = analyze_orderbook(token_id)

    if side.upper() == "YES":
        entry_price = ob["best_ask"]
    else:
        entry_price = 1 - ob["best_bid"]

    if entry_price <= 0 or entry_price >= 1:
        return {"error": f"Invalid entry price: {entry_price}"}

    tokens = size_usd / entry_price
    profit_if_win = tokens - size_usd
    rr_ratio = profit_if_win / size_usd if size_usd > 0 else 0

    return {
        "side": side.upper(),
        "entry_price": round(entry_price, 4),
        "implied_probability": f"{entry_price*100:.1f}%",
        "size_usd": round(size_usd, 2),
        "tokens": round(tokens, 2),
        "profit_if_win": round(profit_if_win, 2),
        "loss_if_lose": round(size_usd, 2),
        "risk_reward_ratio": f"1:{round(rr_ratio, 2)}",
        "breakeven_probability": f"{entry_price*100:.1f}%",
        "orderbook": {
            "spread": ob["spread"],
            "spread_pct": ob["spread_pct"],
            "bid_depth_5c": ob["bid_depth_5c"],
            "ask_depth_5c": ob["ask_depth_5c"],
        },
    }
