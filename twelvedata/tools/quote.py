"""
Twelve Data Quote Tools — Real-time market quotes for stocks and forex.

Provides tools for fetching current market data including price, volume, and 52-week metrics.
"""

import logging
from typing import List

from core.tool import BaseTool, ToolContext, ToolResult
from .client import get_client, handle_api_error

logger = logging.getLogger(__name__)


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
- prepost: (optional) Include pre/post-market data when available (US/Cboe Europe, Pro+ only)

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
                "prepost": {
                    "type": "boolean",
                    "description": "Include pre/post-market data when available (US/Cboe Europe, Pro+ only)",
                },
            },
            "required": ["symbol"],
        }

    async def execute(self, ctx: ToolContext, symbol: str = "", prepost: bool = False, **kwargs) -> ToolResult:
        if not symbol:
            return ToolResult(success=False, error="'symbol' is required")
        try:
            data = await get_client().get_quote(symbol=symbol, prepost=prepost)
            if data.get("status") == "error":
                return ToolResult(success=False, error=f"API Error: {data.get('message', 'Unknown error')}")
            return ToolResult(success=True, output=data)
        except Exception as e:
            return handle_api_error(e)


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
- prepost: (optional) Include pre/post-market data when available (US/Cboe Europe, Pro+ only)

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
                "prepost": {
                    "type": "boolean",
                    "description": "Include pre/post-market data when available (US/Cboe Europe, Pro+ only)",
                },
            },
            "required": ["symbols"],
        }

    async def execute(self, ctx: ToolContext, symbols: List[str] = None, prepost: bool = False, **kwargs) -> ToolResult:
        if not symbols:
            return ToolResult(success=False, error="'symbols' array is required and must not be empty")
        try:
            data = await get_client().get_quote_batch(symbols=symbols, prepost=prepost)
            if data.get("status") == "error":
                return ToolResult(success=False, error=f"API Error: {data.get('message', 'Unknown error')}")
            return ToolResult(success=True, output=data)
        except Exception as e:
            return handle_api_error(e)


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
- prepost: (optional) Include pre/post-market data when available (US/Cboe Europe, Pro+ only)

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
                "prepost": {
                    "type": "boolean",
                    "description": "Include pre/post-market data when available (US/Cboe Europe, Pro+ only)",
                },
            },
            "required": ["symbols"],
        }

    async def execute(self, ctx: ToolContext, symbols: List[str] = None, prepost: bool = False, **kwargs) -> ToolResult:
        if not symbols:
            return ToolResult(success=False, error="'symbols' array is required and must not be empty")
        try:
            data = await get_client().get_price_batch(symbols=symbols, prepost=prepost)
            if data.get("status") == "error":
                return ToolResult(success=False, error=f"API Error: {data.get('message', 'Unknown error')}")
            return ToolResult(success=True, output=data)
        except Exception as e:
            return handle_api_error(e)
