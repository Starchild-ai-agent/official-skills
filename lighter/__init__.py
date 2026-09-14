"""
Lighter.xyz Skill — ZK-rollup DEX Trading Tools

Provides tools for:
- Market data (orderbook, trades, candles, funding rates)
- Account management (positions, balances, orders, PnL)
- Order execution (create, cancel, modify, close-all)
- Position management (leverage, margin)
- Fund management (withdraw, transfer between perp/spot)

Credentials (env vars or ~/.lighter/lighter-agent-kit/credentials):
- LIGHTER_PRIVATE_KEY: API private key for signing (required for trading)
- LIGHTER_ACCOUNT_INDEX: Account index on Lighter (required for trading)
- LIGHTER_API_KEY_INDEX: API key index (default: 2)
- LIGHTER_NETWORK: Which deployment — "ethereum" (app.lighter.xyz) or "robinhood"
  (robinhoodchain.lighter.xyz). Required: the user must pick one.
- LIGHTER_API_URL: Explicit base REST URL (overrides LIGHTER_NETWORK)

Usage:
    This skill is auto-loaded by the SkillToolLoader.
    Tools are available to agents configured with these tools in agents.yaml.
"""
import logging
from typing import List

logger = logging.getLogger(__name__)


def register(api) -> List[str]:
    """Skill entry point — register all Lighter tools."""
    registered = []

    try:
        from .tools import (
            # Network selection (1)
            LighterGetNetworkTool,
            # Market Data (7)
            LighterGetMarketsTool,
            LighterGetOrderbookTool,
            LighterGetRecentTradesTool,
            LighterGetCandlesTool,
            LighterGetExchangeStatsTool,
            LighterGetFundingRatesTool,
            LighterGetAssetDetailsTool,
            # Account (5)
            LighterGetAccountTool,
            LighterGetActiveOrdersTool,
            LighterGetOrderHistoryTool,
            LighterGetTradeHistoryTool,
            LighterGetPnlTool,
            # Trading (4)
            LighterCreateOrderTool,
            LighterCancelOrderTool,
            LighterCancelAllOrdersTool,
            LighterModifyOrderTool,
            # Position & Fund Management (5) — ported from lighter-agent-kit
            LighterCloseAllPositionsTool,
            LighterSetLeverageTool,
            LighterAdjustMarginTool,
            LighterWithdrawTool,
            LighterTransferFundsTool,
            # Paper Trading (6)
            LighterPaperInitTool,
            LighterPaperResetTool,
            LighterPaperStatusTool,
            LighterPaperPositionsTool,
            LighterPaperOrderTool,
            LighterPaperTradesTool,
            LighterPaperHealthTool,
        )

        tools = [
            # Network selection
            LighterGetNetworkTool(),
            # Market Data
            LighterGetMarketsTool(),
            LighterGetOrderbookTool(),
            LighterGetRecentTradesTool(),
            LighterGetCandlesTool(),
            LighterGetExchangeStatsTool(),
            LighterGetFundingRatesTool(),
            LighterGetAssetDetailsTool(),
            # Account
            LighterGetAccountTool(),
            LighterGetActiveOrdersTool(),
            LighterGetOrderHistoryTool(),
            LighterGetTradeHistoryTool(),
            LighterGetPnlTool(),
            # Trading
            LighterCreateOrderTool(),
            LighterCancelOrderTool(),
            LighterCancelAllOrdersTool(),
            LighterModifyOrderTool(),
            # Position & Fund Management
            LighterCloseAllPositionsTool(),
            LighterSetLeverageTool(),
            LighterAdjustMarginTool(),
            LighterWithdrawTool(),
            LighterTransferFundsTool(),
            # Paper Trading
            LighterPaperInitTool(),
            LighterPaperResetTool(),
            LighterPaperStatusTool(),
            LighterPaperPositionsTool(),
            LighterPaperOrderTool(),
            LighterPaperTradesTool(),
            LighterPaperHealthTool(),
        ]

        for tool in tools:
            api.register_tool(tool)
            registered.append(tool.name)

        logger.info(f"Registered Lighter tools ({len(registered)} tools)")

    except Exception as e:
        logger.warning(f"Failed to load Lighter tools: {e}")

    return registered


EXTENSION_INFO = {
    "name": "lighter",
    "version": "2.0.0",
    "description": "Lighter.xyz ZK-rollup DEX trading tools with symbol resolution and auto-scaling",
    "tools": [
        # Market Data (7)
        "lighter_get_markets",
        "lighter_get_orderbook",
        "lighter_get_recent_trades",
        "lighter_get_candles",
        "lighter_get_exchange_stats",
        "lighter_get_funding_rates",
        "lighter_get_asset_details",
        # Account (5)
        "lighter_get_account",
        "lighter_get_active_orders",
        "lighter_get_order_history",
        "lighter_get_trade_history",
        "lighter_get_pnl",
        # Trading (4)
        "lighter_create_order",
        "lighter_cancel_order",
        "lighter_cancel_all_orders",
        "lighter_modify_order",
        # Position & Fund Management (5)
        "lighter_close_all_positions",
        "lighter_set_leverage",
        "lighter_adjust_margin",
        "lighter_withdraw",
        "lighter_transfer_funds",
        # Paper Trading (7)
        "lighter_paper_init",
        "lighter_paper_reset",
        "lighter_paper_status",
        "lighter_paper_positions",
        "lighter_paper_order",
        "lighter_paper_trades",
        "lighter_paper_health",
    ],
    "env_vars": [
        "LIGHTER_API_URL",
        "LIGHTER_PRIVATE_KEY",
        "LIGHTER_ACCOUNT_INDEX",
        "LIGHTER_API_KEY_INDEX",
    ],
}
