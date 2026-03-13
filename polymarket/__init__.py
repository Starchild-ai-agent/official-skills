"""
Polymarket Extension — Browse and Analyze Prediction Markets

Provides 10 read-only tools for Polymarket prediction markets:
- Market discovery: search, markets, event, tags
- Price & trading: price, book, history, trades
- Analytics: leaderboard, holders

No API key required — all endpoints are public.

Usage:
    This extension is auto-loaded by the ExtensionLoader.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


def register(api) -> List[str]:
    """
    Extension entry point — register all Polymarket tools.

    Args:
        api: ExtensionApi instance with registry and config

    Returns:
        List of registered tool names
    """
    registered = []

    try:
        from .tools import (
            # Market Discovery (4)
            PolymarketSearchTool,
            PolymarketMarketsTool,
            PolymarketEventTool,
            PolymarketTagsTool,
            # Price & Trading Data (4)
            PolymarketPriceTool,
            PolymarketBookTool,
            PolymarketHistoryTool,
            PolymarketTradesTool,
            # Analytics (2)
            PolymarketLeaderboardTool,
            PolymarketHoldersTool,
        )

        # Market Discovery
        api.register_tool(PolymarketSearchTool())
        api.register_tool(PolymarketMarketsTool())
        api.register_tool(PolymarketEventTool())
        api.register_tool(PolymarketTagsTool())

        # Price & Trading Data
        api.register_tool(PolymarketPriceTool())
        api.register_tool(PolymarketBookTool())
        api.register_tool(PolymarketHistoryTool())
        api.register_tool(PolymarketTradesTool())

        # Analytics
        api.register_tool(PolymarketLeaderboardTool())
        api.register_tool(PolymarketHoldersTool())

        registered = [
            "polymarket_search",
            "polymarket_markets",
            "polymarket_event",
            "polymarket_tags",
            "polymarket_price",
            "polymarket_book",
            "polymarket_history",
            "polymarket_trades",
            "polymarket_leaderboard",
            "polymarket_holders",
        ]

        logger.info(f"Registered Polymarket tools ({len(registered)} tools)")
    except Exception as e:
        logger.warning(f"Failed to load Polymarket tools: {e}")

    return registered


# Extension metadata
EXTENSION_INFO = {
    "name": "polymarket",
    "version": "1.0.0",
    "description": "Polymarket prediction markets — browse, search, and analyze event probabilities",
    "tools": [
        "polymarket_search",
        "polymarket_markets",
        "polymarket_event",
        "polymarket_tags",
        "polymarket_price",
        "polymarket_book",
        "polymarket_history",
        "polymarket_trades",
        "polymarket_leaderboard",
        "polymarket_holders",
    ],
    "env_vars": [],
}
