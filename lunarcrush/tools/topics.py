#!/usr/bin/env python3
"""
LunarCrush Topics API Tools

Tools for fetching trending topics, news summaries, and top posts.
Provides social sentiment analysis for crypto-related topics.
"""

import json
import argparse
from typing import Dict, Any, Optional, List

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


def get_topic_posts(topic: str, limit: int = 20) -> Dict[str, Any]:
    """
    Get top posts for a topic.

    Args:
        topic: Topic name or slug
        limit: Number of posts (max 100)

    Returns:
        Dictionary with top posts for the topic
    """
    topic_slug = topic.lower().strip().replace(" ", "-")

    params = {
        "limit": min(limit, 100)
    }

    data = make_request(f"/public/topic/{topic_slug}/posts/v1", params)

    posts = data.get("data", [])
    formatted = []

    for post in posts:
        formatted.append({
            "id": post.get("id"),
            "network": post.get("network", ""),  # twitter, reddit, etc.
            "body": post.get("body", ""),
            "title": post.get("title", ""),
            "url": post.get("url", ""),
            "author": post.get("author", ""),
            "author_followers": post.get("author_followers"),
            "interactions": post.get("interactions"),
            "sentiment": post.get("sentiment"),
            "created_at": post.get("created_at")
        })

    return {
        "topic": topic_slug,
        "posts": formatted,
        "count": len(formatted)
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
