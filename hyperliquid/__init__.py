"""
Hyperliquid Extension — Perpetual & Spot Trading on Hyperliquid DEX

Provides 19 tools for trading on Hyperliquid:
- 8 info tools: account state, balances, orders, market data, orderbook, fills, candles, funding
- 11 exchange tools: order, spot order, TP/SL order, cancel, cancel all, modify, leverage, USDC transfer, withdraw, deposit, set abstraction

Environment Variables:
- WALLET_SERVICE_URL: Privy wallet service URL (required for signing)

Usage:
    This extension is auto-loaded by the ExtensionLoader.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


def register(api) -> List[str]:
    """
    Extension entry point — register all Hyperliquid tools.

    Args:
        api: ExtensionApi instance with registry and config

    Returns:
        List of registered tool names
    """
    registered = []

    try:
        from .tools import (
            # Info tools (8)
            HLAccountTool,
            HLBalancesTool,
            HLOpenOrdersTool,
            HLMarketTool,
            HLOrderbookTool,
            HLFillsTool,
            HLCandlesTool,
            HLFundingTool,
            # Exchange tools (11)
            HLOrderTool,
            HLSpotOrderTool,
            HLTPSLOrderTool,
            HLCancelTool,
            HLCancelAllTool,
            HLModifyTool,
            HLLeverageTool,
            HLTransferUsdTool,
            HLWithdrawTool,
            HLDepositTool,
            HLSetAbstractionTool,
        )

        # Info tools
        api.register_tool(HLAccountTool())
        api.register_tool(HLBalancesTool())
        api.register_tool(HLOpenOrdersTool())
        api.register_tool(HLMarketTool())
        api.register_tool(HLOrderbookTool())
        api.register_tool(HLFillsTool())
        api.register_tool(HLCandlesTool())
        api.register_tool(HLFundingTool())

        # Exchange tools
        api.register_tool(HLOrderTool())
        api.register_tool(HLSpotOrderTool())
        api.register_tool(HLTPSLOrderTool())
        api.register_tool(HLCancelTool())
        api.register_tool(HLCancelAllTool())
        api.register_tool(HLModifyTool())
        api.register_tool(HLLeverageTool())
        api.register_tool(HLTransferUsdTool())
        api.register_tool(HLWithdrawTool())
        api.register_tool(HLDepositTool())
        api.register_tool(HLSetAbstractionTool())

        registered = [
            # Info (8)
            "hl_account",
            "hl_balances",
            "hl_open_orders",
            "hl_market",
            "hl_orderbook",
            "hl_fills",
            "hl_candles",
            "hl_funding",
            # Exchange (11)
            "hl_order",
            "hl_spot_order",
            "hl_tpsl_order",
            "hl_cancel",
            "hl_cancel_all",
            "hl_modify",
            "hl_leverage",
            "hl_transfer_usd",
            "hl_withdraw",
            "hl_deposit",
            "hl_set_abstraction",
        ]

        logger.info(f"Registered Hyperliquid tools ({len(registered)} tools)")
    except Exception as e:
        logger.warning(f"Failed to load Hyperliquid tools: {e}")

    return registered


# Extension metadata
EXTENSION_INFO = {
    "name": "hyperliquid",
    "version": "1.0.0",
    "description": "Hyperliquid DEX trading — perpetual futures and spot",
    "tools": [
        "hl_account",
        "hl_balances",
        "hl_open_orders",
        "hl_market",
        "hl_orderbook",
        "hl_fills",
        "hl_candles",
        "hl_funding",
        "hl_order",
        "hl_spot_order",
        "hl_tpsl_order",
        "hl_cancel",
        "hl_cancel_all",
        "hl_modify",
        "hl_leverage",
        "hl_transfer_usd",
        "hl_withdraw",
        "hl_deposit",
        "hl_set_abstraction",
    ],
    "env_vars": [
        "WALLET_SERVICE_URL",
    ],
}
