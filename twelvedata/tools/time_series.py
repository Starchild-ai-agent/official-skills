"""
Twelve Data Time Series Tools — Historical OHLCV data for stocks and forex.

Provides tools for fetching historical price data with various intervals.
"""

import logging
from typing import Optional

from core.tool import BaseTool, ToolContext, ToolResult
from .client import TwelveDataClient, INTERVALS

logger = logging.getLogger(__name__)

# Singleton client instance
_client: Optional[TwelveDataClient] = None


def _get_client() -> TwelveDataClient:
    """Get or create singleton client instance."""
    global _client
    if _client is None:
        _client = TwelveDataClient()
    return _client


class TwelveDataTimeSeriesTools(BaseTool):
    """Get historical OHLCV time series data for stocks and forex."""

    @property
    def name(self) -> str:
        return "twelvedata_time_series"

    @property
    def description(self) -> str:
        return """Get historical OHLCV (Open, High, Low, Close, Volume) time series data for stocks and forex pairs.

Use this for historical price analysis, backtesting, and charting. Supports multiple intervals from 1-minute to monthly data.

Parameters:
- symbol: Stock symbol (e.g., AAPL, MSFT, TSLA) or forex pair (e.g., EUR/USD, GBP/JPY)
- interval: Time interval - 1min, 5min, 15min, 30min, 1h, 4h, 1day, 1week, 1month (default: 1day)
- outputsize: Number of data points to return (1-5000, default: 30). Common values: 30 (compact), 100, 500, 5000 (maximum)
- start_date: (optional) Start date in YYYY-MM-DD format
- end_date: (optional) End date in YYYY-MM-DD format

Returns: Historical OHLCV data with metadata including symbol, exchange, currency, and interval"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol (AAPL, MSFT) or forex pair (EUR/USD, GBP/JPY)",
                },
                "interval": {
                    "type": "string",
                    "description": f"Time interval: {', '.join(INTERVALS)} (default: 1day)",
                    "enum": INTERVALS,
                },
                "outputsize": {
                    "type": "integer",
                    "description": "Number of data points to return (1-5000). Default 30.",
                    "minimum": 1,
                    "maximum": 5000,
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format (optional)",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format (optional)",
                },
            },
            "required": ["symbol"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        symbol: str = "",
        interval: str = "1day",
        outputsize: int = 30,
        start_date: str = "",
        end_date: str = "",
        **kwargs,
    ) -> ToolResult:
        if not symbol:
            return ToolResult(success=False, error="'symbol' is required")

        try:
            client = _get_client()
            data = await client.get_time_series(
                symbol=symbol,
                interval=interval,
                outputsize=outputsize,
                start_date=start_date if start_date else None,
                end_date=end_date if end_date else None,
            )

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


class TwelveDataPriceTool(BaseTool):
    """Get latest trading price for a stock or forex pair."""

    @property
    def name(self) -> str:
        return "twelvedata_price"

    @property
    def description(self) -> str:
        return """Get the latest available trading price for a stock or forex pair.

This is a lightweight endpoint for quick price checks without full quote data.

Parameters:
- symbol: Stock symbol (AAPL, MSFT) or forex pair (EUR/USD, GBP/JPY)

Returns: Current price value"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol or forex pair",
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
            data = await client.get_price(symbol=symbol)

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


class TwelveDataEODTool(BaseTool):
    """Get end-of-day price for a stock or forex pair."""

    @property
    def name(self) -> str:
        return "twelvedata_eod"

    @property
    def description(self) -> str:
        return """Get end-of-day (EOD) closing price for a stock or forex pair.

Useful for daily analysis and reports. Returns the closing price for the most recent trading day or a specific date.

Parameters:
- symbol: Stock symbol (AAPL, MSFT) or forex pair (EUR/USD, GBP/JPY)
- date: (optional) Specific date in YYYY-MM-DD format (defaults to latest available)

Returns: EOD price data with close, high, low, open, volume"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol or forex pair",
                },
                "date": {
                    "type": "string",
                    "description": "Specific date in YYYY-MM-DD format (optional)",
                },
            },
            "required": ["symbol"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        symbol: str = "",
        date: str = "",
        **kwargs,
    ) -> ToolResult:
        if not symbol:
            return ToolResult(success=False, error="'symbol' is required")

        try:
            client = _get_client()
            data = await client.get_eod(
                symbol=symbol,
                date=date if date else None,
            )

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
