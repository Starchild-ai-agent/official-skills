"""
1inch Extension — Same-Chain Swap + Fusion+ Cross-Chain (EVM↔SOL) + Limit Orders.

Supports EVM: Ethereum, Arbitrum, Base, Optimism, Polygon, BSC, Avalanche, Gnosis.
Cross-chain also supports Solana (chain ID 501) as src or dst.

Provides 14 tools:
- 5 same-chain:      quote, tokens, check_allowance, approve, swap
- 5 cross-chain:     cross_chain_quote, cross_chain_swap, cross_chain_status
                     sol_cross_chain_quote, sol_to_evm_swap
- 4 limit orders:    get_orders, get_order, create_limit_order, cancel_limit_order

Architecture: All write ops use wallet_sign_transaction / wallet_sign_typed_data (EVM)
              or wallet_sol_sign_transaction (Solana). No Fly Machine dependency.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


def register(api) -> List[str]:
    """
    Extension entry point — register all 1inch tools.

    Args:
        api: ExtensionApi instance with registry and config

    Returns:
        List of registered tool names
    """
    registered = []

    try:
        from .tools import (
            # Read-only tools (3)
            OneInchQuoteTool,
            OneInchTokensTool,
            OneInchCheckAllowanceTool,
            # Write tools (2)
            OneInchApproveTool,
            OneInchSwapTool,
        )
        from .fusion_tools import (
            # Cross-chain read-only tools (3)
            CrossChainQuoteTool,
            CrossChainStatusTool,
            SolCrossChainQuoteTool,
            # Cross-chain write tools (2)
            CrossChainSwapTool,
            SolToEvmSwapTool,
        )
        from .orderbook_tools import (
            # Limit order read-only tools (2)
            GetOrdersTool,
            GetOrderTool,
            # Limit order write tools (2)
            CreateLimitOrderTool,
            CancelLimitOrderTool,
        )

        # Same-chain tools
        api.register_tool(OneInchQuoteTool())
        api.register_tool(OneInchTokensTool())
        api.register_tool(OneInchCheckAllowanceTool())
        api.register_tool(OneInchApproveTool())
        api.register_tool(OneInchSwapTool())

        # Cross-chain Fusion+ tools (EVM↔EVM + EVM↔SOL)
        api.register_tool(CrossChainQuoteTool())
        api.register_tool(CrossChainSwapTool())
        api.register_tool(CrossChainStatusTool())
        api.register_tool(SolCrossChainQuoteTool())
        api.register_tool(SolToEvmSwapTool())

        # Limit order / Orderbook tools
        api.register_tool(GetOrdersTool())
        api.register_tool(GetOrderTool())
        api.register_tool(CreateLimitOrderTool())
        api.register_tool(CancelLimitOrderTool())

        registered = [
            # Same-chain
            "oneinch_quote",
            "oneinch_tokens",
            "oneinch_check_allowance",
            "oneinch_approve",
            "oneinch_swap",
            # Cross-chain EVM↔EVM / EVM→SOL
            "oneinch_cross_chain_quote",
            "oneinch_cross_chain_swap",
            "oneinch_cross_chain_status",
            # Cross-chain SOL→EVM
            "oneinch_sol_cross_chain_quote",
            "oneinch_sol_to_evm_swap",
            # Limit orders
            "oneinch_get_orders",
            "oneinch_get_order",
            "oneinch_create_limit_order",
            "oneinch_cancel_limit_order",
        ]

        logger.info(f"Registered 1inch tools ({len(registered)} tools)")
    except Exception as e:
        logger.warning(f"Failed to load 1inch tools: {e}")

    return registered


# Extension metadata
EXTENSION_INFO = {
    "name": "oneinch",
    "version": "3.0.0",
    "description": "1inch DEX aggregator — same-chain swap, Fusion+ cross-chain (EVM↔SOL), limit orders",
    "tools": [
        "oneinch_quote",
        "oneinch_tokens",
        "oneinch_check_allowance",
        "oneinch_approve",
        "oneinch_swap",
        "oneinch_cross_chain_quote",
        "oneinch_cross_chain_swap",
        "oneinch_cross_chain_status",
        "oneinch_sol_cross_chain_quote",
        "oneinch_sol_to_evm_swap",
        "oneinch_get_orders",
        "oneinch_get_order",
        "oneinch_create_limit_order",
        "oneinch_cancel_limit_order",
    ],
    "env_vars": [
        "ONEINCH_API_KEY",
    ],
}
