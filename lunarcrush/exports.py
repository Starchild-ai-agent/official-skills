"""
LunarCrush skill exports — tool names match SKILL.md frontmatter.

Usage in task scripts:
    from core.skill_tools import lunarcrush
    btc = lunarcrush.lunar_coin(coin="BTC")
    ts = lunarcrush.lunar_coin_time_series(coin="BTC", bucket="day", interval="1m")
    meta = lunarcrush.lunar_coin_meta(coin="ETH")
    topic = lunarcrush.lunar_topic(topic="bitcoin")
    posts = lunarcrush.lunar_topic_posts(topic="defi", limit=10)
    creator = lunarcrush.lunar_creator(network="twitter", id="elonmusk")
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tools"))

from coins import get_coin, get_coin_time_series, get_coin_meta
from topics import (
    get_topic,
    get_topic_posts,
    get_topic_news,
    get_category_posts,
    get_category_news,
    get_content_feed,
    search_content,
)
from creators import get_creator


def lunar_coin(coin):
    """Get detailed social metrics for a single coin."""
    return get_coin(coin=coin)


def lunar_coin_time_series(coin, bucket="day", interval="1m"):
    """Get coin time-series data (price + social metrics over time)."""
    return get_coin_time_series(coin=coin, bucket=bucket, interval=interval)


def lunar_coin_meta(coin):
    """Get coin metadata (links, description, social accounts)."""
    return get_coin_meta(coin=coin)


def lunar_topic(topic):
    """Get metrics for a specific topic (24h aggregation)."""
    return get_topic(topic=topic)


def lunar_topic_posts(topic, limit=20):
    """Get top posts for a topic."""
    return get_topic_posts(topic=topic, limit=limit)


def lunar_topic_news(topic, limit=20):
    """Get topic news feed."""
    return get_topic_news(topic=topic, limit=limit)


def lunar_category_posts(category, limit=20):
    """Get top posts for a category."""
    return get_category_posts(category=category, limit=limit)


def lunar_category_news(category, limit=20):
    """Get category news feed."""
    return get_category_news(category=category, limit=limit)


def lunar_content_feed(feed_type, scope_type, scope, limit=20):
    """Unified content feed: topic/category × news/posts."""
    return get_content_feed(feed_type=feed_type, scope_type=scope_type, scope=scope, limit=limit)


def lunar_search_content(
    query="",
    topics=None,
    categories=None,
    feed_types=None,
    time_window="24h",
    limit=50,
):
    """Cross-topic/category content search + sentiment summary."""
    return search_content(
        query=query,
        topics=topics,
        categories=categories,
        feed_types=feed_types,
        time_window=time_window,
        limit=limit,
    )


def lunar_creator(network, id):
    """Get details for a specific influencer."""
    return get_creator(network=network, id=id)
