"""
Polymarket Skill v4.0 — Prediction Markets Trading

Privy-only. 13 tools: auth(1) + discovery(4) + trading(8).
No CLI dependency. No private key export.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


def register(api) -> List[str]:
    registered = []

    try:
        from .polymarket import (
            # Authentication (1)
            PolymarketAuthTool,
            # Discovery (4)
            PolymarketSearchTool,
            PolymarketLookupTool,
            PolymarketOrderbookTool,
            PolymarketRRAnalysisTool,
            # Trading (8)
            PolymarketGetBalanceTool,
            PolymarketGetOrdersTool,
            PolymarketGetPositionsTool,
            PolymarketGetTradesTool,
            PolymarketPrepareOrderTool,
            PolymarketPostOrderTool,
            PolymarketCancelOrderTool,
            PolymarketCancelAllTool,
        )

        for tool_cls in [
            PolymarketAuthTool,
            PolymarketSearchTool,
            PolymarketLookupTool,
            PolymarketOrderbookTool,
            PolymarketRRAnalysisTool,
            PolymarketGetBalanceTool,
            PolymarketGetOrdersTool,
            PolymarketGetPositionsTool,
            PolymarketGetTradesTool,
            PolymarketPrepareOrderTool,
            PolymarketPostOrderTool,
            PolymarketCancelOrderTool,
            PolymarketCancelAllTool,
        ]:
            tool = tool_cls()
            api.register_tool(tool)
            registered.append(tool.name)

        logger.info(f"Registered {len(registered)} Polymarket tools (Privy-only, v4.0)")
    except Exception as e:
        logger.warning(f"Failed to load Polymarket tools: {e}")

    return registered


EXTENSION_INFO = {
    "name": "polymarket",
    "version": "4.0.0",
    "description": "Polymarket prediction markets — Privy-only, 13 tools, search-v2 + VPN auto-detect",
    "tools": [
        "polymarket_auth",
        "polymarket_search",
        "polymarket_lookup",
        "polymarket_orderbook",
        "polymarket_rr_analysis",
        "polymarket_get_balances",
        "polymarket_get_orders",
        "polymarket_get_positions",
        "polymarket_get_trades",
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
