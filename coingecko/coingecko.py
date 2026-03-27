"""
CoinGecko Tool Wrappers

Wraps tools from /tools/coingecko/ for use in Agent framework.
Provides price data, charts, market discovery, global stats, derivatives,
exchanges, NFTs, infrastructure, search, and contract lookups.
"""
import asyncio
import logging
from typing import List, Optional

from core.tool import BaseTool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

# Import original tools from local tools directory
try:
    from .tools.coin_prices import get_coin_prices_at_timestamps
    from .tools.coin_ohlc_range_by_id import get_coin_ohlc_range_by_id
    from .tools.coin_historical_chart_range_by_id import get_coin_historical_chart_range_by_id
    from .tools.market_discovery import (
        get_trending,
        get_top_gainers_losers,
        get_new_coins,
    )
    from .tools.global_data import (
        get_global,
        get_global_defi,
    )
    from .tools.derivatives import (
        get_derivatives,
        get_derivatives_exchanges,
        get_categories,
    )
    # New imports for expanded API coverage
    from .tools.coins import (
        get_coins_list,
        get_coins_markets,
        get_coin_data,
        get_coin_tickers,
    )
    from .tools.exchanges import (
        get_exchanges,
        get_exchange,
        get_exchange_tickers,
        get_exchange_volume_chart,
    )
    from .tools.nfts import (
        get_nfts_list,
        get_nft,
        get_nft_by_contract,
    )
    from .tools.infrastructure import (
        get_asset_platforms,
        get_exchange_rates,
        get_vs_currencies,
        get_categories_list,
    )
    from .tools.search import search
    from .tools.contracts import (
        get_token_price,
        get_coin_by_contract,
    )
    COINGECKO_AVAILABLE = True
except ImportError as e:
    logger.warning(f"CoinGecko tools not available: {e}")
    COINGECKO_AVAILABLE = False


class CoinPriceTool(BaseTool):
    """
    Get cryptocurrency prices at specific timestamps.

    Supports current price ("now") and historical prices.
    Accepts coin IDs (bitcoin, ethereum) or symbols (BTC, ETH).
    """

    @property
    def name(self) -> str:
        return "coin_price"

    @property
    def description(self) -> str:
        return """Get cryptocurrency prices. Supports current ("now") and historical prices.

If unsure about the coin ID, first use cg_search to find the correct ID.

Examples:
- Get BTC current price: coin_price(coin_ids="bitcoin")
- Get multiple coins: coin_price(coin_ids="BTC,ETH,SOL")
- Get historical price: coin_price(coin_ids="bitcoin", timestamps=["2024-01-01"])"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "coin_ids": {
                    "type": "string",
                    "description": "Coin ID or symbol (bitcoin, BTC) or comma-separated list (BTC,ETH,SOL)"
                },
                "timestamps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of timestamps. Use 'now' for current price, or date strings like '2024-01-01'",
                    "default": ["now"]
                },
                "vs_currency": {
                    "type": "string",
                    "description": "Target currency (usd, eur, btc)",
                    "default": "usd"
                }
            },
            "required": ["coin_ids"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        coin_ids: str,
        timestamps: Optional[List[str]] = None,
        vs_currency: str = "usd"
    ) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available. Check if /tools/coingecko exists."
            )

        try:
            result = await asyncio.to_thread(
                get_coin_prices_at_timestamps,
                coin_ids=coin_ids,
                timestamps=timestamps or ["now"],
                vs_currency=vs_currency
            )
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CoinOHLCTool(BaseTool):
    """
    Get OHLC (candlestick) data for a cryptocurrency.
    """

    @property
    def name(self) -> str:
        return "coin_ohlc"

    @property
    def description(self) -> str:
        return """Get OHLC candlestick data for technical analysis.

Examples:
- Get BTC daily OHLC for last 30 days: coin_ohlc(coin_id="bitcoin", days=30)
- Get ETH 4h candles: coin_ohlc(coin_id="ethereum", days=7)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "coin_id": {
                    "type": "string",
                    "description": "CoinGecko coin ID (bitcoin, ethereum, solana)"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days (1, 7, 14, 30, 90, 180, 365)",
                    "default": 30
                },
                "vs_currency": {
                    "type": "string",
                    "description": "Target currency",
                    "default": "usd"
                }
            },
            "required": ["coin_id"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        coin_id: str,
        days: int = 30,
        vs_currency: str = "usd"
    ) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            import time
            to_timestamp = int(time.time())
            from_timestamp = to_timestamp - (days * 24 * 60 * 60)

            result = await asyncio.to_thread(
                get_coin_ohlc_range_by_id,
                coin_id=coin_id,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp
            )
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CoinChartTool(BaseTool):
    """
    Get historical price chart data for a cryptocurrency.
    """

    @property
    def name(self) -> str:
        return "coin_chart"

    @property
    def description(self) -> str:
        return """Get historical price chart data (prices, market caps, volumes).

Examples:
- Get BTC 30-day chart: coin_chart(coin_id="bitcoin", days=30)
- Get ETH 7-day chart: coin_chart(coin_id="ethereum", days=7)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "coin_id": {
                    "type": "string",
                    "description": "CoinGecko coin ID"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days of data",
                    "default": 30
                },
                "vs_currency": {
                    "type": "string",
                    "default": "usd"
                }
            },
            "required": ["coin_id"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        coin_id: str,
        days: int = 30,
        vs_currency: str = "usd"
    ) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            import time
            to_timestamp = int(time.time())
            from_timestamp = to_timestamp - (days * 24 * 60 * 60)

            result = await asyncio.to_thread(
                get_coin_historical_chart_range_by_id,
                coin_id=coin_id,
                vs_currency=vs_currency,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp
            )
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Market Discovery Tools ====================

class CoinGeckoTrendingTool(BaseTool):
    """
    Get trending coins based on user search data.
    """

    @property
    def name(self) -> str:
        return "cg_trending"

    @property
    def description(self) -> str:
        return """Get trending coins in the last 24 hours based on user search data.

Also returns trending NFTs and categories.

Examples:
- Get trending: cg_trending()"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {}
        }

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(get_trending)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CoinGeckoTopGainersLosersTool(BaseTool):
    """
    Get top gainers and losers by price change.
    """

    @property
    def name(self) -> str:
        return "cg_top_gainers_losers"

    @property
    def description(self) -> str:
        return """Get top 30 gainers and losers by price change percentage.

Examples:
- Get 24h movers: cg_top_gainers_losers()
- Get 7d movers: cg_top_gainers_losers(duration="7d")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "vs_currency": {
                    "type": "string",
                    "description": "Target currency",
                    "default": "usd"
                },
                "duration": {
                    "type": "string",
                    "description": "Time duration: 1h, 24h, 7d, 14d, 30d, 60d, 1y",
                    "default": "24h"
                }
            }
        }

    async def execute(
        self,
        ctx: ToolContext,
        vs_currency: str = "usd",
        duration: str = "24h"
    ) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(get_top_gainers_losers, vs_currency, duration)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CoinGeckoNewCoinsTool(BaseTool):
    """
    Get recently added coins.
    """

    @property
    def name(self) -> str:
        return "cg_new_coins"

    @property
    def description(self) -> str:
        return """Get recently added coins to CoinGecko.

Examples:
- Get new coins: cg_new_coins()"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {}
        }

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(get_new_coins)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Global Data Tools ====================

class CoinGeckoGlobalTool(BaseTool):
    """
    Get global cryptocurrency market statistics.
    """

    @property
    def name(self) -> str:
        return "cg_global"

    @property
    def description(self) -> str:
        return """Get global cryptocurrency market statistics.

Returns total market cap, volume, BTC dominance, and more.

Examples:
- Get global stats: cg_global()"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {}
        }

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(get_global)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CoinGeckoGlobalDefiTool(BaseTool):
    """
    Get global DeFi market statistics.
    """

    @property
    def name(self) -> str:
        return "cg_global_defi"

    @property
    def description(self) -> str:
        return """Get global DeFi market statistics.

Returns DeFi market cap, TVL, DeFi dominance.

Examples:
- Get DeFi stats: cg_global_defi()"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {}
        }

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(get_global_defi)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Derivatives Tools ====================

class CoinGeckoDerivativesTool(BaseTool):
    """
    Get all derivatives tickers.
    """

    @property
    def name(self) -> str:
        return "cg_derivatives"

    @property
    def description(self) -> str:
        return """Get all derivatives tickers (perpetuals, futures).

Includes funding rates, open interest, spread, basis.

Examples:
- Get all derivatives: cg_derivatives()
- Get unexpired only: cg_derivatives(include_tickers="unexpired")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "include_tickers": {
                    "type": "string",
                    "description": "Filter: all or unexpired",
                    "default": "unexpired"
                }
            }
        }

    async def execute(
        self,
        ctx: ToolContext,
        include_tickers: str = "unexpired"
    ) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(get_derivatives, include_tickers)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CoinGeckoDerivativesExchangesTool(BaseTool):
    """
    Get derivatives exchanges with rankings.
    """

    @property
    def name(self) -> str:
        return "cg_derivatives_exchanges"

    @property
    def description(self) -> str:
        return """Get list of derivatives exchanges with ranking.

Sorted by open interest or volume.

Examples:
- Get exchanges by OI: cg_derivatives_exchanges()
- Get exchanges by volume: cg_derivatives_exchanges(order="trade_volume_24h_btc_desc")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "order": {
                    "type": "string",
                    "description": "Sort order",
                    "default": "open_interest_btc_desc"
                },
                "per_page": {
                    "type": "integer",
                    "description": "Results per page (max 100)",
                    "default": 50
                }
            }
        }

    async def execute(
        self,
        ctx: ToolContext,
        order: str = "open_interest_btc_desc",
        per_page: int = 50
    ) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(get_derivatives_exchanges, order, per_page)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CoinGeckoCategoriesjTool(BaseTool):
    """
    Get coin categories with market data.
    """

    @property
    def name(self) -> str:
        return "cg_categories"

    @property
    def description(self) -> str:
        return """Get coin categories with market data (DeFi, L1, L2, Memes, etc.).

See sector performance and top coins in each category.

Examples:
- Get categories by market cap: cg_categories()
- Get categories by 24h change: cg_categories(order="market_cap_change_24h_desc")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "order": {
                    "type": "string",
                    "description": "Sort order: market_cap_desc, market_cap_change_24h_desc, etc.",
                    "default": "market_cap_desc"
                }
            }
        }

    async def execute(
        self,
        ctx: ToolContext,
        order: str = "market_cap_desc"
    ) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(get_categories, order)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Coin Data Tools ====================

class CoinGeckoCoinsListTool(BaseTool):
    """
    Get all supported coins with IDs, names, and symbols.
    """

    @property
    def name(self) -> str:
        return "cg_coins_list"

    @property
    def description(self) -> str:
        return """Get all supported coins with id, symbol, and name.

Useful for coin discovery and ID lookup.

Examples:
- Get all coins: cg_coins_list()
- Get coins with platform addresses: cg_coins_list(include_platform=True)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "include_platform": {
                    "type": "boolean",
                    "description": "Include platform contract addresses",
                    "default": False
                }
            }
        }

    async def execute(
        self,
        ctx: ToolContext,
        include_platform: bool = False
    ) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(get_coins_list, include_platform)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CoinGeckoCoinsMarketsTool(BaseTool):
    """
    Get bulk market data for coins with sorting and filtering.
    """

    @property
    def name(self) -> str:
        return "cg_coins_markets"

    @property
    def description(self) -> str:
        return """Get market data for coins with sorting, filtering, and pagination.

Screen coins by market cap, volume, price change, or category.

Examples:
- Get top 100 by market cap: cg_coins_markets()
- Get top by volume: cg_coins_markets(order="volume_desc")
- Get DeFi coins: cg_coins_markets(category="decentralized-finance-defi")
- Get specific coins: cg_coins_markets(ids="bitcoin,ethereum,solana")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "vs_currency": {
                    "type": "string",
                    "description": "Target currency (usd, eur, btc)",
                    "default": "usd"
                },
                "order": {
                    "type": "string",
                    "description": "Sort order: market_cap_desc, volume_desc, price_change_24h_desc",
                    "default": "market_cap_desc"
                },
                "per_page": {
                    "type": "integer",
                    "description": "Results per page (max 250)",
                    "default": 100
                },
                "page": {
                    "type": "integer",
                    "description": "Page number",
                    "default": 1
                },
                "sparkline": {
                    "type": "boolean",
                    "description": "Include 7-day sparkline data",
                    "default": False
                },
                "price_change_percentage": {
                    "type": "string",
                    "description": "Price change periods (comma-separated): 1h, 24h, 7d, 14d, 30d, 200d, 1y",
                    "default": "24h"
                },
                "category": {
                    "type": "string",
                    "description": "Filter by category id"
                },
                "ids": {
                    "type": "string",
                    "description": "Comma-separated coin ids to filter"
                }
            }
        }

    async def execute(
        self,
        ctx: ToolContext,
        vs_currency: str = "usd",
        order: str = "market_cap_desc",
        per_page: int = 100,
        page: int = 1,
        sparkline: bool = False,
        price_change_percentage: str = "24h",
        category: Optional[str] = None,
        ids: Optional[str] = None
    ) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(
                get_coins_markets,
                vs_currency=vs_currency,
                order=order,
                per_page=per_page,
                page=page,
                sparkline=sparkline,
                price_change_percentage=price_change_percentage,
                category=category,
                ids=ids
            )
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CoinGeckoCoinDataTool(BaseTool):
    """
    Get full coin metadata including description, links, ATH, ATL.
    """

    @property
    def name(self) -> str:
        return "cg_coin_data"

    @property
    def description(self) -> str:
        return """Get comprehensive coin data including description, links, ATH, ATL, market data.

Deep research on specific coin.

Examples:
- Get Bitcoin data: cg_coin_data(coin_id="bitcoin")
- Include tickers: cg_coin_data(coin_id="ethereum", tickers=True)
- Full data: cg_coin_data(coin_id="solana", community_data=True, developer_data=True)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "coin_id": {
                    "type": "string",
                    "description": "CoinGecko coin ID (bitcoin, ethereum, solana)"
                },
                "localization": {
                    "type": "boolean",
                    "description": "Include localized languages",
                    "default": False
                },
                "tickers": {
                    "type": "boolean",
                    "description": "Include tickers data",
                    "default": False
                },
                "market_data": {
                    "type": "boolean",
                    "description": "Include market data",
                    "default": True
                },
                "community_data": {
                    "type": "boolean",
                    "description": "Include community data",
                    "default": False
                },
                "developer_data": {
                    "type": "boolean",
                    "description": "Include developer data",
                    "default": False
                },
                "sparkline": {
                    "type": "boolean",
                    "description": "Include sparkline 7 days data",
                    "default": False
                }
            },
            "required": ["coin_id"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        coin_id: str,
        localization: bool = False,
        tickers: bool = False,
        market_data: bool = True,
        community_data: bool = False,
        developer_data: bool = False,
        sparkline: bool = False
    ) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(
                get_coin_data,
                coin_id=coin_id,
                localization=localization,
                tickers=tickers,
                market_data=market_data,
                community_data=community_data,
                developer_data=developer_data,
                sparkline=sparkline
            )
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CoinGeckoCoinTickersTool(BaseTool):
    """
    Get all trading pairs/tickers for a coin across exchanges.
    """

    @property
    def name(self) -> str:
        return "cg_coin_tickers"

    @property
    def description(self) -> str:
        return """Get all trading pairs/tickers for a coin across exchanges.

Find liquidity and arbitrage opportunities.

Examples:
- Get BTC tickers: cg_coin_tickers(coin_id="bitcoin")
- Filter by exchange: cg_coin_tickers(coin_id="ethereum", exchange_ids="binance")
- With depth: cg_coin_tickers(coin_id="solana", depth=True)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "coin_id": {
                    "type": "string",
                    "description": "CoinGecko coin ID"
                },
                "exchange_ids": {
                    "type": "string",
                    "description": "Comma-separated exchange ids to filter"
                },
                "include_exchange_logo": {
                    "type": "boolean",
                    "description": "Include exchange logo",
                    "default": False
                },
                "page": {
                    "type": "integer",
                    "description": "Page number",
                    "default": 1
                },
                "order": {
                    "type": "string",
                    "description": "Sort order: trust_score_desc, volume_desc",
                    "default": "volume_desc"
                },
                "depth": {
                    "type": "boolean",
                    "description": "Include order book depth",
                    "default": False
                }
            },
            "required": ["coin_id"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        coin_id: str,
        exchange_ids: Optional[str] = None,
        include_exchange_logo: bool = False,
        page: int = 1,
        order: str = "volume_desc",
        depth: bool = False
    ) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(
                get_coin_tickers,
                coin_id=coin_id,
                exchange_ids=exchange_ids,
                include_exchange_logo=include_exchange_logo,
                page=page,
                order=order,
                depth=depth
            )
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Exchange Tools ====================

class CoinGeckoExchangesTool(BaseTool):
    """
    Get all spot exchanges with volumes and trust scores.
    """

    @property
    def name(self) -> str:
        return "cg_exchanges"

    @property
    def description(self) -> str:
        return """Get all spot exchanges with volumes and trust scores.

Compare exchanges by volume and trust.

Examples:
- Get top 100 exchanges: cg_exchanges()
- Paginate: cg_exchanges(per_page=50, page=2)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "per_page": {
                    "type": "integer",
                    "description": "Results per page (max 250)",
                    "default": 100
                },
                "page": {
                    "type": "integer",
                    "description": "Page number",
                    "default": 1
                }
            }
        }

    async def execute(
        self,
        ctx: ToolContext,
        per_page: int = 100,
        page: int = 1
    ) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(get_exchanges, per_page, page)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CoinGeckoExchangeTool(BaseTool):
    """
    Get detailed exchange data.
    """

    @property
    def name(self) -> str:
        return "cg_exchange"

    @property
    def description(self) -> str:
        return """Get detailed exchange data including tickers and BTC volume.

Research specific exchange.

Examples:
- Get Binance data: cg_exchange(exchange_id="binance")
- Get Coinbase data: cg_exchange(exchange_id="coinbase-exchange")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "exchange_id": {
                    "type": "string",
                    "description": "CoinGecko exchange ID (binance, coinbase-exchange)"
                }
            },
            "required": ["exchange_id"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        exchange_id: str
    ) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(get_exchange, exchange_id)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CoinGeckoExchangeTickersTool(BaseTool):
    """
    Get all trading pairs on an exchange.
    """

    @property
    def name(self) -> str:
        return "cg_exchange_tickers"

    @property
    def description(self) -> str:
        return """Get all trading pairs on an exchange.

Find trading opportunities on specific exchange.

Examples:
- Get Binance pairs: cg_exchange_tickers(exchange_id="binance")
- Filter by coin: cg_exchange_tickers(exchange_id="coinbase-exchange", coin_ids="bitcoin")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "exchange_id": {
                    "type": "string",
                    "description": "CoinGecko exchange ID"
                },
                "coin_ids": {
                    "type": "string",
                    "description": "Comma-separated coin ids to filter"
                },
                "include_exchange_logo": {
                    "type": "boolean",
                    "description": "Include exchange logo",
                    "default": False
                },
                "page": {
                    "type": "integer",
                    "description": "Page number",
                    "default": 1
                },
                "order": {
                    "type": "string",
                    "description": "Sort order: trust_score_desc, volume_desc",
                    "default": "volume_desc"
                },
                "depth": {
                    "type": "boolean",
                    "description": "Include order book depth",
                    "default": False
                }
            },
            "required": ["exchange_id"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        exchange_id: str,
        coin_ids: Optional[str] = None,
        include_exchange_logo: bool = False,
        page: int = 1,
        order: str = "volume_desc",
        depth: bool = False
    ) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(
                get_exchange_tickers,
                exchange_id=exchange_id,
                coin_ids=coin_ids,
                include_exchange_logo=include_exchange_logo,
                page=page,
                order=order,
                depth=depth
            )
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CoinGeckoExchangeVolumeChartTool(BaseTool):
    """
    Get historical volume chart for an exchange.
    """

    @property
    def name(self) -> str:
        return "cg_exchange_volume_chart"

    @property
    def description(self) -> str:
        return """Get historical volume chart for an exchange.

Track exchange growth over time.

Examples:
- Get Binance 30-day volume: cg_exchange_volume_chart(exchange_id="binance")
- Get 90-day history: cg_exchange_volume_chart(exchange_id="coinbase-exchange", days=90)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "exchange_id": {
                    "type": "string",
                    "description": "CoinGecko exchange ID"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days (1, 7, 14, 30, 90, 180, 365)",
                    "default": 30
                }
            },
            "required": ["exchange_id"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        exchange_id: str,
        days: int = 30
    ) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(get_exchange_volume_chart, exchange_id, days)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== NFT Tools ====================

class CoinGeckoNFTsListTool(BaseTool):
    """
    Get all NFT collections.
    """

    @property
    def name(self) -> str:
        return "cg_nfts_list"

    @property
    def description(self) -> str:
        return """Get all NFT collections with IDs and contract addresses.

NFT discovery.

Examples:
- Get top NFTs by market cap: cg_nfts_list()
- Sort by volume: cg_nfts_list(order="h24_volume_usd_desc")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "order": {
                    "type": "string",
                    "description": "Sort order: market_cap_usd_desc, h24_volume_usd_desc",
                    "default": "market_cap_usd_desc"
                },
                "per_page": {
                    "type": "integer",
                    "description": "Results per page (max 250)",
                    "default": 100
                },
                "page": {
                    "type": "integer",
                    "description": "Page number",
                    "default": 1
                }
            }
        }

    async def execute(
        self,
        ctx: ToolContext,
        order: str = "market_cap_usd_desc",
        per_page: int = 100,
        page: int = 1
    ) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(get_nfts_list, order, per_page, page)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CoinGeckoNFTTool(BaseTool):
    """
    Get NFT collection data.
    """

    @property
    def name(self) -> str:
        return "cg_nft"

    @property
    def description(self) -> str:
        return """Get NFT collection data including floor price, volume, market cap.

NFT research.

Examples:
- Get Bored Apes: cg_nft(nft_id="bored-ape-yacht-club")
- Get CryptoPunks: cg_nft(nft_id="cryptopunks")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "nft_id": {
                    "type": "string",
                    "description": "CoinGecko NFT collection ID"
                }
            },
            "required": ["nft_id"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        nft_id: str
    ) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(get_nft, nft_id)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CoinGeckoNFTByContractTool(BaseTool):
    """
    Get NFT collection by contract address.
    """

    @property
    def name(self) -> str:
        return "cg_nft_by_contract"

    @property
    def description(self) -> str:
        return """Get NFT collection by contract address.

On-chain NFT lookup.

Examples:
- Get BAYC by contract: cg_nft_by_contract(asset_platform="ethereum", contract_address="0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "asset_platform": {
                    "type": "string",
                    "description": "Asset platform id (ethereum, solana)"
                },
                "contract_address": {
                    "type": "string",
                    "description": "NFT contract address"
                }
            },
            "required": ["asset_platform", "contract_address"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        asset_platform: str,
        contract_address: str
    ) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(get_nft_by_contract, asset_platform, contract_address)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Infrastructure Tools ====================

class CoinGeckoAssetPlatformsTool(BaseTool):
    """
    Get all blockchain networks/asset platforms.
    """

    @property
    def name(self) -> str:
        return "cg_asset_platforms"

    @property
    def description(self) -> str:
        return """Get all blockchain networks (Ethereum, Solana, etc.).

Filter by chain.

Examples:
- Get all platforms: cg_asset_platforms()
- Filter NFT platforms: cg_asset_platforms(filter="nft")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "Filter platforms (e.g., nft)"
                }
            }
        }

    async def execute(
        self,
        ctx: ToolContext,
        filter: Optional[str] = None
    ) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(get_asset_platforms, filter)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CoinGeckoExchangeRatesTool(BaseTool):
    """
    Get BTC exchange rates to all fiat currencies.
    """

    @property
    def name(self) -> str:
        return "cg_exchange_rates"

    @property
    def description(self) -> str:
        return """Get BTC exchange rates to all fiat currencies.

Currency conversion.

Examples:
- Get exchange rates: cg_exchange_rates()"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {}
        }

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(get_exchange_rates)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CoinGeckoVsCurrenciesTool(BaseTool):
    """
    Get list of supported quote currencies.
    """

    @property
    def name(self) -> str:
        return "cg_vs_currencies"

    @property
    def description(self) -> str:
        return """Get list of supported quote currencies (vs_currencies).

Reference data.

Examples:
- Get supported currencies: cg_vs_currencies()"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {}
        }

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(get_vs_currencies)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CoinGeckoCategoriesListTool(BaseTool):
    """
    Get lightweight list of category names and IDs.
    """

    @property
    def name(self) -> str:
        return "cg_categories_list"

    @property
    def description(self) -> str:
        return """Get lightweight list of category names and IDs (no market data).

Quick lookup.

Examples:
- Get categories list: cg_categories_list()"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {}
        }

    async def execute(self, ctx: ToolContext) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(get_categories_list)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Search Tool ====================

class CoinGeckoSearchTool(BaseTool):
    """
    Search for coins, exchanges, categories, and NFTs.
    """

    @property
    def name(self) -> str:
        return "cg_search"

    @property
    def description(self) -> str:
        return """Search for coins, exchanges, categories, and NFTs.

Discovery across all CoinGecko data.

Examples:
- Search for Solana: cg_search(query="solana")
- Search for DeFi: cg_search(query="defi")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                }
            },
            "required": ["query"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        query: str
    ) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(search, query)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Contract Tools ====================

class CoinGeckoTokenPriceTool(BaseTool):
    """
    Get token prices by contract address.
    """

    @property
    def name(self) -> str:
        return "cg_token_price"

    @property
    def description(self) -> str:
        return """Get token prices by contract address.

On-chain pricing.

Examples:
- Get USDC price on Ethereum: cg_token_price(platform="ethereum", contract_addresses="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")
- Multiple tokens: cg_token_price(platform="ethereum", contract_addresses="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48,0xdac17f958d2ee523a2206206994597c13d831ec7")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "description": "Asset platform id (ethereum, solana, polygon-pos)"
                },
                "contract_addresses": {
                    "type": "string",
                    "description": "Comma-separated contract addresses"
                },
                "vs_currencies": {
                    "type": "string",
                    "description": "Comma-separated target currencies (usd, eur, btc)",
                    "default": "usd"
                },
                "include_market_cap": {
                    "type": "boolean",
                    "description": "Include market cap",
                    "default": False
                },
                "include_24hr_vol": {
                    "type": "boolean",
                    "description": "Include 24h volume",
                    "default": False
                },
                "include_24hr_change": {
                    "type": "boolean",
                    "description": "Include 24h price change",
                    "default": False
                },
                "include_last_updated_at": {
                    "type": "boolean",
                    "description": "Include last updated timestamp",
                    "default": False
                }
            },
            "required": ["platform", "contract_addresses"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        platform: str,
        contract_addresses: str,
        vs_currencies: str = "usd",
        include_market_cap: bool = False,
        include_24hr_vol: bool = False,
        include_24hr_change: bool = False,
        include_last_updated_at: bool = False
    ) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(
                get_token_price,
                platform=platform,
                contract_addresses=contract_addresses,
                vs_currencies=vs_currencies,
                include_market_cap=include_market_cap,
                include_24hr_vol=include_24hr_vol,
                include_24hr_change=include_24hr_change,
                include_last_updated_at=include_last_updated_at
            )
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class CoinGeckoCoinByContractTool(BaseTool):
    """
    Get coin data by contract address.
    """

    @property
    def name(self) -> str:
        return "cg_coin_by_contract"

    @property
    def description(self) -> str:
        return """Get coin data by contract address.

On-chain lookup.

Examples:
- Get USDC on Ethereum: cg_coin_by_contract(platform="ethereum", contract_address="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "description": "Asset platform id (ethereum, solana, polygon-pos)"
                },
                "contract_address": {
                    "type": "string",
                    "description": "Token contract address"
                }
            },
            "required": ["platform", "contract_address"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        platform: str,
        contract_address: str
    ) -> ToolResult:
        if not COINGECKO_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="CoinGecko tools not available."
            )

        try:
            result = await asyncio.to_thread(get_coin_by_contract, platform, contract_address)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
