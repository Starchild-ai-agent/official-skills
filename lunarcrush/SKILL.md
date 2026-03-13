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
      env:
        - LUNARCRUSH_API_KEY

user-invocable: false
disable-model-invocation: false
---

# LunarCrush

LunarCrush provides social intelligence and sentiment data including Galaxy Score, AltRank, social volume, influencer activity, and trending topics. This is the crowd-mood layer.

## When to Use LunarCrush

Use LunarCrush for:
- **Social sentiment** - What is the crowd saying?
- **Galaxy Score** - Overall social momentum (0-100)
- **AltRank** - Social ranking (lower is better)
- **Social volume** - Number of social mentions
- **Influencer activity** - What are key voices saying?
- **Trending topics** - What's gaining attention?

## Common Workflows

### Coin Social Data
```
lunar_coin(symbol="BTC")  # Current social metrics
lunar_coin(symbol="ETH")  # Ethereum social data
lunar_coin_time_series(symbol="SOL", interval="1d", bucket="day")  # Historical
lunar_coin_meta(symbol="BTC")  # Metadata and links
```

### Topic Analysis
```
lunar_topic(topic="defi")  # DeFi topic metrics
lunar_topic_posts(topic="nft")  # Recent posts about NFTs
```

### Creator/Influencer
```
lunar_creator(creator_id="123456")  # Specific influencer data
```

## Key Metrics

### Galaxy Score (0-100)

| Score | Read |
|-------|------|
| 80–100 | Exceptional social momentum — watch for tops |
| 60–79 | Strong sustained interest |
| 40–59 | Normal activity |
| 20–39 | Declining interest |
| 0–19 | Dead or bottoming |

**Divergence signal**: High Galaxy Score + negative price = potential reversal.

### AltRank

Lower is better. #1–50 is top tier social presence. Useful for finding altcoins gaining attention before price moves.

- **Rank 1-10**: Highest social attention
- **Rank 11-50**: Strong social presence
- **Rank 51-100**: Moderate attention
- **Rank 100+**: Low social attention

### Social Volume

Number of social mentions across platforms (Twitter, Reddit, etc.). Rising social volume often precedes price moves.

### Social Dominance

Percentage of total crypto social volume. High dominance means the coin is dominating crypto conversations.

## Analysis Patterns

**Social alpha**: Rising Galaxy Score + flat price = potential breakout setup. Social attention building before price moves.

**Divergence signals**:
- High Galaxy Score + falling price = bearish divergence
- Low Galaxy Score + rising price = weak rally

**Sentiment confirmation**: Combine Galaxy Score + social volume + AltRank. All three moving in same direction = strong signal.

**Influencer tracking**: Monitor what key voices are saying via creator tools. Influencer attention can drive retail interest.

## Time Intervals

- `1h` - Hourly
- `1d` - Daily
- `1w` - Weekly

## Important Notes

- **API Key**: Requires LUNARCRUSH_API_KEY environment variable
- **Symbols**: Use standard symbols (BTC, ETH, SOL, etc.)
- **Social platforms**: Data aggregated from Twitter, Reddit, Medium, YouTube, and more
- **Real-time**: Social metrics update in near real-time
- **Leading indicator**: Social data often leads price - attention builds before price moves

## Workflow Examples

### Find Rising Coins
1. Use `lunar_coin` to check AltRank and Galaxy Score
2. Look for coins with rising AltRank (lower number = better) and Galaxy Score > 60
3. Check if price is flat or rising - social attention building is a leading signal

### Sentiment Check
1. Get current Galaxy Score and social volume
2. Compare to historical data via `lunar_coin_time_series`
3. High score + rising volume = strong momentum
4. Low score + falling volume = weak interest

### Topic Trends
1. Use `lunar_topic` to find trending topics (DeFi, NFT, Gaming, etc.)
2. Use `lunar_topic_posts` to see what people are saying
3. Cross-reference with price action for early trend signals
