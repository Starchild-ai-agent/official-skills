---
name: "LayerZero Value Transfer"
version: 1.0.0
description: Cross-chain asset transfers via the LayerZero Value Transfer API. Quote, execute, and track bridging of 450+ tokens across 150+ chains (EVM, Solana, Aptos, TON) using OFT, Stargate, CCTP, and Aori routes. Quote-then-execute workflow with status polling.
author: starchild
tags: [layerzero, bridge, cross-chain, defi, stargate, cctp, oft]
metadata: {"starchild":{"emoji":"🌐","requires":{"bins":["curl"]}}}
---

# LayerZero Value Transfer API

Unified REST API for moving assets across 150+ blockchains. One endpoint consolidates
multiple bridge/swap protocols — you get a quote, sign the returned transactions, and
poll for completion. Gas is paid on the source chain only.

**Base URL:** `https://transfer.layerzero-api.com/v1`

**Auth (Starchild): the key is injected by sc-proxy — you do NOT set
`LAYERZERO_API_KEY`.** `transfer.layerzero-api.com` is a proxied domain, so route
transfer calls through `core.http_client` and the platform adds the real key. The
`x-api-key` header value can be anything (or omitted); the proxy overrides it.

```python
from core.http_client import proxied_post, proxied_get
r = proxied_post(
    "https://transfer.layerzero-api.com/v1/quotes",
    json=body,
    headers={"x-api-key": "proxy", "SC-CALLER-ID": f"chat:{thread_id}"},
    timeout=40,
)
```

Discovery endpoints (`/chains`, `/tokens`, `/metadata`) need no auth and work with
plain `curl` too. A direct `curl` to a transfer endpoint bypasses the proxy and
returns `{"error": "Unauthorized"}` — use `proxied_*` for anything that needs the key.

## Route types

| Route | Protocol |
|---|---|
| `OFT` | Standard omnichain token transfer |
| `STARGATE_V2_TAXI` | Instant Stargate transfer |
| `STARGATE_V2_BUS` | Batched (cheaper, slower) Stargate transfer |
| `CCTP` | Circle native USDC |
| `AORI` | Intent-based swap (uses EIP-712 signatures) |

The API picks the optimal route; you don't normally need to choose.

## Workflow

```
1. GET  /chains, /tokens        → discover routes (optional)
2. POST /quotes                 → get quote.id, feeUsd, userSteps
3. Execute userSteps            → sign & send each tx (or EIP-712 signature)
4. GET  /status/{quoteId}       → poll every ~4s until terminal
```

### 1. Discovery

```bash
curl -s https://transfer.layerzero-api.com/v1/chains
# → { "chains": [{ "name": "Base", "chainKey": "base", "chainType": "EVM",
#                 "chainId": 8453, "nativeCurrency": { "symbol": "ETH", "decimals": 18,
#                 "address": "0xEeee...EEeE" } }, ...] }
# Note: results are under the "chains" key (not a bare array). chainType is
# uppercase: EVM, SOLANA, APTOS, SUI, TON, TRON, STARKNET, IOTAMOVE.

# Tokens receivable from a given source token:
curl -s "https://transfer.layerzero-api.com/v1/tokens?transferrableFromChainKey=base&transferrableFromTokenAddress=0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
# → { "tokens": [{ chainKey, address, decimals, symbol, name, price.usd }, ...],
#     "pagination": { "nextToken"? } }   (results under the "tokens" key)
```

- Native token address is `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`.
- List endpoints paginate: pass `pagination[nextToken]` and keep fetching until
  the response has no `nextToken`.
- `GET /metadata` returns contract deployment addresses per chain.

### 2. Get a quote

```python
from core.http_client import proxied_post
r = proxied_post(
    "https://transfer.layerzero-api.com/v1/quotes",
    json={
        "srcChainKey": "base",
        "dstChainKey": "optimism",
        "srcTokenAddress": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "dstTokenAddress": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "srcWalletAddress": "0xYOUR_WALLET",
        "dstWalletAddress": "0xYOUR_WALLET",
        "amount": "1000000000000000",
        "options": {
            "amountType": "EXACT_SRC_AMOUNT",
            "feeTolerance": {"type": "PERCENT", "amount": 2},
        },
    },
    headers={"x-api-key": "proxy", "SC-CALLER-ID": f"chat:{thread_id}"},
    timeout=40,
)
quote = r.json()["quotes"][0]   # id, feeUsd, dstAmount, userSteps
```

Response shape: `{"error": null, "quotes": [{ "id", "routeSteps", "fees",
"feeUsd", "feePercent", "srcAmount", "dstAmount", "dstAmountMin", "userSteps" }]}`.
`quotes` is an array (the API may return several routes); take `quotes[0]` unless
you want to compare `feeUsd`.

- `amount` is a string in the token's local decimals (wei for ETH).
- Response: `quote.id`, `quote.feeUsd`, `quote.userSteps` (ordered transactions to
  execute). Show the user `feeUsd` and expected output before executing.

### 3. Execute userSteps

**EVM:** loop through `userSteps` in order; each contains ready-to-send transaction
calldata. Sign with the agent wallet, send, and wait for confirmation before the next
step. ERC-20 transfers typically yield two steps: `approve` then the bridge tx.

**Solana:** transaction blockhashes expire in ~60s, so first regenerate fresh data:

```python
r = proxied_post(
    "https://transfer.layerzero-api.com/v1/build-user-steps",
    json={"quoteId": "QUOTE_ID"},
    headers={"x-api-key": "proxy", "SC-CALLER-ID": f"chat:{thread_id}"},
)
```

**Signature steps (intent routes like AORI):** sign the EIP-712 payload in
`userStep.signature.typedData`, then submit:

```python
r = proxied_post(
    "https://transfer.layerzero-api.com/v1/submit-signature",
    json={"quoteId": "QUOTE_ID", "signatures": ["0xSIGNATURE"]},
    headers={"x-api-key": "proxy", "SC-CALLER-ID": f"chat:{thread_id}"},
)
```

### 4. Poll status

```python
from core.http_client import proxied_get
r = proxied_get(
    "https://transfer.layerzero-api.com/v1/status/QUOTE_ID",
    params={"txHash": "0xSRC_TX_HASH"},
    headers={"x-api-key": "proxy", "SC-CALLER-ID": f"chat:{thread_id}"},
)
# → { "status": "PROCESSING", "explorerUrl": "..." }
```

Poll every ~4 seconds. Terminal states: `SUCCEEDED`, `FAILED`, `UNKNOWN`.
Non-terminal: `PENDING`, `PROCESSING`. Share `explorerUrl` with the user.

## Safety rules

- ⚠️ **Never approve the LZMulticall (Wrapper) contract as a token spender.** The
  API-generated calldata already uses the TransferDelegate contract for approvals —
  execute steps as returned, don't hand-craft approvals.
- Quotes expire — get a fresh quote if execution is delayed; don't reuse old ones.
- Always confirm with the user before signing/sending real-value transactions:
  state source/destination chains, token, amount, and `feeUsd`.
- Verify the destination address matches the user's intent before quoting.
- On `FAILED` or `UNKNOWN`, report the `explorerUrl` and do not retry blindly.
