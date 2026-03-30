"""
Tokenmist Extension - Token unlock, allocation, and emission data tools.

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
        from .tools.tokenmist_tools import (
            TokenmistTokenListTool,
            TokenmistResolveTokenTool,
            TokenmistAllocationsTool,
            TokenmistAllocationsSummaryTool,
            TokenmistDailyEmissionTool,
            TokenmistUnlockEventsTool,
            TokenmistTokenOverviewTool,
        )

        api.register_tool(TokenmistTokenListTool())
        api.register_tool(TokenmistResolveTokenTool())
        api.register_tool(TokenmistAllocationsTool())
        api.register_tool(TokenmistAllocationsSummaryTool())
        api.register_tool(TokenmistDailyEmissionTool())
        api.register_tool(TokenmistUnlockEventsTool())
        api.register_tool(TokenmistTokenOverviewTool())

        registered.extend(
            [
                "tokenmist_token_list",
                "tokenmist_resolve_token",
                "tokenmist_allocations",
                "tokenmist_allocations_summary",
                "tokenmist_daily_emission",
                "tokenmist_unlock_events",
                "tokenmist_token_overview",
            ]
        )
        logger.info("Registered Tokenmist tools (7 tools)")
    except Exception as e:
        logger.warning(f"Failed to load Tokenmist tools: {e}")

    return registered


EXTENSION_INFO = {
    "name": "tokenmist",
    "version": "1.0.0",
    "description": "Token unlock, allocation, and emission data from Tokenomist API",
    "tools": [
        "tokenmist_token_list",
        "tokenmist_resolve_token",
        "tokenmist_allocations",
        "tokenmist_allocations_summary",
        "tokenmist_daily_emission",
        "tokenmist_unlock_events",
        "tokenmist_token_overview",
    ],
    "env_vars": ["TOKENMIST_API_KEY"],
}
