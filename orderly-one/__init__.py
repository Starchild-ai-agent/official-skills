"""
Orderly One DEX Builder — Create and manage custom DEXes on Orderly Network.

Provides 13 tools for DEX management via the Orderly One API:
- 3 public tools: networks, leaderboard, stats
- 4 DEX CRUD tools: get, create, update, delete
- 3 branding tools: social card, domain, visibility
- 3 operations tools: deploy status, theme, graduation

Authentication: JWT via EIP-191 personal_sign (not Ed25519).
API server: https://api.dex.orderly.network

Environment Variables:
- WALLET_SERVICE_URL: Privy wallet service URL (required for signing)
- ORDERLY_ONE_API_URL: API base URL (default: https://api.dex.orderly.network)

Usage:
    This skill is auto-loaded by the SkillToolLoader.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


def register(api) -> List[str]:
    """
    Skill entry point — register all Orderly One tools.

    Args:
        api: ExtensionApi instance with registry and config

    Returns:
        List of registered tool names
    """
    registered = []

    try:
        from .tools import (
            # Public tools (3)
            OrderlyOneNetworksTool,
            OrderlyOneLeaderboardTool,
            OrderlyOneStatsTool,
            # DEX CRUD tools (4)
            OrderlyOneDexGetTool,
            OrderlyOneDexCreateTool,
            OrderlyOneDexUpdateTool,
            OrderlyOneDexDeleteTool,
            # Branding tools (3)
            OrderlyOneSocialCardTool,
            OrderlyOneDomainTool,
            OrderlyOneVisibilityTool,
            # Operations tools (3)
            OrderlyOneDeployStatusTool,
            OrderlyOneThemeTool,
            OrderlyOneGraduationTool,
        )

        # Public tools
        api.register_tool(OrderlyOneNetworksTool())
        api.register_tool(OrderlyOneLeaderboardTool())
        api.register_tool(OrderlyOneStatsTool())

        # DEX CRUD tools
        api.register_tool(OrderlyOneDexGetTool())
        api.register_tool(OrderlyOneDexCreateTool())
        api.register_tool(OrderlyOneDexUpdateTool())
        api.register_tool(OrderlyOneDexDeleteTool())

        # Branding tools
        api.register_tool(OrderlyOneSocialCardTool())
        api.register_tool(OrderlyOneDomainTool())
        api.register_tool(OrderlyOneVisibilityTool())

        # Operations tools
        api.register_tool(OrderlyOneDeployStatusTool())
        api.register_tool(OrderlyOneThemeTool())
        api.register_tool(OrderlyOneGraduationTool())

        registered = [
            # Public (3)
            "orderly_one_networks",
            "orderly_one_leaderboard",
            "orderly_one_stats",
            # DEX CRUD (4)
            "orderly_one_dex_get",
            "orderly_one_dex_create",
            "orderly_one_dex_update",
            "orderly_one_dex_delete",
            # Branding (3)
            "orderly_one_social_card",
            "orderly_one_domain",
            "orderly_one_visibility",
            # Operations (3)
            "orderly_one_deploy_status",
            "orderly_one_theme",
            "orderly_one_graduation",
        ]

        logger.info(f"Registered Orderly One tools ({len(registered)} tools)")
    except Exception as e:
        logger.warning(f"Failed to load Orderly One tools: {e}")

    return registered


# Extension metadata
EXTENSION_INFO = {
    "name": "orderly-one",
    "version": "1.0.0",
    "description": "Orderly One DEX Builder — create and manage custom DEXes",
    "tools": [
        "orderly_one_networks",
        "orderly_one_leaderboard",
        "orderly_one_stats",
        "orderly_one_dex_get",
        "orderly_one_dex_create",
        "orderly_one_dex_update",
        "orderly_one_dex_delete",
        "orderly_one_social_card",
        "orderly_one_domain",
        "orderly_one_visibility",
        "orderly_one_deploy_status",
        "orderly_one_theme",
        "orderly_one_graduation",
    ],
    "env_vars": [
        "WALLET_SERVICE_URL",
        "ORDERLY_ONE_API_URL",
    ],
}
