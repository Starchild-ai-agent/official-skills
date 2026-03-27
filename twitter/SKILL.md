---
name: twitter
version: 1.0.0
description: Twitter/X data lookup — search tweets, user profiles, followers, replies. Use when the user asks about Twitter activity, social signals, or wants to look up accounts.
tools:
  - twitter_search_tweets
  - twitter_get_tweets
  - twitter_user_info
  - twitter_user_tweets
  - twitter_user_followers
  - twitter_user_followings
  - twitter_tweet_replies
  - twitter_tweet_retweeters
  - twitter_search_users

metadata:
  starchild:
    emoji: "🐦"
    skillKey: twitter
    requires:
      env: [TWITTER_API_KEY]

user-invocable: false
disable-model-invocation: false
---

# Twitter / X Data

Read-only access to Twitter/X. No posting/liking/following.

## Tools

| Tool | Use when | Key params |
|------|----------|------------|
| `twitter_search_tweets` | Search tweets by topic | `query`, `cursor` |
| `twitter_get_tweets` | Look up specific tweets | `tweet_ids` (array) |
| `twitter_user_info` | Who is this account? | `username` |
| `twitter_user_tweets` | What have they posted? | `username`, `cursor` |
| `twitter_user_followers` | Who follows them? | `username`, `cursor` |
| `twitter_user_followings` | Who do they follow? | `username`, `cursor` |
| `twitter_tweet_replies` | Replies to a tweet | `tweet_id`, `cursor` |
| `twitter_tweet_retweeters` | Who retweeted? | `tweet_id`, `cursor` |
| `twitter_search_users` | Find accounts by keyword | `query`, `cursor` |

## Search Query Operators

Combine freely: `from:VitalikButerin $ETH min_faves:100 since:2024-01-01`

| Operator | Example |
|----------|---------|
| keyword | `bitcoin` |
| exact phrase | `"ethereum merge"` |
| `from:` / `to:` | `from:elonmusk` |
| `#hashtag` / `$cashtag` | `#crypto`, `$BTC` |
| `lang:` | `lang:en` |
| `has:media` / `has:links` | Media or URL filter |
| `min_faves:` / `min_retweets:` | `min_faves:100` |
| `since:` / `until:` | `since:2024-01-01` |

## Common Workflows

**Research account:** `twitter_user_info` → `twitter_user_tweets` → `twitter_user_followings`

**Track topic/token:** `twitter_search_tweets` (e.g. `"$SOL min_faves:50"`) → `twitter_search_users` → drill into interesting accounts

**Analyze engagement:** `twitter_get_tweets` → `twitter_tweet_replies` → `twitter_tweet_retweeters`

## Notes

- Usernames without `@` prefix (`"elonmusk"` not `"@elonmusk"`)
- Tweet IDs as strings (avoid integer overflow)
- Cursor-based pagination: pass returned `cursor` for next page; no cursor = end
