---
name: starchild-swap-and-bridge
version: 1.2.0
description: |
  Unified swap + bridge router combining WOOFi (best-price meta-aggregator on 14 EVM
  chains) and the LayerZero Value Transfer API (broad multi-chain bridging incl.
  Solana, Aptos, TON — discover supported chains/tokens dynamically). One workflow:
  classify the request, validate the wallet can actually execute, quote, compare
  complete routes, approve-then-requote-then-execute, and verify destination receipt.
author: starchild
tags: [swap, bridge, cross-chain, dex-aggregator, best-price, layerzero, stargate, woofi, cctp, oft, defi, multichain]

metadata:
  starchild:
    emoji: "🧭"
    skillKey: omniroute-swap-bridge
    registry: starchild-official
    requires:
      bins: [curl]

triggers:
  - "swap"
  - "bridge"
  - "trade"
  - "convert tokens"
  - "cross chain swap"
  - "bridge tokens"
  - "best price"
  - "best rate"
  - "swap and bridge"
  - "move tokens to another chain"
  - "transfer across chains"

user-invocable: true
---

# OmniRoute — Unified Swap + Bridge Router

One skill for any "get token A on chain X into token B on chain Y" request. It combines
two engines and selects the best *complete executable route*, not just the best quote:

| Engine | Base URL | Strengths |
|---|---|---|
| **WOOFi V2** | `https://sapi.woofi.com` | Best-price same-chain swaps (WooPP + 1inch + ODOS), simple cross-chain on 14 EVM chains. Chain names + token symbols, human-readable amounts, no auth. Rate limit 5 req/s. |
| **LayerZero Value Transfer** | `https://transfer.layerzero-api.com/v1` | Broad multi-chain bridging (EVM, Solana, Aptos, TON…) via OFT / Stargate / CCTP / Aori. Status polling with explorer URLs. Proxied auth via `core.http_client`. |

Do not hard-code chain/token coverage claims — discover live via LayerZero
`GET /v1/chains` and `GET /v1/tokens`, and WOOFi's chain table below.

## Step 0 — Classify the request

1. **Same-chain swap on an EVM chain** → **WOOFi** (`/v2/swap`). LayerZero does not do
   same-chain swaps.
2. **Cross-chain, both chains in WOOFi's 14 EVM list, both tokens ERC-20/native** →
   quote **both** engines and select per the route-ranking rules in Step 2.
3. **Any non-EVM chain (Solana, Aptos, TON, Tron…), or a chain outside WOOFi's list,
   or native-USDC-via-CCTP preference** → **LayerZero** only.
4. **Swap needed on the destination that LayerZero can't fulfill** → chain the engines:
   LayerZero bridge first, then WOOFi swap on the destination chain (two confirmations,
   gas on both chains — tell the user, and include destination gas in the comparison).

WOOFi's documented v2 chain set (validate support at execution time — treat an API
error as "unsupported", not a bug): arbitrum, base, bsc, polygon, optimism, avalanche,
ethereum, linea, mantle, sonic, berachain, hyperevm, monad, zksync.

**Native-token handling differs per engine:**
- **WOOFi (EVM only):** use the symbol (`"ETH"`, `"BNB"`, `"AVAX"`, `"POL"`, `"MNT"`,
  `"S"`, `"BERA"`, `"MON"`) or the EVM placeholder
  `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`.
- **LayerZero:** do NOT assume a universal placeholder. Resolve the native/token
  address per chain via `GET /v1/chains` (`nativeCurrency.address`) and
  `GET /v1/tokens` — non-EVM chains (Solana, Aptos, TON…) use different address
  formats entirely.

## Step 1 — Pre-flight validation (two stages)

A better quote can still be an unexecutable route. Exact gas requirements are unknown
before transaction construction, so validation happens in two stages:

**Stage A — before quoting:**
- **Source token balance** covers the sell amount (fetch on-chain, using the token's
  real `decimals` — never assume 18).
- **Token identity**: confirm chain ID, token address, decimals, and symbol together.
  Never trust symbol resolution alone, especially for unknown or unverified tokens —
  cross-check the resolved address against discovery data before quoting.
- **Destination address** is valid for the destination chain's format and matches the
  user's stated intent (source and destination wallets may legitimately differ —
  confirm explicitly when they do).
- **Wallet compatibility** in broad terms (e.g. can it sign EIP-712? can it sign on
  Solana?).

**Stage B — after transaction construction, before signing:**
- **Native gas balance** covers the actual built steps: approval gas + swap/bridge gas
  + any `value`/`native_fee` attached. For chained routes, also destination-chain gas.
- **Step types** in the built route are all executable by the wallet.
- **Approval target and spender** match the API-generated calldata.
- **Balances still sufficient** for the exact amounts in the built transactions.

If any check fails, report it instead of proceeding.

## Step 2 — Quote and compare complete routes

### WOOFi (no auth, human-readable amounts)

```bash
# Same-chain
curl -X POST "https://sapi.woofi.com/v2/quote" -H "Content-Type: application/json" \
  -d '{"chain": "arbitrum", "sell_token": "USDC", "buy_token": "WETH", "sell_amount": "1000"}'

# Cross-chain
curl -X POST "https://sapi.woofi.com/v2/cross_chain/quote" -H "Content-Type: application/json" \
  -d '{"src_chain": "arbitrum", "dst_chain": "base", "src_token": "USDC", "dst_token": "USDC", "src_amount": "100"}'
```

### LayerZero (proxied auth, base-unit string amounts)

The key is injected by sc-proxy — do **not** set `LAYERZERO_API_KEY`; route calls
through `core.http_client` (`proxied_post`/`proxied_get`). Plain `curl` works only for
the no-auth discovery endpoints (`/chains`, `/tokens`, `/metadata`).

```python
from core.http_client import proxied_post
r = proxied_post(
    "https://transfer.layerzero-api.com/v1/quotes",
    json={
        "srcChainKey": "base", "dstChainKey": "solana",
        "srcTokenAddress": "<src token address, resolved via discovery>",
        "dstTokenAddress": "<dst token address, resolved via discovery>",
        "srcWalletAddress": "<wallet>", "dstWalletAddress": "<dst wallet>",
        "amount": "1000000000000000",  # STRING, token base units per its decimals
        "options": {"amountType": "EXACT_SRC_AMOUNT",
                    "feeTolerance": {"type": "PERCENT", "amount": 2}},
    },
    headers={"x-api-key": "proxy", "SC-CALLER-ID": f"chat:{thread_id}"},
    timeout=40,
)
```

**Handle the LayerZero response defensively:**
- The body may contain `error`, an empty `quotes` array, and/or `rejectedQuotes`.
  Treat empty/error as "no route" and say why (surface rejection reasons if present).
- **Compare every entry in `quotes`** on `dstAmount`, `dstAmountMin`, `feeUsd`, and
  step count — do not blindly take `quotes[0]`.
- Inspect each quote's `userSteps` for step *types*: transaction steps vs signature
  (EIP-712) steps. Only select routes whose step types the wallet can execute.
- Quotes expire — track age and re-quote if execution is delayed.

### Comparison rules

- **Never subtract `feeUsd` from a destination token quantity.** Compare destination
  output in **human token units** (convert LayerZero base units using the destination
  token's `decimals`; WOOFi amounts are already human-readable).
- **Minimum received is an amount, not a price.** LayerZero returns it directly as
  `dstAmountMin`. WOOFi's `guaranteed_price` is a *price*: compute WOOFi's minimum
  output as `guaranteed_price × sell_amount` (or use a returned minimum-output field
  if the response provides one). Never present the two fields as equivalent.
- Display these **separately**, never blended into one number:
  - protocol destination output (expected)
  - minimum received, in destination-token units (computed as above)
  - native gas cost on source (and destination, for chained routes)
  - bridge/protocol fee (`feeUsd`, `native_fee`)
  - estimated USD value of the output (informational)
- Account for approval gas, and for chained routes the destination swap's gas and
  slippage, when ranking.

### Route ranking (no fixed engine preference)

Rank candidate routes by, in order of weight:
1. Net destination value, defined as:
   `output USD value − source gas USD − destination gas USD − protocol fees USD`.
   Token and native-gas USD prices must come from a stated live source (e.g. token
   `price.usd` from LayerZero `/v1/tokens`, or another live price feed named in the
   comparison). If reliable live prices are unavailable, do not claim a definitive
   net-value winner — present the raw per-route figures and let the user choose.
2. Minimum received (worst-case protection)
3. Total gas across all required transactions
4. Estimated duration
5. Number of signatures/transactions and route reliability — **when outputs are
   close, prefer the route with fewer transactions and fewer failure points**
6. Slippage exposure

Present the comparison and get explicit user confirmation before signing anything.

## Step 3 — Execute

### ⚠️ Approval sequencing — never blindly iterate original tx_steps

After an approval confirms, rebuild the transaction: quotes, calldata, allowance
state, and routing conditions may have changed since the original response was built,
and executing the stale step risks a revert (observed in live testing). For **both**
WOOFi same-chain and cross-chain routes:

1. If `needs_approve` is true, send **only the approval step** first.
   - Before signing it, verify the approval's `to` is the sell token's contract and
     the approved spender matches the spender in the API-generated calldata. Use an
     **exact-amount approval** where possible — never unlimited allowances.
2. Wait for the approval transaction to confirm on-chain.
3. **Re-call `/v2/swap` (or `/v2/cross_chain/swap`) to rebuild the transaction.**
4. Verify the fresh response has `needs_approve: false`.
5. Execute the fresh swap step. If it still reports approval needed, stop and report —
   do not loop retries.

The same principle applies to LayerZero `userSteps`: after an approval step confirms,
prefer regenerating steps (`POST /v1/build-user-steps` with `{"quoteId": ...}`) before
sending the bridge transaction, and always regenerate for Solana (blockhashes expire
in ~60s).

### Before every signature

Decode and display to the user: destination contract, chain, token, amount, spender
(for approvals), and native `value` attached. Enforce guardrails: maximum total fee,
maximum slippage, and minimum received — abort if the fresh transaction violates what
was confirmed.

**Confirmation validity:** a rebuilt/fresh quote may execute without asking the user
again only if amount, destination address, spender, slippage, minimum received, and
total fee all remain within the limits the user already approved. Any material change
to any of these requires renewed confirmation.

### LayerZero step types

- **Transaction steps:** sign and send in order, waiting for confirmation between steps.
- **Signature steps (AORI/intent):** sign the EIP-712 payload in
  `userStep.signature.typedData`, then `POST /v1/submit-signature` with
  `{"quoteId", "signatures": ["0x..."]}`.
- **AA wallets:** if the wallet returns only a `user_operation_hash`, resolve it to
  the final on-chain transaction hash — via the bundler receipt when available,
  otherwise via wallet transaction history or destination transfer records. A
  missing bundler receipt is not evidence of failure: never mark a transfer failed
  merely because the receipt is unavailable; fall back to on-chain verification.

## Step 4 — Verify completion (not just "tx sent")

Success requires **all** of the following, not merely an explorer link:

1. Source transaction confirmed (final tx hash, not a user-op hash).
2. Source wallet actually debited the expected amount.
3. Destination receipt — **primary evidence is the destination transaction receipt
   and its token Transfer logs** (amount, recipient, token contract). Use the
   destination wallet's balance delta only as corroboration: unrelated concurrent
   transfers can distort a balance-only check, and for native assets the delta is
   also skewed by destination gas or other activity. Compare the received amount
   against the minimum received — flag if below.
4. Report the exact destination amount received, in human units.

Polling:
- **LayerZero:** `GET /v1/status/{quoteId}?txHash=0x...` (proxied) every ~4s.
  Terminal: `SUCCEEDED`, `FAILED`, `UNKNOWN`; non-terminal: `PENDING`, `PROCESSING`.
  Share `explorerUrl` — but still perform the destination receipt/log verification
  above.
- **WOOFi cross-chain:** LayerZeroScan (`https://layerzeroscan.com/tx/<hash>`) is a
  tracking aid only — completion is confirmed by the destination receipt/log
  verification.
- **Chained flows (bridge → swap):** start the destination-chain WOOFi swap only after
  the bridge is verified complete (funds visible), then run the full approval-requote
  sequence again on the destination chain.

## Safety rules

- ⚠️ **Never approve the LZMulticall (Wrapper) contract as a token spender.** Execute
  API-returned steps as-is; never hand-craft approvals.
- Prefer exact-amount approvals; never unlimited allowances.
- Quotes expire — re-quote if execution is delayed; never reuse a stale quote.
- Check source token and native gas balances before asking the user to confirm.
- Rate limits: WOOFi 5 req/s; keep LayerZero status polling at ~4s intervals.
- **Never retry a failed transaction automatically.** On revert, `FAILED`, or
  `UNKNOWN`, report the tx hash / `explorerUrl` and the decoded cause if available,
  then wait for the user.
- State chain, token, amount, fees, spender, and destination address before every
  signature; re-verify guardrails against the freshest quote, not the original one.

## Pre-release test gate

Before treating a deployment as production-ready, pass live tests for:
same-chain ERC-20→ERC-20; native→ERC-20 and ERC-20→native; cross-chain same-token
EVM→EVM; cross-chain token conversion; LayerZero-only EVM→Solana and Solana→EVM;
bridge-then-destination-swap; existing-allowance and approval-required paths;
insufficient token and insufficient gas; expired quote, reverted swap, failed bridge,
delayed destination; different source vs destination wallets; AA wallet returning only
`user_operation_hash`.
