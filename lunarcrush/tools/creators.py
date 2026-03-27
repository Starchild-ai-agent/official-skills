#!/usr/bin/env python3
"""
LunarCrush Creators/Influencers API Tools

Tools for fetching crypto influencer data including rankings, metrics, and posts.
"""

import json
import argparse
from typing import Dict, Any

try:
    from .utils import make_request
except ImportError:
    from utils import make_request


# MCP Tool Schemas
MCP_CREATORS_SCHEMA = {
    "name": "lunar_creators",
    "title": "LunarCrush Top Creators",
    "description": "Get top crypto influencers/creators.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "sort": {
                "type": "string",
                "description": "Sort field",
                "default": "influence_rank",
                "enum": ["influence_rank", "followers", "engagement", "interactions"]
            },
            "network": {
                "type": "string",
                "description": "Filter by social network",
                "enum": ["twitter", "youtube", "all"],
                "default": "all"
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

MCP_CREATOR_SCHEMA = {
    "name": "lunar_creator",
    "title": "LunarCrush Single Creator",
    "description": "Get details for a specific influencer.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "network": {
                "type": "string",
                "description": "Social network (twitter, youtube)",
                "enum": ["twitter", "youtube"]
            },
            "id": {
                "type": "string",
                "description": "Creator ID or username"
            }
        },
        "required": ["network", "id"],
        "additionalProperties": False
    }
}

MCP_CREATOR_POSTS_SCHEMA = {
    "name": "lunar_creator_posts",
    "title": "LunarCrush Creator Posts",
    "description": "Get top posts from a specific influencer.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "network": {
                "type": "string",
                "description": "Social network (twitter, youtube)",
                "enum": ["twitter", "youtube"]
            },
            "id": {
                "type": "string",
                "description": "Creator ID or username"
            },
            "limit": {
                "type": "integer",
                "description": "Number of posts (max 100)",
                "default": 20,
                "minimum": 1,
                "maximum": 100
            }
        },
        "required": ["network", "id"],
        "additionalProperties": False
    }
}


def get_creators(
    sort: str = "influence_rank",
    network: str = "all",
    limit: int = 50
) -> Dict[str, Any]:
    """
    Get top crypto influencers/creators.

    Args:
        sort: Sort field (influence_rank, followers, engagement, interactions)
        network: Filter by network (twitter, youtube, all)
        limit: Number of results (max 100)

    Returns:
        Dictionary with list of top creators
    """
    params = {
        "sort": sort,
        "limit": min(limit, 100)
    }

    if network != "all":
        params["network"] = network

    data = make_request("/public/creators/list/v1", params)

    creators = data.get("data", [])
    formatted = []

    for creator in creators:
        formatted.append({
            "id": creator.get("id"),
            "username": creator.get("username", ""),
            "display_name": creator.get("display_name", ""),
            "network": creator.get("network", ""),
            "followers": creator.get("followers"),
            "influence_rank": creator.get("influence_rank"),
            "engagement_rate": creator.get("engagement_rate"),
            "interactions_24h": creator.get("interactions_24h"),
            "posts_24h": creator.get("posts_24h"),
            "avg_sentiment": creator.get("avg_sentiment"),
            "profile_url": creator.get("profile_url", ""),
            "profile_image": creator.get("profile_image", ""),
            "bio": creator.get("bio", ""),
            "verified": creator.get("verified", False),
            "categories": creator.get("categories", [])
        })

    return {
        "creators": formatted,
        "count": len(formatted),
        "sort_by": sort,
        "network_filter": network
    }


def get_creator(network: str, id: str) -> Dict[str, Any]:
    """
    Get details for a specific influencer.

    Args:
        network: Social network (twitter, youtube)
        id: Creator ID or username

    Returns:
        Dictionary with creator details
    """
    network = network.lower().strip()
    if network not in ["twitter", "youtube"]:
        raise ValueError(f"Invalid network: {network}. Must be 'twitter' or 'youtube'")

    data = make_request(f"/public/creator/{network}/{id}/v1")

    creator = data.get("data", {})

    return {
        "id": creator.get("id", id),
        "username": creator.get("username", ""),
        "display_name": creator.get("display_name", ""),
        "network": network,
        "followers": creator.get("followers"),
        "following": creator.get("following"),
        "influence_rank": creator.get("influence_rank"),
        "engagement_rate": creator.get("engagement_rate"),
        "interactions_24h": creator.get("interactions_24h"),
        "interactions_7d": creator.get("interactions_7d"),
        "posts_24h": creator.get("posts_24h"),
        "posts_7d": creator.get("posts_7d"),
        "avg_sentiment": creator.get("avg_sentiment"),
        "profile_url": creator.get("profile_url", ""),
        "profile_image": creator.get("profile_image", ""),
        "bio": creator.get("bio", ""),
        "verified": creator.get("verified", False),
        "categories": creator.get("categories", []),
        "top_coins_mentioned": creator.get("top_coins_mentioned", []),
        "top_topics": creator.get("top_topics", []),
        "joined": creator.get("joined")
    }


def get_creator_posts(network: str, id: str, limit: int = 20) -> Dict[str, Any]:
    """
    Get top posts from a specific influencer.

    Args:
        network: Social network (twitter, youtube)
        id: Creator ID or username
        limit: Number of posts (max 100)

    Returns:
        Dictionary with creator's top posts
    """
    network = network.lower().strip()
    if network not in ["twitter", "youtube"]:
        raise ValueError(f"Invalid network: {network}. Must be 'twitter' or 'youtube'")

    params = {
        "limit": min(limit, 100)
    }

    data = make_request(f"/public/creator/{network}/{id}/posts/v1", params)

    posts = data.get("data", [])
    formatted = []

    for post in posts:
        formatted.append({
            "id": post.get("id"),
            "body": post.get("body", ""),
            "title": post.get("title", ""),
            "url": post.get("url", ""),
            "interactions": post.get("interactions"),
            "likes": post.get("likes"),
            "retweets": post.get("retweets") if network == "twitter" else None,
            "replies": post.get("replies"),
            "views": post.get("views"),
            "sentiment": post.get("sentiment"),
            "coins_mentioned": post.get("coins_mentioned", []),
            "topics": post.get("topics", []),
            "created_at": post.get("created_at")
        })

    return {
        "network": network,
        "creator_id": id,
        "posts": formatted,
        "count": len(formatted)
    }


def main():
    """CLI interface for LunarCrush creators tools."""
    parser = argparse.ArgumentParser(
        description="LunarCrush Creators API Tools",
        epilog="""
Commands:
  list     Get top crypto influencers
  creator  Get single creator details
  posts    Get creator's top posts

Examples:
  python creators.py list --limit 10
  python creators.py creator --network twitter --id elonmusk
  python creators.py posts --network twitter --id VitalikButerin --limit 10
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser("list", help="Get top creators")
    list_parser.add_argument("--sort", default="influence_rank",
                            choices=["influence_rank", "followers", "engagement", "interactions"])
    list_parser.add_argument("--network", default="all",
                            choices=["twitter", "youtube", "all"])
    list_parser.add_argument("--limit", type=int, default=50)

    # Creator command
    creator_parser = subparsers.add_parser("creator", help="Get single creator")
    creator_parser.add_argument("--network", required=True, choices=["twitter", "youtube"])
    creator_parser.add_argument("--id", required=True, help="Creator ID or username")

    # Posts command
    posts_parser = subparsers.add_parser("posts", help="Get creator posts")
    posts_parser.add_argument("--network", required=True, choices=["twitter", "youtube"])
    posts_parser.add_argument("--id", required=True, help="Creator ID or username")
    posts_parser.add_argument("--limit", type=int, default=20)

    # Schema output
    parser.add_argument("--schema", action="store_true", help="Output MCP schema")

    args = parser.parse_args()

    if args.schema:
        schemas = {
            "creators": MCP_CREATORS_SCHEMA,
            "creator": MCP_CREATOR_SCHEMA,
            "creator_posts": MCP_CREATOR_POSTS_SCHEMA
        }
        print(json.dumps(schemas, indent=2))
        return 0

    try:
        if args.command == "list":
            result = get_creators(sort=args.sort, network=args.network, limit=args.limit)
        elif args.command == "creator":
            result = get_creator(args.network, args.id)
        elif args.command == "posts":
            result = get_creator_posts(args.network, args.id, args.limit)
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
