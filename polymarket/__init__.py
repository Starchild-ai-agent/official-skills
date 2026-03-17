"""
Polymarket Skill — Browse, Analyze, and Trade Prediction Markets

Uses the official Polymarket Rust CLI for all operations.

Provides 21 tools for Polymarket prediction markets:
- Market data (6): markets, event, tags, price, book, leaderboard
- Trading (8): limit/market orders, cancel orders, get orders/positions/balances/trades
- Approvals (2): check/set contract approvals
- CTF operations (3): split, merge, redeem conditional tokens
- Bridge (2): deposit addresses, deposit status

Market data requires no authentication.
Trading and on-chain operations require wallet configuration via polymarket wallet commands.

No Privy wallet integration - users manage their own private keys.
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
            # Market Data (6)
            PolymarketMarketsTool,
            PolymarketEventTool,
            PolymarketTagsTool,
            PolymarketPriceTool,
            PolymarketBookTool,
            PolymarketLeaderboardTool,
            # Trading (8)
            PolymarketPlaceLimitOrderTool,
            PolymarketPlaceMarketOrderTool,
            PolymarketCancelOrderTool,
            PolymarketCancelAllOrdersTool,
            PolymarketGetOrdersTool,
            PolymarketGetBalancesTool,
            PolymarketGetPositionsTool,
            PolymarketGetTradesTool,
            # Approvals (2)
            PolymarketCheckApprovalsTool,
            PolymarketSetApprovalsTool,
            # CTF Operations (3)
            PolymarketCTFSplitTool,
            PolymarketCTFMergeTool,
            PolymarketCTFRedeemTool,
            # Bridge (2)
            PolymarketBridgeDepositTool,
            PolymarketBridgeStatusTool,
        )

        # Market Data (6)
        api.register_tool(PolymarketMarketsTool())
        api.register_tool(PolymarketEventTool())
        api.register_tool(PolymarketTagsTool())
        api.register_tool(PolymarketPriceTool())
        api.register_tool(PolymarketBookTool())
        api.register_tool(PolymarketLeaderboardTool())

        # Trading (8)
        api.register_tool(PolymarketPlaceLimitOrderTool())
        api.register_tool(PolymarketPlaceMarketOrderTool())
        api.register_tool(PolymarketCancelOrderTool())
        api.register_tool(PolymarketCancelAllOrdersTool())
        api.register_tool(PolymarketGetOrdersTool())
        api.register_tool(PolymarketGetBalancesTool())
        api.register_tool(PolymarketGetPositionsTool())
        api.register_tool(PolymarketGetTradesTool())

        # Approvals (2)
        api.register_tool(PolymarketCheckApprovalsTool())
        api.register_tool(PolymarketSetApprovalsTool())

        # CTF Operations (3)
        api.register_tool(PolymarketCTFSplitTool())
        api.register_tool(PolymarketCTFMergeTool())
        api.register_tool(PolymarketCTFRedeemTool())

        # Bridge (2)
        api.register_tool(PolymarketBridgeDepositTool())
        api.register_tool(PolymarketBridgeStatusTool())

        registered = [
            # Market Data
            "polymarket_markets",
            "polymarket_event",
            "polymarket_tags",
            "polymarket_price",
            "polymarket_book",
            "polymarket_leaderboard",
            # Trading
            "polymarket_place_limit_order",
            "polymarket_place_market_order",
            "polymarket_cancel_order",
            "polymarket_cancel_all_orders",
            "polymarket_get_orders",
            "polymarket_get_balances",
            "polymarket_get_positions",
            "polymarket_get_trades",
            # Approvals
            "polymarket_check_approvals",
            "polymarket_set_approvals",
            # CTF Operations
            "polymarket_ctf_split",
            "polymarket_ctf_merge",
            "polymarket_ctf_redeem",
            # Bridge
            "polymarket_bridge_deposit",
            "polymarket_bridge_status",
        ]

        logger.info(f"Registered Polymarket tools ({len(registered)} tools via official Rust CLI)")
    except Exception as e:
        logger.warning(f"Failed to load Polymarket tools: {e}")

    return registered


# Extension metadata
EXTENSION_INFO = {
    "name": "polymarket",
    "version": "5.0.0",
    "description": "Polymarket prediction markets via official Rust CLI — market data, analytics, trading, CTF operations, approvals, and bridge deposits",
    "tools": [
        # Market Data (6)
        "polymarket_markets",
        "polymarket_event",
        "polymarket_tags",
        "polymarket_price",
        "polymarket_book",
        "polymarket_leaderboard",
        # Trading (8)
        "polymarket_place_limit_order",
        "polymarket_place_market_order",
        "polymarket_cancel_order",
        "polymarket_cancel_all_orders",
        "polymarket_get_orders",
        "polymarket_get_balances",
        "polymarket_get_positions",
        "polymarket_get_trades",
        # Approvals (2)
        "polymarket_check_approvals",
        "polymarket_set_approvals",
        # CTF Operations (3)
        "polymarket_ctf_split",
        "polymarket_ctf_merge",
        "polymarket_ctf_redeem",
        # Bridge (2)
        "polymarket_bridge_deposit",
        "polymarket_bridge_status",
    ],
    "env_vars": [],  # No env vars needed - users configure via polymarket wallet commands
}
