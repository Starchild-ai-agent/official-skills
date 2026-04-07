---
name: twitter
version: 1.1.0
description: "Twitter/X data lookup — search tweets, user profiles, followers, replies. Use when the user asks about Twitter activity, social signals, or wants to look up accounts."
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

Read-only access to Twitter/X via twitterapi.io.

## Keyword → Tool Lookup

| User asks about | Tool | NOT this |
|----------------|------|----------|
| "tweets about BTC", "搜推文" | `twitter_search_tweets` | — |
| "看某条推文" (by ID) | `twitter_get_tweets` | Not search |
| "@username 是谁" | `twitter_user_info` | — |
| "@username 最近发了什么" | `twitter_user_tweets` | — |
| "谁关注了他" | `twitter_user_followers` | — |
| "他关注了谁" | `twitter_user_followings` | — |
| "这条推文下面评论" | `twitter_tweet_replies` | — |
| "谁转发了" | `twitter_tweet_retweeters` | — |
| "找相关账号" | `twitter_search_users` | — |
| "BTC 社交情绪" / sentiment score | **LunarCrush** `lunar_coin` | Not twitter — see boundary below |

## Twitter vs LunarCrush — When to Use Which

| Need | Use | Why |
|------|-----|-----|
| Raw tweets / what people said | **Twitter** | Actual content |
| Quantified sentiment score | **LunarCrush** | Galaxy Score > manual tweet reading |
| KOL profile / follower count | **Twitter** `twitter_user_info` | — |
| KOL engagement quality | **LunarCrush** `lunar_creator` | Cross-platform metric |
| Non-crypto topics (AI, stocks) | **Twitter** | LunarCrush is crypto-only |
| "市场情绪" without specifying tweets | **LunarCrush** first | Structured > unstructured |

## MISTAKES — Read Before Calling

### ❌ MISTAKE 1: Using Twitter for sentiment scoring
```
User: "市场情绪怎么样"
❌ WRONG: twitter_search_tweets("$BTC") → manually count positive/negative tweets
✅ RIGHT: lunar_coin(symbol="BTC")  ← Galaxy Score gives instant quantified sentiment
```
Only use Twitter for sentiment if user specifically wants tweet-level content or non-crypto topics.

### ❌ MISTAKE 2: Calling user_info during sentiment scan
```
User: "扫描一下 BTC ETH SOL 的推特讨论"
❌ WRONG: twitter_search_tweets("$BTC") → twitter_user_info on each author → ...
✅ RIGHT: twitter_search_tweets("$BTC"), twitter_search_tweets("$ETH"), twitter_search_tweets("$SOL") → summarize tone
```
⛔ Sentiment scan = text analysis only. NEVER call user_info/followers/tweets during scan.

### ❌ MISTAKE 3: Searching with @ prefix in username
```
❌ WRONG: twitter_user_info(username="@elonmusk")
✅ RIGHT: twitter_user_info(username="elonmusk")  ← no @ prefix
```

### ❌ MISTAKE 4: Repeating same search query
```
❌ WRONG: twitter_search_tweets("$BTC") twice in same response
✅ RIGHT: One call per coin/topic, then summarize
```

### ❌ MISTAKE 5: Too many tool calls in one response
```
❌ WRONG: 8 Twitter tool calls researching an account
✅ RIGHT: Max 5 Twitter calls per response. Account research = user_info + user_tweets (2 calls).
```

## Token Budget Rules

| Scenario | Max calls |
|----------|-----------|
| Sentiment scan (multi-coin) | 3 `search_tweets` calls total |
| Account research | 2 calls (user_info + user_tweets) |
| Any single response | 5 Twitter calls max |
| Pagination | Only if user explicitly asks "more" |

## Search Query Operators

| Operator | Example | Description |
|----------|---------|-------------|
| keyword | `bitcoin` | Contains word |
| exact phrase | `"ethereum merge"` | Exact match |
| `from:` | `from:elonmusk` | By specific user |
| `to:` | `to:elonmusk` | Replying to user |
| `#hashtag` | `#crypto` | With hashtag |
| `$cashtag` | `$BTC` | With cashtag |
| `lang:` | `lang:en` | Filter language |
| `has:media` | `has:media` | With images/video |
| `min_faves:` | `min_faves:100` | Minimum likes |
| `min_retweets:` | `min_retweets:50` | Minimum retweets |
| `since:` / `until:` | `since:2024-01-01` | Date range |

Combine: `from:VitalikButerin $ETH min_faves:100 since:2024-01-01`

## Compound Queries

### KOL Tracking
```
1. twitter_user_info(username="cobie")          → profile + follower count
2. twitter_user_tweets(username="cobie")        → recent posts
```

### Project Sentiment (hybrid with LunarCrush)
```
1. lunar_coin(symbol="SOL")                     → Galaxy Score baseline
2. twitter_search_tweets(query="$SOL min_faves:50")  → high-engagement tweets
3. Synthesize: quantified score + qualitative content
```

### Event Monitoring
```
twitter_search_tweets(query="$ETH ETF min_faves:100 since:2025-01-01")
→ Filter high-engagement tweets about a specific event
```

## Output Rules

- Summarize tweet results inline (3-5 sentences). Never write to files.
- Max 3 `twitter_user_info` calls per response — profile lookups are expensive.
- No `bash` or `write_file` for Twitter data.

## Notes

- **Read-only**: No posting, liking, or following.
- **Usernames**: Always without `@` prefix.
- **Tweet IDs**: Use string format (avoid integer overflow).
- **Pagination**: cursor-based. Only paginate if user explicitly requests more.
