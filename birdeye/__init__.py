"""
Birdeye Extension — Token Intelligence and Wallet Analytics

Provides 3 working tools for token analysis and wallet tracking across Solana and EVM chains.

Token Intelligence Tools (2):
- birdeye_token_security: Security score and risk analysis
- birdeye_token_overview: Comprehensive token data

Wallet Analytics Tools (1):
- birdeye_wallet_networth: Current net worth snapshot

Environment Variables Required:
- BIRDEYE_API_KEY: Your Birdeye API key

Note: Wallet APIs have limited rate (5 req/s, 75 req/min).

Usage:
    This extension is auto-loaded by the ExtensionLoader.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


def register(api) -> List[str]:
    """
    Extension entry point — register all Birdeye tools.

    Args:
        api: ExtensionApi instance with registry and config

    Returns:
        List of registered tool names
    """
    registered = []

    # Token Intelligence Tools (2)
    try:
        from .token import (
            BirdeyeTokenSecurityTool,
            BirdeyeTokenOverviewTool
        )

        api.register_tool(BirdeyeTokenSecurityTool())
        api.register_tool(BirdeyeTokenOverviewTool())

        registered.extend([
            "birdeye_token_security",
            "birdeye_token_overview"
        ])

        logger.info("Registered Birdeye token intelligence tools (2 tools)")
    except Exception as e:
        logger.warning(f"Failed to load Birdeye token intelligence tools: {e}")

    # Wallet Analytics Tools (1)
    try:
        from .wallet import (
            BirdeyeWalletNetworthTool
        )

        api.register_tool(BirdeyeWalletNetworthTool())

        registered.append("birdeye_wallet_networth")

        logger.info("Registered Birdeye wallet analytics tools (1 tool)")
    except Exception as e:
        logger.warning(f"Failed to load Birdeye wallet analytics tools: {e}")

    logger.info(f"Registered Birdeye extension ({len(registered)} tools total)")
    return registered


# Extension metadata
EXTENSION_INFO = {
    "name": "birdeye",
    "version": "2.0.0",
    "description": "Birdeye token intelligence and wallet analytics for Solana and EVM chains",
    "tools": [
        # Token Intelligence (2)
        "birdeye_token_security",
        "birdeye_token_overview",
        # Wallet Analytics (1)
        "birdeye_wallet_networth"
    ],
    "env_vars": [
        "BIRDEYE_API_KEY",
    ],
}
