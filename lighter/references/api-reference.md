# Lighter.xyz Complete API Reference

## Deployments & Base URLs

Lighter runs as independent deployments. Same REST/WS API surface; different hosts, accounts, keys, contracts, markets.

| Deployment | `LIGHTER_NETWORK` | REST API | WebSocket | Signing chain ID | L1 chain ID |
|---|---|---|---|---|---|
| **Lighter on Ethereum** (mainnet) | `ethereum` | `https://mainnet.zklighter.elliot.ai` | `wss://mainnet.zklighter.elliot.ai/stream` | 304 | 1 |
| **Lighter on Robinhood Chain** (mainnet) | `robinhood` | `https://api.rh.lighter.xyz` | `wss://api.rh.lighter.xyz/stream` | 466324 | 4663 |
| Ethereum testnet | `ethereum-testnet` | `https://testnet.zklighter.elliot.ai` | `wss://testnet.zklighter.elliot.ai/stream` | 300 | 11155111 |
| Robinhood Chain testnet | `robinhood-testnet` | `https://api.rh-testnet.lighter.xyz` | `wss://api.rh-testnet.lighter.xyz/stream` | 300 | — |

Other: Explorer `https://explorer.elliot.ai/api/` (Ethereum). Docs: `https://apidocs.lighter.xyz` (Ethereum), `https://apidocs.rh.lighter.xyz` (Robinhood Chain). Status: `https://robinhoodstatus.lighter.xyz/`.

Recommended colocation (both): AWS Tokyo `ap-northeast-1a` (apne1-az4)

Contracts (from `/api/v1/layer1BasicInfo`):

| Deployment | ZkLighterContract | USDC/USDG |
|---|---|---|
| Ethereum | `0x3B4D794a66304F130a4Db8F2551B0070dfCf5ca7` | `0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48` (USDC) |
| Robinhood Chain | `0x94bAB9693Ba2f6358507eFfcbd372b0660AFfF9d` | `0x5fc5360D0400a0Fd4f2af552ADD042D716F1d168` |

Robinhood Chain spot markets are quoted in USDG (e.g. `META/USDG`) and include tokenized stocks (`HOOD`, `SPY`, `QQQ`).
The Python SDK's `SignerClient` accepts `chain_id=`; the skill pins it per network.

SDKs:
- Python: `pip install lighter-sdk` ([GitHub](https://github.com/elliottech/lighter-python))
- Go: `go get github.com/elliottech/lighter-go` ([GitHub](https://github.com/elliottech/lighter-go))

---

## Authentication

### Standard Auth Tokens (Read + Write)
- Generated via SDK using API private keys
- Max expiry: **8 hours** (default 10 minutes)
- Format: `{expiry_unix}:{account_index}:{api_key_index}:{random_hex}`
- Passed via `authorization` header or `auth` query parameter

### Read-Only Tokens
- Created via `POST /api/v1/tokens/create` or frontend
- Max expiry: **10 years**; minimum: **1 day**
- Format: `ro:{account_index}:{single|all}:{expiry_unix}:{random_hex}`
- Cannot place trades or request withdrawals

### API Keys
- Up to **256 keys** per account (indices 0-254; 255 = retrieve all)
- Indices **0-3** reserved for desktop/mobile
- Indices **2-254** available for programmatic use
- Each key has its own independent **nonce**
- Created programmatically via SDK; requires L1 private key signature to associate

### Nonce Management
- Each API key maintains independent nonce (must increment by 1)
- **SkipNonce**: Set `SkipNonce=1` in L2TxAttributes; constraint: `2^47-1 > new_nonce > old_nonce`
- Max nonce: `2^48-1`
- API-level errors do NOT increment nonce; sequencer-accepted-then-rejected orders DO

---

## Complete REST Endpoints

### System

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | System status |
| GET | `/info` | No | System info |
| GET | `/api/v1/systemConfig` | No | System configuration (pool indices, max fees, cooldowns) |
| GET | `/api/v1/layer1BasicInfo` | No | L1 contract addresses, chain/network IDs |
| GET | `/api/v1/announcement` | No | Announcements |
| GET | `/api/v1/currentHeight` | No | Current blockchain height |

### Account

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/account` | No | Get account by index or l1_address |
| GET | `/api/v1/accountsByL1Address` | No | All accounts for an L1 address |
| GET | `/api/v1/accountMetadata` | Optional | Account metadata (name, description, referral) |
| POST | `/api/v1/setAccountMetadata` | Optional | Set account metadata |
| GET | `/api/v1/accountLimits` | Yes | Tier info, fee ticks, LIT stakes |
| GET | `/api/v1/apikeys` | No | API key info (nonce, public key) |
| GET | `/api/v1/getMakerOnlyApiKeys` | Yes | Maker-only designated keys |
| POST | `/api/v1/setMakerOnlyApiKeys` | Yes | Set maker-only keys (premium, 1hr cooldown) |
| GET | `/api/v1/l1Metadata` | Yes | L1 metadata for address |
| POST | `/api/v1/changeAccountTier` | Optional | Switch standard/premium (24hr cooldown, no open positions) |
| GET | `/api/v1/faucet` | No | Testnet faucet |

### Auth Tokens (Read-Only)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/tokens` | Optional | List read-only tokens |
| POST | `/api/v1/tokens/create` | Yes | Create read-only token |
| POST | `/api/v1/tokens/revoke` | Yes | Revoke token |

### Markets & Orderbooks

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/orderBooks` | No | Market metadata (symbol, fees, decimals, limits) |
| GET | `/api/v1/orderBookDetails` | No | Detailed market metadata |
| GET | `/api/v1/orderBookOrders` | No | Orderbook depth (limit 1-250) |
| GET | `/api/v1/assetDetails` | No | Asset config (decimals, caps, liquidation params) |

### Orders

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/accountActiveOrders` | Yes | Active/open orders |
| GET | `/api/v1/accountInactiveOrders` | Yes | Filled/canceled orders (limit 1-100, paginated) |

### Trades

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/recentTrades` | No | Recent trades for market (limit 1-100) |
| GET | `/api/v1/trades` | Optional | Filtered trades (by account, market, role, type, paginated) |

### Candlesticks & Charts

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/candles` | No | OHLCV data (resolutions: 1m/5m/15m/30m/1h/4h/12h/1d/1w, max 500) |
| GET | `/api/v1/fundings` | No | Historical funding data (resolutions: 1h/1d) |
| GET | `/api/v1/funding-rates` | No | Current rates across Binance/Bybit/Hyperliquid/Lighter |
| GET | `/api/v1/pnl` | Optional | PnL chart (resolutions: 1m/5m/15m/1h/4h/1d) |

### Exchange Statistics

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/exchangeStats` | No | 24h volume, per-market prices/OI/funding |
| GET | `/api/v1/exchangeMetrics` | No | Filtered metrics (volume, fees, OI, account counts) |
| GET | `/api/v1/executeStats` | No | Execution latency stats |

### Transactions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/nextNonce` | No | Next nonce for API key |
| POST | `/api/v1/sendTx` | No* | Submit signed transaction (form: tx_type, tx_info) |
| POST | `/api/v1/sendTxBatch` | No* | Submit batch (up to 15 txs) |
| GET | `/api/v1/tx` | No | Get tx by hash or sequence_index |
| GET | `/api/v1/txFromL1TxHash` | No | Get L2 tx from L1 hash |
| GET | `/api/v1/txs` | No | List packed transactions |
| GET | `/api/v1/accountTxs` | Optional | Account transactions |

*Transactions are self-authenticated via cryptographic signatures.

### Positions & Funding

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/liquidations` | Yes | Liquidation history |
| GET | `/api/v1/positionFunding` | Optional | Position funding payments |

### Deposits & Withdrawals

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/deposit/history` | Optional | Deposit history |
| GET | `/api/v1/deposit/latest` | Optional | Latest deposit |
| GET | `/api/v1/deposit/networks` | No | Available deposit networks |
| GET | `/api/v1/withdraw/history` | Optional | Withdrawal history |
| GET | `/api/v1/withdrawalDelay` | No | Current withdrawal delay (seconds) |
| GET | `/api/v1/transfer/history` | Optional | Transfer history |
| GET | `/api/v1/transferFeeInfo` | Yes | Transfer fee info |
| POST | `/api/v1/fastwithdraw` | Optional | Fast USDC withdrawal (min 4 USDC) |
| GET | `/api/v1/fastwithdraw/info` | Optional | Fast withdrawal info |
| GET | `/api/v1/fastbridge/info` | No | Fast bridge info |

### Bridge (CCTP)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/createIntentAddress` | No | Create CCTP bridge address (Arbitrum/Base/Avalanche) |
| GET | `/api/v1/bridges` | No | Get bridges for L1 address |
| GET | `/api/v1/bridges/isNextBridgeFast` | No | Check if next bridge is fast |

### Blocks

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/blocks` | No | List blocks (paginated) |
| GET | `/api/v1/blockTxs` | No | Block transactions |

### Export

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/export` | Yes | CSV export (trades: 12mo/1M limit; funding: 3mo limit) |

### LIT Leasing

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/leaseOptions` | No | Available lease duration/rate tiers |
| GET | `/api/v1/leases` | Optional | Account lease history |
| POST | `/api/v1/litLease` | Yes | Submit LIT lease (1 LIT = 100000000 raw) |

### Public Pools

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/publicPoolsMetadata` | Optional | Pool metadata (filter: all/user/protocol/stake) |

### Referrals

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/referral/userReferrals` | Optional | User referral data |
| GET | `/api/v1/referral/points` | — | Referral points |
| POST | `/api/v1/referral/create` | — | Create referral code |
| GET | `/api/v1/referral/get` | — | Get referral info |
| POST | `/api/v1/referral/use` | — | Use referral code |

### Notifications

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/notification/ack` | Optional | Acknowledge notification |
| POST | `/api/v1/pushnotif/register` | Yes | Register push notifications |
| GET | `/api/v1/pushnotif/settings` | Optional | Get push settings |
| POST | `/api/v1/pushnotif/settings` | Yes | Update push settings |
| POST | `/api/v1/pushnotif/unregister` | Yes | Unregister push notifications |

### Partner Integration

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/partnerStats` | — | Partner fee statistics |

---

## Transaction Types

| Code | Type | Description |
|------|------|-------------|
| 8 | L2ChangePubKey | Assign API keys |
| 9 | L2CreateSubAccount | Create sub-account |
| 10 | L2CreatePublicPool | Create public pool |
| 11 | L2UpdatePublicPool | Update public pool |
| 12 | L2Transfer | Transfer funds |
| 13 | L2Withdraw | Withdraw funds |
| 14 | L2CreateOrder | Create order |
| 15 | L2CancelOrder | Cancel order |
| 16 | L2CancelAllOrders | Cancel all orders |
| 17 | L2ModifyOrder | Modify order |
| 18 | L2MintShares | Mint pool shares |
| 19 | L2BurnShares | Burn pool shares |
| 20 | L2UpdateLeverage | Update leverage |
| 28 | L2CreateGroupedOrders | OTO/OCO grouped orders |
| 29 | L2UpdateMargin | Update margin |
| 30 | L1BurnShares | L1 burn shares |

### Transaction Status

| Code | Status |
|------|--------|
| 0 | Failed |
| 1 | Pending |
| 2 | Executed |
| 3 | Pending - Final State |

---

## Order Types

| Code | Type | Description |
|------|------|-------------|
| 0 | LIMIT | Limit order |
| 1 | MARKET | Market order |
| 2 | STOP_LOSS | Stop-loss (market fill) |
| 3 | STOP_LOSS_LIMIT | Stop-loss with limit price |
| 4 | TAKE_PROFIT | Take-profit (market fill) |
| 5 | TAKE_PROFIT_LIMIT | Take-profit with limit price |
| 6 | TWAP | Time-weighted average price |

### Time-in-Force

| Code | Type | Description |
|------|------|-------------|
| 0 | IOC | Immediate-or-cancel |
| 1 | GTT | Good-till-time (default 28 days) |
| 2 | POST_ONLY | Add-liquidity-only (maker only) |

### Order Grouping

| Code | Type | Description |
|------|------|-------------|
| 1 | OTO | One-triggers-the-other |
| 2 | OCO | One-cancels-the-other |
| 3 | OTOCO | One-triggers-a-one-cancels-the-other |

### Order Status

| Code | Status |
|------|--------|
| 0 | InProgressOrder |
| 1 | PendingOrder (awaiting trigger) |
| 2 | ActiveLimitOrder (live in market) |
| 3 | FilledOrder |
| 4 | CancelledPostOnly |
| 5 | CancelledReduceOnly |
| 6 | CancelledPositionNotAllowed |
| 7 | CancelledMarginNotAllowed |
| 8 | CancelledTooMuchSlippage |
| 9 | CancelledNotEnoughLiquidity |
| 10 | CancelledSelfTrade |
| 11 | CancelledExpired |
| 12 | CancelledOCO |
| 13 | CancelledChild |
| 14 | CancelledLiquidation |
| 15 | CancelledInvalidBalance |
| 16 | CancelledByUser |

### Order Limits

| Scope | Limit |
|-------|-------|
| Active orders per account | 1,500 |
| Active orders per market | 1,000 |
| Pending orders per account | 500 |
| Pending orders per market | 16 |

---

## Account Types & Fees

### Standard (Default)

| Property | Value |
|----------|-------|
| Maker fee | 0% |
| Taker fee | 0% |
| Taker latency | 300ms |
| Maker/cancel latency | 200ms |
| Rate limit | 60 req/min |

### Premium (Opt-in via `changeAccountTier`)

| Staked LIT | Discount | Maker Fee | Taker Fee | Latency | Tx/Min | Sub-accounts |
|------------|----------|-----------|-----------|---------|--------|--------------|
| 0 | 0% | 0.0040% | 0.0280% | 200ms | 4,000 | 8 |
| 1,000 | 2.5% | 0.0039% | 0.0273% | 195ms | 5,000 | 8 |
| 3,000 | 5% | 0.0038% | 0.0266% | 190ms | 6,000 | 8 |
| 10,000 | 10% | 0.0036% | 0.0252% | 180ms | 7,000 | 8 |
| 30,000 | 15% | 0.0034% | 0.0238% | 170ms | 8,000 | 8 |
| 100,000 | 20% | 0.0032% | 0.0224% | 160ms | 12,000 | 8 |
| 300,000 | 25% | 0.0030% | 0.0210% | 150ms | 24,000 | 8 |
| 500,000 | 30% | 0.0028% | 0.0196% | 140ms | 40,000 | 64 |

---

## Rate Limits

### REST API (rolling minute)

| Tier | Limit |
|------|-------|
| Builder | 240,000 weighted req/min |
| Premium | 24,000 weighted req/min |
| Standard | 60 req/min (unweighted) |

### Endpoint Weights

| Weight | Endpoints |
|--------|-----------|
| 6 | sendTx, sendTxBatch, nextNonce |
| 50 | publicPools, txFromL1TxHash |
| 100 | accountInactiveOrders, deposit/latest |
| 150 | apikeys |
| 300 | Default (all unlisted endpoints) |
| 500 | transferFeeInfo |
| 600 | trades, recentTrades |
| 3,000 | changeAccountTier, tokens, createIntentAddress |
| 23,000 | tokens/create |

### WebSocket Limits (per IP)

| Resource | Limit |
|----------|-------|
| Connections | 100 |
| Subscriptions/connection | 500 |
| Unique accounts/connection | 500 |
| New connections/minute | 80 |
| Client messages/minute | 200 (excl. tx sends) |
| Inflight messages | 50 (excl. tx sends) |

### Transaction Limits (per user, all tiers)

| Transaction Type | Limit |
|-----------------|-------|
| Default | 40/min |
| L2Withdraw | 2/min |
| L2CreateSubAccount | 2/min |
| L2CreatePublicPool | 2/min |
| L2UpdateLeverage | 40/min |
| L2ChangePubKey | 300/min |
| L2Transfer | 120/min |
| L2MintShares | 1 per 15s |
| L2UnstakeAssets | 1 per 15s |

### Rate Limit Errors
- HTTP **429** or **405** on violation
- Firewall cooldown: 60 seconds static
- API cooldown: `endpointWeight / (totalWeight / 60)` seconds

---

## WebSocket API

### Connection
```
wss://mainnet.zklighter.elliot.ai/stream
```
- Append `?readonly=true` for restricted regions
- Keepalive: send frame every **2 minutes**
- Supports `permessage-deflate` compression

### Subscribe / Unsubscribe
```json
{"type": "subscribe", "channel": "order_book/0"}
{"type": "unsubscribe", "channel": "order_book/0"}
```

### Send Transaction via WebSocket
```json
{"type": "jsonapi/sendtx", "data": {"tx_type": 14, "tx_info": "..."}}
```

### Send Batch (up to 15)
```json
{"type": "jsonapi/sendtxbatch", "data": {"tx_types": "[14,15]", "tx_infos": "[...,...]"}}
```

### Public Channels (no auth)

| Channel | Description |
|---------|-------------|
| `order_book/{MARKET}` | Orderbook snapshot + 50ms batched diffs. Track `begin_nonce`/`nonce` for continuity |
| `ticker/{MARKET}` | Best bid/offer on every nonce change |
| `market_stats/{MARKET}` or `market_stats/all` | Index/mark price, funding, OI, volume |
| `spot_market_stats/{MARKET}` or `spot_market_stats/all` | Spot market stats |
| `trade/{MARKET}` | Trade events including liquidations |
| `height` | Blockchain height updates |

### Account Channels (auth required via `"auth"` param)

| Channel | Description |
|---------|-------------|
| `account_all/{ACCOUNT}` | Full snapshot: assets, positions, trades, shares, funding |
| `account_market/{MARKET}/{ACCOUNT}` | Market-specific account data |
| `user_stats/{ACCOUNT}` | Collateral, portfolio value, leverage, margin, buying power |
| `account_tx/{ACCOUNT}` | Transaction history |
| `account_all_orders/{ACCOUNT}` | All orders keyed by market |
| `account_orders/{MARKET}/{ACCOUNT}` | Orders on specific market |
| `account_all_trades/{ACCOUNT}` | All trades with volume aggregates |
| `account_all_positions/{ACCOUNT}` | All positions + pool shares |
| `account_all_assets/{ACCOUNT}` | Spot asset holdings |
| `account_spot_avg_entry_prices/{ACCOUNT}` | Spot average entry prices |
| `notification/{ACCOUNT}` | Liquidation, deleverage, announcement alerts |

### Pool Channels (auth required)

| Channel | Description |
|---------|-------------|
| `pool_data/{ACCOUNT}` | Pool trades, orders, positions, shares, fundings |
| `pool_info/{ACCOUNT}` | Pool status, APY, Sharpe ratio, returns |

---

## Error Codes

### Account Errors (21100-21141)
- 21100 AccountNotFound
- 21101 AccountNonceNotFound
- 21102 InvalidAccountIndex
- 21104 InvalidNonce
- 21105 NonIncreasingNonce
- 21108 InvalidPublicKey
- 21109 ApiKeyNotFound
- 21110 InvalidApiKeyIndex
- 21111 PreLiquidation
- 21112 AccountIsInLiquidation

### Collateral Errors (21300-21305)
- 21300 InvalidAssetAmount
- 21301 NotEnoughCollateral
- 21304 NotEnoughAssetBalance
- 21305 NotEnoughAssetBalanceForFee

### Transaction Errors (21400-21516)
- 21402 TxNotFound
- 21403 InvalidTxInfo
- 21407 UnsupportedTxType
- 21408 TooManyTxs

### OrderBook Errors (21600-21626)
- 21601 OrderBookFull
- 21602 InvalidMarketIndex
- 21604 InvalidMarketStatus

### Order Errors (21700-21745)
- 21700 InvalidOrderIndex
- 21701 InvalidBaseAmount
- 21702 InvalidPrice
- 21703 InvalidOrderType
- 21705 MaxOrdersPerAccount
- 21706 MaxPendingOrdersPerAccount
- 21707 FatFingerPrice (accidental price protection)
- 21708 PriceTooFarFromMarkPrice

### Asset Errors (21801-21809)
- 21801 InvalidAssetIndex
- 21804 AssetDoesNotExist

### Rate Limit Errors (23000-23004)
- 23000 TooManyRequests
- 23001 TooManyWithdrawalRequests

### General Errors
- 29404 NotFound
- 29500 InternalServerError
- 29501 ProcessTimeout

### WebSocket Errors (30000-30012)
- 30000 InvalidJSON
- 30001 AlreadySubscribed

---

## Known Asset IDs

| ID | Symbol | Decimals | Scale |
|----|--------|----------|-------|
| 1 | ETH | 8 | 1e8 |
| 2 | LIT | 8 | 1e8 |
| 3 | USDC | 6 | 1e6 |
| 5 | LINK | 8 | 1e8 |
| 6 | UNI | 8 | 1e8 |
| 7 | AAVE | 8 | 1e8 |
| 8 | SKY | 8 | 1e8 |
| 9 | LDO | 8 | 1e8 |
| 10 | AZTEC | 8 | 1e8 |

Route types: PERP=0, SPOT=1

---

## Markets Overview

**220+ total markets:**
- **217 perpetual** — crypto (BTC, ETH, SOL, etc.), stocks (AAPL, TSLA, GOOGL, NVDA), forex (EURUSD, GBPUSD, USDJPY), commodities (XAU, XAG, WTI, NATGAS)
- **3 spot** — ETH/USDC (2048), LINK/USDC (2050), UNI/USDC (2051)

---

## SDK Quick Reference

### Python SDK

```python
import lighter

# Read-only client
api = lighter.ApiClient(url="https://mainnet.zklighter.elliot.ai")
books = await api.get_order_books(market_id=255)
trades = await api.get_recent_trades(market_id=0, limit=50)
candles = await api.get_candles(market_id=0, resolution="1h",
                                 start_timestamp=0, end_timestamp=now_ms,
                                 count_back=100)

# Signer client (extends ApiClient)
client = lighter.SignerClient(
    url="https://mainnet.zklighter.elliot.ai",
    api_private_keys={2: "0xYOUR_PRIVATE_KEY"},
    account_index=123,
)

# Market order
tx, hash, err = await client.create_order(
    market_index=0, client_order_index=0,
    base_amount=10000, price=310000,
    is_ask=False, order_type=client.ORDER_TYPE_MARKET,
    time_in_force=client.ORDER_TIME_IN_FORCE_IMMEDIATE_OR_CANCEL,
    reduce_only=False, order_expiry=client.DEFAULT_IOC_EXPIRY,
)

# Limit order (28-day expiry)
tx, hash, err = await client.create_order(
    market_index=0, client_order_index=0,
    base_amount=10000, price=290000,
    is_ask=False, order_type=client.ORDER_TYPE_LIMIT,
    time_in_force=client.ORDER_TIME_IN_FORCE_GOOD_TILL_TIME,
    reduce_only=False, order_expiry=client.DEFAULT_28_DAY_ORDER_EXPIRY,
)

# Cancel
tx, hash, err = await client.cancel_order(market_index=0, order_index=1234)

# Cancel all
tx, hash, err = await client.cancel_all_orders(time_in_force=0)

# Modify
tx, hash, err = await client.modify_order(
    market_index=0, order_index=1234,
    base_amount=20000, price=300000,
)

# WebSocket
ws = lighter.WsClient(
    order_book_ids=[0, 1],
    account_ids=[123],
    on_order_book_update=handle_ob,
    on_account_update=handle_acct,
)
ws.run()
```

### SDK Constants

```python
# Order types
ORDER_TYPE_LIMIT = 0
ORDER_TYPE_MARKET = 1
ORDER_TYPE_STOP_LOSS = 2
ORDER_TYPE_STOP_LOSS_LIMIT = 3
ORDER_TYPE_TAKE_PROFIT = 4
ORDER_TYPE_TAKE_PROFIT_LIMIT = 5
ORDER_TYPE_TWAP = 6

# Time-in-force
ORDER_TIME_IN_FORCE_IMMEDIATE_OR_CANCEL = 0
ORDER_TIME_IN_FORCE_GOOD_TILL_TIME = 1
ORDER_TIME_IN_FORCE_POST_ONLY = 2

# Grouping types
GROUPING_TYPE_ONE_TRIGGERS_THE_OTHER = 1
GROUPING_TYPE_ONE_CANCELS_THE_OTHER = 2
GROUPING_TYPE_ONE_TRIGGERS_A_ONE_CANCELS_THE_OTHER = 3

# Margin modes
CROSS_MARGIN_MODE = 0
ISOLATED_MARGIN_MODE = 1

# Default expiries
DEFAULT_28_DAY_ORDER_EXPIRY = -1
DEFAULT_IOC_EXPIRY = 0
DEFAULT_10_MIN_AUTH_EXPIRY = -1
NIL_TRIGGER_PRICE = 0
```

---

## Deposits & Withdrawals

### Ethereum Mainnet Deposits
- Contract: `0x3B4D794a66304F130a4Db8F2551B0070dfCf5ca7`
- Function: `deposit` (0x8a857083)
- Params: `_to` (L1 address), `_assetIndex`, `_routeType` (0=perps, 1=spot), `_amount`
- Minimum: 1 USDC equivalent
- ERC20 approval required for non-ETH assets

### CCTP Deposits (Other EVM Chains)
- Supported: Arbitrum (42161), Base, Avalanche C-Chain
- Minimum: 5 USDC
- Use `POST /api/v1/createIntentAddress`
- Credit time: ~15-20 minutes

### Withdrawals
- **Secure**: Standard processing, 1 USDC min, all assets
- **Fast**: USDC only, 4 USDC min, `POST /api/v1/fastwithdraw`
- Both route to original L1 address

### Transfers
- Between Lighter accounts, 1 USDC min
- L1 signature required for different L1 addresses

---

## Partner Integration (Integrator Fees)

- Permissionless: clients approve partners via `ApproveIntegrator` tx
- Max 4 approved partners per client
- Fee: `trade_size * (fee_value / 1e6)` (500 = 5 bps)
- Perp fees in USDC; spot fees in received asset
- Orders include: `IntegratorAccountIndex`, `IntegratorMakerFee`, `IntegratorTakerFee`

---

## Communication Channels

- Telegram API Updates: `https://t.me/+4OylVDvI0z9lZDFk`
- Discord: `https://discord.gg/lighterxyz`
- Historical data (S3): contact Discord #support
