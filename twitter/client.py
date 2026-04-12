"""
Twitter API client — wraps twitterapi.io endpoints.

Read-only: search tweets, user profiles, followers, replies, thread context,
quote tweets, article, and trends.
Auth: X-API-Key header from TWITTER_API_KEY env var.
"""

import logging
import os
from typing import Any, List

from core.http_client import proxied_get

CALLER_ID = "chat:twitter-skill"

logger = logging.getLogger(__name__)

TWITTERAPI_BASE_URL = "https://api.twitterapi.io"


class TwitterApiClient:
    """
    Sync twitterapi.io client using proxied_get.

    All endpoints are public GET requests authenticated via X-API-Key header.
    """

    def __init__(self):
        self.base_url = TWITTERAPI_BASE_URL
        self.api_key = os.environ.get("TWITTER_API_KEY", "")

    def _get(self, path: str, params: dict = None) -> Any:
        """GET a twitterapi.io endpoint."""
        url = f"{self.base_url}{path}"

        headers = {"SC-CALLER-ID": CALLER_ID}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        response = proxied_get(url, headers=headers, params=params, timeout=15)
        if response.status_code >= 400:
            raise Exception(f"twitterapi.io {response.status_code}: {response.text}")
        return response.json()

    # ── Tweet Endpoints ──────────────────────────────────────────────────

    def search_tweets(self, query: str, cursor: str = None) -> dict:
        """Advanced tweet search."""
        params = {"query": query}
        if cursor:
            params["cursor"] = cursor
        return self._get("/twitter/tweet/advanced_search", params)

    def get_tweets(self, tweet_ids: List[str]) -> dict:
        """Get tweets by IDs."""
        params = {"tweet_ids": ",".join(tweet_ids)}
        return self._get("/twitter/tweets", params)

    def get_tweet_replies(self, tweet_id: str, cursor: str = None) -> dict:
        """Get replies to a tweet."""
        params = {"tweetId": tweet_id}
        if cursor:
            params["cursor"] = cursor
        return self._get("/twitter/tweet/replies", params)

    def get_tweet_retweeters(self, tweet_id: str, cursor: str = None) -> dict:
        """Get users who retweeted a tweet."""
        params = {"tweetId": tweet_id}
        if cursor:
            params["cursor"] = cursor
        return self._get("/twitter/tweet/retweeters", params)

    def get_tweet_thread_context(self, tweet_id: str) -> dict:
        """Get complete thread context for a tweet (parents + direct replies)."""
        return self._get("/twitter/tweet/thread_context", {"tweetId": tweet_id})

    def get_tweet_quote(self, tweet_id: str, cursor: str = None) -> dict:
        """Get quote tweets for a tweet."""
        params = {"tweetId": tweet_id}
        if cursor:
            params["cursor"] = cursor
        return self._get("/twitter/tweet/quotes", params)

    def get_article(self, tweet_id: str) -> dict:
        """Get article content by tweet ID (long-form X article)."""
        return self._get("/twitter/article", {"tweet_id": tweet_id})

    def get_trends(self, woeid: str = None, country: str = None, category: str = None, limit: int = None) -> dict:
        """Get trending topics."""
        params = {}
        if woeid:
            params["woeid"] = woeid
        if country:
            params["country"] = country
        if category:
            params["category"] = category
        if limit is not None:
            params["limit"] = limit
        return self._get("/twitter/trends", params)

    # ── User Endpoints ───────────────────────────────────────────────────

    def get_user_info(self, username: str) -> dict:
        """Get user profile info."""
        return self._get("/twitter/user/info", {"userName": username})

    def get_user_tweets(self, username: str, cursor: str = None) -> dict:
        """Get user's recent tweets."""
        params = {"userName": username}
        if cursor:
            params["cursor"] = cursor
        return self._get("/twitter/user/last_tweets", params)

    def get_user_followers(self, username: str, cursor: str = None) -> dict:
        """Get user's followers."""
        params = {"userName": username}
        if cursor:
            params["cursor"] = cursor
        return self._get("/twitter/user/followers", params)

    def get_user_followings(self, username: str, cursor: str = None) -> dict:
        """Get accounts the user follows."""
        params = {"userName": username}
        if cursor:
            params["cursor"] = cursor
        return self._get("/twitter/user/followings", params)

    def search_users(self, query: str, cursor: str = None) -> dict:
        """Search for users."""
        params = {"query": query}
        if cursor:
            params["cursor"] = cursor
        return self._get("/twitter/user/search", params)
