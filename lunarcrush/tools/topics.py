#!/usr/bin/env python3
"""
LunarCrush Topics API Tools

Tools for fetching trending topics, news summaries, and top posts.
Provides social sentiment analysis for crypto-related topics.
"""

import json
import time
import argparse
from typing import Dict, Any

try:
    from .utils import make_request
except ImportError:
    from utils import make_request


# MCP Tool Schemas
MCP_TOPICS_SCHEMA = {
    "name": "lunar_topics",
    "title": "LunarCrush Trending Topics",
    "description": "Get trending social topics in crypto.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "sort": {
                "type": "string",
                "description": "Sort field",
                "default": "interactions_24h",
                "enum": ["interactions_24h", "social_dominance", "num_contributors"]
            },
            "limit": {
                "type": "integer",
                "description": "Number of results (max 100)",
                "default": 50,
                "minimum": 1,
                "maximum": 100
            }
        },
        "additionalProperties": False
    }
}

MCP_TOPIC_SCHEMA = {
    "name": "lunar_topic",
    "title": "LunarCrush Single Topic",
    "description": "Get metrics for a specific topic (24h aggregation).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "Topic name or slug (e.g., 'bitcoin', 'defi', 'nft')"
            }
        },
        "required": ["topic"],
        "additionalProperties": False
    }
}

MCP_TOPIC_SUMMARY_SCHEMA = {
    "name": "lunar_topic_summary",
    "title": "LunarCrush Topic Summary",
    "description": "Get AI-generated news summary for a topic.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "Topic name or slug"
            }
        },
        "required": ["topic"],
        "additionalProperties": False
    }
}

MCP_TOPIC_POSTS_SCHEMA = {
    "name": "lunar_topic_posts",
    "title": "LunarCrush Topic Posts",
    "description": "Get top posts for a topic.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "Topic name or slug"
            },
            "limit": {
                "type": "integer",
                "description": "Number of posts (max 100)",
                "default": 20,
                "minimum": 1,
                "maximum": 100
            }
        },
        "required": ["topic"],
        "additionalProperties": False
    }
}


def get_topics(
    sort: str = "interactions_24h",
    limit: int = 50
) -> Dict[str, Any]:
    """
    Get trending social topics in crypto.

    Args:
        sort: Sort field (interactions_24h, social_dominance, num_contributors)
        limit: Number of results (max 100)

    Returns:
        Dictionary with list of trending topics
    """
    params = {
        "sort": sort,
        "limit": min(limit, 100)
    }

    data = make_request("/public/topics/list/v1", params)

    topics = data.get("data", [])
    formatted = []

    for topic in topics:
        formatted.append({
            "topic": topic.get("topic", ""),
            "title": topic.get("title", ""),
            "interactions_24h": topic.get("interactions_24h"),
            "social_dominance": topic.get("social_dominance"),
            "num_contributors": topic.get("num_contributors"),
            "sentiment": topic.get("sentiment"),
            "trend": topic.get("trend"),
            "categories": topic.get("categories", [])
        })

    return {
        "topics": formatted,
        "count": len(formatted),
        "sort_by": sort
    }


def get_topic(topic: str) -> Dict[str, Any]:
    """
    Get metrics for a specific topic (24h aggregation).

    Args:
        topic: Topic name or slug (e.g., 'bitcoin', 'defi', 'nft')

    Returns:
        Dictionary with topic metrics
    """
    topic_slug = topic.lower().strip().replace(" ", "-")
    data = make_request(f"/public/topic/{topic_slug}/v1")

    topic_data = data.get("data", {})

    return {
        "topic": topic_data.get("topic", topic_slug),
        "title": topic_data.get("title", ""),
        "interactions_24h": topic_data.get("interactions_24h"),
        "social_dominance": topic_data.get("social_dominance"),
        "num_contributors": topic_data.get("num_contributors"),
        "sentiment": topic_data.get("sentiment"),
        "trend": topic_data.get("trend"),
        "average_sentiment": topic_data.get("average_sentiment"),
        "tweets": topic_data.get("tweets"),
        "reddit_posts": topic_data.get("reddit_posts"),
        "news_articles": topic_data.get("news"),
        "youtube_videos": topic_data.get("youtube"),
        "categories": topic_data.get("categories", []),
        "related_topics": topic_data.get("related_topics", []),
        "related_coins": topic_data.get("related_coins", [])
    }


def get_topic_summary(topic: str) -> Dict[str, Any]:
    """
    Get AI-generated news summary for a topic.

    Args:
        topic: Topic name or slug

    Returns:
        Dictionary with AI-generated summary and key points
    """
    topic_slug = topic.lower().strip().replace(" ", "-")
    data = make_request(f"/public/topic/{topic_slug}/whatsup/v1")

    summary_data = data.get("data", {})

    return {
        "topic": topic_slug,
        "summary": summary_data.get("summary", ""),
        "key_points": summary_data.get("key_points", []),
        "sentiment_summary": summary_data.get("sentiment_summary", ""),
        "trending_narratives": summary_data.get("trending_narratives", []),
        "notable_news": summary_data.get("notable_news", []),
        "generated_at": summary_data.get("generated_at")
    }


def _slug(value: str) -> str:
    """Normalize topic/category string to slug format used by API paths."""
    return value.lower().strip().replace(" ", "-")


def _format_content_items(items):
    """Normalize news/post payload fields into a stable shape."""
    formatted = []
    for item in items:
        formatted.append({
            "id": item.get("id"),
            "post_type": item.get("post_type"),
            "network": item.get("network", ""),
            "title": item.get("post_title") or item.get("title", ""),
            "description": item.get("post_description") or item.get("description", ""),
            "body": item.get("body", ""),
            "url": item.get("post_link") or item.get("url", ""),
            "image": item.get("post_image") or item.get("image", ""),
            "author": item.get("creator_name") or item.get("author", ""),
            "author_display_name": item.get("creator_display_name", ""),
            "author_followers": item.get("creator_followers") or item.get("author_followers"),
            "interactions_24h": item.get("interactions_24h"),
            "interactions_total": item.get("interactions_total") or item.get("interactions"),
            "sentiment": item.get("post_sentiment") if item.get("post_sentiment") is not None else item.get("sentiment"),
            "created_at": item.get("post_created") if item.get("post_created") is not None else item.get("created_at")
        })
    return formatted


def get_topic_posts(topic: str, limit: int = 20) -> Dict[str, Any]:
    """
    Get top posts for a topic.

    Args:
        topic: Topic name or slug
        limit: Number of posts (max 100)

    Returns:
        Dictionary with top posts for the topic
    """
    topic_slug = _slug(topic)
    params = {"limit": min(limit, 100)}
    data = make_request(f"/public/topic/{topic_slug}/posts/v1", params)

    posts = _format_content_items(data.get("data", []))[:min(limit, 100)]

    return {
        "topic": topic_slug,
        "posts": posts,
        "count": len(posts)
    }


def get_topic_news(topic: str, limit: int = 20) -> Dict[str, Any]:
    """
    Get news feed for a topic.

    Args:
        topic: Topic name or slug
        limit: Number of news items returned in output (max 100)

    Returns:
        Dictionary with topic news items
    """
    topic_slug = _slug(topic)
    # API quirk: /topic/:topic/news/v1 does not accept `limit` query param.
    data = make_request(f"/public/topic/{topic_slug}/news/v1")
    news = _format_content_items(data.get("data", []))[:min(limit, 100)]

    return {
        "topic": topic_slug,
        "news": news,
        "count": len(news)
    }


def get_category_posts(category: str, limit: int = 20) -> Dict[str, Any]:
    """
    Get top social posts for a category.

    Args:
        category: Category name or slug (e.g. defi, gaming, memecoin)
        limit: Number of posts returned in output (max 100)

    Returns:
        Dictionary with category posts
    """
    category_slug = _slug(category)
    # API quirk: /category/:category/posts/v1 does not accept `limit` query param.
    data = make_request(f"/public/category/{category_slug}/posts/v1")
    posts = _format_content_items(data.get("data", []))[:min(limit, 100)]

    return {
        "category": category_slug,
        "posts": posts,
        "count": len(posts)
    }


def get_category_news(category: str, limit: int = 20) -> Dict[str, Any]:
    """
    Get news feed for a category.

    Args:
        category: Category name or slug (e.g. defi, gaming, memecoin)
        limit: Number of news items returned in output (max 100)

    Returns:
        Dictionary with category news items
    """
    category_slug = _slug(category)
    # API quirk: /category/:category/news/v1 does not accept `limit` query param.
    data = make_request(f"/public/category/{category_slug}/news/v1")
    news = _format_content_items(data.get("data", []))[:min(limit, 100)]

    return {
        "category": category_slug,
        "news": news,
        "count": len(news)
    }


def get_content_feed(feed_type: str, scope_type: str, scope: str, limit: int = 20) -> Dict[str, Any]:
    """
    Unified content feed entry point for agent use.

    Args:
        feed_type: "news" or "posts"
        scope_type: "topic" or "category"
        scope: Topic/category value
        limit: Number of items (max 100)

    Returns:
        Dictionary with normalized feed output
    """
    feed_type = feed_type.lower().strip()
    scope_type = scope_type.lower().strip()

    if feed_type not in {"news", "posts"}:
        raise ValueError("feed_type must be one of: news, posts")
    if scope_type not in {"topic", "category"}:
        raise ValueError("scope_type must be one of: topic, category")

    if scope_type == "topic" and feed_type == "news":
        data = get_topic_news(scope, limit)
    elif scope_type == "topic" and feed_type == "posts":
        data = get_topic_posts(scope, limit)
    elif scope_type == "category" and feed_type == "news":
        data = get_category_news(scope, limit)
    else:
        data = get_category_posts(scope, limit)

    return {
        "scope_type": scope_type,
        "scope": _slug(scope),
        "feed_type": feed_type,
        "count": data.get("count", 0),
        "items": data.get(feed_type, []) if feed_type in data else data.get("posts", [])
    }


def _matches_query(item: dict, query: str) -> bool:
    """Check if a content item contains the query keyword (case-insensitive)."""
    q = query.lower()
    searchable = " ".join(str(v) for v in [
        item.get("title", ""),
        item.get("description", ""),
        item.get("body", ""),
        item.get("author", ""),
        item.get("author_display_name", ""),
    ] if v)
    return q in searchable.lower()


def search_content(
    query: str = "",
    topics: list | None = None,
    categories: list | None = None,
    feed_types: list | None = None,
    time_window: str = "24h",
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Cross-topic/category content search for Agent use.

    Aggregates news + posts from multiple scopes, deduplicates by URL,
    sorts by interactions (engagement), and optionally filters by keyword.

    Args:
        query: Keyword filter (empty = no filter, returns all). Searches
               title + description + body + author fields.
        topics: List of topic slugs to search (e.g. ["bitcoin", "defi"]).
                Default: ["bitcoin", "ethereum", "solana"]
        categories: List of category slugs (e.g. ["defi", "gaming"]).
                    Default: ["defi"]
        feed_types: Which content types: "news", "posts", or both.
                    Default: ["news", "posts"]
        time_window: Time scope filter placeholder (API returns recent content).
                     Accepted values: "1h", "24h", "7d", "30d". Default: "24h"
        limit: Max items returned (max 200). Default: 50

    Returns:
        {
            "query": str,
            "total_fetched": int,
            "items": [deduplicated, sorted items],
            "count": int,
            "sentiment_summary": {avg, bullish_pct, bearish_pct, neutral_pct}
        }
    """
    # Defaults
    if topics is None:
        topics = ["bitcoin", "ethereum", "solana"]
    if categories is None:
        categories = ["defi"]
    if feed_types is None:
        feed_types = ["news", "posts"]
    if time_window not in {"1h", "24h", "7d", "30d"}:
        time_window = "24h"

    all_items: list[dict] = []
    call_count = 0

    def _fetch_with_retry(fn, retries=3, backoff=5):
        """Fetch with retry on rate limit (429)."""
        for attempt in range(retries + 1):
            try:
                result = fn()
                return result
            except Exception as e:
                err_str = str(e)
                if "429" in err_str and attempt < retries:
                    wait = backoff * (attempt + 1)
                    time.sleep(wait)
                else:
                    raise

    def _safe_fetch(fn):
        """Fetch with rate-limit spacing and retry."""
        nonlocal call_count
        if call_count > 0:
            time.sleep(1.0)
        call_count += 1
        try:
            return _fetch_with_retry(fn)
        except Exception:
            return None

    # Fetch from topics
    for t in topics:
        for ft in feed_types:
            if ft == "news":
                data = _safe_fetch(lambda topic=t: get_topic_news(topic, limit=100))
                if data:
                    all_items.extend(data.get("news", []))
            else:
                data = _safe_fetch(lambda topic=t: get_topic_posts(topic, limit=100))
                if data:
                    all_items.extend(data.get("posts", []))

    # Fetch from categories
    for c in categories:
        for ft in feed_types:
            if ft == "news":
                data = _safe_fetch(lambda cat=c: get_category_news(cat, limit=100))
                if data:
                    all_items.extend(data.get("news", []))
            else:
                data = _safe_fetch(lambda cat=c: get_category_posts(cat, limit=100))
                if data:
                    all_items.extend(data.get("posts", []))

    # Deduplicate by URL
    seen_urls: set[str] = set()
    deduped: list[dict] = []
    for item in all_items:
        url = item.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            deduped.append(item)
        elif not url:
            deduped.append(item)

    # Keyword filter
    if query.strip():
        deduped = [item for item in deduped if _matches_query(item, query)]

    total_fetched = len(deduped)

    # Sort by interactions (engagement-first)
    deduped.sort(
        key=lambda x: x.get("interactions_24h") or x.get("interactions_total") or 0,
        reverse=True,
    )

    # Slice
    result_items = deduped[:min(limit, 200)]

    # Sentiment summary
    sentiments = []
    for item in result_items:
        s = item.get("sentiment")
        if s is not None:
            sentiments.append(s)

    sentiment_summary = {}
    if sentiments:
        avg = sum(sentiments) / len(sentiments)
        sentiment_summary = {
            "average_sentiment": round(avg, 3),
            "bullish_pct": round(sum(1 for s in sentiments if s > 0) / len(sentiments) * 100, 1),
            "bearish_pct": round(sum(1 for s in sentiments if s < 0) / len(sentiments) * 100, 1),
            "neutral_pct": round(sum(1 for s in sentiments if s == 0) / len(sentiments) * 100, 1),
            "sample_count": len(sentiments),
        }

    return {
        "query": query,
        "time_window": time_window,
        "total_fetched": total_fetched,
        "items": result_items,
        "count": len(result_items),
        "sentiment_summary": sentiment_summary,
    }


def main():
    """CLI interface for LunarCrush topics tools."""
    parser = argparse.ArgumentParser(
        description="LunarCrush Topics API Tools",
        epilog="""
Commands:
  list     Get trending topics
  topic    Get single topic metrics
  summary  Get AI-generated topic summary
  posts    Get top posts for topic

Examples:
  python topics.py list --limit 10
  python topics.py topic --name bitcoin
  python topics.py summary --name defi
  python topics.py posts --name nft --limit 20
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser("list", help="Get trending topics")
    list_parser.add_argument("--sort", default="interactions_24h",
                            choices=["interactions_24h", "social_dominance", "num_contributors"])
    list_parser.add_argument("--limit", type=int, default=50)

    # Topic command
    topic_parser = subparsers.add_parser("topic", help="Get single topic metrics")
    topic_parser.add_argument("--name", required=True, help="Topic name or slug")

    # Summary command
    summary_parser = subparsers.add_parser("summary", help="Get topic AI summary")
    summary_parser.add_argument("--name", required=True, help="Topic name")

    # Posts command
    posts_parser = subparsers.add_parser("posts", help="Get topic posts")
    posts_parser.add_argument("--name", required=True, help="Topic name")
    posts_parser.add_argument("--limit", type=int, default=20)

    # Schema output
    parser.add_argument("--schema", action="store_true", help="Output MCP schema")

    args = parser.parse_args()

    if args.schema:
        schemas = {
            "topics": MCP_TOPICS_SCHEMA,
            "topic": MCP_TOPIC_SCHEMA,
            "topic_summary": MCP_TOPIC_SUMMARY_SCHEMA,
            "topic_posts": MCP_TOPIC_POSTS_SCHEMA
        }
        print(json.dumps(schemas, indent=2))
        return 0

    try:
        if args.command == "list":
            result = get_topics(sort=args.sort, limit=args.limit)
        elif args.command == "topic":
            result = get_topic(args.name)
        elif args.command == "summary":
            result = get_topic_summary(args.name)
        elif args.command == "posts":
            result = get_topic_posts(args.name, args.limit)
        else:
            parser.print_help()
            return 0

        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))
        return 1


if __name__ == "__main__":
    exit(main())
