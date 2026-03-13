"""
Twitter/X Tools — BaseTool subclasses for agent use.

9 read-only tools: search tweets, get tweets, user info, user tweets,
user followers, user followings, tweet replies, tweet retweeters, search users.
"""

import asyncio
import logging

from core.tool import BaseTool, ToolContext, ToolResult
from .client import TwitterApiClient

logger = logging.getLogger(__name__)

# Module-level shared client instance
_client: TwitterApiClient = None


def _get_client() -> TwitterApiClient:
    global _client
    if _client is None:
        _client = TwitterApiClient()
    return _client


# ── Tweet Tools ──────────────────────────────────────────────────────────────


class TwitterSearchTweetsTool(BaseTool):
    """Search tweets with advanced query syntax."""

    @property
    def name(self) -> str:
        return "twitter_search_tweets"

    @property
    def description(self) -> str:
        return """Search Twitter/X tweets using advanced query syntax.

Supports operators: keyword matching, from:user, to:user, #hashtag, $cashtag,
lang:en, has:media, has:links, is:reply, min_faves:100, since:2024-01-01, until:2024-12-31.

Parameters:
- query: Search query (required). Examples: "bitcoin", "from:elonmusk crypto", "$SOL min_faves:50"
- cursor: Pagination cursor from previous response (optional)

Returns: tweets array with text, author, metrics, and next cursor for pagination"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (supports advanced operators)",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from previous response",
                },
            },
            "required": ["query"],
        }

    async def execute(self, ctx: ToolContext, query: str = "", cursor: str = None, **kwargs) -> ToolResult:
        if not query:
            return ToolResult(success=False, error="'query' is required")
        try:
            client = _get_client()
            data = await asyncio.to_thread(client.search_tweets, query, cursor=cursor)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class TwitterGetTweetsTool(BaseTool):
    """Get tweets by their IDs."""

    @property
    def name(self) -> str:
        return "twitter_get_tweets"

    @property
    def description(self) -> str:
        return """Get one or more tweets by their tweet IDs.

Parameters:
- tweet_ids: Array of tweet ID strings (required, e.g. ["1234567890", "9876543210"])

Returns: tweets array with full tweet data"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "tweet_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of tweet ID strings",
                },
            },
            "required": ["tweet_ids"],
        }

    async def execute(self, ctx: ToolContext, tweet_ids: list = None, **kwargs) -> ToolResult:
        if not tweet_ids:
            return ToolResult(success=False, error="'tweet_ids' is required")
        try:
            client = _get_client()
            data = await asyncio.to_thread(client.get_tweets, tweet_ids)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class TwitterTweetRepliesTool(BaseTool):
    """Get replies to a specific tweet."""

    @property
    def name(self) -> str:
        return "twitter_tweet_replies"

    @property
    def description(self) -> str:
        return """Get replies to a specific tweet.

Parameters:
- tweet_id: Tweet ID to get replies for (required)
- cursor: Pagination cursor from previous response (optional)

Returns: replies array with tweet data and next cursor"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "tweet_id": {
                    "type": "string",
                    "description": "Tweet ID to get replies for",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from previous response",
                },
            },
            "required": ["tweet_id"],
        }

    async def execute(self, ctx: ToolContext, tweet_id: str = "", cursor: str = None, **kwargs) -> ToolResult:
        if not tweet_id:
            return ToolResult(success=False, error="'tweet_id' is required")
        try:
            client = _get_client()
            data = await asyncio.to_thread(client.get_tweet_replies, tweet_id, cursor=cursor)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class TwitterTweetRetweetersTool(BaseTool):
    """Get users who retweeted a tweet."""

    @property
    def name(self) -> str:
        return "twitter_tweet_retweeters"

    @property
    def description(self) -> str:
        return """Get users who retweeted a specific tweet.

Parameters:
- tweet_id: Tweet ID to get retweeters for (required)
- cursor: Pagination cursor from previous response (optional)

Returns: users array with profile data and next cursor"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "tweet_id": {
                    "type": "string",
                    "description": "Tweet ID to get retweeters for",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from previous response",
                },
            },
            "required": ["tweet_id"],
        }

    async def execute(self, ctx: ToolContext, tweet_id: str = "", cursor: str = None, **kwargs) -> ToolResult:
        if not tweet_id:
            return ToolResult(success=False, error="'tweet_id' is required")
        try:
            client = _get_client()
            data = await asyncio.to_thread(client.get_tweet_retweeters, tweet_id, cursor=cursor)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ── User Tools ───────────────────────────────────────────────────────────────


class TwitterUserInfoTool(BaseTool):
    """Get a Twitter user's profile information."""

    @property
    def name(self) -> str:
        return "twitter_user_info"

    @property
    def description(self) -> str:
        return """Get a Twitter/X user's profile information: bio, follower count, following count, tweet count, verification status.

Parameters:
- username: Twitter handle without @ (required, e.g. "elonmusk")

Returns: user profile with name, bio, followers_count, following_count, tweet_count, verified"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Twitter handle without @ (e.g. 'elonmusk')",
                },
            },
            "required": ["username"],
        }

    async def execute(self, ctx: ToolContext, username: str = "", **kwargs) -> ToolResult:
        if not username:
            return ToolResult(success=False, error="'username' is required")
        try:
            client = _get_client()
            data = await asyncio.to_thread(client.get_user_info, username)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class TwitterUserTweetsTool(BaseTool):
    """Get a user's recent tweets."""

    @property
    def name(self) -> str:
        return "twitter_user_tweets"

    @property
    def description(self) -> str:
        return """Get a Twitter/X user's recent tweets.

Parameters:
- username: Twitter handle without @ (required, e.g. "elonmusk")
- cursor: Pagination cursor from previous response (optional)

Returns: tweets array with text, metrics, timestamps, and next cursor"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Twitter handle without @ (e.g. 'elonmusk')",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from previous response",
                },
            },
            "required": ["username"],
        }

    async def execute(self, ctx: ToolContext, username: str = "", cursor: str = None, **kwargs) -> ToolResult:
        if not username:
            return ToolResult(success=False, error="'username' is required")
        try:
            client = _get_client()
            data = await asyncio.to_thread(client.get_user_tweets, username, cursor=cursor)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class TwitterUserFollowersTool(BaseTool):
    """Get a user's followers."""

    @property
    def name(self) -> str:
        return "twitter_user_followers"

    @property
    def description(self) -> str:
        return """Get a Twitter/X user's followers.

Parameters:
- username: Twitter handle without @ (required, e.g. "elonmusk")
- cursor: Pagination cursor from previous response (optional)

Returns: users array with profile data and next cursor"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Twitter handle without @ (e.g. 'elonmusk')",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from previous response",
                },
            },
            "required": ["username"],
        }

    async def execute(self, ctx: ToolContext, username: str = "", cursor: str = None, **kwargs) -> ToolResult:
        if not username:
            return ToolResult(success=False, error="'username' is required")
        try:
            client = _get_client()
            data = await asyncio.to_thread(client.get_user_followers, username, cursor=cursor)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class TwitterUserFollowingsTool(BaseTool):
    """Get accounts a user follows."""

    @property
    def name(self) -> str:
        return "twitter_user_followings"

    @property
    def description(self) -> str:
        return """Get accounts that a Twitter/X user follows.

Parameters:
- username: Twitter handle without @ (required, e.g. "elonmusk")
- cursor: Pagination cursor from previous response (optional)

Returns: users array with profile data and next cursor"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Twitter handle without @ (e.g. 'elonmusk')",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from previous response",
                },
            },
            "required": ["username"],
        }

    async def execute(self, ctx: ToolContext, username: str = "", cursor: str = None, **kwargs) -> ToolResult:
        if not username:
            return ToolResult(success=False, error="'username' is required")
        try:
            client = _get_client()
            data = await asyncio.to_thread(client.get_user_followings, username, cursor=cursor)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class TwitterSearchUsersTool(BaseTool):
    """Search for Twitter users."""

    @property
    def name(self) -> str:
        return "twitter_search_users"

    @property
    def description(self) -> str:
        return """Search for Twitter/X users by name or keyword.

Parameters:
- query: Search query (required, e.g. "crypto analyst", "bitcoin")
- cursor: Pagination cursor from previous response (optional)

Returns: users array with profile data and next cursor"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for users",
                },
                "cursor": {
                    "type": "string",
                    "description": "Pagination cursor from previous response",
                },
            },
            "required": ["query"],
        }

    async def execute(self, ctx: ToolContext, query: str = "", cursor: str = None, **kwargs) -> ToolResult:
        if not query:
            return ToolResult(success=False, error="'query' is required")
        try:
            client = _get_client()
            data = await asyncio.to_thread(client.search_users, query, cursor=cursor)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
