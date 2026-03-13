"""
Polymarket Prediction Market Tools — BaseTool subclasses for agent use.

All 10 tools are read-only (no wallet required, no API key needed).
"""

import json
import logging

from core.tool import BaseTool, ToolContext, ToolResult
from .client import PolymarketClient

logger = logging.getLogger(__name__)

# Module-level shared client instance
_client: PolymarketClient = None


def _get_client() -> PolymarketClient:
    global _client
    if _client is None:
        _client = PolymarketClient()
    return _client


def _parse_json_field(value):
    """Parse a JSON string field from Gamma API (clobTokenIds, outcomes, outcomePrices)."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return value


def _format_market(market: dict) -> dict:
    """Extract key fields from a Gamma market dict."""
    outcomes = _parse_json_field(market.get("outcomes"))
    prices = _parse_json_field(market.get("outcomePrices"))
    clob_ids = _parse_json_field(market.get("clobTokenIds"))

    result = {
        "id": market.get("id") or market.get("conditionId") or market.get("condition_id"),
        "question": market.get("question"),
        "slug": market.get("slug"),
        "outcomes": outcomes,
        "prices": prices,
        "clobTokenIds": clob_ids,
        "volume24hr": market.get("volume24hr"),
        "liquidity": market.get("liquidity"),
        "active": market.get("active"),
    }
    # Include neg_risk if present
    if market.get("neg_risk") is not None:
        result["neg_risk"] = market.get("neg_risk")
    return result


# ── Market Discovery (Gamma API) ─────────────────────────────────────────────


class PolymarketSearchTool(BaseTool):
    """Search Polymarket prediction markets by keyword."""

    @property
    def name(self) -> str:
        return "polymarket_search"

    @property
    def description(self) -> str:
        return """Search Polymarket prediction markets by keyword.

Returns matching markets and events with questions, outcomes, prices, and volume.

Parameters:
- query: Search keyword (e.g. "bitcoin", "election", "Trump")

Returns: List of matching markets with question, outcomes, probabilities, volume"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keyword",
                },
            },
            "required": ["query"],
        }

    async def execute(self, ctx: ToolContext, query: str = "", **kwargs) -> ToolResult:
        if not query:
            return ToolResult(success=False, error="'query' is required")
        try:
            client = _get_client()
            data = await client.search(query)

            # Format results — search may return markets list or mixed data
            if isinstance(data, list):
                markets = [_format_market(m) for m in data[:20]]
            elif isinstance(data, dict):
                # May have separate markets/events keys
                markets = []
                for m in data.get("markets", data.get("data", [])):
                    markets.append(_format_market(m))
                markets = markets[:20]
            else:
                markets = data

            return ToolResult(success=True, output={"results": markets, "count": len(markets) if isinstance(markets, list) else 0})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PolymarketMarketsTool(BaseTool):
    """Browse and filter Polymarket prediction markets."""

    @property
    def name(self) -> str:
        return "polymarket_markets"

    @property
    def description(self) -> str:
        return """Browse and filter Polymarket prediction markets.

Parameters:
- status: "active" (default), "closed", or "all"
- sort: "volume" (default), "liquidity", or "newest"
- tag: Category slug to filter by (use polymarket_tags to see options)
- limit: Number of results, 1-25 (default 10)

Returns: List of markets with question, outcomes, prices, volume, liquidity"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter: active (default), closed, or all",
                    "enum": ["active", "closed", "all"],
                },
                "sort": {
                    "type": "string",
                    "description": "Sort by: volume (default), liquidity, or newest",
                    "enum": ["volume", "liquidity", "newest"],
                },
                "tag": {
                    "type": "string",
                    "description": "Category slug to filter by",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of results (1-25, default 10)",
                },
            },
        }

    async def execute(
        self, ctx: ToolContext,
        status: str = "active",
        sort: str = "volume",
        tag: str = "",
        limit: int = 10,
        **kwargs,
    ) -> ToolResult:
        try:
            # Map sort param to Gamma API order field
            sort_map = {
                "volume": "volume24hr",
                "liquidity": "liquidity",
                "newest": "created_at",
            }
            order = sort_map.get(sort, "volume24hr")

            # Map status to active/closed bools
            active = None
            closed = None
            if status == "active":
                active = True
            elif status == "closed":
                closed = True

            limit = max(1, min(25, limit))

            client = _get_client()

            # Resolve tag slug to tag_id if provided
            tag_id = None
            if tag:
                tags = await client.get_tags()
                if isinstance(tags, list):
                    for t in tags:
                        if t.get("slug") == tag or t.get("label", "").lower() == tag.lower():
                            tag_id = t.get("id")
                            break

            data = await client.get_markets(
                active=active,
                closed=closed,
                limit=limit,
                order=order,
                ascending=(sort == "newest"),
                tag_id=tag_id,
            )

            markets = []
            if isinstance(data, list):
                markets = [_format_market(m) for m in data]
            elif isinstance(data, dict):
                for m in data.get("data", data.get("markets", [])):
                    markets.append(_format_market(m))

            return ToolResult(success=True, output={"markets": markets, "count": len(markets)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PolymarketEventTool(BaseTool):
    """Get a Polymarket event with all child markets."""

    @property
    def name(self) -> str:
        return "polymarket_event"

    @property
    def description(self) -> str:
        return """Get a Polymarket event with all its child markets.

An event groups related markets (e.g. "2024 Election" has markets for each state/race).

Parameters:
- event_id: Event ID (from search or markets results)

Returns: Event title, description, and list of child markets with outcomes and prices"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "Event ID",
                },
            },
            "required": ["event_id"],
        }

    async def execute(self, ctx: ToolContext, event_id: str = "", **kwargs) -> ToolResult:
        if not event_id:
            return ToolResult(success=False, error="'event_id' is required")
        try:
            client = _get_client()
            data = await client.get_event(event_id)

            if not data:
                return ToolResult(success=False, error=f"Event not found: {event_id}")

            # Format child markets
            child_markets = []
            for m in data.get("markets", []):
                child_markets.append(_format_market(m))

            result = {
                "id": data.get("id"),
                "title": data.get("title"),
                "description": data.get("description"),
                "slug": data.get("slug"),
                "markets": child_markets,
                "market_count": len(child_markets),
            }
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PolymarketTagsTool(BaseTool):
    """List Polymarket market categories."""

    @property
    def name(self) -> str:
        return "polymarket_tags"

    @property
    def description(self) -> str:
        return """List all Polymarket market categories/tags.

Use these to filter markets with polymarket_markets(tag="...").

Returns: List of categories with id, label, and slug"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {},
        }

    async def execute(self, ctx: ToolContext, **kwargs) -> ToolResult:
        try:
            client = _get_client()
            data = await client.get_tags()

            tags = []
            if isinstance(data, list):
                for t in data:
                    tags.append({
                        "id": t.get("id"),
                        "label": t.get("label"),
                        "slug": t.get("slug"),
                    })

            return ToolResult(success=True, output={"tags": tags, "count": len(tags)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Price & Trading Data (CLOB API) ──────────────────────────────────────────


class PolymarketPriceTool(BaseTool):
    """Get live price/probability for a Polymarket market."""

    @property
    def name(self) -> str:
        return "polymarket_price"

    @property
    def description(self) -> str:
        return """Get live price/probability for a Polymarket prediction market.

Prices represent probabilities: $0.75 = 75% chance. Accepts a market slug or condition ID.

Parameters:
- market_id: Market slug (e.g. "will-bitcoin-reach-100k-2025") or condition ID

Returns: Market question, each outcome with probability %, volume, liquidity, neg_risk flag"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "market_id": {
                    "type": "string",
                    "description": "Market slug or condition ID",
                },
            },
            "required": ["market_id"],
        }

    async def execute(self, ctx: ToolContext, market_id: str = "", **kwargs) -> ToolResult:
        if not market_id:
            return ToolResult(success=False, error="'market_id' is required")
        try:
            client = _get_client()

            # Try slug first, fallback to condition ID
            market = None
            try:
                market = await client.get_market_by_slug(market_id)
            except Exception:
                pass

            if not market or (isinstance(market, list) and not market):
                try:
                    market = await client.get_market_by_id(market_id)
                except Exception:
                    pass

            if not market:
                return ToolResult(success=False, error=f"Market not found: {market_id}")

            outcomes = _parse_json_field(market.get("outcomes"))
            clob_ids = _parse_json_field(market.get("clobTokenIds"))
            static_prices = _parse_json_field(market.get("outcomePrices"))

            # Try to get live CLOB midpoint prices
            live_prices = []
            if clob_ids and isinstance(clob_ids, list):
                for token_id in clob_ids:
                    try:
                        mid = await client.get_midpoint(token_id)
                        price = mid.get("mid") if isinstance(mid, dict) else mid
                        live_prices.append(float(price) if price else None)
                    except Exception:
                        live_prices.append(None)

            # Build outcome list
            outcome_list = []
            if outcomes and isinstance(outcomes, list):
                for i, outcome_name in enumerate(outcomes):
                    price = None
                    # Prefer live CLOB price
                    if i < len(live_prices) and live_prices[i] is not None:
                        price = live_prices[i]
                    elif static_prices and isinstance(static_prices, list) and i < len(static_prices):
                        try:
                            price = float(static_prices[i])
                        except (ValueError, TypeError):
                            price = None

                    entry = {"outcome": outcome_name}
                    if price is not None:
                        entry["price"] = round(price, 4)
                        entry["probability"] = f"{price * 100:.1f}%"
                    if clob_ids and isinstance(clob_ids, list) and i < len(clob_ids):
                        entry["token_id"] = clob_ids[i]
                    outcome_list.append(entry)

            result = {
                "id": market.get("id") or market.get("conditionId") or market.get("condition_id"),
                "question": market.get("question"),
                "slug": market.get("slug"),
                "outcomes": outcome_list,
                "volume24hr": market.get("volume24hr"),
                "liquidity": market.get("liquidity"),
                "active": market.get("active"),
            }
            if market.get("neg_risk") is not None:
                result["neg_risk"] = market.get("neg_risk")

            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PolymarketBookTool(BaseTool):
    """Get orderbook depth for a Polymarket token."""

    @property
    def name(self) -> str:
        return "polymarket_book"

    @property
    def description(self) -> str:
        return """Get orderbook depth for a Polymarket CLOB token.

Shows bid/ask levels, spread, and liquidity. Use token_id from polymarket_price results.

Parameters:
- token_id: CLOB token ID (from polymarket_price output)

Returns: Top 10 bid/ask levels, best bid, best ask, spread, mid price"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "token_id": {
                    "type": "string",
                    "description": "CLOB token ID",
                },
            },
            "required": ["token_id"],
        }

    async def execute(self, ctx: ToolContext, token_id: str = "", **kwargs) -> ToolResult:
        if not token_id:
            return ToolResult(success=False, error="'token_id' is required")
        try:
            client = _get_client()
            data = await client.get_book(token_id)

            bids = data.get("bids", [])
            asks = data.get("asks", [])

            # Take top 10
            top_bids = bids[:10] if isinstance(bids, list) else []
            top_asks = asks[:10] if isinstance(asks, list) else []

            # Calculate spread
            best_bid = float(top_bids[0].get("price", 0)) if top_bids else 0
            best_ask = float(top_asks[0].get("price", 0)) if top_asks else 0
            spread = round(best_ask - best_bid, 4) if best_bid and best_ask else None
            mid = round((best_bid + best_ask) / 2, 4) if best_bid and best_ask else None

            result = {
                "token_id": token_id,
                "bids": top_bids,
                "asks": top_asks,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "spread": spread,
                "mid_price": mid,
            }
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PolymarketHistoryTool(BaseTool):
    """Get price history timeseries for a Polymarket token."""

    @property
    def name(self) -> str:
        return "polymarket_history"

    @property
    def description(self) -> str:
        return """Get price history timeseries for a Polymarket CLOB token.

Parameters:
- token_id: CLOB token ID (from polymarket_price output)
- interval: Time interval — "1m" (1 minute), "1h" (1 hour, default), "1d" (1 day)
- fidelity: Minutes between data points (optional, overrides interval)

Returns: Array of {timestamp, price} data points"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "token_id": {
                    "type": "string",
                    "description": "CLOB token ID",
                },
                "interval": {
                    "type": "string",
                    "description": "Time interval: 1m, 1h (default), or 1d",
                },
                "fidelity": {
                    "type": "integer",
                    "description": "Minutes between data points (overrides interval)",
                },
            },
            "required": ["token_id"],
        }

    async def execute(
        self, ctx: ToolContext,
        token_id: str = "",
        interval: str = "1h",
        fidelity: int = 0,
        **kwargs,
    ) -> ToolResult:
        if not token_id:
            return ToolResult(success=False, error="'token_id' is required")
        try:
            # Map interval to fidelity (minutes) if not explicitly set
            if not fidelity:
                fidelity_map = {"1m": 1, "1h": 60, "1d": 1440}
                fidelity = fidelity_map.get(interval, 60)

            client = _get_client()
            data = await client.get_prices_history(token_id, fidelity=fidelity)

            # Normalize to consistent format
            points = []
            if isinstance(data, dict):
                history = data.get("history", [])
            elif isinstance(data, list):
                history = data
            else:
                history = []

            for pt in history:
                points.append({
                    "timestamp": pt.get("t"),
                    "price": pt.get("p"),
                })

            return ToolResult(success=True, output={"token_id": token_id, "points": points, "count": len(points)})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PolymarketTradesTool(BaseTool):
    """Get recent trades for a Polymarket market."""

    @property
    def name(self) -> str:
        return "polymarket_trades"

    @property
    def description(self) -> str:
        return """Get recent trades for a Polymarket prediction market.

Parameters:
- condition_id: Market condition ID (from search/markets/price results)
- limit: Number of trades (default 20, max 50)

Returns: List of recent trades with price, size, side, timestamp"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "condition_id": {
                    "type": "string",
                    "description": "Market condition ID",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of trades (default 20, max 50)",
                },
            },
            "required": ["condition_id"],
        }

    async def execute(
        self, ctx: ToolContext,
        condition_id: str = "",
        limit: int = 20,
        **kwargs,
    ) -> ToolResult:
        if not condition_id:
            return ToolResult(success=False, error="'condition_id' is required")
        try:
            limit = max(1, min(50, limit))
            client = _get_client()
            data = await client.get_trades(condition_id, limit=limit)

            trades = data if isinstance(data, list) else data.get("data", data.get("trades", []))

            return ToolResult(success=True, output={"trades": trades, "count": len(trades) if isinstance(trades, list) else 0})
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── Community & Analytics (Data API) ─────────────────────────────────────────


class PolymarketLeaderboardTool(BaseTool):
    """Get top Polymarket traders leaderboard."""

    @property
    def name(self) -> str:
        return "polymarket_leaderboard"

    @property
    def description(self) -> str:
        return """Get top Polymarket traders ranked by profit.

Parameters:
- window: Time window — "1d", "7d", "30d", or "all" (default)
- limit: Number of traders (default 10, max 25)

Returns: Ranked list of traders with profit, volume, number of trades"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "window": {
                    "type": "string",
                    "description": "Time window: 1d, 7d, 30d, or all (default)",
                    "enum": ["1d", "7d", "30d", "all"],
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of traders (default 10, max 25)",
                },
            },
        }

    async def execute(
        self, ctx: ToolContext,
        window: str = "all",
        limit: int = 10,
        **kwargs,
    ) -> ToolResult:
        try:
            limit = max(1, min(25, limit))
            client = _get_client()
            data = await client.get_leaderboard(window=window, limit=limit)

            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PolymarketHoldersTool(BaseTool):
    """Get top holders of a Polymarket token."""

    @property
    def name(self) -> str:
        return "polymarket_holders"

    @property
    def description(self) -> str:
        return """Get top holders of a Polymarket market token.

Parameters:
- token_id: CLOB token ID (from polymarket_price output)
- limit: Number of holders (default 10, max 20)

Returns: List of top holders with address and position size"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "token_id": {
                    "type": "string",
                    "description": "CLOB token ID",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of holders (default 10, max 20)",
                },
            },
            "required": ["token_id"],
        }

    async def execute(
        self, ctx: ToolContext,
        token_id: str = "",
        limit: int = 10,
        **kwargs,
    ) -> ToolResult:
        if not token_id:
            return ToolResult(success=False, error="'token_id' is required")
        try:
            limit = max(1, min(20, limit))
            client = _get_client()
            data = await client.get_holders(token_id, limit=limit)

            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
