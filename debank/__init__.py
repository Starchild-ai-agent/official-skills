"""
DeBank Extension - Blockchain Data Tools

Provides comprehensive blockchain data including:
- User portfolios and balances
- Token data and prices
- Transaction history
- DeFi protocol positions
- NFT holdings
- Transaction simulation

Environment Variables Required:
- DEBANK_API_KEY: DeBank Cloud API key

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
    Extension entry point - register all DeBank tools.

    Args:
        api: ExtensionApi instance with registry and config

    Returns:
        List of registered tool names
    """
    registered = []

    try:
        from .debank import (
            # Chain tools (3)
            DebankChainListTool,
            DebankChainTool,
            DebankGasMarketTool,
            # Token tools (4)
            DebankTokenTool,
            DebankTokenHistoryPriceTool,
            DebankTokenListByIdsTool,
            DebankTokenTopHoldersTool,
            # User balance tools (3)
            DebankUserTotalBalanceTool,
            DebankUserTokenListTool,
            DebankUserAllTokenListTool,
            # User history tools (2)
            DebankUserHistoryListTool,
            DebankUserAllHistoryListTool,
            # User protocol tools (5)
            DebankUserSimpleProtocolListTool,
            DebankUserAllSimpleProtocolListTool,
            DebankUserComplexProtocolListTool,
            DebankUserAllComplexProtocolListTool,
            DebankUserComplexAppListTool,
            # User NFT tools (2)
            DebankUserNftListTool,
            DebankUserAllNftListTool,
            # User misc tools (8)
            DebankUserChainBalanceTool,
            DebankUserTokenTool,
            DebankUserProtocolTool,
            DebankUserUsedChainListTool,
            DebankUserTokenAuthorizedListTool,
            DebankUserNftAuthorizedListTool,
            DebankUserChainNetCurveTool,
            DebankUserTotalNetCurveTool,
            # Wallet tools (2)
            DebankPreExecTxTool,
            DebankExplainTxTool,
            # Protocol tools (5)
            DebankProtocolTool,
            DebankProtocolListTool,
            DebankProtocolAllListTool,
            DebankAppProtocolListTool,
            DebankPoolTool,
        )

        # Register chain tools
        api.register_tool(DebankChainListTool())
        api.register_tool(DebankChainTool())
        api.register_tool(DebankGasMarketTool())

        # Register token tools
        api.register_tool(DebankTokenTool())
        api.register_tool(DebankTokenHistoryPriceTool())
        api.register_tool(DebankTokenListByIdsTool())
        api.register_tool(DebankTokenTopHoldersTool())

        # Register user balance tools
        api.register_tool(DebankUserTotalBalanceTool())
        api.register_tool(DebankUserTokenListTool())
        api.register_tool(DebankUserAllTokenListTool())

        # Register user history tools
        api.register_tool(DebankUserHistoryListTool())
        api.register_tool(DebankUserAllHistoryListTool())

        # Register user protocol tools
        api.register_tool(DebankUserSimpleProtocolListTool())
        api.register_tool(DebankUserAllSimpleProtocolListTool())
        api.register_tool(DebankUserComplexProtocolListTool())
        api.register_tool(DebankUserAllComplexProtocolListTool())
        api.register_tool(DebankUserComplexAppListTool())

        # Register user NFT tools
        api.register_tool(DebankUserNftListTool())
        api.register_tool(DebankUserAllNftListTool())

        # Register user misc tools
        api.register_tool(DebankUserChainBalanceTool())
        api.register_tool(DebankUserTokenTool())
        api.register_tool(DebankUserProtocolTool())
        api.register_tool(DebankUserUsedChainListTool())
        api.register_tool(DebankUserTokenAuthorizedListTool())
        api.register_tool(DebankUserNftAuthorizedListTool())
        api.register_tool(DebankUserChainNetCurveTool())
        api.register_tool(DebankUserTotalNetCurveTool())

        # Register wallet tools
        api.register_tool(DebankPreExecTxTool())
        api.register_tool(DebankExplainTxTool())

        # Register protocol tools
        api.register_tool(DebankProtocolTool())
        api.register_tool(DebankProtocolListTool())
        api.register_tool(DebankProtocolAllListTool())
        api.register_tool(DebankAppProtocolListTool())
        api.register_tool(DebankPoolTool())

        registered.extend([
            # Chain (3)
            "db_chain_list",
            "db_chain",
            "db_gas_market",
            # Token (4)
            "db_token",
            "db_token_history_price",
            "db_token_list_by_ids",
            "db_token_top_holders",
            # User Balance (3)
            "db_user_total_balance",
            "db_user_token_list",
            "db_user_all_token_list",
            # User History (2)
            "db_user_history_list",
            "db_user_all_history_list",
            # User Protocol (5)
            "db_user_simple_protocol_list",
            "db_user_all_simple_protocol_list",
            "db_user_complex_protocol_list",
            "db_user_all_complex_protocol_list",
            "db_user_complex_app_list",
            # User NFT (2)
            "db_user_nft_list",
            "db_user_all_nft_list",
            # User Misc (8)
            "db_user_chain_balance",
            "db_user_token",
            "db_user_protocol",
            "db_user_used_chain_list",
            "db_user_token_authorized_list",
            "db_user_nft_authorized_list",
            "db_user_chain_net_curve",
            "db_user_total_net_curve",
            # Wallet (2)
            "db_pre_exec_tx",
            "db_explain_tx",
            # Protocol (5)
            "db_protocol",
            "db_protocol_list",
            "db_protocol_all_list",
            "db_app_protocol_list",
            "db_pool",
        ])
        logger.info("Registered DeBank tools (34 tools)")
    except Exception as e:
        logger.warning(f"Failed to load DeBank tools: {e}")

    return registered


# Extension metadata
EXTENSION_INFO = {
    "name": "debank",
    "version": "1.0.0",
    "description": "DeBank blockchain data tools",
    "tools": [
        # Chain (3)
        "db_chain_list",
        "db_chain",
        "db_gas_market",
        # Token (4)
        "db_token",
        "db_token_history_price",
        "db_token_list_by_ids",
        "db_token_top_holders",
        # User Balance (3)
        "db_user_total_balance",
        "db_user_token_list",
        "db_user_all_token_list",
        # User History (2)
        "db_user_history_list",
        "db_user_all_history_list",
        # User Protocol (5)
        "db_user_simple_protocol_list",
        "db_user_all_simple_protocol_list",
        "db_user_complex_protocol_list",
        "db_user_all_complex_protocol_list",
        "db_user_complex_app_list",
        # User NFT (2)
        "db_user_nft_list",
        "db_user_all_nft_list",
        # User Misc (8)
        "db_user_chain_balance",
        "db_user_token",
        "db_user_protocol",
        "db_user_used_chain_list",
        "db_user_token_authorized_list",
        "db_user_nft_authorized_list",
        "db_user_chain_net_curve",
        "db_user_total_net_curve",
        # Wallet (2)
        "db_pre_exec_tx",
        "db_explain_tx",
        # Protocol (5)
        "db_protocol",
        "db_protocol_list",
        "db_protocol_all_list",
        "db_app_protocol_list",
        "db_pool",
    ],
    "env_vars": [
        "DEBANK_API_KEY",
    ],
}
