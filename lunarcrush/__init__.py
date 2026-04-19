"""
LunarCrush Extension - Social Intelligence and Sentiment Data

Provides social intelligence and sentiment data including:
- Galaxy Score (social momentum)
- AltRank (social ranking)
- Social volume and dominance
- Influencer activity
- Trending topics

Environment Variables Required:
- LUNARCRUSH_API_KEY: LunarCrush API key

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
    Extension entry point - register all LunarCrush tools.

    Args:
        api: ExtensionApi instance with registry and config

    Returns:
        List of registered tool names
    """
    registered = []

    try:
        from .lunarcrush import (
            LunarCoinTool,
            LunarCoinTimeSeriesTool,
            LunarCoinMetaTool,
            LunarTopicTool,
            LunarTopicPostsTool,
            LunarTopicNewsTool,
            LunarCategoryPostsTool,
            LunarCategoryNewsTool,
            LunarContentFeedTool,
            LunarSearchContentTool,
            LunarCreatorTool,
        )
        api.register_tool(LunarCoinTool())
        api.register_tool(LunarCoinTimeSeriesTool())
        api.register_tool(LunarCoinMetaTool())
        api.register_tool(LunarTopicTool())
        api.register_tool(LunarTopicPostsTool())
        api.register_tool(LunarTopicNewsTool())
        api.register_tool(LunarCategoryPostsTool())
        api.register_tool(LunarCategoryNewsTool())
        api.register_tool(LunarContentFeedTool())
        api.register_tool(LunarSearchContentTool())
        api.register_tool(LunarCreatorTool())
        registered.extend([
            "lunar_coin",
            "lunar_coin_time_series",
            "lunar_coin_meta",
            "lunar_topic",
            "lunar_topic_posts",
            "lunar_topic_news",
            "lunar_category_posts",
            "lunar_category_news",
            "lunar_content_feed",
            "lunar_search_content",
            "lunar_creator",
        ])
        logger.info("Registered LunarCrush tools (11 tools)")
    except Exception as e:
        logger.warning(f"Failed to load LunarCrush tools: {e}")

    return registered


# Extension metadata
EXTENSION_INFO = {
    "name": "lunarcrush",
    "version": "1.2.0",
    "description": "LunarCrush social intelligence, news aggregation, and content search",
    "tools": [
        "lunar_coin",
        "lunar_coin_time_series",
        "lunar_coin_meta",
        "lunar_topic",
        "lunar_topic_posts",
        "lunar_topic_news",
        "lunar_category_posts",
        "lunar_category_news",
        "lunar_content_feed",
        "lunar_search_content",
        "lunar_creator",
    ],
    "env_vars": [
        "LUNARCRUSH_API_KEY",
    ],
}
