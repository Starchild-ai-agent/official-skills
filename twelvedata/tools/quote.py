"""
Twelve Data Quote Tools — Real-time market quotes for stocks and forex.

Provides tools for fetching current market data including price, volume, and 52-week metrics.
"""

import logging
from typing import Optional, List

from core.tool import BaseTool, ToolContext, ToolResult
from .client import TwelveDataClient

logger = logging.getLogger(__name__)

# Singleton client instance
_client: Optional[TwelveDataClient] = None


def _get_client() -> TwelveDataClient:
    """Get or create singleton client instance."""
    global _client
    if _client is None:
        _client = TwelveDataClient()
    return _client


class TwelveDataQuoteTool(BaseTool):
    """Get real-time quote for a stock or forex pair."""

    @property
    def name(self) -> str:
        return "twelvedata_quote"

    @property
    def description(self) -> str:
        return """Get real-time market quote for a stock or forex pair.

Returns comprehensive current market data including:
- Current price, open, high, low, close
- Volume and trading data
- Price change and percent change
- 52-week high and low
- Previous close and timestamp

Use this for current market analysis and live monitoring.

Parameters:
- symbol: Stock symbol (e.g., AAPL, MSFT, TSLA) or forex pair (e.g., EUR/USD, GBP/JPY)

Returns: Real-time quote with all current market metrics"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol (AAPL, MSFT) or forex pair (EUR/USD, GBP/JPY)",
                },
            },
            "required": ["symbol"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        symbol: str = "",
        **kwargs,
    ) -> ToolResult:
        if not symbol:
            return ToolResult(success=False, error="'symbol' is required")

        try:
            client = _get_client()
            data = await client.get_quote(symbol=symbol)

            # Check for API errors
            if "status" in data and data["status"] == "error":
                return ToolResult(
                    success=False,
                    error=f"API Error: {data.get('message', 'Unknown error')}",
                )

            return ToolResult(success=True, output=data)
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg:
                return ToolResult(
                    success=False,
                    error="Invalid API key. Set TWELVEDATA_API_KEY environment variable.",
                )
            elif "429" in error_msg:
                return ToolResult(
                    success=False,
                    error="Rate limit exceeded. Wait a moment and try again.",
                )
            return ToolResult(success=False, error=error_msg)


class TwelveDataQuoteBatchTool(BaseTool):
    """Get real-time quotes for multiple stocks or forex pairs at once."""

    @property
    def name(self) -> str:
        return "twelvedata_quote_batch"

    @property
    def description(self) -> str:
        return """Get real-time quotes for multiple stocks or forex pairs in a single API call.

Efficient way to fetch market data for multiple symbols simultaneously. Maximum 120 symbols per request.

Parameters:
- symbols: Array of stock symbols or forex pairs (max 120)

Returns: Quotes for all requested symbols"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of stock symbols or forex pairs (max 120)",
                    "minItems": 1,
                    "maxItems": 120,
                },
            },
            "required": ["symbols"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        symbols: List[str] = None,
        **kwargs,
    ) -> ToolResult:
        if not symbols or len(symbols) == 0:
            return ToolResult(success=False, error="'symbols' array is required and must not be empty")

        try:
            client = _get_client()
            data = await client.get_quote_batch(symbols=symbols)

            # Check for API errors
            if "status" in data and data["status"] == "error":
                return ToolResult(
                    success=False,
                    error=f"API Error: {data.get('message', 'Unknown error')}",
                )

            return ToolResult(success=True, output=data)
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg:
                return ToolResult(
                    success=False,
                    error="Invalid API key. Set TWELVEDATA_API_KEY environment variable.",
                )
            elif "429" in error_msg:
                return ToolResult(
                    success=False,
                    error="Rate limit exceeded. Wait a moment and try again.",
                )
            return ToolResult(success=False, error=error_msg)


class TwelveDataPriceBatchTool(BaseTool):
    """Get latest prices for multiple stocks or forex pairs at once."""

    @property
    def name(self) -> str:
        return "twelvedata_price_batch"

    @property
    def description(self) -> str:
        return """Get latest trading prices for multiple stocks or forex pairs in a single API call.

Lightweight endpoint for quick price checks on multiple symbols. Maximum 120 symbols per request.

Parameters:
- symbols: Array of stock symbols or forex pairs (max 120)

Returns: Current prices for all requested symbols"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of stock symbols or forex pairs (max 120)",
                    "minItems": 1,
                    "maxItems": 120,
                },
            },
            "required": ["symbols"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        symbols: List[str] = None,
        **kwargs,
    ) -> ToolResult:
        if not symbols or len(symbols) == 0:
            return ToolResult(success=False, error="'symbols' array is required and must not be empty")

        try:
            client = _get_client()
            data = await client.get_price_batch(symbols=symbols)

            # Check for API errors
            if "status" in data and data["status"] == "error":
                return ToolResult(
                    success=False,
                    error=f"API Error: {data.get('message', 'Unknown error')}",
                )

            return ToolResult(success=True, output=data)
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg:
                return ToolResult(
                    success=False,
                    error="Invalid API key. Set TWELVEDATA_API_KEY environment variable.",
                )
            elif "429" in error_msg:
                return ToolResult(
                    success=False,
                    error="Rate limit exceeded. Wait a moment and try again.",
                )
            return ToolResult(success=False, error=error_msg)
