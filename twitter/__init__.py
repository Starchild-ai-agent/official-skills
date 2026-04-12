"""
Twitter/X Extension — Read-only data via twitterapi.io

Provides 13 tools for Twitter/X data:
- twitter_search_tweets: Advanced tweet search
- twitter_get_tweets: Get tweets by ID
- twitter_get_article: Get long-form article by tweet ID
- twitter_tweet_thread_context: Get complete thread context
- twitter_tweet_quote: Get quote tweets for a tweet
- twitter_get_trends: Get trends
- twitter_user_info: User profile lookup
- twitter_user_tweets: User's recent tweets
- twitter_user_followers: User's followers
- twitter_user_followings: User's followings
- twitter_tweet_replies: Replies to a tweet
- twitter_tweet_retweeters: Users who retweeted
- twitter_search_users: Search for users

Environment Variables:
- TWITTER_API_KEY: API key for twitterapi.io (required)

Usage:
    This extension is auto-loaded by the ExtensionLoader.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


def register(api) -> List[str]:
    """
    Extension entry point — register all Twitter tools.

    Args:
        api: ExtensionApi instance with registry and config

    Returns:
        List of registered tool names
    """
    registered = []

    try:
        from .tools import (
            TwitterSearchTweetsTool,
            TwitterGetTweetsTool,
            TwitterGetArticleTool,
            TwitterTweetThreadContextTool,
            TwitterTweetQuoteTool,
            TwitterGetTrendsTool,
            TwitterUserInfoTool,
            TwitterUserTweetsTool,
            TwitterUserFollowersTool,
            TwitterUserFollowingsTool,
            TwitterTweetRepliesTool,
            TwitterTweetRetweetersTool,
            TwitterSearchUsersTool,
        )

        api.register_tool(TwitterSearchTweetsTool())
        api.register_tool(TwitterGetTweetsTool())
        api.register_tool(TwitterGetArticleTool())
        api.register_tool(TwitterTweetThreadContextTool())
        api.register_tool(TwitterTweetQuoteTool())
        api.register_tool(TwitterGetTrendsTool())
        api.register_tool(TwitterUserInfoTool())
        api.register_tool(TwitterUserTweetsTool())
        api.register_tool(TwitterUserFollowersTool())
        api.register_tool(TwitterUserFollowingsTool())
        api.register_tool(TwitterTweetRepliesTool())
        api.register_tool(TwitterTweetRetweetersTool())
        api.register_tool(TwitterSearchUsersTool())

        registered = [
            "twitter_search_tweets",
            "twitter_get_tweets",
            "twitter_get_article",
            "twitter_tweet_thread_context",
            "twitter_tweet_quote",
            "twitter_get_trends",
            "twitter_user_info",
            "twitter_user_tweets",
            "twitter_user_followers",
            "twitter_user_followings",
            "twitter_tweet_replies",
            "twitter_tweet_retweeters",
            "twitter_search_users",
        ]

        logger.info(f"Registered Twitter tools ({len(registered)} tools)")
    except Exception as e:
        logger.warning(f"Failed to load Twitter tools: {e}")

    return registered


# Extension metadata
EXTENSION_INFO = {
    "name": "twitter",
    "version": "1.1.0",
    "description": "Twitter/X data — search tweets, article, thread context, quote tweets, trends, users",
    "tools": [
        "twitter_search_tweets",
        "twitter_get_tweets",
        "twitter_get_article",
        "twitter_tweet_thread_context",
        "twitter_tweet_quote",
        "twitter_get_trends",
        "twitter_user_info",
        "twitter_user_tweets",
        "twitter_user_followers",
        "twitter_user_followings",
        "twitter_tweet_replies",
        "twitter_tweet_retweeters",
        "twitter_search_users",
    ],
    "env_vars": [
        "TWITTER_API_KEY",
    ],
}
