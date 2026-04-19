"""
LunarCrush Tool Wrappers

Wraps tools from /tools/lunarcrush/ for use in Agent framework.
Provides social intelligence: Galaxy Score, sentiment, influencers, trending topics.

Note: Some endpoints require higher API tiers or have strict rate limits.
Only the most reliable endpoints are exposed here.
"""
import asyncio
import logging

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
        get_topic_news,
        get_category_posts,
        get_category_news,
        get_content_feed,
        search_content,
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


# ==================== Content Search ====================

class LunarContentFeedTool(BaseTool):
    """Unified content feed: topic/category × news/posts."""

    @property
    def name(self) -> str:
        return "lunar_content_feed"

    @property
    def description(self) -> str:
        return """Unified content feed — one call, any scope.

Examples:
- Topic news: lunar_content_feed(feed_type="news", scope_type="topic", scope="bitcoin")
- Category posts: lunar_content_feed(feed_type="posts", scope_type="category", scope="defi")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "feed_type": {
                    "type": "string",
                    "description": "Content type: news or posts",
                    "enum": ["news", "posts"]
                },
                "scope_type": {
                    "type": "string",
                    "description": "Scope: topic or category",
                    "enum": ["topic", "category"]
                },
                "scope": {
                    "type": "string",
                    "description": "Topic or category value (e.g. bitcoin, defi, gaming)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max items (max 100)",
                    "default": 20
                }
            },
            "required": ["feed_type", "scope_type", "scope"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        feed_type: str,
        scope_type: str,
        scope: str,
        limit: int = 20
    ) -> ToolResult:
        if not LUNARCRUSH_AVAILABLE:
            return ToolResult(success=False, output=None, error="LunarCrush tools not available.")
        try:
            result = await asyncio.to_thread(get_content_feed, feed_type, scope_type, scope, limit)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class LunarTopicNewsTool(BaseTool):
    """Get news feed for a specific topic."""

    @property
    def name(self) -> str:
        return "lunar_topic_news"

    @property
    def description(self) -> str:
        return """Get news articles for a topic.

Examples:
- Get Bitcoin news: lunar_topic_news(topic="bitcoin", limit=10)
- Get DeFi news: lunar_topic_news(topic="defi")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic slug (bitcoin, defi, nft, etc.)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max items (max 100)",
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
            return ToolResult(success=False, output=None, error="LunarCrush tools not available.")
        try:
            result = await asyncio.to_thread(get_topic_news, topic, limit)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class LunarCategoryPostsTool(BaseTool):
    """Get social posts for a category."""

    @property
    def name(self) -> str:
        return "lunar_category_posts"

    @property
    def description(self) -> str:
        return """Get social posts for a category.

Examples:
- Get gaming posts: lunar_category_posts(category="gaming", limit=10)
- Get memecoin posts: lunar_category_posts(category="memecoin")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Category slug (defi, gaming, memecoin, etc.)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max items (max 100)",
                    "default": 20
                }
            },
            "required": ["category"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        category: str,
        limit: int = 20
    ) -> ToolResult:
        if not LUNARCRUSH_AVAILABLE:
            return ToolResult(success=False, output=None, error="LunarCrush tools not available.")
        try:
            result = await asyncio.to_thread(get_category_posts, category, limit)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class LunarCategoryNewsTool(BaseTool):
    """Get news feed for a category."""

    @property
    def name(self) -> str:
        return "lunar_category_news"

    @property
    def description(self) -> str:
        return """Get news articles for a category.

Examples:
- Get DeFi news: lunar_category_news(category="defi", limit=10)
- Get gaming news: lunar_category_news(category="gaming")"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Category slug (defi, gaming, memecoin, etc.)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max items (max 100)",
                    "default": 20
                }
            },
            "required": ["category"]
        }

    async def execute(
        self,
        ctx: ToolContext,
        category: str,
        limit: int = 20
    ) -> ToolResult:
        if not LUNARCRUSH_AVAILABLE:
            return ToolResult(success=False, output=None, error="LunarCrush tools not available.")
        try:
            result = await asyncio.to_thread(get_category_news, category, limit)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class LunarSearchContentTool(BaseTool):
    """Cross-scope content search + sentiment summary."""

    @property
    def name(self) -> str:
        return "lunar_search_content"

    @property
    def description(self) -> str:
        return """Crypto content search engine — searches news + posts across topics/categories.

Aggregates, deduplicates, sorts by engagement, and provides sentiment summary.

Examples:
- Search "ETF" across default scopes: lunar_search_content(query="ETF")
- Search "halving" in bitcoin+solana topics: lunar_search_content(query="halving", topics=["bitcoin","solana"])
- Get all recent DeFi news+posts: lunar_search_content(topics=["defi"], feed_types=["news","posts"])
- Search with time window: lunar_search_content(query="regulation", time_window="7d", limit=30)"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keyword to filter by (title, description, body, author). Empty = no filter."
                },
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Topic slugs to search. Default: [bitcoin, ethereum, solana]"
                },
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Category slugs to search. Default: [defi]"
                },
                "feed_types": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["news", "posts"]},
                    "description": "Content types. Default: [news, posts]"
                },
                "time_window": {
                    "type": "string",
                    "description": "Time scope: 1h, 24h, 7d, 30d. Default: 24h"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max items returned (max 200). Default: 50"
                }
            }
        }

    async def execute(
        self,
        ctx: ToolContext,
        query: str = "",
        topics: list | None = None,
        categories: list | None = None,
        feed_types: list | None = None,
        time_window: str = "24h",
        limit: int = 50
    ) -> ToolResult:
        if not LUNARCRUSH_AVAILABLE:
            return ToolResult(success=False, output=None, error="LunarCrush tools not available.")
        try:
            result = await asyncio.to_thread(
                search_content, query, topics, categories, feed_types, time_window, limit
            )
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
