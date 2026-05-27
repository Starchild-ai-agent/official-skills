# Polymarket Onboarding Checklist v5.0.3

## Goal
Get to a state where the agent can place and close a Polymarket trade reliably.

## Preconditions
- `skills/polymarket/scripts/*.py` available (script-first)
- Wallet signing available (`wallet_sign_typed_data`)
- Agent has POL (gas) and USDC.e (collateral) on Polygon

## 1) Auth
1. `python3 scripts/auth.py --check`
2. If stale/missing: `python3 scripts/auth.py --prepare 0xWALLET`
3. `wallet_sign_typed_data(...)` on `/tmp/poly_auth.json`
4. `python3 scripts/auth.py --save 0xSIG 0xWALLET TIMESTAMP`
5. `python3 scripts/status.py --json` → confirm auth works

## 2) Funding / Allowance
1. Check on-chain balances (POL + USDC.e)
2. If `status.py` allowance remains 0, verify ERC20 `allowance(owner,spender)` on-chain
3. Ensure non-zero allowance for CLOB spenders before order test

## 3) Trade
1. `python3 scripts/search.py "keyword" --limit 2` → pick active market token_id
2. `python3 scripts/prepare_order.py TOKEN_ID BUY PRICE SIZE`
3. `wallet_sign_typed_data(...)` on `/tmp/poly_order.json`
4. `python3 scripts/post_order.py 0xSIG` → submit
5. `python3 scripts/status.py --json` + trades/positions verify

## Common Failures
| Error | Fix |
|-------|-----|
| 401/INVALID_API_KEY | Re-run auth flow (steps 1-4) |
| INVALID_ORDER_PAYLOAD | Use `polymarket_prepare_order` (handles normalization) |
| L2_BALANCE_TOO_LOW | Fund wallet with USDC.e |
| 403 geo-block | VPN auto-detection handles this transparently |
