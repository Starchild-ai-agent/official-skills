"""
Aave Extension — Aave V3 Yield Farming (Supply/Withdraw/Positions)

Supports: Ethereum, Arbitrum, Base, Optimism, Polygon, Avalanche.

Provides 3 tools:
- aave_supply: Supply tokens to Aave V3 to earn yield
- aave_withdraw: Withdraw tokens from Aave V3
- aave_positions: View Aave V3 account data (read-only)

Environment Variables:
- WALLET_SERVICE_URL: Privy wallet service URL (required for supply/withdraw)
- RPC_URL_{chain_id}: Optional RPC URL override per chain

Usage:
    This extension is auto-loaded by the ExtensionLoader.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


def register(api) -> List[str]:
    """
    Extension entry point — register all Aave tools.

    Args:
        api: ExtensionApi instance with registry and config

    Returns:
        List of registered tool names
    """
    registered = []

    try:
        from .tools import (
            AaveSupplyTool,
            AaveWithdrawTool,
            AavePositionsTool,
        )

        api.register_tool(AaveSupplyTool())
        api.register_tool(AaveWithdrawTool())
        api.register_tool(AavePositionsTool())

        registered = [
            "aave_supply",
            "aave_withdraw",
            "aave_positions",
        ]

        logger.info(f"Registered Aave tools ({len(registered)} tools)")
    except Exception as e:
        logger.warning(f"Failed to load Aave tools: {e}")

    return registered


# Extension metadata
EXTENSION_INFO = {
    "name": "aave",
    "version": "1.0.0",
    "description": "Aave V3 yield farming - supply, withdraw, and view positions",
    "tools": [
        "aave_supply",
        "aave_withdraw",
        "aave_positions",
    ],
    "env_vars": [
        "WALLET_SERVICE_URL",
    ],
}
