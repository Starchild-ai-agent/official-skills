---
name: pear-protocol
version: 2.3.0
description: |
  Pear Protocol pair/basket trading on Hyperliquid — headless agent-wallet
  auth (SIWE), V3 gateway REST + Orchard MCP server: markets, pair ratios,
  positions, orders, and trade execution.

  Use when the user wants to pair trade (long one asset / short another),
  check pair ratios, correlation or funding, or manage Pear positions
  (e.g. long BTC short ETH, check my Pear positions, find trending pairs).
author: starchild
tags: [pear, pair-trading, hyperliquid, mcp, defi, perps, long-short]
metadata:
  starchild:
    emoji: "🍐"
    skillKey: pear-protocol
    auth: api-key
---

# 🍐 Pear Protocol — Headless (agent wallet)

Pair/basket trading on top of Hyperliquid: open a long and a short leg as one
synthetic position. **This skill uses HEADLESS auth only** — the agent's own
Privy wallet signs a SIWE login against the V3 gateway; no browser, no OAuth,
no user interaction. Works out of the box for any Starchild agent.

## Endpoints

- **V3 gateway (REST):** `https://pro-gateway.pearprotocol.io`
- **Orchard MCP:** `https://mcp.pearprotocol.io/mcp` (streamable HTTP,
  stateless — accepts `x-api-key` directly; docs: https://docs.pear.garden)

## Auth — `scripts/gateway.py` (use this, don't hand-roll curl)

```bash
python3 skills/pear-protocol/scripts/gateway.py login        # SIWE login w/ agent wallet, caches tokens
python3 skills/pear-protocol/scripts/gateway.py status       # identity + token validity
python3 skills/pear-protocol/scripts/gateway.py ensure-key   # mint PEAR_API_KEY into .env (once)
python3 skills/pear-protocol/scripts/gateway.py markets --limit 15
python3 skills/pear-protocol/scripts/gateway.py get /trade-accounts
python3 skills/pear-protocol/scripts/gateway.py post <path> '<json>'   # writes; auto Bearer
```

Flow: `POST /auth/nonce {address}` → `wallet.wallet_sign(message)` (EIP-191;
gateway accepts the smart-wallet address even though personal_sign recovers to
the underlying EOA — no EIP-1271 issue) → `POST /auth/login
{method:"wallet",address,signature}` → `accessToken` (JWT ~15 min,
auto-refresh/re-login). Tokens cached in `workspace/.pear/gateway_tokens.json`
(0600). Single-flight nonce→login: concurrent nonce requests rotate the nonce
and 401 the earlier signature.

## Which credential for which call

| Call type | Auth | Notes |
|---|---|---|
| Gateway reads (markets, funding) | `x-api-key: $PEAR_API_KEY` | persistent, read scope |
| Gateway writes (orders, trade-accounts) | `Authorization: Bearer …` | api_key → 403; gateway.py auto-refreshes |
| Account-scoped calls | + `x-trade-account-id: <id>` | mandatory once >1 account |
| **MCP server** | `x-api-key` directly | gateway wallet Bearer is REJECTED on MCP (different token type) |

- `GET /markets` REQUIRES `?connector=hyperliquid` (291 markets: price,
  funding, OI, 24h vol/change).

## API-key scopes gate the MCP tool surface

`POST /api-keys` (Bearer) body `{"label": "...", "scope": "read"|"read_write"}`
(field is `label` NOT `name`; raw key returned ONCE). Read key → 16
analytics/account tools. `read_write` → 32 tools, adding trading:
plan/execute pairs for open_basket, close_basket, set_position_tpsl,
rebalance_position, adjust_position, enable_auto_rebalance, plus
sync_account, cancel_pending_order, manage_saved_basket.

Convention: store the read key as `PEAR_API_KEY` and (if trading) a
read_write key as `PEAR_API_KEY_RW` in workspace/.env. For MCP trading,
export `PEAR_API_KEY=$PEAR_API_KEY_RW` before calling `pear_mcp.py`.

## MCP client — `scripts/pear_mcp.py`

```bash
python3 skills/pear-protocol/scripts/pear_mcp.py status
python3 skills/pear-protocol/scripts/pear_mcp.py list
python3 skills/pear-protocol/scripts/pear_mcp.py call <tool> '<json-args>'
```

Auto-uses `PEAR_API_KEY` from env/.env (x-api-key header). Read tools:
get_position(+history), discover_assets, list_baskets,
search_prediction_markets, get_leaderboard, list_trade_accounts,
get_account_summary, get_fee_quote, get_tca, list_pending_orders, etc.

## Trade account (Hyperliquid) — REQUIRED before any execute_*

One-time setup per agent (the connected account id is returned at step 3;
keep it in `.pear/trade_account.json`):
1. Generate keypair (`eth_account.Account.create()`) → save to
   `.pear/hl_signer.json` (0600).
2. Approve as HL agent wallet — user-signed `approveAgent` action, EIP-712
   domain `HyperliquidSignTransaction` (chainId **421614**), types
   `HyperliquidTransaction:ApproveAgent` [hyperliquidChain, agentAddress,
   agentName, nonce] — signed by the Privy master via wallet service
   `/agent/sign-typed-data` (same pattern as hyperliquid skill's
   `sign_user_action`). Submit to `POST api.hyperliquid.xyz/exchange` with
   `signatureChainId: "0x66eee"` (used even on Mainnet — the `hyperliquidChain`
   field selects the network; use that). 42161 / `0xa4b1` is also accepted and
   was verified working — the real requirement is that `signatureChainId`
   exactly matches the domain chainId used when signing. Verify with info
   `{"type":"extraAgents","user":<master>}`.
3. `POST /trade-accounts` (Bearer) — EXACT payload (validation errors only
   show details when `connector` is present):
   `{"alias": "...", "connector": "hyperliquid", "exchangeIdentifier":
   <master addr>, "credentials": {"signer_key": <signer priv, snake_case!>},
   "metadata": {"agentWalletAddress": <signer addr>, "isSubaccount": false,
   "mainAccountAddress": <master addr>}}` → 201 with `account.id`.

Funds stay under the master HL account; signer trades, can't withdraw.

4. **Approve Pear's builder fee (REQUIRED — executions fail without it).**
   Pear does NOT do this for you. Get the builder address via MCP
   `get_fee_recipient {"connector":"hyperliquid"}` (currently
   `0xa47d4d99191db54a4829cdf3de2417e527c3b042`, fee 6 bps). Sign a
   user-signed `approveBuilderFee` action with the MASTER wallet (not the
   signer): EIP-712 type `HyperliquidTransaction:ApproveBuilderFee`
   [hyperliquidChain, maxFeeRate, builder, nonce], same domain/chain-id
   rules as approveAgent. Use `maxFeeRate: "0.1%"` (HL perps cap). Submit to
   `POST api.hyperliquid.xyz/exchange` with matching `signatureChainId`.
   Verify: info `{"type":"maxBuilderFee","user":<master>,"builder":<builder>}`
   must return > 0 (100 = 0.1%).

## Trading via MCP — plan → execute pattern

Arg shape: `{"tradeAccountId": <id>, "params": {...}}` — `params` is a
discriminated union on `executionStyle` (market|twap|trigger|ladder).
Legs: `{"source":"symbol","symbol":"BTC","side":"BUY"|"SELL"}` + top-level
`totalUsd`, `leverage`, `marginMode`. `plan_*` = dry-run with priced
legs/margin (ALWAYS show the user before executing); `execute_*` = live.
HL $10 min notional per leg (auto-bumped with warning).

**Preflight (run before every execute_*):**
```
python3 scripts/preflight.py check --notional <usd> [--leverage N]
```
Verifies: API key, trade account, on-chain builder-fee approval, balance
breakdown (perp equity vs spot — catches funds stuck in spot / account-mode
issues that zero out margin on xyz:* builder-DEX markets), and available
margin vs the planned notional. Exit 0 = safe to execute; nonzero = blocked
with the specific reason. Do NOT execute on a failing preflight.

**Post-trade receipt (run after every execute_*):**
```
python3 scripts/preflight.py verify <execution_id> --trade-account <id>
```
Checks execution status + venue errors + filledQuantity + that the position
actually exists. Only "FILLED ✅" means a trade happened.

⚠️ **`status: executed` ≠ filled.** The execute_* response only means Pear
submitted the order. ALWAYS verify the outcome: check the execution record
for venue errors and `filledQuantity > 0`, then confirm the position exists
(get_position / HL clearinghouseState). A common definitive rejection is
`"Builder fee has not been approved"` → run step 4 of the trade-account
recipe, then retry.

`get_account_summary` args: `{"tradeAccountId": <id>, "params":
{"scope": "balance"}}`.

## Notes

- Read-only pair data (funding, ratios) can also come from the `hyperliquid`
  skill; use Pear when acting on a Pear account or using Pear analytics.
- Optional: a Pear-issued `clientId` attributes routed volume (contact Pear).
- Docs: https://docs.pear.garden/api-integration/access-management/authentication-process

## Troubleshooting

- **Builder-fee approval has cache propagation delay.** After on-chain
  `maxBuilderFee` verifies > 0, Pear's venue check may still reject briefly
  ("Builder fee has not been approved") — wait ~1–2 min and retry before
  debugging further.
- **xyz:* (HIP-3 builder-DEX) markets show $0 margin until unified account
  abstraction is enabled** on the Hyperliquid account. If a plan prices fine
  but available margin reads zero on an xyz pair, enable unified/abstracted
  account mode first, then re-plan.

- Account-scoped gateway/MCP calls (positions, account summary, execute_*) fail
  until a trade account is connected — expected; follow the trade-account
  recipe first. Market data and analytics tools work without one.
- Importing the wallet module may print harmless warnings about unavailable
  optional analytics integrations (e.g. CoinGecko/Coinglass) — ignore them;
  they don't affect Pear.
- Scripts auto-route HTTP through Starchild's authenticated proxy when
  available and fall back to direct connections otherwise; no configuration
  needed.
