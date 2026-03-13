---
name: polymarket
version: 1.0.0
description: Browse and analyze Polymarket prediction markets. Use when the user asks about prediction markets, event probabilities, political odds, or wants market sentiment on real-world events.
tools:
  - polymarket_search
  - polymarket_markets
  - polymarket_event
  - polymarket_tags
  - polymarket_price
  - polymarket_book
  - polymarket_history
  - polymarket_trades
  - polymarket_leaderboard
  - polymarket_holders
metadata:
  starchild:
    emoji: "🔮"
    skillKey: polymarket
user-invocable: true
disable-model-invocation: false
---

# Polymarket Prediction Markets

Browse, search, and analyze prediction markets on Polymarket — the largest decentralized prediction market. Prices represent crowd-implied probabilities of real-world events (politics, crypto, sports, etc.).

**No API key needed** — all Polymarket read endpoints are public.

## Decision Tree

- "What prediction markets exist for X?" → `polymarket_search`
- "What are the trending/biggest markets?" → `polymarket_markets` (sort by volume)
- "What categories of markets are there?" → `polymarket_tags`
- "What's the probability of X?" → `polymarket_price`
- "What are all sub-markets for this event?" → `polymarket_event`
- "How deep is the liquidity?" → `polymarket_book`
- "How has this market moved over time?" → `polymarket_history`
- "What trades are happening?" → `polymarket_trades`
- "Who are the top traders?" → `polymarket_leaderboard`
- "Who holds the most shares?" → `polymarket_holders`

## Available Tools (10)

### Market Discovery (Gamma API)

| Tool | Description | Key Params |
|------|-------------|------------|
| `polymarket_search` | Search markets by keyword | `query` |
| `polymarket_markets` | Browse/filter markets | `status`, `sort`, `tag`, `limit` |
| `polymarket_event` | Get event with child markets | `event_id` |
| `polymarket_tags` | List market categories | (none) |

### Price & Trading Data (CLOB API)

| Tool | Description | Key Params |
|------|-------------|------------|
| `polymarket_price` | Live price/probability | `market_id` (slug or condition ID) |
| `polymarket_book` | Orderbook depth | `token_id` |
| `polymarket_history` | Price timeseries | `token_id`, `interval` |
| `polymarket_trades` | Recent trades | `condition_id`, `limit` |

### Community & Analytics (Data API)

| Tool | Description | Key Params |
|------|-------------|------------|
| `polymarket_leaderboard` | Top traders | `window`, `limit` |
| `polymarket_holders` | Top holders of a token | `token_id`, `limit` |

## Tool Usage Examples

### Search for markets

```
polymarket_search(query="bitcoin")
polymarket_search(query="election")
```

### Browse top markets by volume

```
polymarket_markets(status="active", sort="volume", limit=10)
```

### Filter by category

```
polymarket_tags()
polymarket_markets(tag="crypto", sort="volume")
```

### Get live probability

```
polymarket_price(market_id="will-bitcoin-reach-100k-2025")
```

### Check orderbook depth

```
polymarket_book(token_id="<token_id from price results>")
```

### Get price history

```
polymarket_history(token_id="<token_id>", interval="1d")
```

### Get recent trades

```
polymarket_trades(condition_id="<condition_id from price results>", limit=20)
```

### Check top traders

```
polymarket_leaderboard(window="7d", limit=10)
```

### Check top holders

```
polymarket_holders(token_id="<token_id>", limit=10)
```

## Common Workflows

### Quick Lookup

1. `polymarket_search(query="bitcoin ETF")` — find relevant markets
2. `polymarket_price(market_id="<slug>")` — get current probability

### Deep Analysis

1. `polymarket_search(query="...")` — find the market
2. `polymarket_price(market_id="<slug>")` — current odds + token IDs
3. `polymarket_book(token_id="<token_id>")` — check liquidity depth
4. `polymarket_history(token_id="<token_id>", interval="1d")` — see trend
5. `polymarket_trades(condition_id="<id>")` — recent trading activity

### Market Overview by Category

1. `polymarket_tags()` — see all categories
2. `polymarket_markets(tag="politics", sort="volume")` — top markets in category
3. `polymarket_price(market_id="<slug>")` — drill into specific market

### Smart Money Analysis

1. `polymarket_leaderboard(window="7d")` — who's profiting most?
2. `polymarket_price(market_id="<slug>")` — get token IDs for a market
3. `polymarket_holders(token_id="<token_id>")` — who holds the most?

## Interpreting Prices

Polymarket prices = probabilities. Each share pays $1 if the outcome occurs.

| Price Range | Interpretation |
|-------------|---------------|
| $0.90-$1.00 | Near-certain — strong consensus |
| $0.70-$0.89 | Strong consensus — likely to happen |
| $0.50-$0.69 | Lean yes, significant uncertainty |
| $0.30-$0.49 | Lean no, but uncertain |
| $0.01-$0.29 | Unlikely — market thinks probably not |

## Spread & Liquidity Analysis

| Spread | Meaning |
|--------|---------|
| < $0.02 | Tight — reliable price signal, high confidence |
| $0.02-$0.05 | Normal — decent liquidity |
| $0.05-$0.10 | Wide — lower confidence, less liquid |
| > $0.10 | Very wide — unreliable, thin market |

Check `polymarket_book` to see actual depth. A tight spread with shallow depth can still be unreliable.

## Multi-Outcome & Negative Risk Markets

- **Binary markets**: Yes/No — prices sum to ~$1.00
- **Multi-outcome**: 3+ outcomes (e.g. "Who wins?") — all outcomes sum to ~$1.00
- **Negative risk (`neg_risk=true`)**: Market uses a special mechanism where shares are minted as a group. Prices still represent probabilities. This is common in multi-outcome events.

Always iterate all outcomes — never hardcode Yes/No.

## Common Patterns

- **Sentiment check**: Prediction prices as leading indicators for crypto/political events
- **Event risk assessment**: Combine prediction market odds with crypto price data for risk analysis
- **Contrarian signals**: Extreme probabilities ($0.95+) with declining volume may indicate complacency
- **Smart money tracking**: Leaderboard + holders reveal informed positioning on specific markets

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| "Market not found" | Invalid slug or condition ID | Use `polymarket_search` to find correct ID |
| "Gamma API 404" | Event or market doesn't exist | Verify event_id from search results |
| "CLOB API 400" | Invalid token_id | Use token_id from `polymarket_price` output |
| Timeout | API slow or unreachable | Retry once, then inform user |
| Empty results | No matching markets | Try broader search terms |
| Prices missing | Resolved/pre-CLOB market | Tool falls back to Gamma static prices automatically |
