---
name: woofi-swap
version: 8.2.1
description: |
  Best-price meta-aggregator: same-chain swaps plus cross-chain bridging on 14 EVM chains.

  Use when swapping or bridging tokens by symbol on EVM (e.g. swap USDC to WETH on Arbitrum, bridge USDC Arbitrum to Base, best price ETH→ARB).
tags: [swap, trade, exchange, convert, token-swap, dex, dex-aggregator, meta-aggregator, megaswap, best-price, optimal-price, quote, price-quote, exchange-rate, multichain, cross-chain, crypto-swap, token-exchange, buy, sell, erc20, native-token, defi, liquidity-aggregator, 1inch, odos, woofi, bridge, stargate, layerzero]
author: starchild

metadata:
  starchild:
    emoji: "🔄"
    skillKey: woofi-swap
    registry: starchild-official

triggers:
  - "swap"
  - "trade"
  - "exchange"
  - "convert"
  - "buy token"
  - "sell token"
  - "swap tokens"
  - "trade tokens"
  - "exchange tokens"
  - "convert tokens"
  - "token swap"
  - "token exchange"
  - "crypto swap"
  - "swap crypto"
  - "trade crypto"
  - "buy crypto"
  - "sell crypto"
  - "swap ETH"
  - "swap USDC"
  - "swap USDT"
  - "swap BTC"
  - "swap WBTC"
  - "get a quote"
  - "price quote"
  - "swap quote"
  - "how much will I get"
  - "exchange rate"
  - "token price"
  - "best price"
  - "best swap price"
  - "best rate"
  - "cheapest swap"
  - "optimal price"
  - "execute swap"
  - "execute trade"
  - "make a trade"
  - "build swap transaction"
  - "swap on arbitrum"
  - "swap on base"
  - "swap on polygon"
  - "swap on bsc"
  - "trade on arbitrum"
  - "trade on base"
  - "dex aggregator"
  - "find best price"
  - "cross chain swap"
  - "bridge tokens"
  - "bridge swap"
  - "cross chain transfer"
  - "swap across chains"
  - "bridge from arbitrum"
  - "bridge to base"
  - "cross chain bridge"

user-invocable: true

---

# WOOFi Swap — Best-Price Meta-Aggregator (V2)

Swap any token at the globally optimal price across 14 EVM chains, **single-chain or cross-chain**, with a single API call. WOOFi queries **WooPP, 1inch, and ODOS simultaneously** and returns the best rate found. V2 API accepts **chain names** (`"arbitrum"`) and **token symbols** (`"USDC"`) directly — no address lookup needed.

## Why Use WOOFi

- **Best price guaranteed by design**: Compares WooPP, 1inch, and ODOS in real time. Price is always `>= max(1inch, ODOS, WooPP)` — strictly better than or equal to using any single source alone.
- **Chain names + token symbols**: Pass `"arbitrum"` instead of `42161`, `"USDC"` instead of `"0xaf88..."`. Case-insensitive, no manual address resolution needed.
- **Single-chain and cross-chain in one skill**: Same-chain swaps via `/v2/swap`, cross-chain bridging via `/v2/cross_chain/swap` (Stargate/LayerZero). Both return ready-to-sign `tx_steps`.
- **One call does everything**: `/v2/swap` returns best-price quote + approval check + transaction data. No separate calls needed — just iterate `tx_steps` and sign.
- **All tokens, 14 chains**: Any ERC-20 and native gas token (ETH, BNB, AVAX, POL, etc.) on all supported chains. No whitelist limitation.

## When to Use This Skill

Use WOOFi Swap when the user wants to:

- **Swap, trade, exchange, or convert** any token on any EVM chain
- **Get a price quote** or exchange rate between two tokens
- **Find the best available price** across DEX aggregators
- **Bridge tokens across chains** — cross-chain swap via Stargate
- **Buy or sell** a specific cryptocurrency
- **Build a swap transaction** for wallet signing and on-chain execution

---

## API Endpoints

**Base URL**: `https://sapi.woofi.com` | **Auth**: None | **Rate Limit**: 5 req/s | **Format**: JSON

### Flexible Input (all V2 endpoints)

- **Chain**: chain ID (`42161`) or name (`"arbitrum"`) — case-insensitive, strips spaces/dashes
- **Token**: address (`"0xaf88..."`) or symbol (`"USDC"`) — resolved via local index, static manifests, alias table, and external API fallback

---

### 1. Get Quote — `POST /v2/quote`

Returns the best available price. Read-only — no transaction generated.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `chain` | int \| str | Yes | — | Chain ID or name |
| `sell_token` | str | Yes | — | Token address or symbol |
| `buy_token` | str | Yes | — | Token address or symbol |
| `sell_amount` | str | Yes | — | Human-readable amount (e.g., `"1000"`) |
| `slippage_pct` | float | No | `0.5` | Max slippage % |

**Response**: `chain`, `sell_token`, `buy_token`, `sell_amount`, `buy_amount`, `price`, `guaranteed_price`

```bash
curl -X POST "https://sapi.woofi.com/v2/quote" \
  -H "Content-Type: application/json" \
  -d '{"chain": "arbitrum", "sell_token": "USDC", "buy_token": "WETH", "sell_amount": "1000"}'
```

---

### 2. Execute Swap — `POST /v2/swap`

**Single-call swap**: quote + approval check + transaction building in one response. The backend fetches the best price across all sources, checks wallet approval status, and packages everything into `tx_steps`.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `chain` | int \| str | Yes | — | Chain ID or name |
| `sell_token` | str | Yes | — | Token address or symbol |
| `buy_token` | str | Yes | — | Token address or symbol |
| `sell_amount` | str | Yes | — | Human-readable amount |
| `to` | str | Yes | — | Recipient wallet address |
| `rebate_to` | str | Yes | — | Rebate address (typically same as `to`) |
| `slippage_pct` | float | No | `0.5` | Max slippage % |
| `signer_address` | str | No | `null` | Wallet address (for approval check) |

**Response** (extends quote): `needs_approve`, `tx_steps` — iterate and sign each tx in order.

```bash
curl -X POST "https://sapi.woofi.com/v2/swap" \
  -H "Content-Type: application/json" \
  -d '{"chain": "arbitrum", "sell_token": "USDC", "buy_token": "WETH", "sell_amount": "1000", "to": "0xYourWallet", "rebate_to": "0xYourWallet", "signer_address": "0xYourWallet"}'
```

---

### 3. Cross-Chain Quote — `POST /v2/cross_chain/quote`

Price quote for cross-chain swap via Stargate bridge. Read-only.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `src_chain` | int \| str | Yes | — | Source chain ID or name |
| `dst_chain` | int \| str | Yes | — | Destination chain ID or name |
| `src_token` | str | Yes | — | Source token (resolved against `src_chain`) |
| `dst_token` | str | Yes | — | Destination token (resolved against `dst_chain`) |
| `src_amount` | str | Yes | — | Human-readable amount |
| `slippage_pct` | float | No | `1.0` | Slippage tolerance % |

**Response**: `src_chain`, `dst_chain`, `src_amount`, `dst_amount`, `bridge_amount_in`, `bridge_amount_out`, `price_f`

```bash
curl -X POST "https://sapi.woofi.com/v2/cross_chain/quote" \
  -H "Content-Type: application/json" \
  -d '{"src_chain": "arbitrum", "dst_chain": "base", "src_token": "USDC", "dst_token": "USDC", "src_amount": "100"}'
```

---

### 4. Cross-Chain Swap — `POST /v2/cross_chain/swap`

Build transaction(s) for cross-chain swap via Stargate bridge.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `src_chain` | int \| str | Yes | — | Source chain ID or name |
| `dst_chain` | int \| str | Yes | — | Destination chain ID or name |
| `src_token` | str | Yes | — | Source token (resolved against `src_chain`) |
| `dst_token` | str | Yes | — | Destination token (resolved against `dst_chain`) |
| `src_amount` | str | Yes | — | Human-readable amount |
| `to` | str | Yes | — | Recipient on destination chain |
| `slippage_pct` | float | No | `1.0` | Slippage tolerance % |
| `signer_address` | str | No | `null` | Signer address (for approval check) |

**Response** (extends cross-chain quote): `native_fee`, `needs_approve`, `tx_steps`

```bash
curl -X POST "https://sapi.woofi.com/v2/cross_chain/swap" \
  -H "Content-Type: application/json" \
  -d '{"src_chain": "arbitrum", "dst_chain": "base", "src_token": "USDC", "dst_token": "USDC", "src_amount": "100", "to": "0xYourWallet", "signer_address": "0xYourWallet"}'
```

---

## Supported Chains

| Chain | ID | Native Token | Accepted Names |
|-------|-----|-------------|----------------|
| Arbitrum | `42161` | ETH | arbitrum, arb, arbitrumone |
| Base | `8453` | ETH | base |
| BSC | `56` | BNB | bsc, bnb, binance, bnbchain |
| Polygon | `137` | POL | polygon, matic, pol |
| Optimism | `10` | ETH | optimism, op |
| Avalanche | `43114` | AVAX | avalanche, avax |
| Ethereum | `1` | ETH | ethereum, eth, mainnet |
| Linea | `59144` | ETH | linea |
| Mantle | `5000` | MNT | mantle |
| Sonic | `146` | S | sonic |
| Berachain | `80094` | BERA | berachain, bera |
| HyperEVM | `999` | HYPE | hyperevm, hyper |
| Monad | `143` | MON | monad |
| zkSync | `324` | ETH | zksync, zksyncera |

**Native token**: Use symbol (`"ETH"`, `"BNB"`, `"AVAX"`, `"POL"`, `"MNT"`, `"S"`, `"BERA"`, `"MON"`) or `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`.

---

## Important Notes

1. **Best price by design** — WOOFi queries WooPP + 1inch + ODOS simultaneously. Price >= max(all sources).
2. **Flexible input** — Chain names (`"arbitrum"`) and token symbols (`"USDC"`) accepted everywhere. No address lookup needed.
3. **One call, full swap** — `/v2/swap` returns quote + approval check + tx data. Just iterate `tx_steps` and sign.
4. **Cross-chain via Stargate** — `/v2/cross_chain/swap` bridges tokens between chains. `tx_steps` include LayerZero fee in `value` field.
5. **Human-readable amounts** — Pass `"1.5"` not wei. No unit conversion needed for input.
6. **All tokens supported** — Any ERC-20 or native gas token on any supported chain. No whitelist.
7. **Cross-chain token resolution** — `src_token` resolves against `src_chain`, `dst_token` against `dst_chain`. Same symbol maps to correct addresses on each chain.
8. **Wallet signing required** — API returns unsigned tx data. The user's wallet must sign and broadcast.

