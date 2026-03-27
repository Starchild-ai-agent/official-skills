# Polymarket Smoke Test v4.0

## Objective
Complete one full loop: search → buy → verify → sell → verify.

## Test Size
5-10 USDC

## Procedure

### A — Init (3 calls)
1. `wallet_info()`
2. `polymarket_auth(...)` (full 2-step flow)
3. `polymarket_get_balances()` → confirm balance readable

### B — Discover (1-2 calls)
1. `polymarket_search(query="...")` → pick active market
2. `polymarket_orderbook(token_id)` → confirm liquidity

### C — Open (3 calls)
1. `polymarket_prepare_order(token_id, "BUY", price, size)`
2. `wallet_sign_typed_data(domain, types, "Order", message)`
3. `polymarket_post_order(token_id, signature, order_meta)`

### D — Verify Open (2 calls)
1. `polymarket_get_trades(limit=5)`
2. `polymarket_get_positions()`

### E — Close (3 calls)
1. `polymarket_prepare_order(token_id, "SELL", price, size)`
2. `wallet_sign_typed_data(...)`
3. `polymarket_post_order(...)`

### F — Verify Close (2 calls)
1. `polymarket_get_trades(limit=5)`
2. `polymarket_get_positions()` → position back to baseline

## Pass Criteria
- No auth errors
- Order placed and filled
- Position opened and closed
- All tool outputs include verifiable IDs

## Retry Policy
- Auth failure: re-auth once
- Payload error: rebuild with prepare_order once
- VPN failure: auto-handled, retry once
- Same error twice → stop and report
