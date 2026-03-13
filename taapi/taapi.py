"""
TaAPI Tool Wrappers

Wraps tools from /tools/taapi/ for use in Agent framework.
Provides pre-calculated technical analysis indicators.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional

from core.tool import BaseTool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

# Import original tools from local tools directory
try:
    from .tools.indicators import get_indicator, get_multiple_indicators
    from .tools.support_resistance import get_support_resistance
    TAAPI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"TaAPI tools not available: {e}")
    TAAPI_AVAILABLE = False


class IndicatorTool(BaseTool):
    """
    Get technical analysis indicators (RSI, MACD, Bollinger Bands, etc.)
    """

    @property
    def name(self) -> str:
        return "indicator"

    @property
    def description(self) -> str:
        return """Get technical analysis indicators from TaAPI.

Supported indicators: rsi, macd, bbands, ema, sma, stoch, adx, cci, atr, obv, mfi
Supported intervals: 1m, 5m, 15m, 30m, 1h, 2h, 4h, 12h, 1d, 1w
Supported exchanges: binance, binancefutures, bybit, okex

Examples:
- Get BTC RSI: indicator(name="rsi", symbol="BTC/USDT", interval="1h")
- Get ETH MACD: indicator(name="macd", symbol="ETH/USDT", interval="4h")
- Get BTC Bollinger Bands: indicator(name="bbands", symbol="BTC/USDT", interval="1d")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Indicator name: rsi, macd, bbands, ema, sma, stoch, adx, cci, atr, obv, mfi"
                },
                "symbol": {
                    "type": "string",
                    "description": "Trading pair in COIN/MARKET format (BTC/USDT, ETH/USDT)"
                },
                "interval": {
                    "type": "string",
                    "description": "Timeframe: 1m, 5m, 15m, 30m, 1h, 2h, 4h, 12h, 1d, 1w",
                    "default": "1h"
                },
                "exchange": {
                    "type": "string",
                    "description": "Exchange: binance, binancefutures, bybit, okex",
                    "default": "binance"
                }
            },
            "required": ["name", "symbol"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        name: str,
        symbol: str,
        interval: str = "1h",
        exchange: str = "binance"
    ) -> ToolResult:
        if not TAAPI_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="TaAPI tools not available. Check if /tools/taapi exists."
            )

        try:
            result = await asyncio.to_thread(
                get_indicator,
                indicator=name,
                exchange=exchange,
                symbol=symbol,
                interval=interval
            )

            if result is None:
                return ToolResult(
                    success=False,
                    output=None,
                    error="Failed to fetch indicator. Check TAAPI_API_KEY."
                )

            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class SupportResistanceTool(BaseTool):
    """
    Get support and resistance levels for a trading pair.
    """

    @property
    def name(self) -> str:
        return "support_resistance"

    @property
    def description(self) -> str:
        return """Get support and resistance price levels.

Useful for identifying key price levels for entries, exits, and stop losses.

Examples:
- Get BTC S/R levels: support_resistance(symbol="BTC/USDT", interval="4h")
- Get ETH daily levels: support_resistance(symbol="ETH/USDT", interval="1d")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Trading pair (BTC/USDT, ETH/USDT)"
                },
                "interval": {
                    "type": "string",
                    "description": "Timeframe: 1h, 4h, 1d",
                    "default": "4h"
                },
                "exchange": {
                    "type": "string",
                    "default": "binance"
                }
            },
            "required": ["symbol"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        symbol: str,
        interval: str = "4h",
        exchange: str = "binance"
    ) -> ToolResult:
        if not TAAPI_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="TaAPI tools not available."
            )

        try:
            result = await asyncio.to_thread(
                get_support_resistance,
                exchange=exchange,
                symbol=symbol,
                interval=interval
            )

            if result is None:
                return ToolResult(
                    success=False,
                    output=None,
                    error="Failed to fetch S/R levels. Check TAAPI_API_KEY."
                )

            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
