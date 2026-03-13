"""
Orderly Network API Client — async HTTP client for public, private, and trading endpoints.

Public endpoints: unauthenticated GET requests for market data.
Private endpoints: Ed25519-signed requests for account data and trading.

Symbol resolution: accepts "BTC" and auto-expands to "PERP_BTC_USDC".
Full symbols (e.g. "PERP_BTC_USDC", "SPOT_ETH_USDC") are also accepted.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import aiohttp

from . import signing

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "https://api.orderly.org"


class OrderlyClient:
    """
    Async Orderly Network client.

    - Public methods: GET requests (no auth)
    - Private methods: Ed25519-signed requests
    - Trading methods: Ed25519-signed POST/PUT/DELETE
    """

    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url or os.environ.get(
            "ORDERLY_API_URL", DEFAULT_API_URL
        )
        self._ready = False
        # Cached futures info
        self._futures_info: Optional[Dict[str, dict]] = None

    # ── Internal helpers ─────────────────────────────────────────────────

    async def _ensure_ready(self) -> None:
        """Lazy init: register with Orderly on first private API call."""
        if not self._ready:
            await signing.ensure_registered()
            self._ready = True

    async def _public_get(self, path: str, params: Optional[dict] = None) -> Any:
        """Unauthenticated GET request to Orderly public API."""
        url = f"{self.api_url}{path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    raise Exception(f"Orderly API {resp.status}: {body}")
                data = await resp.json()
                if not data.get("success", True):
                    raise Exception(f"Orderly error: {data.get('message', data)}")
                return data.get("data", data)

    async def _private_request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        body: Optional[dict] = None,
    ) -> Any:
        """Ed25519-signed request to Orderly private API."""
        await self._ensure_ready()

        body_str = json.dumps(body) if body else ""
        headers = signing.build_auth_headers(method.upper(), path, body_str)
        headers["Content-Type"] = "application/json"

        url = f"{self.api_url}{path}"
        async with aiohttp.ClientSession() as session:
            kwargs = {
                "headers": headers,
                "timeout": aiohttp.ClientTimeout(total=15),
            }
            if method.upper() == "GET":
                kwargs["params"] = params
            elif body:
                kwargs["data"] = body_str

            async with session.request(method.upper(), url, **kwargs) as resp:
                if resp.status >= 400:
                    resp_body = await resp.text()
                    logger.error(f"Orderly private API error: {method.upper()} {path} → {resp.status}: {resp_body}")
                    raise Exception(f"Orderly API {resp.status}: {resp_body}")
                data = await resp.json()
                if not data.get("success", True):
                    logger.error(f"Orderly business error: {method.upper()} {path} → {data}")
                    raise Exception(f"Orderly error: {data.get('message', data)}")
                return data.get("data", data)

    # ── Symbol Resolution ────────────────────────────────────────────────

    async def _ensure_futures_info(self) -> None:
        """Cache futures instrument metadata."""
        if self._futures_info is not None:
            return
        data = await self._public_get("/v1/public/futures")
        self._futures_info = {}
        rows = data if isinstance(data, list) else data.get("rows", data)
        if isinstance(rows, list):
            for item in rows:
                symbol = item.get("symbol", "")
                self._futures_info[symbol] = item

    def _resolve_symbol(self, coin_or_symbol: str, market_type: str = "perp") -> str:
        """
        Resolve a coin name to an Orderly symbol.

        Accepts:
        - "BTC" → "PERP_BTC_USDC" (perp) or "SPOT_BTC_USDC" (spot)
        - "PERP_BTC_USDC" → passed through as-is
        - "SPOT_ETH_USDC" → passed through as-is
        """
        upper = coin_or_symbol.upper()
        if upper.startswith("PERP_") or upper.startswith("SPOT_"):
            return upper
        if market_type == "spot":
            return f"SPOT_{upper}_USDC"
        return f"PERP_{upper}_USDC"

    # ── Public Methods (no auth) ─────────────────────────────────────────

    async def get_system_info(self) -> dict:
        """Get system maintenance status."""
        return await self._public_get("/v1/public/info")

    async def get_futures(self, symbol: Optional[str] = None) -> Any:
        """Get futures instrument info."""
        if symbol:
            return await self._public_get(f"/v1/public/futures/{symbol}")
        return await self._public_get("/v1/public/futures")

    async def get_funding_rate(self, symbol: str) -> dict:
        """Get current funding rate for a symbol."""
        return await self._public_get(f"/v1/public/funding_rate/{symbol}")

    async def get_funding_rate_history(
        self, symbol: str, limit: int = 24, page: int = 1
    ) -> Any:
        """Get funding rate history."""
        return await self._public_get(
            f"/v1/public/funding_rate_history",
            params={"symbol": symbol, "limit": limit, "page": page},
        )

    async def get_volume_stats(self) -> dict:
        """Get volume statistics."""
        return await self._public_get("/v1/public/volume/stats")

    async def get_orderbook(self, symbol: str, max_level: int = 20) -> dict:
        """Get orderbook snapshot."""
        return await self._public_get(
            f"/v1/orderbook/{symbol}",
            params={"max_level": max_level},
        )

    async def get_kline(
        self,
        symbol: str,
        kline_type: str = "1h",
        limit: int = 100,
    ) -> Any:
        """Get OHLCV candlestick data."""
        return await self._public_get(
            "/v1/kline",
            params={"symbol": symbol, "type": kline_type, "limit": limit},
        )

    async def get_market_trades(self, symbol: str, limit: int = 50) -> Any:
        """Get recent market trades."""
        return await self._public_get(
            f"/v1/public/market_trades",
            params={"symbol": symbol, "limit": limit},
        )

    async def get_chain_info(self) -> dict:
        """Get chain and broker configuration."""
        return await self._public_get("/v1/public/chain_info")

    # ── Private Methods (Ed25519 auth) ───────────────────────────────────

    async def get_account_info(self) -> dict:
        """Get account info (fees, tier, etc.)."""
        return await self._private_request("GET", "/v1/client/info")

    async def get_holdings(self) -> Any:
        """Get asset balances (holdings)."""
        return await self._private_request("GET", "/v1/client/holding")

    async def get_positions(self) -> Any:
        """Get open positions."""
        return await self._private_request("GET", "/v1/positions")

    async def get_orders(
        self,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> Any:
        """Get orders (open or historical)."""
        params = {"limit": limit}
        if symbol:
            params["symbol"] = symbol
        if status:
            params["status"] = status
        return await self._private_request("GET", "/v1/orders", params=params)

    async def get_trades(
        self,
        symbol: Optional[str] = None,
        limit: int = 50,
    ) -> Any:
        """Get trade/fill history."""
        params = {"limit": limit}
        if symbol:
            params["symbol"] = symbol
        return await self._private_request("GET", "/v1/trades", params=params)

    async def get_liquidations(self, limit: int = 50) -> Any:
        """Get liquidation history."""
        return await self._private_request(
            "GET", "/v1/liquidations", params={"limit": limit}
        )

    # ── Trading Methods (Ed25519 auth) ───────────────────────────────────

    async def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        order_quantity: Optional[float] = None,
        order_price: Optional[float] = None,
        reduce_only: bool = False,
        visible_quantity: Optional[float] = None,
        order_tag: str = "starchild",
    ) -> dict:
        """
        Create an order.

        Args:
            symbol: Orderly symbol (e.g. "PERP_BTC_USDC")
            side: "BUY" or "SELL"
            order_type: "LIMIT", "MARKET", "IOC", "FOK", "POST_ONLY"
            order_quantity: Size in base asset
            order_price: Limit price (required for LIMIT, IOC, FOK, POST_ONLY)
            reduce_only: If True, only reduces position
            visible_quantity: Iceberg order visible size
            order_tag: Tag for order tracking
        """
        broker_id = signing._get_broker_id()

        body = {
            "symbol": symbol,
            "side": side.upper(),
            "order_type": order_type.upper(),
            "broker_id": broker_id,
            "order_tag": order_tag,
        }

        if order_quantity is not None:
            body["order_quantity"] = order_quantity
        if order_price is not None:
            body["order_price"] = order_price
        if reduce_only:
            body["reduce_only"] = True
        if visible_quantity is not None:
            body["visible_quantity"] = visible_quantity

        return await self._private_request("POST", "/v1/order", body=body)

    async def modify_order(
        self,
        order_id: int,
        symbol: str,
        side: str,
        order_type: str,
        order_quantity: Optional[float] = None,
        order_price: Optional[float] = None,
    ) -> dict:
        """Modify an existing order."""
        body = {
            "order_id": order_id,
            "symbol": symbol,
            "side": side.upper(),
            "order_type": order_type.upper(),
        }
        if order_quantity is not None:
            body["order_quantity"] = order_quantity
        if order_price is not None:
            body["order_price"] = order_price

        return await self._private_request("PUT", "/v1/order", body=body)

    async def cancel_order(self, symbol: str, order_id: int) -> dict:
        """Cancel an order by ID."""
        return await self._private_request(
            "DELETE",
            f"/v1/order?symbol={symbol}&order_id={order_id}",
        )

    async def cancel_all_orders(self, symbol: Optional[str] = None) -> dict:
        """Cancel all orders, optionally filtered by symbol."""
        body = {}
        if symbol:
            body["symbol"] = symbol
        return await self._private_request("DELETE", "/v1/orders", body=body or None)

    async def update_leverage(self, symbol: str, leverage: int) -> dict:
        """Update leverage for a symbol."""
        return await self._private_request(
            "POST",
            "/v1/client/leverage",
            body={"symbol": symbol, "leverage": leverage},
        )


# ── Module-level singleton ───────────────────────────────────────────────────

_client: Optional[OrderlyClient] = None


def _get_client() -> OrderlyClient:
    global _client
    if _client is None:
        _client = OrderlyClient()
    return _client
