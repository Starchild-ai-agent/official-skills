"""
Twitter/X skill exports — script-mode wrapper around twitterapi.io.

Usage from a bash block:
    python3 - <<'EOF'
    import sys
    sys.path.insert(0, "/data/workspace/skills/twitter")
    from exports import twitter_user_info, twitter_search_tweets
    print(twitter_user_info(username="elonmusk"))
    EOF

All 13 functions are flat, sync wrappers around TwitterApiClient methods.
HTTP traffic goes through sc-proxy via core.http_client — credentials
injected server-side, no TWITTER_API_KEY needed locally.
"""
from __future__ import annotations

import os
import sys
from typing import List, Optional

# Make local client.py importable regardless of caller cwd.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from client import TwitterApiClient  # noqa: E402

_client_singleton: Optional[TwitterApiClient] = None


def _client() -> TwitterApiClient:
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = TwitterApiClient()
    return _client_singleton


# ── Tweet endpoints ──────────────────────────────────────────────────────────


def twitter_search_tweets(query: str, cursor: Optional[str] = None) -> dict:
    """Search Twitter/X tweets using advanced query syntax.

    Operators: from:user, to:user, #hashtag, $cashtag, lang:en, has:media,
    has:links, is:reply, min_faves:100, since:YYYY-MM-DD, until:YYYY-MM-DD.

    Returns dict with `tweets` array and `next_cursor` for pagination.
    """
    return _client().search_tweets(query, cursor=cursor)


def twitter_get_tweets(tweet_ids: List[str]) -> dict:
    """Get one or more tweets by their tweet IDs.

    `tweet_ids` is a list of stringified tweet IDs.
    Returns dict with `tweets` array containing full tweet data.
    """
    if isinstance(tweet_ids, str):
        # Be forgiving — accept comma string too.
        tweet_ids = [t.strip() for t in tweet_ids.split(",") if t.strip()]
    return _client().get_tweets(tweet_ids)


def twitter_tweet_replies(tweet_id: str, cursor: Optional[str] = None) -> dict:
    """Get replies to a specific tweet (by tweet ID)."""
    return _client().get_tweet_replies(tweet_id, cursor=cursor)


def twitter_tweet_retweeters(tweet_id: str, cursor: Optional[str] = None) -> dict:
    """Get users who retweeted a specific tweet."""
    return _client().get_tweet_retweeters(tweet_id, cursor=cursor)


def twitter_tweet_thread_context(tweet_id: str) -> dict:
    """Get full thread context for a tweet (parent chain + direct replies)."""
    return _client().get_tweet_thread_context(tweet_id)


def twitter_tweet_quote(tweet_id: str, cursor: Optional[str] = None) -> dict:
    """Get quote tweets that quote a specific tweet."""
    return _client().get_tweet_quote(tweet_id, cursor=cursor)


def twitter_get_article(tweet_id: str) -> dict:
    """Get long-form X article content by the article's tweet ID."""
    return _client().get_article(tweet_id)


def twitter_get_trends(
    woeid: Optional[str] = None,
    country: Optional[str] = None,
    category: Optional[str] = None,
    limit: Optional[int] = None,
) -> dict:
    """Get Twitter/X trending topics.

    All filters optional. `woeid` = Where On Earth ID (numeric region code).
    """
    return _client().get_trends(woeid=woeid, country=country, category=category, limit=limit)


# ── User endpoints ───────────────────────────────────────────────────────────


def twitter_user_info(username: str) -> dict:
    """Get a user's profile: bio, follower/following count, tweet count, verified."""
    return _client().get_user_info(username)


def twitter_user_tweets(username: str, cursor: Optional[str] = None) -> dict:
    """Get a user's recent tweets (paginated)."""
    return _client().get_user_tweets(username, cursor=cursor)


def twitter_user_followers(username: str, cursor: Optional[str] = None) -> dict:
    """Get a user's followers (paginated)."""
    return _client().get_user_followers(username, cursor=cursor)


def twitter_user_followings(username: str, cursor: Optional[str] = None) -> dict:
    """Get accounts a user follows (paginated)."""
    return _client().get_user_followings(username, cursor=cursor)


def twitter_search_users(query: str, cursor: Optional[str] = None) -> dict:
    """Search for users by name or keyword."""
    return _client().search_users(query, cursor=cursor)


__all__ = [
    "twitter_search_tweets",
    "twitter_get_tweets",
    "twitter_tweet_replies",
    "twitter_tweet_retweeters",
    "twitter_tweet_thread_context",
    "twitter_tweet_quote",
    "twitter_get_article",
    "twitter_get_trends",
    "twitter_user_info",
    "twitter_user_tweets",
    "twitter_user_followers",
    "twitter_user_followings",
    "twitter_search_users",
]
