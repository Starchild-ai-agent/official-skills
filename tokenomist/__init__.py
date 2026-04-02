"""
Tokenomist Extension - Token unlock, allocation, and emission data tools.

Uses Tokenomist API via sc-proxy through core/http_client.py helper.
"""

import os
import sys
import logging
from typing import List

logger = logging.getLogger(__name__)

TOOLS_DIR = os.path.join(os.path.dirname(__file__), "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)


def register(api) -> List[str]:
    """Extension entrypoint for tool registration."""
    registered: List[str] = []

    try:
        from .tools.tokenomist_tools import (
            TokenomistTokenListTool,
            TokenomistResolveTokenTool,
            TokenomistAllocationsTool,
            TokenomistAllocationsSummaryTool,
            TokenomistDailyEmissionTool,
            TokenomistUnlockEventsTool,
            TokenomistTokenOverviewTool,
        )

        api.register_tool(TokenomistTokenListTool())
        api.register_tool(TokenomistResolveTokenTool())
        api.register_tool(TokenomistAllocationsTool())
        api.register_tool(TokenomistAllocationsSummaryTool())
        api.register_tool(TokenomistDailyEmissionTool())
        api.register_tool(TokenomistUnlockEventsTool())
        api.register_tool(TokenomistTokenOverviewTool())

        registered.extend(
            [
                "tokenomist_token_list",
                "tokenomist_resolve_token",
                "tokenomist_allocations",
                "tokenomist_allocations_summary",
                "tokenomist_daily_emission",
                "tokenomist_unlock_events",
                "tokenomist_token_overview",
            ]
        )
        logger.info("Registered Tokenomist tools (7 tools)")
    except Exception as e:
        logger.warning(f"Failed to load Tokenomist tools: {e}")

    return registered


EXTENSION_INFO = {
    "name": "tokenomist",
    "version": "1.0.0",
    "description": "Token unlock, allocation, and emission data from Tokenomist API",
    "tools": [
        "tokenomist_token_list",
        "tokenomist_resolve_token",
        "tokenomist_allocations",
        "tokenomist_allocations_summary",
        "tokenomist_daily_emission",
        "tokenomist_unlock_events",
        "tokenomist_token_overview",
    ],
    "env_vars": ["TOKENMIST_API_KEY"],
}
