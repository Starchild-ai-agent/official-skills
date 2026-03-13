"""
Twelve Data API Client — Async HTTP client for stocks and forex market data.

Supports stocks and forex (FX) data via REST API.
Configured for Pro subscription tier endpoints only.

Environment Variables:
- TWELVEDATA_API_KEY: Twelve Data API key (required, get from twelvedata.com)

Supported Endpoints (Pro Tier):
- Time series data (price, quote, EOD, historical OHLCV)
- Reference data (search, stocks list, forex pairs, exchanges)
- Batch requests (multiple symbols)

Not Included (Requires Grow/Pro+/Ultra/Enterprise):
- Fundamental data (financials, statistics, earnings)
- Executive data (key executives, compensation)

API Documentation: https://twelvedata.com/docs
"""

import logging
import os
from typing import Any, Dict, Optional, List

import aiohttp

from core.http_client import get_aiohttp_proxy_kwargs

logger = logging.getLogger(__name__)

# API Configuration
BASE_URL = "https://api.twelvedata.com"

# Supported intervals for time series
INTERVALS = ["1min", "5min", "15min", "30min", "45min", "1h", "2h", "4h", "8h", "1day", "1week", "1month"]


class TwelveDataClient:
    """
    Async Twelve Data client for stocks and forex.

    All methods call the Twelve Data REST API with API key authentication.
    Supports both header and query parameter authentication methods.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("TWELVEDATA_API_KEY", "")
        if not self.api_key:
            logger.warning("TWELVEDATA_API_KEY not set — API calls will fail")

    # ── Internal helpers ─────────────────────────────────────────────────

    async def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """GET request to Twelve Data API with API key auth."""
        url = f"{BASE_URL}/{endpoint}"

        # Add API key to params (can also use header: Authorization: apikey YOUR_KEY)
        if params is None:
            params = {}
        params["apikey"] = self.api_key

        headers = {
            "Accept": "application/json",
        }

        proxy_kw = get_aiohttp_proxy_kwargs(url)
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30),
                **proxy_kw,
            ) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    raise Exception(f"Twelve Data API {resp.status}: {body}")
                return await resp.json()

    # ── Time Series & Price Data ─────────────────────────────────────────

    async def get_time_series(
        self,
        symbol: str,
        interval: str = "1day",
        outputsize: int = 30,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict:
        """
        Get historical OHLCV time series data.

        Args:
            symbol: Stock symbol (AAPL, MSFT) or forex pair (EUR/USD, GBP/JPY)
            interval: Time interval (1min, 5min, 15min, 30min, 1h, 4h, 1day, 1week, 1month)
            outputsize: Number of data points to return (1-5000). Default 30.
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)

        Returns:
            dict with meta and values (OHLCV data)
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "outputsize": outputsize,
        }

        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        return await self._get("time_series", params)

    async def get_quote(self, symbol: str) -> dict:
        """
        Get real-time quote for a stock or forex pair.

        Args:
            symbol: Stock symbol (AAPL) or forex pair (EUR/USD)

        Returns:
            dict with current price, open, high, low, volume, change, etc.
        """
        params = {"symbol": symbol}
        return await self._get("quote", params)

    async def get_price(self, symbol: str) -> dict:
        """
        Get latest trading price.

        Args:
            symbol: Stock symbol or forex pair

        Returns:
            dict with price value
        """
        params = {"symbol": symbol}
        return await self._get("price", params)

    async def get_eod(self, symbol: str, date: Optional[str] = None) -> dict:
        """
        Get end-of-day price.

        Args:
            symbol: Stock symbol or forex pair
            date: Specific date in YYYY-MM-DD format (optional, defaults to latest)

        Returns:
            dict with EOD price data
        """
        params = {"symbol": symbol}
        if date:
            params["date"] = date
        return await self._get("eod", params)

    # ── Reference Data ───────────────────────────────────────────────────

    async def search_symbol(self, query: str) -> dict:
        """
        Search for stocks or forex pairs by name or symbol.

        Args:
            query: Search query (company name, stock symbol, or currency pair)

        Returns:
            dict with search results array
        """
        params = {"symbol": query}
        return await self._get("symbol_search", params)

    async def get_stocks(
        self,
        exchange: Optional[str] = None,
        country: Optional[str] = None,
    ) -> dict:
        """
        Get list of available stocks.

        Args:
            exchange: Filter by exchange (NASDAQ, NYSE, etc.)
            country: Filter by country code (US, GB, etc.)

        Returns:
            dict with stocks array
        """
        params = {}
        if exchange:
            params["exchange"] = exchange
        if country:
            params["country"] = country
        return await self._get("stocks", params)

    async def get_forex_pairs(self) -> dict:
        """
        Get list of available forex pairs.

        Returns:
            dict with forex pairs array
        """
        return await self._get("forex_pairs")

    async def get_exchanges(self) -> dict:
        """
        Get list of supported exchanges.

        Returns:
            dict with exchanges array
        """
        return await self._get("exchanges")

    # ── Batch Requests ───────────────────────────────────────────────────

    async def get_quote_batch(self, symbols: List[str]) -> dict:
        """
        Get quotes for multiple symbols in one request.

        Args:
            symbols: List of stock symbols or forex pairs (max 120)

        Returns:
            dict with quotes for each symbol
        """
        if len(symbols) > 120:
            logger.warning(f"Maximum 120 symbols per batch request. Truncating from {len(symbols)} to 120.")
            symbols = symbols[:120]

        params = {"symbol": ",".join(symbols)}
        return await self._get("quote", params)

    async def get_price_batch(self, symbols: List[str]) -> dict:
        """
        Get prices for multiple symbols in one request.

        Args:
            symbols: List of stock symbols or forex pairs (max 120)

        Returns:
            dict with prices for each symbol
        """
        if len(symbols) > 120:
            logger.warning(f"Maximum 120 symbols per batch request. Truncating from {len(symbols)} to 120.")
            symbols = symbols[:120]

        params = {"symbol": ",".join(symbols)}
        return await self._get("price", params)
