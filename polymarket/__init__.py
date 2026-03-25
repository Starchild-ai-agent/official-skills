"""
Polymarket Skill — Prediction Markets Trading

API-based Polymarket prediction markets integration.
Uses direct CLOB and Gamma API calls (no CLI dependency).

Provides 14 tools for market discovery, research, and trading:
- Authentication (1): API credential creation
- Market data (4): lookup, search, orderbook, R/R analysis
- Trading (9): balance, orders, positions, trades, quick_prepare🚀, prepare/post order, cancel

🚀 polymarket_quick_prepare: Fast unified workflow (balance + orderbook + R/R + order prep in ONE call)

No Rust CLI dependency - pure Python API integration.
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
        from .polymarket import (
            # Authentication (1)
            PolymarketAuthTool,
            # Market Discovery (4)
            PolymarketLookupTool,
            PolymarketSearchTool,
            PolymarketOrderbookTool,
            PolymarketRRAnalysisTool,
            # Trading (9 - added quick_prepare)
            PolymarketGetBalanceTool,
            PolymarketGetOrdersTool,
            PolymarketGetPositionsTool,
            PolymarketGetTradesTool,
            PolymarketQuickPrepareTool,  # 🚀 Fast unified preparation
            PolymarketPrepareOrderTool,
            PolymarketPostOrderTool,
            PolymarketCancelOrderTool,
            PolymarketCancelAllTool,
        )

        # Register Authentication
        api.register_tool(PolymarketAuthTool())

        # Register Market Discovery
        api.register_tool(PolymarketLookupTool())
        api.register_tool(PolymarketSearchTool())
        api.register_tool(PolymarketOrderbookTool())
        api.register_tool(PolymarketRRAnalysisTool())

        # Register Trading
        api.register_tool(PolymarketGetBalanceTool())
        api.register_tool(PolymarketGetOrdersTool())
        api.register_tool(PolymarketGetPositionsTool())
        api.register_tool(PolymarketGetTradesTool())
        api.register_tool(PolymarketQuickPrepareTool())  # 🚀 Fast workflow
        api.register_tool(PolymarketPrepareOrderTool())
        api.register_tool(PolymarketPostOrderTool())
        api.register_tool(PolymarketCancelOrderTool())
        api.register_tool(PolymarketCancelAllTool())

        registered = [
            # Authentication
            "polymarket_auth",
            # Market Discovery
            "polymarket_lookup",
            "polymarket_search",
            "polymarket_orderbook",
            "polymarket_rr_analysis",
            # Trading
            "polymarket_get_balance",
            "polymarket_get_orders",
            "polymarket_get_positions",
            "polymarket_get_trades",
            "polymarket_quick_prepare",  # 🚀 Fast unified prep
            "polymarket_prepare_order",
            "polymarket_post_order",
            "polymarket_cancel_order",
            "polymarket_cancel_all",
        ]

        logger.info(f"Registered Polymarket tools ({len(registered)} API-based tools)")
    except Exception as e:
        logger.warning(f"Failed to load Polymarket tools: {e}")

    return registered


# Extension metadata
EXTENSION_INFO = {
    "name": "polymarket",
    "version": "2.2.0",  # Auto VPN detection - zero config geo-unblocking
    "description": "Polymarket prediction markets via API — market research and trading",
    "tools": [
        # Authentication (1)
        "polymarket_auth",
        # Market Discovery (4)
        "polymarket_lookup",
        "polymarket_search",
        "polymarket_orderbook",
        "polymarket_rr_analysis",
        # Trading (9)
        "polymarket_get_balance",
        "polymarket_get_orders",
        "polymarket_get_positions",
        "polymarket_get_trades",
        "polymarket_quick_prepare",  # 🚀 Optimized fast workflow
        "polymarket_prepare_order",
        "polymarket_post_order",
        "polymarket_cancel_order",
        "polymarket_cancel_all",
    ],
    "env_vars": [
        "POLY_API_KEY",
        "POLY_SECRET",
        "POLY_PASSPHRASE",
        "POLY_WALLET",
    ],
}
