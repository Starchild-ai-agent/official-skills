# Polymarket Smoke Test v5.0.3

## Objective
Complete one full loop: search → buy → verify → sell → verify.

## Test Size
5-10 USDC

## Procedure

### A — Init (script-first)
1. `python3 scripts/auth.py --check`
2. If needed: `python3 scripts/auth.py --prepare 0xWALLET` → sign → `python3 scripts/auth.py --save ...`
3. `python3 scripts/status.py --json`

### B — Discover
1. `python3 scripts/search.py "keyword" --limit 2` (avoid long literal full-sentence query)
2. Pick token_id from outcomes

### C — Open
1. `python3 scripts/prepare_order.py TOKEN_ID BUY PRICE SIZE`
2. `wallet_sign_typed_data(domain, types, "Order", message)`
3. `python3 scripts/post_order.py 0xSIG`

### D — Verify Open
1. `python3 scripts/status.py --json`
2. Check orders/positions/trades fields

### E — Close
1. `python3 scripts/prepare_order.py TOKEN_ID SELL PRICE SIZE`
2. `wallet_sign_typed_data(...)`
3. `python3 scripts/post_order.py 0xSIG`

### F — Verify Close
1. `python3 scripts/status.py --json` → position back to baseline

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
