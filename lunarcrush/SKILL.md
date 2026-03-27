---
name: lunarcrush
version: 1.0.0
description: Social intelligence and sentiment data - Galaxy Score, AltRank, social volume, influencer activity
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
      env: [LUNARCRUSH_API_KEY]

user-invocable: false
disable-model-invocation: false
---

# LunarCrush

Social intelligence: Galaxy Score, AltRank, social volume, influencer tracking, trending topics.

## Tools

| Tool | Purpose |
|------|---------|
| `lunar_coin(symbol)` | Current social metrics for a coin |
| `lunar_coin_time_series(symbol, interval, bucket)` | Historical social data (1h/1d/1w) |
| `lunar_coin_meta(symbol)` | Metadata and links |
| `lunar_topic(topic)` | Topic metrics (e.g. "defi", "nft") |
| `lunar_topic_posts(topic)` | Recent posts about a topic |
| `lunar_creator(creator_id)` | Influencer data |

## Key Metrics

**Galaxy Score (0-100):** Overall social momentum
- 80-100: Exceptional — watch for tops
- 60-79: Strong interest
- 40-59: Normal
- 0-39: Declining/dead

**AltRank:** Social ranking (lower = better). #1-50 = top tier.

**Social Volume:** Total mentions across Twitter, Reddit, YouTube etc. Rising volume often precedes price moves.

## Signals

| Pattern | Meaning |
|---------|---------|
| Rising Galaxy Score + flat price | Potential breakout setup |
| High Galaxy Score + falling price | Bearish divergence |
| Low Galaxy Score + rising price | Weak rally |
| All three metrics aligned | Strong confirmation signal |

## Workflows

**Find rising coins:** `lunar_coin` → look for rising AltRank + Galaxy Score >60 + flat/rising price.

**Sentiment check:** `lunar_coin` → `lunar_coin_time_series` → compare current vs historical.

**Topic trends:** `lunar_topic` → `lunar_topic_posts` → cross-reference with price action.
