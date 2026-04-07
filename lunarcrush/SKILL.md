---
name: lunarcrush
version: 1.1.0
description: "Social intelligence and sentiment data — Galaxy Score, AltRank, social volume, influencer activity, trending topics"
tools:
  - lunar_coin
  - lunar_coin_time_series
  - lunar_coin_meta
  - lunar_topic
  - lunar_topic_posts
  - lunar_creator

metadata:
  starchild:
    emoji: "🌙"
    skillKey: lunarcrush
    requires:
      env:
        - LUNARCRUSH_API_KEY

user-invocable: false
disable-model-invocation: false
---

# LunarCrush

Social intelligence and sentiment data: Galaxy Score, AltRank, social volume, influencer activity, trending topics. This is the **crowd-mood layer**.

## Keyword → Tool Lookup

| User asks about | Tool | NOT this |
|----------------|------|----------|
| "BTC 社交情绪", "Galaxy Score", "social sentiment" | `lunar_coin(symbol="BTC")` | Not twitter_search_tweets |
| "社交情绪趋势", "sentiment over time" | `lunar_coin_time_series` | Not lunar_coin (snapshot only) |
| "token links", "official site" | `lunar_coin_meta` | — |
| "DeFi 话题热度", "topic trending" | `lunar_topic(topic="defi")` | — |
| "人们在说什么", "recent posts about X" | `lunar_topic_posts` | — |
| "KOL 数据", "influencer stats" | `lunar_creator` | Not twitter_user_info |

## LunarCrush vs Twitter — When to Use Which

| Need | Use | Why |
|------|-----|-----|
| Overall crowd mood / sentiment score | **LunarCrush** | Aggregated score across all platforms |
| Specific tweets / what someone said | **Twitter** | Raw tweet content |
| Galaxy Score / AltRank | **LunarCrush** | Proprietary metrics, Twitter doesn't have |
| KOL follower count / bio | **Twitter** `twitter_user_info` | Profile data |
| KOL influence metrics / engagement quality | **LunarCrush** `lunar_creator` | Cross-platform engagement |
| "市场情绪怎么样" (general mood) | **LunarCrush** first | Structured score > raw tweet scan |
| "推特上在讨论什么" (specific discussion) | **Twitter** first | Raw content > aggregated score |

## MISTAKES — Read Before Calling

### ❌ MISTAKE 1: Using Twitter for sentiment scores
```
User: "BTC 社交情绪怎么样"
❌ WRONG: twitter_search_tweets(query="$BTC") then manually summarize tone
✅ RIGHT: lunar_coin(symbol="BTC")  ← returns Galaxy Score, AltRank, social volume as numbers
```
LunarCrush gives quantified sentiment. Twitter gives raw text you'd have to interpret.

### ❌ MISTAKE 2: Using lunar_coin for historical trends
```
User: "最近一周社交情绪变化"
❌ WRONG: lunar_coin(symbol="BTC")  ← snapshot only, no history
✅ RIGHT: lunar_coin_time_series(symbol="BTC", interval="1d", bucket="day")  ← daily history
```

### ❌ MISTAKE 3: Calling lunar_creator without a creator_id
```
❌ WRONG: lunar_creator(creator_id="elonmusk")  ← not a username, needs numeric ID
✅ RIGHT: Get creator_id from lunar_topic_posts results, then call lunar_creator
```

### ❌ MISTAKE 4: Confusing AltRank direction
```
❌ WRONG: "AltRank 500, social presence is strong"
✅ RIGHT: "AltRank 500, social presence is weak"  ← lower = better, #1 = highest attention
```

### ❌ MISTAKE 5: Using LunarCrush for non-crypto topics
```
User: "AI 行业社交热度"
❌ WRONG: lunar_topic(topic="artificial intelligence")  ← LunarCrush is crypto-only
✅ RIGHT: twitter_search_tweets(query="artificial intelligence")
```
**Boundary**: LunarCrush = crypto social metrics only. General topics → Twitter.

## Key Metrics — How to Read

### Galaxy Score (0-100)

| Score | Read | Trading Signal |
|-------|------|---------------|
| 80–100 | Exceptional social momentum | Watch for tops / FOMO peak |
| 60–79 | Strong sustained interest | Momentum confirmed |
| 40–59 | Normal activity | Neutral |
| 20–39 | Declining interest | Caution |
| 0–19 | Dead or bottoming | Contrarian opportunity? |

### AltRank (lower = better)

| Rank | Read |
|------|------|
| 1–10 | Top social attention — likely already priced in |
| 11–50 | Strong presence — monitor for entry |
| 51–100 | Moderate — potential early signal |
| 100+ | Low attention — under the radar |

### Divergence Signals

| Pattern | Interpretation |
|---------|---------------|
| High Galaxy Score + falling price | Bearish divergence — crowd bullish but price disagrees |
| Low Galaxy Score + rising price | Weak rally — no crowd conviction |
| Rising social volume + flat price | Potential breakout setup — attention building |
| Falling social volume + rising price | Unsustainable rally — watch for reversal |

## Time Intervals

- `1h` - Hourly
- `1d` - Daily
- `1w` - Weekly

## Compound Queries

### Crypto Social Alpha Scan
```
1. lunar_coin(symbol="BTC")          → Galaxy Score + AltRank baseline
2. lunar_coin(symbol="SOL")          → Compare social momentum
3. lunar_coin_time_series(symbol="SOL", interval="1d", bucket="day")  → Trend direction
```

### Topic Sentiment Deep Dive
```
1. lunar_topic(topic="defi")         → Overall DeFi social metrics
2. lunar_topic_posts(topic="defi")   → What people are actually saying
3. twitter_search_tweets(query="$DeFi min_faves:50")  → Cross-reference with raw tweets
```
