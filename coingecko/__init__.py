"""
CoinGecko Extension - Crypto Market Data Tools

Provides comprehensive crypto market data including:
- Price data, charts, OHLC candles
- Market discovery (trending, top gainers/losers, new coins)
- Coin information and tickers
- Exchange data
- NFT collections
- Global market stats

Environment Variables Required:
- COINGECKO_API_KEY: CoinGecko Pro API key

Usage:
    This extension is auto-loaded by the ExtensionLoader.
    Tools are available to agents configured with these tools in agents.yaml.
"""
import os
import sys
import logging
from typing import List

try:
    from core.tool import ToolRegistry
except Exception:
    ToolRegistry = None  # Standalone script usage

logger = logging.getLogger(__name__)

# Add local tools directory to path for imports
TOOLS_DIR = os.path.join(os.path.dirname(__file__), 'tools')
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)


def register(api) -> List[str]:
    """
    Extension entry point - register all CoinGecko tools.

    Args:
        api: ExtensionApi instance with registry and config

    Returns:
        List of registered tool names
    """
    registered = []

    try:
        from .coingecko import (
            # Original tools (11)
            CoinPriceTool,
            CoinOHLCTool,
            CoinChartTool,
            CoinGeckoTrendingTool,
            CoinGeckoTopGainersLosersTool,
            CoinGeckoNewCoinsTool,
            CoinGeckoGlobalTool,
            CoinGeckoGlobalDefiTool,
            CoinGeckoDerivativesTool,
            CoinGeckoDerivativesExchangesTool,
            CoinGeckoCategoriesjTool,
            # New coin data tools (4)
            CoinGeckoCoinsListTool,
            CoinGeckoCoinsMarketsTool,
            CoinGeckoCoinDataTool,
            CoinGeckoCoinTickersTool,
            # New exchange tools (4)
            CoinGeckoExchangesTool,
            CoinGeckoExchangeTool,
            CoinGeckoExchangeTickersTool,
            CoinGeckoExchangeVolumeChartTool,
            # New NFT tools (3)
            CoinGeckoNFTsListTool,
            CoinGeckoNFTTool,
            CoinGeckoNFTByContractTool,
            # New infrastructure tools (4)
            CoinGeckoAssetPlatformsTool,
            CoinGeckoExchangeRatesTool,
            CoinGeckoVsCurrenciesTool,
            CoinGeckoCategoriesListTool,
            # New search tool (1)
            CoinGeckoSearchTool,
            # New contract tools (2)
            CoinGeckoTokenPriceTool,
            CoinGeckoCoinByContractTool,
        )
        # Register original tools
        api.register_tool(CoinPriceTool())
        api.register_tool(CoinOHLCTool())
        api.register_tool(CoinChartTool())
        api.register_tool(CoinGeckoTrendingTool())
        api.register_tool(CoinGeckoTopGainersLosersTool())
        api.register_tool(CoinGeckoNewCoinsTool())
        api.register_tool(CoinGeckoGlobalTool())
        api.register_tool(CoinGeckoGlobalDefiTool())
        api.register_tool(CoinGeckoDerivativesTool())
        api.register_tool(CoinGeckoDerivativesExchangesTool())
        api.register_tool(CoinGeckoCategoriesjTool())
        # Register new coin data tools
        api.register_tool(CoinGeckoCoinsListTool())
        api.register_tool(CoinGeckoCoinsMarketsTool())
        api.register_tool(CoinGeckoCoinDataTool())
        api.register_tool(CoinGeckoCoinTickersTool())
        # Register new exchange tools
        api.register_tool(CoinGeckoExchangesTool())
        api.register_tool(CoinGeckoExchangeTool())
        api.register_tool(CoinGeckoExchangeTickersTool())
        api.register_tool(CoinGeckoExchangeVolumeChartTool())
        # Register new NFT tools
        api.register_tool(CoinGeckoNFTsListTool())
        api.register_tool(CoinGeckoNFTTool())
        api.register_tool(CoinGeckoNFTByContractTool())
        # Register new infrastructure tools
        api.register_tool(CoinGeckoAssetPlatformsTool())
        api.register_tool(CoinGeckoExchangeRatesTool())
        api.register_tool(CoinGeckoVsCurrenciesTool())
        api.register_tool(CoinGeckoCategoriesListTool())
        # Register new search tool
        api.register_tool(CoinGeckoSearchTool())
        # Register new contract tools
        api.register_tool(CoinGeckoTokenPriceTool())
        api.register_tool(CoinGeckoCoinByContractTool())
        registered.extend([
            # Original (11)
            "coin_price",
            "coin_ohlc",
            "coin_chart",
            "cg_trending",
            "cg_top_gainers_losers",
            "cg_new_coins",
            "cg_global",
            "cg_global_defi",
            "cg_derivatives",
            "cg_derivatives_exchanges",
            "cg_categories",
            # New coin data (4)
            "cg_coins_list",
            "cg_coins_markets",
            "cg_coin_data",
            "cg_coin_tickers",
            # New exchanges (4)
            "cg_exchanges",
            "cg_exchange",
            "cg_exchange_tickers",
            "cg_exchange_volume_chart",
            # New NFTs (3)
            "cg_nfts_list",
            "cg_nft",
            "cg_nft_by_contract",
            # New infrastructure (4)
            "cg_asset_platforms",
            "cg_exchange_rates",
            "cg_vs_currencies",
            "cg_categories_list",
            # New search (1)
            "cg_search",
            # New contracts (2)
            "cg_token_price",
            "cg_coin_by_contract",
        ])
        logger.info("Registered CoinGecko tools (29 tools)")
    except Exception as e:
        logger.warning(f"Failed to load CoinGecko tools: {e}")

    return registered


# Extension metadata
EXTENSION_INFO = {
    "name": "coingecko",
    "version": "1.0.0",
    "description": "CoinGecko crypto market data tools",
    "tools": [
        # Price & Chart (3)
        "coin_price",
        "coin_ohlc",
        "coin_chart",
        # Market Discovery (3)
        "cg_trending",
        "cg_top_gainers_losers",
        "cg_new_coins",
        # Global & Categories (3)
        "cg_global",
        "cg_global_defi",
        "cg_categories",
        # Derivatives (2)
        "cg_derivatives",
        "cg_derivatives_exchanges",
        # Coin Data (4)
        "cg_coins_list",
        "cg_coins_markets",
        "cg_coin_data",
        "cg_coin_tickers",
        # Exchanges (4)
        "cg_exchanges",
        "cg_exchange",
        "cg_exchange_tickers",
        "cg_exchange_volume_chart",
        # NFTs (3)
        "cg_nfts_list",
        "cg_nft",
        "cg_nft_by_contract",
        # Infrastructure (5)
        "cg_asset_platforms",
        "cg_exchange_rates",
        "cg_vs_currencies",
        "cg_categories_list",
        "cg_search",
        # Contracts (2)
        "cg_token_price",
        "cg_coin_by_contract",
    ],
    "env_vars": [
        "COINGECKO_API_KEY",
    ],
}
