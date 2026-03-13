"""
1inch Extension — Spot Token Swaps + Fusion+ Cross-Chain Swaps via 1inch DEX Aggregator (Multi-Network)

Supports: Ethereum, Arbitrum, Base, Optimism, Polygon, BSC, Avalanche, Gnosis.
Same-chain tools require a `chain` parameter. Cross-chain tools require `src_chain` and `dst_chain`.

Provides 8 tools:
- 5 same-chain: quote, tokens, check_allowance, approve, swap
- 3 cross-chain (Fusion+): cross_chain_quote, cross_chain_swap, cross_chain_status

Environment Variables:
- ONEINCH_API_KEY: 1inch Developer Portal API key (required)
- WALLET_SERVICE_URL: Privy wallet service URL (required for swap/approve)

Usage:
    This extension is auto-loaded by the ExtensionLoader.
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
            # Cross-chain read-only tools (2)
            CrossChainQuoteTool,
            CrossChainStatusTool,
            # Cross-chain write tools (1)
            CrossChainSwapTool,
        )

        # Same-chain tools
        api.register_tool(OneInchQuoteTool())
        api.register_tool(OneInchTokensTool())
        api.register_tool(OneInchCheckAllowanceTool())
        api.register_tool(OneInchApproveTool())
        api.register_tool(OneInchSwapTool())

        # Cross-chain tools
        api.register_tool(CrossChainQuoteTool())
        api.register_tool(CrossChainSwapTool())
        api.register_tool(CrossChainStatusTool())

        registered = [
            "oneinch_quote",
            "oneinch_tokens",
            "oneinch_check_allowance",
            "oneinch_approve",
            "oneinch_swap",
            "oneinch_cross_chain_quote",
            "oneinch_cross_chain_swap",
            "oneinch_cross_chain_status",
        ]

        logger.info(f"Registered 1inch tools ({len(registered)} tools)")
    except Exception as e:
        logger.warning(f"Failed to load 1inch tools: {e}")

    return registered


# Extension metadata
EXTENSION_INFO = {
    "name": "oneinch",
    "version": "2.0.0",
    "description": "1inch DEX aggregator - spot token swaps + Fusion+ cross-chain swaps",
    "tools": [
        "oneinch_quote",
        "oneinch_tokens",
        "oneinch_check_allowance",
        "oneinch_approve",
        "oneinch_swap",
        "oneinch_cross_chain_quote",
        "oneinch_cross_chain_swap",
        "oneinch_cross_chain_status",
    ],
    "env_vars": [
        "ONEINCH_API_KEY",
    ],
}
