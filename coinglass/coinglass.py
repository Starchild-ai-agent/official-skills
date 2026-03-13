"""
Coinglass Tool Wrappers

Wraps tools from /tools/coinglass/ for use in Agent framework.
Provides derivatives data: funding rates, open interest, liquidations, long/short ratios.
"""
import asyncio
import logging
from typing import Any, Dict, Optional

from core.tool import BaseTool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

# Import original tools from local tools directory
try:
    from .tools.funding_rate import get_funding_rates, get_symbol_funding_rate
    from .tools.long_short_ratio import get_long_short_ratio
    from .tools.long_short_advanced import (
        get_global_account_ratio,
        get_top_account_ratio,
        get_top_position_ratio,
        get_taker_buysell_exchanges,
        get_net_position
    )
    from .tools.open_interest import get_open_interest
    from .tools.liquidations import get_liquidations, get_liquidation_aggregated
    from .tools.liquidations_advanced import (
        get_coin_liquidation_history,
        get_pair_liquidation_history,
        get_liquidation_coin_list,
        get_liquidation_orders
    )
    from .tools.hyperliquid import (
        get_whale_alerts,
        get_whale_positions,
        get_positions_by_coin,
        get_position_distribution
    )
    from .tools.futures_market import (
        get_supported_coins,
        get_supported_exchanges,
        get_coins_data,
        get_pair_data,
        get_ohlc_history
    )
    from .tools.volume_flow import (
        get_taker_volume_history,
        get_aggregated_taker_volume,
        get_cumulative_volume_delta,
        get_coin_netflow
    )
    from .tools.whale_transfer import get_whale_transfers
    from .tools.bitcoin_etf import (
        get_btc_etf_flows,
        get_btc_etf_premium_discount,
        get_btc_etf_history,
        get_btc_etf_list,
        get_hk_btc_etf_flows
    )
    from .tools.other_etfs import (
        get_eth_etf_flows,
        get_eth_etf_list,
        get_sol_etf_flows,
        get_xrp_etf_flows
    )
    COINGLASS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Coinglass tools not available: {e}")
    COINGLASS_AVAILABLE = False


class FundingRateTool(BaseTool):
    """
    Get perpetual futures funding rates across exchanges.

    Funding rates indicate market sentiment:
    - Positive rates: Longs pay shorts (bullish bias)
    - Negative rates: Shorts pay longs (bearish bias)
    - Extreme rates often precede reversals
    """

    @property
    def name(self) -> str:
        return "funding_rate"

    @property
    def description(self) -> str:
        return """Get perpetual futures funding rates across exchanges.

Positive rates = longs pay shorts (bullish sentiment)
Negative rates = shorts pay longs (bearish sentiment)
Extreme funding often signals reversal risk.

Examples:
- Get BTC funding rates: funding_rate(symbol="BTC")
- Get ETH funding on Binance: funding_rate(symbol="ETH", exchange="Binance")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Symbol (BTC, ETH, SOL, etc.)"
                },
                "exchange": {
                    "type": "string",
                    "description": "Optional: specific exchange (Binance, OKX, Bybit, etc.)"
                }
            },
            "required": ["symbol"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        symbol: str,
        exchange: Optional[str] = None
    ) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="Coinglass tools not available. Check if /tools/coinglass exists."
            )

        try:
            if exchange:
                result = await asyncio.to_thread(get_symbol_funding_rate, symbol=symbol, exchange=exchange)
            else:
                result = await asyncio.to_thread(get_funding_rates, symbol=symbol)

            if result is None:
                return ToolResult(
                    success=False,
                    output=None,
                    error="Failed to fetch funding rates. Check COINGLASS_API_KEY."
                )

            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class LongShortRatioTool(BaseTool):
    """
    Get long/short ratio for a cryptocurrency.

    Shows the ratio of long vs short positions across exchanges.
    Useful for sentiment analysis.
    """

    @property
    def name(self) -> str:
        return "long_short_ratio"

    @property
    def description(self) -> str:
        return """Get long/short position ratio across exchanges.

Ratio > 1: More longs than shorts
Ratio < 1: More shorts than longs
Extreme ratios often signal crowded trades.

Examples:
- Get BTC L/S ratio: long_short_ratio(symbol="BTC")
- Get ETH L/S ratio with timeframe: long_short_ratio(symbol="ETH", interval="h4")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Symbol (BTC, ETH, SOL, etc.)"
                },
                "interval": {
                    "type": "string",
                    "description": "Time interval: h1, h4, h12, h24",
                    "default": "h4"
                }
            },
            "required": ["symbol"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        symbol: str,
        interval: str = "h4"
    ) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="Coinglass tools not available."
            )

        try:
            result = await asyncio.to_thread(get_long_short_ratio, symbol=symbol, time_type=interval)

            if result is None:
                return ToolResult(
                    success=False,
                    output=None,
                    error="Failed to fetch long/short ratio. Check COINGLASS_API_KEY."
                )

            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Advanced Long/Short Ratio Tools ====================

class GlobalAccountRatioTool(BaseTool):
    """Get global long/short account ratio history."""

    @property
    def name(self) -> str:
        return "cg_global_account_ratio"

    @property
    def description(self) -> str:
        return """Get global long/short account ratio history for a trading pair.

Shows the percentage of accounts holding long vs short positions over time.

Examples:
- Get BTC global ratio: cg_global_account_ratio(symbol="BTC", exchange="Binance")
- Get ETH with 4h interval: cg_global_account_ratio(symbol="ETH", exchange="OKX", interval="4h")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading coin (BTC, ETH, SOL, etc.)"},
                "exchange": {"type": "string", "description": "Exchange name (Binance, OKX, Bybit, etc.)"},
                "interval": {"type": "string", "description": "Time interval: 1m, 5m, 15m, 30m, 1h, 4h, 12h, 1d, 1w", "default": "1h"},
                "limit": {"type": "integer", "description": "Number of results (default: 100)", "default": 100}
            },
            "required": ["symbol", "exchange"]
        }

    async def execute(self, ctx: ToolContext, symbol: str, exchange: str, interval: str = "1h", limit: int = 100) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_global_account_ratio, symbol, exchange, interval, limit)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch global account ratio. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class TopAccountRatioTool(BaseTool):
    """Get top traders long/short account ratio."""

    @property
    def name(self) -> str:
        return "cg_top_account_ratio"

    @property
    def description(self) -> str:
        return """Get long/short account ratio for top traders only.

Shows what the most successful traders are doing. More reliable than global ratios.

Examples:
- Get BTC top trader ratio: cg_top_account_ratio(symbol="BTC", exchange="Binance")
- Get ETH 4h: cg_top_account_ratio(symbol="ETH", exchange="OKX", interval="4h")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading coin (BTC, ETH, SOL, etc.)"},
                "exchange": {"type": "string", "description": "Exchange name (Binance, OKX, Bybit, etc.)"},
                "interval": {"type": "string", "description": "Time interval: 1m, 5m, 15m, 30m, 1h, 4h, 12h, 1d, 1w", "default": "1h"},
                "limit": {"type": "integer", "description": "Number of results (default: 100)", "default": 100}
            },
            "required": ["symbol", "exchange"]
        }

    async def execute(self, ctx: ToolContext, symbol: str, exchange: str, interval: str = "1h", limit: int = 100) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_top_account_ratio, symbol, exchange, interval, limit)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch top account ratio. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class TopPositionRatioTool(BaseTool):
    """Get top traders long/short position ratio."""

    @property
    def name(self) -> str:
        return "cg_top_position_ratio"

    @property
    def description(self) -> str:
        return """Get long/short position ratio for top traders (by position size, not account count).

Shows the actual $ amount split between longs and shorts for top traders.

Examples:
- Get BTC top position ratio: cg_top_position_ratio(symbol="BTC", exchange="Binance")
- Get ETH 4h: cg_top_position_ratio(symbol="ETH", exchange="OKX", interval="4h")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading coin (BTC, ETH, SOL, etc.)"},
                "exchange": {"type": "string", "description": "Exchange name (Binance, OKX, Bybit, etc.)"},
                "interval": {"type": "string", "description": "Time interval: 1m, 5m, 15m, 30m, 1h, 4h, 12h, 1d, 1w", "default": "1h"},
                "limit": {"type": "integer", "description": "Number of results (default: 100)", "default": 100}
            },
            "required": ["symbol", "exchange"]
        }

    async def execute(self, ctx: ToolContext, symbol: str, exchange: str, interval: str = "1h", limit: int = 100) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_top_position_ratio, symbol, exchange, interval, limit)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch top position ratio. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class TakerBuySellExchangesTool(BaseTool):
    """Get exchanges with taker buy/sell volume data."""

    @property
    def name(self) -> str:
        return "cg_taker_exchanges"

    @property
    def description(self) -> str:
        return """Get list of exchanges with taker buy/sell volume data available.

Shows which exchanges provide taker volume metrics and their current ratios.

Examples:
- Get BTC exchanges (1h): cg_taker_exchanges(symbol="BTC")
- Get ETH exchanges (24h): cg_taker_exchanges(symbol="ETH", range="24h")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading coin (BTC, ETH, SOL, etc.)"},
                "range": {"type": "string", "description": "Time range: 1h, 4h, 12h, 24h (default: 1h)", "default": "1h"}
            },
            "required": ["symbol"]
        }

    async def execute(self, ctx: ToolContext, symbol: str, range: str = "1h") -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_taker_buysell_exchanges, symbol, range)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch taker exchanges. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class NetPositionTool(BaseTool):
    """Get net position changes (net long/short delta)."""

    @property
    def name(self) -> str:
        return "cg_net_position"

    @property
    def description(self) -> str:
        return """Get historical net position data showing net long/short changes.

Net position = difference between long and short positions opened.
Useful for tracking institutional positioning.

Examples:
- Get BTC net position: cg_net_position(symbol="BTC", exchange="Binance")
- Get ETH 4h: cg_net_position(symbol="ETH", exchange="OKX", interval="4h")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading coin (BTC, ETH, SOL, etc.)"},
                "exchange": {"type": "string", "description": "Exchange name (Binance, OKX, Bybit, etc.)"},
                "interval": {"type": "string", "description": "Time interval: 1m, 5m, 15m, 30m, 1h, 4h, 12h, 1d, 1w", "default": "1h"},
                "limit": {"type": "integer", "description": "Number of results (default: 100)", "default": 100}
            },
            "required": ["symbol", "exchange"]
        }

    async def execute(self, ctx: ToolContext, symbol: str, exchange: str, interval: str = "1h", limit: int = 100) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_net_position, symbol, exchange, interval, limit)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch net position. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Open Interest Tools ====================

class OpenInterestTool(BaseTool):
    """
    Get aggregate open interest across exchanges.
    """

    @property
    def name(self) -> str:
        return "cg_open_interest"

    @property
    def description(self) -> str:
        return """Get aggregate open interest across exchanges for a symbol.

Open interest = total outstanding derivative contracts.
Rising OI + rising price = new money entering (bullish)
Rising OI + falling price = new shorts opening (bearish)
Falling OI = positions closing (trend weakening)

Examples:
- Get BTC open interest: cg_open_interest(symbol="BTC")
- Get ETH open interest: cg_open_interest(symbol="ETH")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Symbol (BTC, ETH, SOL, etc.)"
                }
            },
            "required": ["symbol"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        symbol: str
    ) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="Coinglass tools not available."
            )

        try:
            result = await asyncio.to_thread(get_open_interest, symbol)

            if result is None:
                return ToolResult(
                    success=False,
                    output=None,
                    error="Failed to fetch open interest. Check COINGLASS_API_KEY."
                )

            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Liquidation Tools ====================

class LiquidationsTool(BaseTool):
    """
    Get recent liquidation data.
    """

    @property
    def name(self) -> str:
        return "cg_liquidations"

    @property
    def description(self) -> str:
        return """Get recent liquidation data across exchanges.

Liquidations = forced position closures due to insufficient margin.
More long liquidations = bearish pressure (longs being squeezed)
More short liquidations = bullish pressure (shorts being squeezed)

Examples:
- Get BTC liquidations (24h): cg_liquidations(symbol="BTC")
- Get ETH liquidations (4h): cg_liquidations(symbol="ETH", time_type="h4")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Symbol (BTC, ETH, SOL, etc.)"
                },
                "time_type": {
                    "type": "string",
                    "description": "Time window: h1, h4, h12, h24",
                    "default": "h24"
                }
            },
            "required": ["symbol"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        symbol: str,
        time_type: str = "h24"
    ) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="Coinglass tools not available."
            )

        try:
            result = await asyncio.to_thread(get_liquidations, symbol, time_type)

            if result is None:
                return ToolResult(
                    success=False,
                    output=None,
                    error="Failed to fetch liquidations. Check COINGLASS_API_KEY."
                )

            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class LiquidationAnalysisTool(BaseTool):
    """
    Get liquidation data with sentiment analysis.
    """

    @property
    def name(self) -> str:
        return "cg_liquidation_analysis"

    @property
    def description(self) -> str:
        return """Get liquidation data with market sentiment analysis.

Includes interpretation of liquidation imbalances.

Examples:
- Analyze BTC liquidations: cg_liquidation_analysis(symbol="BTC")
- Analyze ETH (4h): cg_liquidation_analysis(symbol="ETH", time_type="h4")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Symbol (BTC, ETH, SOL, etc.)"
                },
                "time_type": {
                    "type": "string",
                    "description": "Time window: h1, h4, h12, h24",
                    "default": "h24"
                }
            },
            "required": ["symbol"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        symbol: str,
        time_type: str = "h24"
    ) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="Coinglass tools not available."
            )

        try:
            result = await asyncio.to_thread(get_liquidation_aggregated, symbol, time_type)

            if result is None:
                return ToolResult(
                    success=False,
                    output=None,
                    error="Failed to fetch liquidation analysis. Check COINGLASS_API_KEY."
                )

            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Advanced Liquidation Tools ====================

class CoinLiquidationHistoryTool(BaseTool):
    """Get aggregated liquidation history for a coin across all exchanges."""

    @property
    def name(self) -> str:
        return "cg_coin_liquidation_history"

    @property
    def description(self) -> str:
        return """Get aggregated liquidation history across all exchanges for a coin.

Shows total long/short liquidations over time, aggregated across all exchanges.

Examples:
- Get BTC liquidation history: cg_coin_liquidation_history(symbol="BTC", interval="1h", limit=100)
- Get ETH 4h intervals: cg_coin_liquidation_history(symbol="ETH", interval="4h", limit=50)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading coin (BTC, ETH, SOL, etc.)"},
                "exchange_list": {"type": "string", "description": "Comma-separated exchange list (e.g. 'Binance,OKX,Bybit')"},
                "interval": {"type": "string", "description": "Time interval: 1m, 3m, 5m, 15m, 30m, 1h, 4h, 6h, 8h, 12h, 1d, 1w", "default": "1h"},
                "limit": {"type": "integer", "description": "Number of results (default: 1000, max: 4500)", "default": 1000},
                "start_time": {"type": "integer", "description": "Start timestamp in milliseconds"},
                "end_time": {"type": "integer", "description": "End timestamp in milliseconds"}
            },
            "required": ["symbol", "exchange_list"]
        }

    async def execute(self, ctx: ToolContext, symbol: str, exchange_list: str, interval: str = "1h", limit: int = 1000,
                     start_time: Optional[int] = None, end_time: Optional[int] = None) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_coin_liquidation_history, symbol, exchange_list, interval, limit, start_time, end_time)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch coin liquidation history. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class PairLiquidationHistoryTool(BaseTool):
    """Get liquidation history for a specific trading pair on an exchange."""

    @property
    def name(self) -> str:
        return "cg_pair_liquidation_history"

    @property
    def description(self) -> str:
        return """Get liquidation history for a specific pair on a specific exchange.

Shows long/short liquidations over time for exchange-specific pairs.

Examples:
- Get BTC/USDT on Binance: cg_pair_liquidation_history(symbol="BTC", exchange="Binance", interval="1h")
- Get ETH/USDT on OKX: cg_pair_liquidation_history(symbol="ETH", exchange="OKX", interval="4h")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading coin (BTC, ETH, SOL, etc.)"},
                "exchange": {"type": "string", "description": "Exchange name (Binance, OKX, Bybit, etc.)"},
                "interval": {"type": "string", "description": "Time interval: 1h, 4h, 12h, 24h", "default": "1h"},
                "limit": {"type": "integer", "description": "Number of results (default: 1000, max: 4500)", "default": 1000},
                "start_time": {"type": "integer", "description": "Start timestamp in seconds"},
                "end_time": {"type": "integer", "description": "End timestamp in seconds"}
            },
            "required": ["symbol", "exchange"]
        }

    async def execute(self, ctx: ToolContext, symbol: str, exchange: str, interval: str = "1h", limit: int = 1000,
                     start_time: Optional[int] = None, end_time: Optional[int] = None) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_pair_liquidation_history, symbol, exchange, interval, limit, start_time, end_time)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch pair liquidation history. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class LiquidationCoinListTool(BaseTool):
    """Get liquidation data for all coins on a specific exchange."""

    @property
    def name(self) -> str:
        return "cg_liquidation_coin_list"

    @property
    def description(self) -> str:
        return """Get liquidation data for all coins on a specific exchange.

Shows liquidation amounts across multiple timeframes (1h, 4h, 12h, 24h) for all coins on an exchange.

Examples:
- Get all Binance liquidations: cg_liquidation_coin_list(exchange="Binance")
- Get all OKX liquidations: cg_liquidation_coin_list(exchange="OKX")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "exchange": {"type": "string", "description": "Exchange name (Binance, OKX, Bybit, etc.)"}
            },
            "required": ["exchange"]
        }

    async def execute(self, ctx: ToolContext, exchange: str) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_liquidation_coin_list, exchange)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch liquidation coin list. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class LiquidationOrdersTool(BaseTool):
    """Get individual liquidation orders (past 7 days)."""

    @property
    def name(self) -> str:
        return "cg_liquidation_orders"

    @property
    def description(self) -> str:
        return """Get individual liquidation orders with price, side, and USD value (past 7 days only).

Shows actual liquidation events. Max 200 records per request.

Examples:
- Get BTC liquidations on Binance (min $10K): cg_liquidation_orders(symbol="BTC", exchange="Binance", min_liquidation_amount="10000")
- Get ETH liquidations on OKX (min $5K): cg_liquidation_orders(symbol="ETH", exchange="OKX", min_liquidation_amount="5000")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading coin (BTC, ETH, SOL, etc.)"},
                "exchange": {"type": "string", "description": "Exchange name (Binance, OKX, Bybit, etc.)"},
                "min_liquidation_amount": {"type": "string", "description": "Minimum threshold for liquidation events (USD)"},
                "start_time": {"type": "integer", "description": "Start timestamp in milliseconds"},
                "end_time": {"type": "integer", "description": "End timestamp in milliseconds"}
            },
            "required": ["symbol", "exchange", "min_liquidation_amount"]
        }

    async def execute(self, ctx: ToolContext, symbol: str, exchange: str, min_liquidation_amount: str,
                     start_time: Optional[int] = None, end_time: Optional[int] = None) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_liquidation_orders, symbol, exchange, min_liquidation_amount, start_time, end_time)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch liquidation orders. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Futures Market Data Tools (V4 API) ====================

class SupportedCoinsTool(BaseTool):
    """Get list of all supported coins for futures trading."""

    @property
    def name(self) -> str:
        return "cg_supported_coins"

    @property
    def description(self) -> str:
        return """Get list of all supported coins for futures trading on Coinglass.

Returns array of coin symbols (BTC, ETH, SOL, XRP, HYPE, DOGE, etc.)

Use this for:
- Market discovery
- Checking if a coin has futures markets
- Finding new trading opportunities

Examples:
- Get all supported coins: cg_supported_coins()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_supported_coins)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch supported coins. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class SupportedExchangesTool(BaseTool):
    """Get all supported exchanges with their trading pairs."""

    @property
    def name(self) -> str:
        return "cg_supported_exchanges"

    @property
    def description(self) -> str:
        return """Get all supported exchanges with trading pairs and specs.

Returns dictionary with exchange pairs including leverage limits, funding intervals, tick sizes.

Examples:
- Get all exchanges: cg_supported_exchanges()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_supported_exchanges)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch supported exchanges. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CoinsMarketDataTool(BaseTool):
    """Get comprehensive market data for ALL coins in one request."""

    @property
    def name(self) -> str:
        return "cg_coins_market_data"

    @property
    def description(self) -> str:
        return """Get market data for ALL coins in ONE request.

Returns: price, funding rates, OI, volume, long/short ratios, liquidations for 100+ coins.

Use this for market screening and bulk analysis. MUCH more efficient than individual calls.

Examples:
- Get all coins data: cg_coins_market_data()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_coins_data)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch coins market data. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class PairMarketDataTool(BaseTool):
    """Get detailed market data for a specific trading pair."""

    @property
    def name(self) -> str:
        return "cg_pair_market_data"

    @property
    def description(self) -> str:
        return """Get detailed market data for a specific pair on an exchange.

Returns: price, volume, OI, funding rate, liquidations, long/short volumes.

Examples:
- Get BTC/USDT on Binance: cg_pair_market_data(symbol="BTC", exchange="Binance")
- Get ETH/USDT on OKX: cg_pair_market_data(symbol="ETH", exchange="OKX")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Coin symbol (BTC, ETH, SOL, etc.)"},
                "exchange": {"type": "string", "description": "Exchange name (Binance, OKX, Bybit, Gate, etc.)"}
            },
            "required": ["symbol", "exchange"]
        }

    async def execute(self, ctx: ToolContext, symbol: str, exchange: str) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_pair_data, symbol, exchange)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch pair market data. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class OHLCHistoryTool(BaseTool):
    """Get OHLC price history for a trading pair."""

    @property
    def name(self) -> str:
        return "cg_ohlc_history"

    @property
    def description(self) -> str:
        return """Get OHLC candlestick data for price analysis.

Returns array of candles with: timestamp, open, high, low, close.

Examples:
- Get BTC 1h candles: cg_ohlc_history(symbol="BTC", exchange="Binance", interval="h1", limit=100)
- Get ETH daily: cg_ohlc_history(symbol="ETH", exchange="OKX", interval="d1", limit=30)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Coin symbol (BTC, ETH, SOL, etc.)"},
                "exchange": {"type": "string", "description": "Exchange name (Binance, OKX, Bybit, etc.)"},
                "interval": {"type": "string", "description": "Time interval: m1, m5, m15, m30, h1, h4, h12, d1", "default": "h1"},
                "limit": {"type": "integer", "description": "Number of candles (default: 100)", "default": 100}
            },
            "required": ["symbol", "exchange"]
        }

    async def execute(self, ctx: ToolContext, symbol: str, exchange: str, interval: str = "h1", limit: int = 100) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_ohlc_history, symbol, exchange, interval, limit)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch OHLC history. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Hyperliquid Tools ====================

class HyperliquidWhaleAlertsTool(BaseTool):
    """Get recent whale alerts on Hyperliquid (positions > $1M)."""

    @property
    def name(self) -> str:
        return "cg_hyperliquid_whale_alerts"

    @property
    def description(self) -> str:
        return """Get recent whale alerts on Hyperliquid (positions > $1M).

Returns approximately 200 most recent large position opens/closes.

Examples:
- Get whale alerts: cg_hyperliquid_whale_alerts()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_whale_alerts)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch whale alerts. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class HyperliquidWhalePositionsTool(BaseTool):
    """Get current whale positions on Hyperliquid."""

    @property
    def name(self) -> str:
        return "cg_hyperliquid_whale_positions"

    @property
    def description(self) -> str:
        return """Get current whale positions on Hyperliquid.

Shows large active positions with entry price, PnL, leverage, and margin data.

Examples:
- Get whale positions: cg_hyperliquid_whale_positions()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_whale_positions)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch whale positions. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class HyperliquidPositionsByCoinTool(BaseTool):
    """Get wallet positions organized by coin on Hyperliquid."""

    @property
    def name(self) -> str:
        return "cg_hyperliquid_positions_by_coin"

    @property
    def description(self) -> str:
        return """Get real-time wallet positions for a specific coin on Hyperliquid.

Shows all open positions for the specified cryptocurrency.

Examples:
- Get BTC positions: cg_hyperliquid_positions_by_coin(symbol="BTC")
- Get ETH positions: cg_hyperliquid_positions_by_coin(symbol="ETH")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading coin (BTC, ETH, SOL, etc.)"}
            },
            "required": ["symbol"]
        }

    async def execute(self, ctx: ToolContext, symbol: str) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_positions_by_coin, symbol)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch positions by coin. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class HyperliquidPositionDistributionTool(BaseTool):
    """Get wallet position distribution on Hyperliquid."""

    @property
    def name(self) -> str:
        return "cg_hyperliquid_position_distribution"

    @property
    def description(self) -> str:
        return """Get wallet position distribution on Hyperliquid.

Shows distribution by size tiers including address counts, long/short values, sentiment, and P/L distribution.

Examples:
- Get position distribution: cg_hyperliquid_position_distribution()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_position_distribution)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch position distribution. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

# ==================== Volume & Flow Tools ====================

class TakerVolumeHistoryTool(BaseTool):
    """Get taker buy/sell volume history for a specific trading pair."""

    @property
    def name(self) -> str:
        return "cg_taker_volume_history"

    @property
    def description(self) -> str:
        return """Get historical taker buy/sell volume data for a specific trading pair.

Taker volume = aggressive market orders (vs passive limit orders).
Higher taker buy volume = bullish pressure.
Higher taker sell volume = bearish pressure.

Examples:
- Get BTC taker volume on Binance: cg_taker_volume_history(symbol="BTC", exchange="Binance", interval="1h")
- Get ETH 4h intervals: cg_taker_volume_history(symbol="ETH", exchange="OKX", interval="4h", limit=50)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading coin (BTC, ETH, SOL, etc.)"},
                "exchange": {"type": "string", "description": "Exchange name (Binance, OKX, Bybit, etc.)"},
                "interval": {"type": "string", "description": "Time interval: 1m, 3m, 5m, 15m, 30m, 1h, 4h, 6h, 8h, 12h, 1d, 1w", "default": "1h"},
                "limit": {"type": "integer", "description": "Number of results (default: 1000, max: 4500)", "default": 1000},
                "start_time": {"type": "integer", "description": "Start timestamp in seconds"},
                "end_time": {"type": "integer", "description": "End timestamp in seconds"}
            },
            "required": ["symbol", "exchange"]
        }

    async def execute(self, ctx: ToolContext, symbol: str, exchange: str, interval: str = "1h", limit: int = 1000,
                     start_time: Optional[int] = None, end_time: Optional[int] = None) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_taker_volume_history, symbol, exchange, interval, limit, start_time, end_time)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch taker volume history. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class AggregatedTakerVolumeTool(BaseTool):
    """Get aggregated taker buy/sell volume across all exchanges."""

    @property
    def name(self) -> str:
        return "cg_aggregated_taker_volume"

    @property
    def description(self) -> str:
        return """Get aggregated taker buy/sell volume across all exchanges for a coin.

Shows total market pressure across all major exchanges.
More comprehensive than single-exchange data.

Examples:
- Get BTC aggregated volume: cg_aggregated_taker_volume(symbol="BTC", interval="1h")
- Get ETH 4h: cg_aggregated_taker_volume(symbol="ETH", interval="4h", limit=100)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading coin (BTC, ETH, SOL, etc.)"},
                "exchange_list": {"type": "string", "description": "Comma-separated exchange list (e.g. 'Binance,OKX,Bybit')"},
                "interval": {"type": "string", "description": "Time interval: 1m, 3m, 5m, 15m, 30m, 1h, 4h, 6h, 8h, 12h, 1d, 1w", "default": "1h"},
                "limit": {"type": "integer", "description": "Number of results (default: 1000, max: 4500)", "default": 1000},
                "start_time": {"type": "integer", "description": "Start timestamp in seconds"},
                "end_time": {"type": "integer", "description": "End timestamp in seconds"}
            },
            "required": ["symbol", "exchange_list"]
        }

    async def execute(self, ctx: ToolContext, symbol: str, exchange_list: str, interval: str = "1h", limit: int = 1000,
                     start_time: Optional[int] = None, end_time: Optional[int] = None) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_aggregated_taker_volume, symbol, exchange_list, interval, limit, start_time, end_time)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch aggregated taker volume. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CumulativeVolumeDeltaTool(BaseTool):
    """Get Cumulative Volume Delta (CVD) for trend analysis."""

    @property
    def name(self) -> str:
        return "cg_cumulative_volume_delta"

    @property
    def description(self) -> str:
        return """Get Cumulative Volume Delta (CVD) history for a trading pair.

CVD = Running total of (taker buy volume - taker sell volume).
Rising CVD = accumulation (bullish).
Falling CVD = distribution (bearish).
Divergences between price and CVD signal trend weakness.

Examples:
- Get BTC CVD on Binance: cg_cumulative_volume_delta(symbol="BTC", exchange="Binance", interval="1h")
- Get ETH CVD: cg_cumulative_volume_delta(symbol="ETH", exchange="OKX", interval="4h", limit=100)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading coin (BTC, ETH, SOL, etc.)"},
                "exchange": {"type": "string", "description": "Exchange name (Binance, OKX, Bybit, etc.)"},
                "interval": {"type": "string", "description": "Time interval: 1m, 3m, 5m, 15m, 30m, 1h, 4h, 6h, 8h, 12h, 1d, 1w", "default": "1h"},
                "limit": {"type": "integer", "description": "Number of results (default: 1000, max: 4500)", "default": 1000},
                "start_time": {"type": "integer", "description": "Start timestamp in seconds"},
                "end_time": {"type": "integer", "description": "End timestamp in seconds"}
            },
            "required": ["symbol", "exchange"]
        }

    async def execute(self, ctx: ToolContext, symbol: str, exchange: str, interval: str = "1h", limit: int = 1000,
                     start_time: Optional[int] = None, end_time: Optional[int] = None) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_cumulative_volume_delta, symbol, exchange, interval, limit, start_time, end_time)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch CVD. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CoinNetflowTool(BaseTool):
    """Get netflow data for all futures coins."""

    @property
    def name(self) -> str:
        return "cg_coin_netflow"

    @property
    def description(self) -> str:
        return """Get coin netflow data for all futures coins.

Netflow = Capital flowing into/out of a coin across exchanges.
Positive netflow = accumulation (bullish signal).
Negative netflow = distribution (bearish signal).

Use for identifying which coins are seeing the strongest capital inflows.

Examples:
- Get all coin netflows: cg_coin_netflow()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_coin_netflow)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch coin netflow. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Whale Transfer Tools ====================

class WhaleTransferTool(BaseTool):
    """Get large on-chain transfers (minimum $10M) across major blockchains."""

    @property
    def name(self) -> str:
        return "cg_whale_transfers"

    @property
    def description(self) -> str:
        return """Get large on-chain whale transfers (minimum $10M) within the past 6 months.

Covers major blockchains: Bitcoin, Ethereum, Tron, Ripple, Dogecoin, Litecoin, Polygon, Algorand, Bitcoin Cash, Solana.

Shows transaction hash, asset, amount, exchanges involved, and transfer direction.
Useful for tracking institutional movements and market impact events.

Transfer types:
- 1 = Inflow (to exchange)
- 2 = Outflow (from exchange)
- 3 = Internal (between exchange wallets)

Examples:
- Get recent whale transfers: cg_whale_transfers()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_whale_transfers)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch whale transfers. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Bitcoin ETF Tools ====================

class BTCETFFlowsTool(BaseTool):
    """Get Bitcoin ETF flow history (inflows/outflows)."""

    @property
    def name(self) -> str:
        return "cg_btc_etf_flows"

    @property
    def description(self) -> str:
        return """Get Bitcoin ETF flow history including daily net inflows and outflows.

Shows institutional money movement into/out of Bitcoin through ETFs.
Large inflows = institutional accumulation (bullish).
Large outflows = institutional distribution (bearish).

Examples:
- Get BTC ETF flows: cg_btc_etf_flows()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_btc_etf_flows)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch BTC ETF flows. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class BTCETFPremiumDiscountTool(BaseTool):
    """Get Bitcoin ETF premium/discount rates."""

    @property
    def name(self) -> str:
        return "cg_btc_etf_premium_discount"

    @property
    def description(self) -> str:
        return """Get Bitcoin ETF premium/discount rates.

Shows how ETF market prices compare to their net asset value (NAV).
Premium (positive) = trading above NAV (high demand).
Discount (negative) = trading below NAV (low demand).

Examples:
- Get BTC ETF premium/discount: cg_btc_etf_premium_discount()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_btc_etf_premium_discount)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch BTC ETF premium/discount. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class BTCETFHistoryTool(BaseTool):
    """Get comprehensive Bitcoin ETF history."""

    @property
    def name(self) -> str:
        return "cg_btc_etf_history"

    @property
    def description(self) -> str:
        return """Get comprehensive Bitcoin ETF history.

Includes market price, NAV, premium/discount %, shares outstanding, and net assets.

Examples:
- Get IBIT history: cg_btc_etf_history(ticker="IBIT")
- Get FBTC history: cg_btc_etf_history(ticker="FBTC")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "ETF ticker symbol (e.g. IBIT, FBTC, GBTC)"}
            },
            "required": ["ticker"]
        }

    async def execute(self, ctx: ToolContext, ticker: str) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_btc_etf_history, ticker)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch BTC ETF history. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class BTCETFListTool(BaseTool):
    """Get list of Bitcoin ETFs."""

    @property
    def name(self) -> str:
        return "cg_btc_etf_list"

    @property
    def description(self) -> str:
        return """Get list of Bitcoin ETFs with key status information.

Returns ticker symbols, names, inception dates, and other ETF metadata.

Examples:
- Get BTC ETF list: cg_btc_etf_list()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_btc_etf_list)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch BTC ETF list. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class HKBTCETFFlowsTool(BaseTool):
    """Get Hong Kong Bitcoin ETF flow history."""

    @property
    def name(self) -> str:
        return "cg_hk_btc_etf_flows"

    @property
    def description(self) -> str:
        return """Get Hong Kong Bitcoin ETF flow history.

Shows ETF flow activity for Bitcoin ETFs in the Hong Kong market.
Useful for tracking Asian institutional demand.

Examples:
- Get HK BTC ETF flows: cg_hk_btc_etf_flows()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_hk_btc_etf_flows)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch HK BTC ETF flows. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Ethereum & Other ETF Tools ====================

class ETHETFFlowsTool(BaseTool):
    """Get Ethereum ETF flow history."""

    @property
    def name(self) -> str:
        return "cg_eth_etf_flows"

    @property
    def description(self) -> str:
        return """Get Ethereum ETF flow history including daily net inflows and outflows.

Shows institutional money movement into/out of Ethereum through ETFs.

Examples:
- Get ETH ETF flows: cg_eth_etf_flows()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_eth_etf_flows)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch ETH ETF flows. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class ETHETFListTool(BaseTool):
    """Get list of Ethereum ETFs."""

    @property
    def name(self) -> str:
        return "cg_eth_etf_list"

    @property
    def description(self) -> str:
        return """Get list of Ethereum ETFs with key status information.

Examples:
- Get ETH ETF list: cg_eth_etf_list()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_eth_etf_list)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch ETH ETF list. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class SOLETFFlowsTool(BaseTool):
    """Get Solana ETF flow history."""

    @property
    def name(self) -> str:
        return "cg_sol_etf_flows"

    @property
    def description(self) -> str:
        return """Get Solana ETF flow history including daily net inflows and outflows.

Examples:
- Get SOL ETF flows: cg_sol_etf_flows()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_sol_etf_flows)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch SOL ETF flows. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class XRPETFFlowsTool(BaseTool):
    """Get XRP ETF flow history."""

    @property
    def name(self) -> str:
        return "cg_xrp_etf_flows"

    @property
    def description(self) -> str:
        return """Get XRP ETF flow history including daily net inflows and outflows.

Examples:
- Get XRP ETF flows: cg_xrp_etf_flows()"""

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGLASS_AVAILABLE:
            return ToolResult(success=False, output=None, error="Coinglass tools not available.")

        try:
            result = await asyncio.to_thread(get_xrp_etf_flows)
            if result is None:
                return ToolResult(success=False, output=None, error="Failed to fetch XRP ETF flows. Check COINGLASS_API_KEY.")
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


