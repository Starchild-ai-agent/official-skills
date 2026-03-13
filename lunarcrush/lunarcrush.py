"""
LunarCrush Tool Wrappers

Wraps tools from /tools/lunarcrush/ for use in Agent framework.
Provides social intelligence: Galaxy Score, sentiment, influencers, trending topics.

Note: Some endpoints require higher API tiers or have strict rate limits.
Only the most reliable endpoints are exposed here.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional

from core.tool import BaseTool, ToolContext, ToolResult

logger = logging.getLogger(__name__)

# Import original tools from local tools directory
try:
    from .tools.coins import (
        get_coin,
        get_coin_time_series,
        get_coin_meta,
    )
    from .tools.topics import (
        get_topic,
        get_topic_posts,
    )
    from .tools.creators import (
        get_creator,
    )
    LUNARCRUSH_AVAILABLE = True
except ImportError as e:
    logger.warning(f"LunarCrush tools not available: {e}")
    LUNARCRUSH_AVAILABLE = False


# ==================== Coin Tools ====================

class LunarCoinTool(BaseTool):
    """
    Get detailed metrics for a single coin.
    """

    @property
    def name(self) -> str:
        return "lunar_coin"

    @property
    def description(self) -> str:
        return """Get detailed social metrics for a single coin.

Returns Galaxy Score, AltRank, social volume, sentiment, and more.

Examples:
- Get BTC social metrics: lunar_coin(coin="BTC")
- Get ETH metrics: lunar_coin(coin="ETH")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "coin": {
                    "type": "string",
                    "description": "Coin symbol (BTC, ETH, SOL)"
                }
            },
            "required": ["coin"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        coin: str
    ) -> ToolResult:
        if not LUNARCRUSH_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="LunarCrush tools not available."
            )

        try:
            result = await asyncio.to_thread(get_coin, coin)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class LunarCoinTimeSeriesTool(BaseTool):
    """
    Get historical social + market data for a coin.
    """

    @property
    def name(self) -> str:
        return "lunar_coin_time_series"

    @property
    def description(self) -> str:
        return """Get historical social and market data for a coin.

Includes Galaxy Score, sentiment, social volume over time.

Examples:
- Get BTC daily data for 1 month: lunar_coin_time_series(coin="BTC", bucket="day", interval="1m")
- Get ETH hourly for 1 week: lunar_coin_time_series(coin="ETH", bucket="hour", interval="1w")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "coin": {
                    "type": "string",
                    "description": "Coin symbol (BTC, ETH)"
                },
                "bucket": {
                    "type": "string",
                    "description": "Time bucket: hour, day, week",
                    "default": "day"
                },
                "interval": {
                    "type": "string",
                    "description": "Time interval: 1w, 1m, 3m, 6m, 1y, all",
                    "default": "1m"
                }
            },
            "required": ["coin"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        coin: str,
        bucket: str = "day",
        interval: str = "1m"
    ) -> ToolResult:
        if not LUNARCRUSH_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="LunarCrush tools not available."
            )

        try:
            result = await asyncio.to_thread(get_coin_time_series, coin, bucket, interval)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class LunarCoinMetaTool(BaseTool):
    """
    Get coin metadata including links, description, social accounts.
    """

    @property
    def name(self) -> str:
        return "lunar_coin_meta"

    @property
    def description(self) -> str:
        return """Get coin metadata: links, description, social accounts.

Examples:
- Get BTC metadata: lunar_coin_meta(coin="BTC")
- Get SOL project info: lunar_coin_meta(coin="SOL")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "coin": {
                    "type": "string",
                    "description": "Coin symbol (BTC, ETH)"
                }
            },
            "required": ["coin"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        coin: str
    ) -> ToolResult:
        if not LUNARCRUSH_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="LunarCrush tools not available."
            )

        try:
            result = await asyncio.to_thread(get_coin_meta, coin)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Topic Tools ====================

class LunarTopicTool(BaseTool):
    """
    Get metrics for a specific topic.
    """

    @property
    def name(self) -> str:
        return "lunar_topic"

    @property
    def description(self) -> str:
        return """Get metrics for a specific topic (24h aggregation).

Examples:
- Get DeFi topic metrics: lunar_topic(topic="defi")
- Get NFT topic metrics: lunar_topic(topic="nft")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic name or slug (defi, nft, bitcoin)"
                }
            },
            "required": ["topic"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        topic: str
    ) -> ToolResult:
        if not LUNARCRUSH_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="LunarCrush tools not available."
            )

        try:
            result = await asyncio.to_thread(get_topic, topic)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class LunarTopicPostsTool(BaseTool):
    """
    Get top posts for a topic.
    """

    @property
    def name(self) -> str:
        return "lunar_topic_posts"

    @property
    def description(self) -> str:
        return """Get top posts for a topic.

Examples:
- Get top DeFi posts: lunar_topic_posts(topic="defi")
- Get top 10 Bitcoin posts: lunar_topic_posts(topic="bitcoin", limit=10)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic name or slug"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of posts (max 100)",
                    "default": 20
                }
            },
            "required": ["topic"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        topic: str,
        limit: int = 20
    ) -> ToolResult:
        if not LUNARCRUSH_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="LunarCrush tools not available."
            )

        try:
            result = await asyncio.to_thread(get_topic_posts, topic, limit)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


# ==================== Creator Tools ====================

class LunarCreatorTool(BaseTool):
    """
    Get details for a specific influencer.
    """

    @property
    def name(self) -> str:
        return "lunar_creator"

    @property
    def description(self) -> str:
        return """Get details for a specific crypto influencer.

Examples:
- Get Twitter influencer: lunar_creator(network="twitter", id="VitalikButerin")
- Get YouTube creator: lunar_creator(network="youtube", id="@CoinBureau")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "network": {
                    "type": "string",
                    "description": "Social network: twitter, youtube"
                },
                "id": {
                    "type": "string",
                    "description": "Creator ID or username"
                }
            },
            "required": ["network", "id"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        network: str,
        id: str
    ) -> ToolResult:
        if not LUNARCRUSH_AVAILABLE:
            return ToolResult(
                success=False,
                output=None,
                error="LunarCrush tools not available."
            )

        try:
            result = await asyncio.to_thread(get_creator, network, id)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
