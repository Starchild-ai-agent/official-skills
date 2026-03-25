"""
Polymarket Market Data Helpers
Market discovery, lookup, orderbook analysis, R/R calculations
"""
import json
from .utils import (
    GAMMA,
    gamma_get,
    parse_polymarket_url,
    enrich_market,
    get_orderbook,
    get_midpoint,
)


def lookup_event(slug):
    """Look up event by slug"""
    r = gamma_get(f"{GAMMA}/events", params={"slug": slug, "limit": 1})
    r.raise_for_status()
    data = r.json()
    return data[0] if data else None


def lookup_market_by_slug(slug):
    """Look up single market by slug"""
    r = gamma_get(f"{GAMMA}/markets", params={"slug": slug, "limit": 1})
    r.raise_for_status()
    data = r.json()
    return data[0] if data else None


def search_markets(query, limit=5):
    """Search for markets"""
    r = gamma_get(
        f"{GAMMA}/markets",
        params={"q": query, "limit": limit, "active": "true", "closed": "false"},
    )
    r.raise_for_status()
    return r.json()


def full_lookup(url_or_slug):
    """
    Full market lookup from URL or slug
    Returns enriched event/market data with live prices
    """
    event_slug, market_slug = parse_polymarket_url(url_or_slug)
    event = lookup_event(event_slug)

    if not event:
        # Try as direct market slug
        market = lookup_market_by_slug(event_slug)
        if market:
            return {"type": "single_market", "market": enrich_market(market)}
        return {"error": f"Not found: {event_slug}"}

    result = {
        "type": "event",
        "title": event.get("title"),
        "slug": event.get("slug"),
        "description": event.get("description", "")[:500],
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


def analyze_orderbook(token_id):
    """
    Analyze orderbook depth and spread
    Returns bid/ask levels, depth metrics, top levels
    """
    book = get_orderbook(token_id)
    mid = get_midpoint(token_id)
    bids = sorted(book.get("bids", []), key=lambda x: float(x["price"]), reverse=True)
    asks = sorted(book.get("asks", []), key=lambda x: float(x["price"]))

    best_bid = float(bids[0]["price"]) if bids else 0
    best_ask = float(asks[0]["price"]) if asks else 1
    spread = best_ask - best_bid
    spread_pct = (spread / mid * 100) if mid else 0

    def depth_within(levels, mp, band, side):
        total = 0
        for lvl in levels:
            p, s = float(lvl["price"]), float(lvl["size"])
            if side == "bid" and p >= mp - band:
                total += p * s
            elif side == "ask" and p <= mp + band:
                total += p * s
        return total

    mp = mid or (best_bid + best_ask) / 2

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


def rr_analysis(token_id, side, size_usd):
    """
    Risk/reward analysis for a potential trade
    Returns entry price, token amount, profit/loss, R/R ratio
    """
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
