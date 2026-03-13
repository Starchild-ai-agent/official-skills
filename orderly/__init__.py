"""
Orderly Network Extension — Perpetual Futures & Spot Trading on Orderly DEX

Provides 21 tools for trading on Orderly Network:
- 8 public tools: system info, futures, funding, volume, orderbook, kline, market, chain info
- 6 private tools: account, holdings, positions, orders, trades, liquidations
- 5 trading tools: order, modify, cancel, cancel all, leverage
- 2 fund tools: deposit, withdraw

Authentication: Ed25519 keys auto-provisioned via Privy EIP-712 signing on first use.
No API key env vars needed.

Environment Variables:
- WALLET_SERVICE_URL: Privy wallet service URL (required for signing)
- ORDERLY_API_URL: API base URL (default: https://api.orderly.org)
- ORDERLY_BROKER_ID: Broker identifier (default: woofi_pro)
- ORDERLY_CHAIN_ID: Chain ID (default: 42161 / Arbitrum)

Usage:
    This extension is auto-loaded by the ExtensionLoader.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


def register(api) -> List[str]:
    """
    Extension entry point — register all Orderly tools.

    Args:
        api: ExtensionApi instance with registry and config

    Returns:
        List of registered tool names
    """
    registered = []

    try:
        from .tools import (
            # Public tools (8)
            OrderlySystemInfoTool,
            OrderlyFuturesTool,
            OrderlyFundingTool,
            OrderlyVolumeTool,
            OrderlyOrderbookTool,
            OrderlyKlineTool,
            OrderlyMarketTool,
            OrderlyChainInfoTool,
            # Private tools (6)
            OrderlyAccountTool,
            OrderlyHoldingsTool,
            OrderlyPositionsTool,
            OrderlyOrdersTool,
            OrderlyTradesTool,
            OrderlyLiquidationsTool,
            # Trading tools (5)
            OrderlyOrderTool,
            OrderlyModifyTool,
            OrderlyCancelTool,
            OrderlyCancelAllTool,
            OrderlyLeverageTool,
            # Fund tools (2)
            OrderlyDepositTool,
            OrderlyWithdrawTool,
        )

        # Public tools
        api.register_tool(OrderlySystemInfoTool())
        api.register_tool(OrderlyFuturesTool())
        api.register_tool(OrderlyFundingTool())
        api.register_tool(OrderlyVolumeTool())
        api.register_tool(OrderlyOrderbookTool())
        api.register_tool(OrderlyKlineTool())
        api.register_tool(OrderlyMarketTool())
        api.register_tool(OrderlyChainInfoTool())

        # Private tools
        api.register_tool(OrderlyAccountTool())
        api.register_tool(OrderlyHoldingsTool())
        api.register_tool(OrderlyPositionsTool())
        api.register_tool(OrderlyOrdersTool())
        api.register_tool(OrderlyTradesTool())
        api.register_tool(OrderlyLiquidationsTool())

        # Trading tools
        api.register_tool(OrderlyOrderTool())
        api.register_tool(OrderlyModifyTool())
        api.register_tool(OrderlyCancelTool())
        api.register_tool(OrderlyCancelAllTool())
        api.register_tool(OrderlyLeverageTool())

        # Fund tools
        api.register_tool(OrderlyDepositTool())
        api.register_tool(OrderlyWithdrawTool())

        registered = [
            # Public (8)
            "orderly_system_info",
            "orderly_futures",
            "orderly_funding",
            "orderly_volume",
            "orderly_orderbook",
            "orderly_kline",
            "orderly_market",
            "orderly_chain_info",
            # Private (6)
            "orderly_account",
            "orderly_holdings",
            "orderly_positions",
            "orderly_orders",
            "orderly_trades",
            "orderly_liquidations",
            # Trading (5)
            "orderly_order",
            "orderly_modify",
            "orderly_cancel",
            "orderly_cancel_all",
            "orderly_leverage",
            # Fund (2)
            "orderly_deposit",
            "orderly_withdraw",
        ]

        logger.info(f"Registered Orderly tools ({len(registered)} tools)")
    except Exception as e:
        logger.warning(f"Failed to load Orderly tools: {e}")

    return registered


# Extension metadata
EXTENSION_INFO = {
    "name": "orderly",
    "version": "1.0.0",
    "description": "Orderly Network DEX trading — perpetual futures and spot",
    "tools": [
        "orderly_system_info",
        "orderly_futures",
        "orderly_funding",
        "orderly_volume",
        "orderly_orderbook",
        "orderly_kline",
        "orderly_market",
        "orderly_chain_info",
        "orderly_account",
        "orderly_holdings",
        "orderly_positions",
        "orderly_orders",
        "orderly_trades",
        "orderly_liquidations",
        "orderly_order",
        "orderly_modify",
        "orderly_cancel",
        "orderly_cancel_all",
        "orderly_leverage",
        "orderly_deposit",
        "orderly_withdraw",
    ],
    "env_vars": [
        "WALLET_SERVICE_URL",
        "ORDERLY_API_URL",
        "ORDERLY_BROKER_ID",
        "ORDERLY_CHAIN_ID",
    ],
}
