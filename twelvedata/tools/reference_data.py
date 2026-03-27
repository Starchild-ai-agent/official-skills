"""
Twelve Data Reference Data Tools — Search and discover stocks and forex pairs.

Provides tools for searching symbols, listing available stocks, forex pairs, and exchanges.
"""

import logging

from core.tool import BaseTool, ToolContext, ToolResult
from .utils import get_client

logger = logging.getLogger(__name__)

class TwelveDataSearchTool(BaseTool):
    """Search for stocks or forex pairs by name or symbol."""

    @property
    def name(self) -> str:
        return "twelvedata_search"

    @property
    def description(self) -> str:
        return """Search for stocks or forex pairs by company name, symbol, or currency.

Use this to find the correct symbol before fetching quotes or time series data.

Examples:
- Search for "Apple" to find AAPL
- Search for "EUR" to find EUR/USD and other EUR pairs
- Search for "MSFT" to get Microsoft details

Parameters:
- query: Search query (company name, stock symbol, or currency pair)

Returns: Array of matching symbols with name, exchange, type, and currency info"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (company name, stock symbol, or currency)",
                },
            },
            "required": ["query"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        query: str = "",
        **kwargs,
    ) -> ToolResult:
        if not query:
            return ToolResult(success=False, error="'query' is required")

        try:
            client = get_client()
            data = await client.search_symbol(query=query)

            # Check for API errors
            if "status" in data and data["status"] == "error":
                return ToolResult(
                    success=False,
                    error=f"API Error: {data.get('message', 'Unknown error')}",
                )

            # Truncate large result sets
            if isinstance(data, dict) and "data" in data:
                items = data["data"]
                if isinstance(items, list) and len(items) > 20:
                    data["data"] = items[:20]
                    data["_truncated"] = True
            elif isinstance(data, list) and len(data) > 20:
                data = data[:20]
            # Truncate large result sets
            if isinstance(data, dict) and "data" in data:
                items = data["data"]
                if isinstance(items, list) and len(items) > 50:
                    data["data"] = items[:50]
                    data["_truncated"] = True
            elif isinstance(data, list) and len(data) > 50:
                data = data[:50]
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

class TwelveDataStocksTool(BaseTool):
    """Get list of available stocks, optionally filtered by exchange or country."""

    @property
    def name(self) -> str:
        return "twelvedata_stocks"

    @property
    def description(self) -> str:
        return """Get list of available stocks on Twelve Data.

Can filter by exchange (NASDAQ, NYSE, etc.) or country (US, GB, etc.) to narrow results.

Parameters:
- exchange: (optional) Filter by exchange code (e.g., NASDAQ, NYSE, LSE)
- country: (optional) Filter by country code (e.g., US, GB, JP)

Returns: Array of stocks with symbol, name, currency, exchange, and type"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "exchange": {
                    "type": "string",
                    "description": "Filter by exchange code (NASDAQ, NYSE, etc.) - optional",
                },
                "country": {
                    "type": "string",
                    "description": "Filter by country code (US, GB, JP, etc.) - optional",
                },
            },
        }

    async def execute(
        self,
        ctx: ToolContext,
        exchange: str = "",
        country: str = "",
        **kwargs,
    ) -> ToolResult:
        try:
            client = get_client()
            data = await client.get_stocks(
                exchange=exchange if exchange else None,
                country=country if country else None,
            )

            # Check for API errors
            if "status" in data and data["status"] == "error":
                return ToolResult(
                    success=False,
                    error=f"API Error: {data.get('message', 'Unknown error')}",
                )

            # Truncate large result sets
            if isinstance(data, dict) and "data" in data:
                items = data["data"]
                if isinstance(items, list) and len(items) > 50:
                    data["data"] = items[:50]
                    data["_truncated"] = True
            elif isinstance(data, list) and len(data) > 50:
                data = data[:50]
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

class TwelveDataForexPairsTool(BaseTool):
    """Get list of available forex pairs."""

    @property
    def name(self) -> str:
        return "twelvedata_forex_pairs"

    @property
    def description(self) -> str:
        return """Get list of all available forex (currency) pairs on Twelve Data.

Returns major, minor, and exotic forex pairs including:
- Major pairs: EUR/USD, GBP/USD, USD/JPY, etc.
- Minor pairs: EUR/GBP, GBP/JPY, etc.
- Exotic pairs: USD/TRY, EUR/HUF, etc.

No parameters required.

Returns: Array of forex pairs with symbol, currency base, currency quote"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {},
        }

    async def execute(
        self,
        ctx: ToolContext,
        **kwargs,
    ) -> ToolResult:
        try:
            client = get_client()
            data = await client.get_forex_pairs()

            # Check for API errors
            if "status" in data and data["status"] == "error":
                return ToolResult(
                    success=False,
                    error=f"API Error: {data.get('message', 'Unknown error')}",
                )

            # Truncate large result sets
            if isinstance(data, dict) and "data" in data:
                items = data["data"]
                if isinstance(items, list) and len(items) > 50:
                    data["data"] = items[:50]
                    data["_truncated"] = True
            elif isinstance(data, list) and len(data) > 50:
                data = data[:50]
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

class TwelveDataExchangesTool(BaseTool):
    """Get list of supported stock exchanges."""

    @property
    def name(self) -> str:
        return "twelvedata_exchanges"

    @property
    def description(self) -> str:
        return """Get list of all supported stock exchanges on Twelve Data.

Returns global exchanges including NASDAQ, NYSE, LSE, TSE, and many more.

No parameters required.

Returns: Array of exchanges with name, code, country, and timezone"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {},
        }

    async def execute(
        self,
        ctx: ToolContext,
        **kwargs,
    ) -> ToolResult:
        try:
            client = get_client()
            data = await client.get_exchanges()

            # Check for API errors
            if "status" in data and data["status"] == "error":
                return ToolResult(
                    success=False,
                    error=f"API Error: {data.get('message', 'Unknown error')}",
                )

            # Truncate large result sets
            if isinstance(data, dict) and "data" in data:
                items = data["data"]
                if isinstance(items, list) and len(items) > 50:
                    data["data"] = items[:50]
                    data["_truncated"] = True
            elif isinstance(data, list) and len(data) > 50:
                data = data[:50]
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
