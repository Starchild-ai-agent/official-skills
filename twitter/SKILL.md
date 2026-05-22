---
name: twitter
version: 2.0.2
description: |
  Twitter/X data: fetch tweets, search, user profiles, followers, replies, trends.

  Use for any x.com or twitter.com URL or lookup (e.g. summarize this tweet, recent posts by @vitalikbuterin, search $SOL min_faves:50).
delivery: script
metadata:
  starchild:
    emoji: "🐦"
    skillKey: twitter
    requires:
      env:
        - TWITTER_API_KEY

user-invocable: false
disable-model-invocation: false

---

# Twitter / X (script-mode)

Read-only access to twitterapi.io endpoints. 13 functions covering tweets,
users, followers, replies, threads, quotes, articles, and trends.

All requests go through sc-proxy via `core.http_client.proxied_get`. The
`TWITTER_API_KEY` env var is auto-injected server-side, no local key needed
on the agent machine.

## Script Usage

Standard invocation pattern:

```bash
python3 - <<'EOF'
import sys, json
sys.path.insert(0, "/data/workspace/skills/twitter")
from exports import twitter_user_info, twitter_user_tweets

profile = twitter_user_info(username="vitalikbuterin")
print(json.dumps(profile, indent=2))

recent = twitter_user_tweets(username="vitalikbuterin")
print(f"got {len(recent.get('tweets', []))} tweets")
EOF
```

Tweet ID extraction from URL: the last path segment of any
`x.com/{user}/status/{id}` or `twitter.com/{user}/status/{id}` URL is the
tweet ID. Pass it as a string (Python int will lose precision on long IDs).

## Function Reference (signatures)

All 13 functions live in `exports.py`. Returns are dicts straight from
twitterapi.io — keys vary per endpoint, inspect once before scripting.

### Tweet endpoints

| Function | Description |
|---|---|
| `twitter_search_tweets(query, cursor=None)` | Advanced search. Operators: `from:user`, `to:user`, `#tag`, `$cashtag`, `lang:en`, `has:media`, `has:links`, `is:reply`, `min_faves:N`, `since:YYYY-MM-DD`, `until:YYYY-MM-DD`. |
| `twitter_get_tweets(tweet_ids)` | Fetch one or more tweets by ID. `tweet_ids` = list of strings (also accepts comma-string). |
| `twitter_tweet_replies(tweet_id, cursor=None)` | Replies to a tweet. |
| `twitter_tweet_retweeters(tweet_id, cursor=None)` | Users who retweeted. |
| `twitter_tweet_thread_context(tweet_id)` | Full thread context (parents + direct replies). |
| `twitter_tweet_quote(tweet_id, cursor=None)` | Quote tweets. |
| `twitter_get_article(tweet_id)` | Long-form X article body. |
| `twitter_get_trends(woeid=None, country=None, category=None, limit=None)` | Trending topics; all filters optional. |

### User endpoints

| Function | Description |
|---|---|
| `twitter_user_info(username)` | Profile: bio, follower/following counts, tweet count, verified. |
| `twitter_user_tweets(username, cursor=None)` | User's recent tweets. |
| `twitter_user_followers(username, cursor=None)` | Follower list. |
| `twitter_user_followings(username, cursor=None)` | Accounts followed. |
| `twitter_search_users(query, cursor=None)` | Search users by name/keyword. |

`username` is the handle WITHOUT `@` (e.g. `"elonmusk"`, not `"@elonmusk"`).
Pagination: when a response includes `next_cursor`, pass it back as `cursor`
on the next call.

## When to use this skill

- ANY `x.com/...` or `twitter.com/...` URL → start here, NOT `web_fetch`
  (Twitter blocks scrapers).
- Single tweet detail → `twitter_get_tweets([tweet_id])`.
- "What's @user been posting?" → `twitter_user_tweets`.
- KOL discovery / cashtag mentions → `twitter_search_tweets("$SOL min_faves:50")`.
- Trending topics → `twitter_get_trends`.

## Error handling

- `402 Credits is not enough` → upstream proxy credits exhausted; tell user
  to top up. Don't retry.
- `429` → rate limited; surface to user, don't auto-retry.
- `404 user not found` → suggest verifying the handle spelling.

## Version Policy (hard rule)

This skill is **script-mode** (`delivery: script`). It does NOT register
runtime tools — agent must `read_file` SKILL.md and call functions via
`bash` + `python3`. The legacy `tools.py` / `__init__.py` files are kept
for backward compatibility but are no longer the preferred entry point.

Bump rules:
- Any signature change, env-var change, or sc-proxy contract change → MAJOR
- New function added, response schema clarified → MINOR
- Bug fix or doc-only change → PATCH
