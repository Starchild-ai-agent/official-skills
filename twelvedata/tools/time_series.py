"""
Twelve Data Time Series Tools — Historical OHLCV data for stocks and forex.

Provides tools for fetching historical price data and end-of-day prices.
"""

import logging

from core.tool import BaseTool, ToolContext, ToolResult
from .client import get_client, handle_api_error, INTERVALS

logger = logging.getLogger(__name__)


class TwelveDataTimeSeriesTools(BaseTool):
    """Get historical OHLCV time series data."""

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
- prepost: (optional) Include pre/post-market data when available (US/Cboe Europe, Pro+ only)

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
                    "description": "Time interval: 1min, 5min, 15min, 30min, 45min, 1h, 2h, 4h, 8h, 1day, 1week, 1month (default: 1day)",
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
                "prepost": {
                    "type": "boolean",
                    "description": "Include pre/post-market data when available (US/Cboe Europe, Pro+ only)",
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
        prepost: bool = False,
        **kwargs,
    ) -> ToolResult:
        if not symbol:
            return ToolResult(success=False, error="'symbol' is required")
        if interval not in INTERVALS:
            return ToolResult(success=False, error=f"Invalid interval '{interval}'. Must be one of: {', '.join(INTERVALS)}")
        try:
            data = await get_client().get_time_series(
                symbol=symbol,
                interval=interval,
                outputsize=outputsize,
                start_date=start_date if start_date else None,
                end_date=end_date if end_date else None,
                prepost=prepost,
            )
            if data.get("status") == "error":
                return ToolResult(success=False, error=f"API Error: {data.get('message', 'Unknown error')}")
            return ToolResult(success=True, output=data)
        except Exception as e:
            return handle_api_error(e)


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
- prepost: (optional) Include pre/post-market data when available (US/Cboe Europe, Pro+ only)

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
            data = await get_client().get_price(symbol=symbol, prepost=prepost)
            if data.get("status") == "error":
                return ToolResult(success=False, error=f"API Error: {data.get('message', 'Unknown error')}")
            return ToolResult(success=True, output=data)
        except Exception as e:
            return handle_api_error(e)


class TwelveDataEODTool(BaseTool):
    """Get end-of-day closing price for a stock or forex pair."""

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
- prepost: (optional) Include pre/post-market data when available (US/Cboe Europe, Pro+ only)

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
                "prepost": {
                    "type": "boolean",
                    "description": "Include pre/post-market data when available (US/Cboe Europe, Pro+ only)",
                },
            },
            "required": ["symbol"],
        }

    async def execute(self, ctx: ToolContext, symbol: str = "", date: str = "", prepost: bool = False, **kwargs) -> ToolResult:
        if not symbol:
            return ToolResult(success=False, error="'symbol' is required")
        try:
            data = await get_client().get_eod(
                symbol=symbol,
                date=date if date else None,
                prepost=prepost,
            )
            if data.get("status") == "error":
                return ToolResult(success=False, error=f"API Error: {data.get('message', 'Unknown error')}")
            return ToolResult(success=True, output=data)
        except Exception as e:
            return handle_api_error(e)
