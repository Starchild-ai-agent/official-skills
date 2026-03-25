# Skill Name

## Quick Reference
<!-- MANDATORY: Small models read this FIRST. Must be self-contained. -->
| Property | Value |
|----------|-------|
| **Tools** | `tool_a`, `tool_b`, `tool_c` |
| **Auth** | API key in `ENV_VAR_NAME` |
| **Rate Limits** | X req/min (free tier), Y req/min (pro) |
| **Common Chains** | ethereum, arbitrum, base (if applicable) |

## Tool Signatures
<!-- MANDATORY: Every tool listed with exact parameters. -->
<!-- Small models use these to construct calls without guessing. -->

### tool_a(param1, param2, optional_param="default")
**Purpose:** One-line description of what this does.
**Returns:** `{field1: type, field2: type}`
**Example:**
```
tool_a("BTC", "1h")
→ {price: 67000.0, volume_24h: 1200000000, change_pct: 2.3}
```
**Errors:**
- `ASSET_NOT_FOUND` — symbol doesn't exist → check spelling
- `RATE_LIMITED` — too many requests → wait 10s, retry

### tool_b(param1, param2)
**Purpose:** ...
**Returns:** ...
**Example:** ...

## Workflows
<!-- MANDATORY: Step-by-step for common tasks. -->
<!-- Small models follow these as recipes — must be unambiguous. -->

### Check Balance and Place Order
```
1. hl_account() → get available_balance
2. hl_market("BTC") → get current price, min_size, tick_size
3. Calculate size: balance * 0.1 / price
4. hl_order("BTC", "buy", size, price * 0.99, "limit")
5. hl_open_orders() → verify order placed
```

### Handle Common Error
```
If hl_order fails with INSUFFICIENT_MARGIN:
  1. hl_account() → check actual balance
  2. Compare required margin vs available
  3. Either reduce size or tell user to deposit
```

## Parameter Reference
<!-- OPTIONAL but recommended: Exhaustive param docs for complex tools. -->

### tool_a Parameters
| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| param1 | string | Yes | — | Asset symbol (e.g., "BTC", "ETH") |
| param2 | string | No | "1h" | Timeframe: "1m","5m","15m","1h","4h","1d" |

## Known Limitations
<!-- MANDATORY: What this skill CANNOT do. Prevents hallucinated capabilities. -->
- Cannot do X (use skill_y instead)
- Rate limited to N requests per minute
- Data delayed by ~M minutes
- Does not support chain Z

## Error Recovery
<!-- MANDATORY for trading/transaction skills. -->
| Error | Cause | Recovery |
|-------|-------|----------|
| INSUFFICIENT_MARGIN | Not enough USDC | Deposit or reduce size |
| ASSET_NOT_FOUND | Wrong symbol | Use exact ticker from hl_market |
| RATE_LIMITED | Too many requests | Wait 10s, retry |
| SIGNING_ERROR | Nonce conflict | Retry once automatically |
