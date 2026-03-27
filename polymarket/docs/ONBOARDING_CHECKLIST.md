# Polymarket Onboarding Checklist v4.0

## Goal
Get to a state where the agent can place and close a Polymarket trade reliably.

## Preconditions
- Skill loaded (`polymarket_search` etc. available)
- Wallet policy allows `eth_signTypedData_v4` and `eth_sendTransaction`
- Agent has POL (gas) and USDC.e (collateral) on Polygon

## 1) Auth
1. `wallet_info()` → confirm EVM address
2. `polymarket_auth(wallet_address="0x...")` → get EIP-712 message
3. `wallet_sign_typed_data(...)` → sign it
4. `polymarket_auth(wallet_address, signature, timestamp)` → credentials saved to .env
5. `polymarket_get_balances()` → confirm no auth error

## 2) Funding
1. `wallet_balance(chain="polygon")` → check USDC.e + POL
2. If short: bridge/swap as needed

## 3) Trade
1. `polymarket_search(query="topic")` → find market
2. `polymarket_orderbook(token_id)` → check liquidity
3. `polymarket_prepare_order(token_id, side, price, size)` → get EIP-712 order
4. `wallet_sign_typed_data(...)` → sign order
5. `polymarket_post_order(token_id, signature, order_meta)` → submit
6. `polymarket_get_trades()` + `polymarket_get_positions()` → verify

## Common Failures
| Error | Fix |
|-------|-----|
| 401/INVALID_API_KEY | Re-run auth flow (steps 1-4) |
| INVALID_ORDER_PAYLOAD | Use `polymarket_prepare_order` (handles normalization) |
| L2_BALANCE_TOO_LOW | Fund wallet with USDC.e |
| 403 geo-block | VPN auto-detection handles this transparently |
