---
name: kalshi
version: 1.0.3
description: >-
  Kalshi US-regulated prediction markets — binary event contracts on politics, economy, sports, weather (CPI, elections).
allowed-tools: Bash, Read, Write, WebFetch
homepage: https://kalshi.com
metadata:
  openclaw:
    emoji: "🎯"
    requires:
      env:
        - KALSHI_ACCESS_KEY
        - KALSHI_PRIVATE_KEY
    primaryEnv: KALSHI_ACCESS_KEY
    homepage: https://kalshi.com
    tags:
      - prediction-market
      - event-contracts
      - binary-options
      - trading
      - orderbook
      - politics
      - economics
      - weather
      - sports
      - crypto
      - implied-probability
      - cftc-regulated
      - elections
      - forecasting

---

# Kalshi API

Trade and query the first CFTC-regulated prediction market exchange. Binary yes/no contracts on real-world events priced 1-99 cents.

**Base URL:** `https://external-api.kalshi.com/trade-api/v2`
**Demo URL:** `https://external-api.demo.kalshi.co/trade-api/v2`

Get your API key at https://kalshi.com/account/api-keys (Premier or Market Maker tier required)

## When to use

Kalshi prediction markets: binary event contracts on politics, economy, sports, weather.

Use when trading or browsing US regulated event markets (e.g. CPI above 3%, NHL Edmonton vs Florida, jobs report > 200k, election odds).

## Key Concepts

### Hierarchy: Series > Events > Markets

- **Series** — recurring event templates (e.g., "Monthly Jobs Report", "Weekly Jobless Claims")
- **Events** — specific instances within a series (e.g., "May 2026 Jobs Report")
- **Markets** — individual binary outcomes within an event (e.g., "Will jobs added be above 200k?")

### Binary Contract Pricing

- Prices are in **cents** (1-99), representing implied probability
- A Yes contract at 65c = market implies 65% probability
- Yes bid at price X is equivalent to No ask at (100 - X) — orderbooks show Yes bids and No bids only
- Settlement: pays $1.00 (100 cents) if Yes, $0 if No
- **All monetary values (balance, prices, settlements) are in cents**

### Ticker Format

- **Series:** `KXBTC`, `KXJOBLESS`, `KXINX`
- **Event:** `KXBTC-25MAY30` (series + date)
- **Market:** `KXBTC-25MAY30-T100000` (event + threshold/outcome)

**Sports game tickers** follow a different pattern: `{SERIES}-{YYMONDD}{TEAM1}{TEAM2}-{TEAM}`
- Example: `KXNHLGAME-25MAY12EDMORL-EDM` (NHL, May 12 2025, Edmonton vs Orlando, Edmonton to win)
- Each game event has **two mutually exclusive YES markets** — one per team

### CRITICAL: Series-Based Market Navigation

**DO NOT use `/markets?keyword=` for sports, elections, or any series-based category.** It only surfaces multi-game parlay bundles, not actual game-level markets. Searching "NHL", "Fulham", "Premier League" etc. returns zero or irrelevant results.

**Always navigate: Series → Events → Markets.** Game-level markets live under the series/event hierarchy and must be accessed via `/events?series_ticker=KXXX`. Also, `/markets/{ticker}` may return 404 for game markets — bid/ask prices only appear in the event endpoint response (`/events/{event_ticker}` with `with_nested_markets=true`).

This pattern applies to **all series-based categories**, not just sports:
- **Sports games** — NHL, NBA, NFL, MLB, EPL, etc.
- **Political races** — individual candidate markets within multi-candidate events
- **Company-specific markets** — earnings, CEO changes within a series
- **Recurring economic data** — jobs reports, jobless claims, CPI, etc.

**Known Sports Series Tickers:**

| Sport | Series Ticker | Example |
|-------|---------------|---------|
| NHL | `KXNHLGAME` | `KXNHLGAME-25MAY12EDMORL` |
| NBA | `KXNBAGAME` | `KXNBAGAME-25MAY12BOSLAL` |
| NFL | `KXNFLGAME` | `KXNFLGAME-25SEP07KCDET` |
| MLB | `KXMLBGAME` | `KXMLBGAME-25MAY12NYYLAD` |
| EPL (Premier League) | `KXEPLGAME` | `KXEPLGAME-25MAY12FULARS` |

**Correct workflow for sports:**
```bash
# 1. List open games for a sport
curl -s "https://external-api.kalshi.com/trade-api/v2/events?series_ticker=KXNHLGAME&status=open&with_nested_markets=true"

# 2. Get specific game with live bid/ask
curl -s "https://external-api.kalshi.com/trade-api/v2/events/KXNHLGAME-25MAY12EDMORL?with_nested_markets=true"

# WRONG — do not do this:
# curl -s "https://external-api.kalshi.com/trade-api/v2/markets?keyword=NHL"  ← returns parlays, not games
```

## How to Call

Kalshi uses **RSA key-pair signature authentication**. Three headers are required on authenticated requests:

| Header | Value |
|--------|-------|
| `KALSHI-ACCESS-KEY` | API key ID (`$KALSHI_ACCESS_KEY`) |
| `KALSHI-ACCESS-SIGNATURE` | RSA-PSS signature of `timestamp + method + path` |
| `KALSHI-ACCESS-TIMESTAMP` | Unix timestamp (ms) |

**Public GET endpoints** (markets, events, orderbooks) can be called without auth headers.

```bash
# Public endpoint — no auth needed
curl -s "https://external-api.kalshi.com/trade-api/v2/markets?limit=10&status=open"
```

For authenticated endpoints, use direct RSA-PSS signing (**not** the `kalshi_python` SDK — it doesn't work):

```python
import os, time, base64, requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from dotenv import load_dotenv
load_dotenv('/data/workspace/.env')

BASE_URL = "https://api.elections.kalshi.com"

def kalshi_headers(method: str, path: str) -> dict:
    import re
    raw = os.environ["KALSHI_PRIVATE_KEY"]
    # Decode literal escape sequences first (some input channels save '\n' as
    # two chars backslash+n instead of a real newline).
    raw = (raw.replace('\\r\\n', '\n').replace('\\n', '\n')
              .replace('\\r', '\n').replace('\\t', ' '))
    # Strip PEM markers if present, then strip ALL whitespace and rewrap.
    body = re.sub(r'-----BEGIN[^-]+-----', '', raw)
    body = re.sub(r'-----END[^-]+-----', '', body)
    body = re.sub(r'\s+', '', body)
    wrapped = '\n'.join(body[i:i+64] for i in range(0, len(body), 64))
    pem = f"-----BEGIN RSA PRIVATE KEY-----\n{wrapped}\n-----END RSA PRIVATE KEY-----\n"
    private_key = serialization.load_pem_private_key(pem.encode(), password=None, backend=default_backend())
    ts = str(int(time.time() * 1000))
    msg = (ts + method + path).encode()  # path must NOT include query string
    sig = private_key.sign(msg, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH), hashes.SHA256())
    return {
        "KALSHI-ACCESS-KEY": os.environ["KALSHI_ACCESS_KEY"].strip(),
        "KALSHI-ACCESS-TIMESTAMP": ts,
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode(),
        "Content-Type": "application/json"
    }

path = "/trade-api/v2/portfolio/balance"
resp = requests.get(BASE_URL + path, headers=kalshi_headers("GET", path))
print(resp.json())  # {"balance": 5000, ...} — balance is in cents
```

**Signing gotchas:**
- **PSS not PKCS1v15** — PKCS1v15 padding returns 401. Must use PSS with SHA256.
- **Strip query strings before signing** — signature is computed on the bare path only (e.g. `/trade-api/v2/portfolio/balance`), not `/trade-api/v2/portfolio/balance?param=value`. Including query string will 401.
- **Key env var format** — `KALSHI_PRIVATE_KEY` accepts any of: raw base64 body, full PEM with real newlines, or full PEM with newlines collapsed to whitespace (common when pasted through web forms). The helper normalises all formats automatically. For the most robust storage, save as a double-quoted multi-line PEM with `\n` escapes in `.env` so python-dotenv rehydrates it to a real PEM string.

### API Spec

Full OpenAPI spec: https://docs.kalshi.com/openapi.yaml

## Intent Routing

Map user intent to the right endpoint. All paths are relative to the base URL.

### Events
| Method | Endpoint | Primary Params | Description |
|--------|----------|----------------|-------------|
| GET | `/events` | `limit` (1-200), `cursor`, `status`, `series_ticker`, `with_nested_markets` | List events (excludes multivariate) |
| GET | `/events/{event_ticker}` | `event_ticker`, `with_nested_markets` | Get specific event |
| GET | `/events/{event_ticker}/metadata` | `event_ticker` | Event metadata only |
| GET | `/events/multivariate` | `limit`, `cursor`, `series_ticker`, `collection_ticker`, `with_nested_markets` | List multivariate (combo) events |

### Markets
| Method | Endpoint | Primary Params | Description |
|--------|----------|----------------|-------------|
| GET | `/markets` | `limit`, `cursor`, `status`, `ticker`, `event_ticker`, `series_ticker`, `min_close_ts`, `max_close_ts` | List/filter markets |
| GET | `/markets/{ticker}` | `ticker` | Get specific market details |
| GET | `/markets/{ticker}/orderbook` | `ticker`, `depth` | Current orderbook (yes bids + no bids) |
| GET | `/markets/orderbooks` | `tickers` (array, max 100) | Batch orderbooks |
| GET | `/markets/trades` | `ticker`, `limit`, `cursor`, `min_ts`, `max_ts` | Trades across markets |

### Candlesticks
| Method | Endpoint | Primary Params | Description |
|--------|----------|----------------|-------------|
| GET | `/series/{series_ticker}/markets/{ticker}/candlesticks` | `series_ticker`, `ticker`, `start_ts`, `end_ts`, `period_interval` | Market-level candles |
| GET | `/series/{series_ticker}/events/{ticker}/candlesticks` | `series_ticker`, `ticker`, `start_ts`, `end_ts`, `period_interval` | Aggregated event-level candles |
| GET | `/markets/candlesticks` | `market_tickers`, `start_ts`, `end_ts`, `period_interval` | Batch candlesticks |

`period_interval` values: `1` (1 min), `60` (1 hour), `1440` (1 day)

### Forecast & Live Data
| Method | Endpoint | Primary Params | Description |
|--------|----------|----------------|-------------|
| GET | `/series/{series_ticker}/events/{ticker}/forecast_percentile_history` | `percentiles` (0-10000), `start_ts`, `end_ts`, `period_interval` | Historical forecast percentiles |
| GET | `/live_data/milestone/{milestone_id}` | `milestone_id`, `include_player_stats` | Live milestone data |
| GET | `/live_data/batch` | `milestone_ids` (array, max 100), `include_player_stats` | Batch live data |
| GET | `/live_data/game-stats/{milestone_id}` | `milestone_id` | Play-by-play stats (football, basketball, soccer, hockey, baseball) |

### Series
| Method | Endpoint | Primary Params | Description |
|--------|----------|----------------|-------------|
| GET | `/series/{series_ticker}` | `series_ticker`, `include_volume` | Get series template |
| GET | `/series` | `category`, `tags`, `include_volume`, `min_updated_ts` | List all series |

### Exchange Info
| Method | Endpoint | Primary Params | Description |
|--------|----------|----------------|-------------|
| GET | `/exchange/status` | — | Current exchange status |
| GET | `/exchange/schedule` | — | Operating hours |
| GET | `/exchange/announcements` | — | Platform announcements |
| GET | `/exchange/user_data_timestamp` | — | Data sync timestamp |
| GET | `/series/fee_changes` | `series_ticker`, `show_historical` | Fee change history |

### Search & Discovery
| Method | Endpoint | Primary Params | Description |
|--------|----------|----------------|-------------|
| GET | `/search/tags_by_categories` | — | Tags organized by series categories |
| GET | `/search/filters_by_sport` | — | Filters organized by sport |

### Orders (Authenticated)
| Method | Endpoint | Primary Params | Description |
|--------|----------|----------------|-------------|
| GET | `/portfolio/orders` | `ticker`, `event_ticker`, `status`, `limit`, `cursor`, `subaccount` | List user orders |
| GET | `/portfolio/orders/{order_id}` | `order_id` | Get specific order |
| POST | `/portfolio/orders` | Body: `ticker`, `action`, `side`, `type`, `count`, `yes_price`/`no_price` | Create order |
| DELETE | `/portfolio/orders/{order_id}` | `order_id`, `subaccount` | Cancel order |
| POST | `/portfolio/orders/{order_id}/amend` | `order_id`, Body: new `count`/`price` | Amend order |
| POST | `/portfolio/orders/{order_id}/decrease` | `order_id`, Body: reduction amount | Decrease order count |
| POST | `/portfolio/orders/batched` | Body: array of orders | Batch create (max size scales with tier) |
| DELETE | `/portfolio/orders/batched` | Body: array of order IDs | Batch cancel |
| GET | `/portfolio/orders/queue_positions` | `market_tickers`, `event_ticker`, `subaccount` | All resting order queue positions |
| GET | `/portfolio/orders/{order_id}/queue_position` | `order_id` | Specific order queue position |

### Orders V2 — Event-Market Orders (Authenticated, Fixed-Point)
| Method | Endpoint | Primary Params | Description |
|--------|----------|----------------|-------------|
| POST | `/portfolio/events/orders` | Body: event ticker, market side, price (fixed-point), count | Create V2 order |
| POST | `/portfolio/events/orders/batched` | Body: array of V2 orders | Batch create V2 |
| DELETE | `/portfolio/events/orders/{order_id}` | `order_id`, `subaccount` | Cancel V2 order |
| DELETE | `/portfolio/events/orders/batched` | Body: array of order IDs | Batch cancel V2 |
| POST | `/portfolio/events/orders/{order_id}/amend` | `order_id`, Body: new count/price | Amend V2 order |
| POST | `/portfolio/events/orders/{order_id}/decrease` | `order_id`, Body: new remaining count | Decrease V2 order |

### Order Groups (Authenticated)
| Method | Endpoint | Primary Params | Description |
|--------|----------|----------------|-------------|
| GET | `/portfolio/order_groups` | `subaccount` | List all order groups |
| POST | `/portfolio/order_groups/create` | Body: contracts limit | Create order group |
| GET | `/portfolio/order_groups/{id}` | `id`, `subaccount` | Get specific group |
| DELETE | `/portfolio/order_groups/{id}` | `id`, `subaccount` | Delete group & cancel all orders |
| PUT | `/portfolio/order_groups/{id}/limit` | `id`, Body: new limit | Update contracts limit |
| PUT | `/portfolio/order_groups/{id}/trigger` | `id`, `subaccount` | Trigger group (cancel all orders) |
| PUT | `/portfolio/order_groups/{id}/reset` | `id`, `subaccount` | Reset matched contracts counter |

### Portfolio (Authenticated)
| Method | Endpoint | Primary Params | Description |
|--------|----------|----------------|-------------|
| GET | `/portfolio/balance` | `subaccount` | Balance & portfolio value (in cents) |
| GET | `/portfolio/positions` | `cursor`, `limit`, `count_filter`, `ticker`, `event_ticker`, `subaccount` | User positions |
| GET | `/portfolio/fills` | `ticker`, `order_id`, `min_ts`, `max_ts`, `limit`, `cursor`, `subaccount` | All trade fills |
| GET | `/portfolio/settlements` | `limit`, `cursor`, `ticker`, `event_ticker`, `min_ts`, `max_ts`, `subaccount` | Settlement history |
| GET | `/portfolio/deposits` | `limit`, `cursor` | Deposit history |
| GET | `/portfolio/withdrawals` | `limit`, `cursor` | Withdrawal history |
| GET | `/portfolio/summary/total_resting_order_value` | — | Total resting order value (FCM only) |

### Subaccounts (Authenticated — Institutions/Market Makers)
| Method | Endpoint | Primary Params | Description |
|--------|----------|----------------|-------------|
| POST | `/portfolio/subaccounts` | — | Create subaccount (max 32) |
| POST | `/portfolio/subaccounts/transfer` | Body: from, to, amount | Transfer between subaccounts |
| GET | `/portfolio/subaccounts/balances` | — | All subaccount balances |
| GET | `/portfolio/subaccounts/transfers` | `limit`, `cursor` | Transfer history |
| GET | `/portfolio/subaccounts/netting` | — | Netting settings |
| PUT | `/portfolio/subaccounts/netting` | Body: subaccount, enabled | Update netting |

### RFQ — Request for Quote (Authenticated)
| Method | Endpoint | Primary Params | Description |
|--------|----------|----------------|-------------|
| GET | `/communications/rfqs` | `cursor`, `limit` (1-100), `event_ticker`, `market_ticker`, `status`, `user_filter` | List RFQs |
| POST | `/communications/rfqs` | Body: market ticker, side, count | Create RFQ (max 100 open) |
| GET | `/communications/rfqs/{rfq_id}` | `rfq_id` | Get specific RFQ |
| DELETE | `/communications/rfqs/{rfq_id}` | `rfq_id` | Delete RFQ |
| GET | `/communications/quotes` | `cursor`, `limit` (1-500), `event_ticker`, `market_ticker`, `status`, `rfq_id` | List quotes |
| POST | `/communications/quotes` | Body: RFQ ID, side, price, count | Create quote response |
| GET | `/communications/quotes/{quote_id}` | `quote_id` | Get specific quote |
| DELETE | `/communications/quotes/{quote_id}` | `quote_id` | Delete quote |
| PUT | `/communications/quotes/{quote_id}/accept` | `quote_id` | Accept quote |
| PUT | `/communications/quotes/{quote_id}/confirm` | `quote_id` | Confirm quote (starts execution timer) |
| GET | `/communications/id` | — | Get user's communications ID |

### API Keys (Authenticated)
| Method | Endpoint | Primary Params | Description |
|--------|----------|----------------|-------------|
| GET | `/api_keys` | — | List all API keys |
| POST | `/api_keys` | Body: public key, name | Create key with user RSA public key |
| POST | `/api_keys/generate` | Body: name | Generate key pair automatically |
| DELETE | `/api_keys/{api_key}` | `api_key` | Delete API key |

### Account (Authenticated)
| Method | Endpoint | Primary Params | Description |
|--------|----------|----------------|-------------|
| GET | `/account/limits` | — | API tier rate limits |
| GET | `/account/endpoint_costs` | — | Non-default endpoint token costs |

### Historical Data
| Method | Endpoint | Primary Params | Description |
|--------|----------|----------------|-------------|
| GET | `/historical/cutoff-timestamps` | — | Boundary between live and historical data |
| GET | `/historical/markets/{ticker}` | `ticker` | Specific historical market |
| GET | `/historical/markets` | mutually exclusive filters | Historical markets |
| GET | `/historical/markets/{ticker}/candlesticks` | `ticker`, `start_ts`, `end_ts`, `period_interval` | Archived candlesticks |
| GET | `/historical/orders` | filters | Archived orders |
| GET | `/historical/fills` | filters | All historical fills |
| GET | `/historical/trades` | filters | All historical trades |

### Milestones & Structured Targets
| Method | Endpoint | Primary Params | Description |
|--------|----------|----------------|-------------|
| GET | `/milestones/{id}` | `id` | Specific milestone |
| GET | `/milestones` | RFC3339 start date filters | List milestones |
| GET | `/structured-targets/{id}` | `id` | Specific structured target |
| GET | `/structured-targets` | pagination (max 2000) | List targets |

### Multivariate Collections
| Method | Endpoint | Primary Params | Description |
|--------|----------|----------------|-------------|
| GET | `/multivariate/collections` | — | List multivariate event collections |
| GET | `/multivariate/collections/{ticker}` | `ticker` | Specific collection |
| POST | `/multivariate/collections/{ticker}/markets` | `ticker`, Body: market params | Create market in collection (5000/week limit) |

### Incentives
| Method | Endpoint | Primary Params | Description |
|--------|----------|----------------|-------------|
| GET | `/incentives` | optional filters | List incentive programs |

## Rate Limits

Token-based system that scales by API tier (Standard, Premier, Market Maker).

| Endpoint Type | Default Cost |
|---------------|-------------|
| Most endpoints | 10 tokens |
| GetOrder | 2 tokens |
| CancelOrder | 2 tokens |
| CreateQuote / DeleteQuote | 2 tokens |
| Batch operations | N x per-item cost |

Check your limits with `GET /account/limits`. Batch operation max size scales with your tier's write budget.

## Pagination

All list endpoints use **cursor-based pagination**. The response includes a `cursor` field — pass it back as a query param to get the next page.

| Param | Description |
|-------|-------------|
| `limit` | Max results per page (varies by endpoint, typically 1-200) |
| `cursor` | Opaque cursor from previous response for next page |

## WebSocket Channels

WebSocket connection at `wss://external-api.kalshi.com/trade-api/ws/v2` (auth required at handshake).

**Public channels:**
- Market Ticker — price, volume, open interest updates
- Public Trades — trade notifications
- Market & Event Lifecycle — state changes, new markets/events
- Multivariate Market & Event Lifecycle — MVE state changes

**Authenticated channels:**
- User Orders — order created/updated notifications
- User Fills — fill notifications
- Market Positions — real-time position updates
- Order Group Updates — lifecycle and limit notifications
- Communications — RFQ and quote notifications
- Orderbook Updates — incremental price level changes

## Order Fields Reference

| Field | Values | Description |
|-------|--------|-------------|
| `action` | `buy`, `sell` | Buy or sell contracts |
| `side` | `yes`, `no` | Which outcome side |
| `type` | `limit`, `market` | Order type |
| `count` | integer | Number of contracts |
| `yes_price` | 1-99 (cents) | Price for yes side |
| `no_price` | 1-99 (cents) | Price for no side |
| `expiration_ts` | unix timestamp | Optional order expiration |
| `sell_position_floor` | integer | Min position to keep when selling |
| `buy_max_cost` | integer (cents) | Max total cost for market buys |

## Safety Notes

- **All prices are in cents** (1-99). A price of 65 means $0.65 per contract, NOT $65.
- **Balance is in cents.** 10000 = $100.00.
- `POST /portfolio/orders` submits real orders on production. Always verify ticker, side, and price before placing.
- Batch operations execute atomically — all succeed or all fail.
- **Demo environment** available at `https://external-api.demo.kalshi.co/trade-api/v2` for risk-free testing.
- Before placing orders, always confirm the market ticker, current price, and position size with the user.
- Max 200,000 open orders per user.

## Known Limitations

- **`/markets?keyword=` misses series-based markets** — sports games, political races, and other series-based categories are invisible to keyword search. Always navigate via `/events?series_ticker=`. See "CRITICAL: Series-Based Market Navigation" above.
- **`/markets/{ticker}` returns 404 for game markets** — bid/ask prices for sports and similar markets only appear in the event endpoint response. Use `/events/{event_ticker}?with_nested_markets=true` instead.
- **RSA signing required** for authenticated endpoints — cannot use simple API key header like most REST APIs. Use the official Python/TypeScript SDK for signing.
- **Binary markets only** — no multi-outcome contracts (except via multivariate events)
- **US-regulated** — trading available to eligible US residents only
- **Market hours** — markets have defined close times, check `close_ts` before trading
- **Historical data split** — older data requires `/historical/*` endpoints, check `/historical/cutoff-timestamps` for the boundary
- **V1 vs V2 order endpoints** — V2 uses fixed-point format, V1 uses cents. Both work but V2 is recommended for new integrations.
- **Subaccounts** — only available to institutions and market makers (max 32 per user)
- **RFQ limit** — max 100 open RFQs at a time
- **Multivariate market creation** — max 5000 per week per collection
