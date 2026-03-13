"""
Polymarket API Client — async HTTP client for Polymarket prediction markets.

Uses three public APIs (no auth required):
- Gamma API: market discovery, categories, search
- CLOB API: live prices, orderbooks, timeseries, trades
- Data API: leaderboard, holders

No API key needed — all endpoints are public.
"""

import logging
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"
DATA_API = "https://data-api.polymarket.com"


class PolymarketClient:
    """
    Async Polymarket client.

    All methods call public Polymarket APIs — no authentication required.
    """

    # ── Internal helpers ─────────────────────────────────────────────────

    async def _gamma_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """GET request to Gamma API."""
        url = f"{GAMMA_API}{path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    raise Exception(f"Gamma API {resp.status}: {body}")
                return await resp.json()

    async def _clob_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """GET request to CLOB API."""
        url = f"{CLOB_API}{path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    raise Exception(f"CLOB API {resp.status}: {body}")
                return await resp.json()

    async def _data_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """GET request to Data API."""
        url = f"{DATA_API}{path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    raise Exception(f"Data API {resp.status}: {body}")
                return await resp.json()

    # ── Gamma API (Market Discovery) ─────────────────────────────────────

    async def search(self, query: str) -> Any:
        """
        Native keyword search across markets and events.

        Args:
            query: Search keyword

        Returns: List of matching markets and events
        """
        return await self._gamma_get("/search", {"query": query})

    async def get_markets(
        self,
        active: Optional[bool] = None,
        closed: Optional[bool] = None,
        limit: int = 10,
        offset: int = 0,
        order: Optional[str] = None,
        ascending: bool = False,
        tag_id: Optional[int] = None,
    ) -> List[Dict]:
        """
        Browse/filter markets.

        Args:
            active: Filter by active status
            closed: Filter by closed status
            limit: Number of results (max 100)
            offset: Pagination offset
            order: Sort field (e.g. volume24hr, liquidity, created_at)
            ascending: Sort direction
            tag_id: Filter by category tag ID

        Returns: List of market dicts
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if active is not None:
            params["active"] = str(active).lower()
        if closed is not None:
            params["closed"] = str(closed).lower()
        if order:
            params["order"] = order
        if ascending:
            params["ascending"] = "true"
        if tag_id is not None:
            params["tag_id"] = tag_id
        return await self._gamma_get("/markets", params)

    async def get_market_by_id(self, market_id: str) -> Optional[Dict]:
        """
        Get a single market by condition ID.

        Args:
            market_id: Market condition ID

        Returns: Market dict or None
        """
        results = await self._gamma_get("/markets", {"id": market_id})
        if isinstance(results, list) and results:
            return results[0]
        return results

    async def get_market_by_slug(self, slug: str) -> Optional[Dict]:
        """
        Get a single market by slug.

        Args:
            slug: Market URL slug

        Returns: Market dict or None
        """
        results = await self._gamma_get("/markets", {"slug": slug})
        if isinstance(results, list) and results:
            return results[0]
        return results

    async def get_event(self, event_id: str) -> Dict:
        """
        Get an event with all child markets.

        Args:
            event_id: Event ID

        Returns: Event dict with child markets
        """
        return await self._gamma_get(f"/events/{event_id}")

    async def get_tags(self) -> List[Dict]:
        """
        Get all market categories/tags.

        Returns: List of {id, label, slug} dicts
        """
        return await self._gamma_get("/tags")

    # ── CLOB API (Price & Trading Data) ──────────────────────────────────

    async def get_midpoint(self, token_id: str) -> Dict:
        """
        Get midpoint price for a CLOB token.

        Args:
            token_id: CLOB token ID

        Returns: Dict with mid price
        """
        return await self._clob_get("/midpoint", {"token_id": token_id})

    async def get_book(self, token_id: str) -> Dict:
        """
        Get full orderbook for a CLOB token.

        Args:
            token_id: CLOB token ID

        Returns: Dict with bids and asks
        """
        return await self._clob_get("/book", {"token_id": token_id})

    async def get_prices_history(
        self,
        token_id: str,
        interval: Optional[str] = None,
        fidelity: Optional[int] = None,
    ) -> List[Dict]:
        """
        Get price timeseries for a CLOB token.

        Args:
            token_id: CLOB token ID
            interval: Time interval (e.g. "max", "1w", "1d")
            fidelity: Minutes between data points

        Returns: List of {t, p} data points
        """
        params: Dict[str, Any] = {"token_id": token_id}
        if interval:
            params["interval"] = interval
        if fidelity is not None:
            params["fidelity"] = fidelity
        return await self._clob_get("/prices-history", params)

    async def get_trades(
        self,
        condition_id: str,
        maker: Optional[str] = None,
        limit: int = 20,
    ) -> Any:
        """
        Get public trade history for a market.

        Args:
            condition_id: Market condition ID
            maker: Filter by maker address (optional)
            limit: Number of results

        Returns: List of trade dicts
        """
        params: Dict[str, Any] = {"condition_id": condition_id, "limit": limit}
        if maker:
            params["maker"] = maker
        return await self._clob_get("/data/trades", params)

    # ── Data API (Analytics) ─────────────────────────────────────────────

    async def get_leaderboard(
        self,
        window: str = "all",
        limit: int = 10,
        offset: int = 0,
    ) -> Any:
        """
        Get top traders leaderboard.

        Args:
            window: Time window ("1d", "7d", "30d", "all")
            limit: Number of results
            offset: Pagination offset

        Returns: Leaderboard data
        """
        params = {"window": window, "limit": limit, "offset": offset}
        return await self._data_get("/v1/leaderboard", params)

    async def get_holders(self, token_id: str, limit: int = 10) -> Any:
        """
        Get top holders of a market token.

        Args:
            token_id: CLOB token ID
            limit: Number of results

        Returns: List of holder dicts
        """
        params = {"token_id": token_id, "limit": limit}
        return await self._data_get("/holders", params)
