---
name: upbit
version: 0.9.2
description: |
  Use upbit CLI for Upbit REST API — spot orders, market data, withdrawals, deposits, travel rule, account management.
  업비트 CLI로 시세 조회, 주문, 잔고 확인, 입출금을 처리합니다.

  Trigger this skill whenever the user wants to query prices, place/cancel orders, check balances, withdraw or deposit assets, or interact with the Upbit exchange API — in any language.
  사용자가 업비트 시세·주문·잔고·입출금을 언급하면 반드시 이 스킬을 사용하세요.
delivery: script
metadata:
  starchild:
    emoji: "🪙"
    skillKey: upbit
    requires:
      env:
        - UPBIT_ACCESS_KEY
        - UPBIT_SECRET_KEY

user-invocable: false
disable-model-invocation: false

---

# Upbit Skill

Use the `upbit` CLI binary for all Upbit REST API interactions.

## ⚠️ Onboarding — when credentials are missing

When `UPBIT_ACCESS_KEY` / `UPBIT_SECRET_KEY` are not set, or an authenticated command returns 401:

**In a single turn, do ALL of the following in this exact order:**

1. Call `bash("curl -s https://api.ipify.org")` to get the outbound IP.
2. Write the setup instructions below in your reply text (substitute `<ip>` with the real IP from step 1):

---

### Step 1 — Allowlist this IP on Upbit
Upbit only accepts API calls from IP addresses you explicitly allow. Add this IP:
```
<ip>
```

### Step 2 — Create an API key
1. Log in to [upbit.com](https://upbit.com) → profile → **API 관리** (API Management)
2. Click **API 키 발급** (Issue API Key)
3. When prompted for an IP, paste `<ip>`
4. Enable scopes:
   - **자산조회** (View assets) — always required
   - **주문조회** (View orders) — required
   - **주문생성** (Place orders) — required to trade
   - **출금** (Withdraw) — only if you want withdrawal support
5. Complete 2FA + email verification, then copy your **Access Key** and **Secret Key**

### Step 3 — Enter your keys
Enter your Access Key and Secret Key in the secure input card below.

---

## Language Behavior

Detect the user's language and respond accordingly:

- **Korean user**: respond in Korean, use Korean terminology from `references/glossary.md` (e.g., 주문, 매수, 잔고, 체결, 호가)
- **English user**: respond in English, use English terminology from the same glossary
- **Mixed/ambiguous**: follow the language of the most recent message

When explaining API fields or command output, always translate field names into the user's language using the glossary. For example, if the user asks in Korean, explain `bid` as "매수", `ask` as "매도", `balance` as "보유 잔고".

Load `references/glossary.md` when translating terminology or explaining response fields.

## Setup

If `upbit` is not installed or credentials are not configured, load `references/setup.md` and follow the steps there.

Check if `upbit` is available:

```bash
upbit --version
```

## Authentication

Private endpoints require credentials. Configure via the CLI (recommended):

```bash
upbit config set
```

Credentials are saved to `~/.upbit/config` and automatically used for all CLI commands.

Alternatively, set via environment variables:

```bash
export UPBIT_ACCESS_KEY=<your-access-key>
export UPBIT_SECRET_KEY=<your-secret-key>
```

Or pass inline per command:

```bash
upbit <resource> <command> --access-key <key> --secret-key <secret>
```

**Private** (require auth): `accounts`, `api-keys`, `orders`, `withdraws`, `deposits`, `travel-rule`, `wallet-status`
**Public** (no auth): `tickers`, `orderbooks`, `trades`, `candles`, `trading-pairs`

## Safety Rule — Write Operations

Before executing any write operation, show the full command and ask the user to type `CONFIRM`.

Write operations:
- `orders create`, `orders cancel`, `orders cancel-and-new`, `orders cancel-by-uuids`, `orders cancel-open`
- `withdraws create-withdrawal`, `withdraws create-krw-withdrawal`, `withdraws cancel-withdrawal`
- `deposits deposit-krw`, `deposits create-coin-address`
- `travel-rule verify-deposit-by-txid`, `travel-rule verify-deposit-by-uuid`

`orders test-create` is a dry-run — no CONFIRM needed.

## Upbit Domain Concepts

### Market Pair Format

- Field name: `market`
- Format: `{QUOTE}-{BASE}` — quote currency first, base asset second
- Delimiter: hyphen (`-`), not slash (`/`)
- Always uppercase
- Quote currencies: `KRW`, `BTC`, `USDT`
- **Not** `{BASE}-{QUOTE}` or `{BASE}/{QUOTE}` — Upbit reverses the conventional order used by most exchanges

| Market | Meaning |
|---|---|
| `KRW-BTC` | BTC priced in KRW; Upbit uses `KRW-BTC`, not `BTC/KRW` or `BTC-KRW` |
| `KRW-ETH` | ETH priced in KRW |
| `KRW-XRP` | XRP priced in KRW |
| `BTC-ETH` | ETH priced in BTC |
| `USDT-XRP` | XRP priced in USDT |

### Account Balance Fields

Each entry from `accounts list`:

| Field | Description |
|---|---|
| `currency` | Asset code (e.g., `KRW`, `BTC`, `ETH`) |
| `balance` | Available balance (not in any open order) |
| `locked` | Balance currently locked in open orders or withdrawals |
| `avg_buy_price` | Average purchase price (decimal string) |
| `unit_currency` | Currency `avg_buy_price` is denominated in (e.g., `KRW`, `BTC`) |

Total holdings = `balance` + `locked`

### Order Types (`ord_type`)

| `ord_type` | Description | Required | Must NOT set |
|---|---|---|---|
| `limit` | Limit order at specified price | `price`, `volume` | — |
| `price` | Market buy — spend a fixed quote amount | `price` | `volume` |
| `market` | Market sell — sell a fixed base amount | `volume` | `price` |
| `best` | Best available price (see rules below) | see below | see below |

**`best` order rules**:
- `time_in_force` must be `ioc` or `fok` (NOT `post_only`)
- If `side=bid` (buy): requires `price`, must omit `volume`
- If `side=ask` (sell): requires `volume`, must omit `price`

**`post_only` + `smp_type` conflict**: these two are mutually exclusive — do not set both.

### Side Values

| `side` | Meaning |
|---|---|
| `bid` | Buy |
| `ask` | Sell |

### Order States

| State | Meaning |
|---|---|
| `wait` | Pending execution |
| `watch` | Pending reservation (stop order) |
| `done` | Fully executed |
| `cancel` | Cancelled |

### Order Fee Fields

| Field | Description |
|---|---|
| `reserved_fee` | Total fee reserved when order was placed |
| `paid_fee` | Fee already charged (for partial fills) |
| `remaining_fee` | `reserved_fee - paid_fee` |
| `locked` | Amount locked for this order (quote currency for buys, base asset for sells) |

### First-Time Order Placement

Before placing an order on an unfamiliar market, run `orders retrieve-chance` to confirm:
- Minimum order amount (`bid.min_total`, `ask.min_total`)
- Supported order types (`bid_types`, `ask_types`)
- Fee rates (`bid_fee`, `ask_fee`, `maker_bid_fee`, `maker_ask_fee`)

```bash
upbit orders retrieve-chance --market "KRW-BTC"
```

### Withdrawal — Multi-Chain Assets

For assets available on multiple networks (e.g., USDT), `net_type` is required to specify the blockchain. Use `withdraws list-coin-addresses` to see supported networks and addresses before withdrawing:

```bash
upbit withdraws list-coin-addresses --currency "USDT"
```

### Withdrawal — Secondary Address

Some assets require a secondary address (Destination Tag, Memo, etc.) in addition to the main address. Always check the registered address via `withdraws list-coin-addresses` to see if `secondary_address` is present before sending.

### Withdrawal — Address Not Registered (`withdraw_address_not_registered`)

When `withdraws create-withdrawal` returns a 400 error with `name: withdraw_address_not_registered`, the address has not been registered in the Upbit Open API withdrawal allowlist.

To register a withdrawal address, visit the allowlist management page for your environment:

| Environment | URL |
|---|---|
| KR | https://www.upbit.com/mypage/open_api_management/withdraw_access_register |
| SG | https://sg.upbit.com/mypage/open_api_management/withdraw_access_register |
| ID | https://id.upbit.com/mypage/open_api_management/withdraw_access_register |
| TH | https://th.upbit.com/mypage/open_api_management/withdraw_access_register |

After registering, run `withdraws list-coin-addresses` to confirm the address appears before retrying.

### Deposit / Withdraw States

| State | Meaning |
|---|---|
| `PROCESSING` | In progress |
| `ACCEPTED` | Completed |
| `CANCELLED` | Cancelled |
| `REJECTED` | Rejected |
| `TRAVEL_RULE_SUSPECTED` | Awaiting Travel Rule verification |
| `REFUNDING` | Refund in progress |
| `REFUNDED` | Refund completed |

When a deposit is in `TRAVEL_RULE_SUSPECTED` state, use `travel-rule` commands to verify.

### Wallet Status

`wallet-status list` returns per-asset network status:

| `wallet_state` | Meaning |
|---|---|
| `working` | Both deposits and withdrawals available |
| `withdraw_only` | Deposits suspended |
| `deposit_only` | Withdrawals suspended |
| `paused` | Both suspended |
| `unsupported` | Not supported |

### Candle Units & Limits

- Minute candles: supported units are `1, 3, 5, 10, 15, 30, 60, 240` only
- Second candles: data retention is 3 months maximum (older queries return empty array)
- `count`: default 1, max 200 per request

### Trade Pagination

- `count`: max 500 per request
- `cursor`: pass `sequential_id` from last result to page forward
- `days_ago`: integer 1–7 (UTC-based day offset)

### Ticker Key Fields

| Field | Description |
|---|---|
| `trade_price` | Current (last) price |
| `acc_trade_price_24h` | 24-hour accumulated trade value |
| `acc_trade_volume_24h` | 24-hour accumulated trade volume |
| `change` | `RISE`, `EVEN`, or `FALL` vs. previous day close |
| `signed_change_price` | Signed absolute change (negative if falling) |
| `highest_52_week_price` / `lowest_52_week_price` | 52-week range |

### Price Direction Enum (`change`, `ask_bid`)

| `change` value | Meaning |
|---|---|
| `RISE` | Price higher than previous close |
| `EVEN` | Same as previous close |
| `FALL` | Price lower than previous close |

| `ask_bid` value | Meaning |
|---|---|
| `ASK` | Trade initiated by a sell order |
| `BID` | Trade initiated by a buy order |

### Units & Formats

| Value | Unit | Format |
|---|---|---|
| `volume` | Base asset quantity | Decimal string (e.g., `"0.01"`) |
| `price` (limit) | Per-unit price in quote currency | Decimal string (e.g., `"140000000"`) |
| `price` (market buy) | Total quote amount to spend | Decimal string (e.g., `"10000"`) |
| Fee fields | Quote currency amount | Decimal string |
| `timestamp` | Milliseconds since epoch | Integer |
| `created_at` / `done_at` | ISO 8601 with KST offset | String (e.g., `2024-01-01T09:00:00+09:00`) |
| `trade_date` | UTC date | String `yyyyMMdd` |
| `trade_time` | UTC time | String `HHmmss` (24-hour) |
| Fee rates | Decimal (0.05% = `"0.0005"`) | Decimal string |

Day boundaries (opening_price, acc_trade_price, etc.) are based on **UTC 00:00**, not KST.

## Command Reference

When you need detailed flag information for a resource, read the corresponding reference file.

| Resource | Subcommands | Reference |
|---|---|---|
| `orders` | create, test-create, retrieve, list-open, list-closed, list-by-uuids, cancel, cancel-and-new, cancel-by-uuids, cancel-open, retrieve-chance | [`references/orders.md`](references/orders.md) |
| `tickers` | list-by-quote-currencies, list-by-trading-pairs | [`references/tickers.md`](references/tickers.md) |
| `candles` | list-minutes, list-days, list-weeks, list-months, list-years, list-seconds | [`references/candles.md`](references/candles.md) |
| `orderbooks` | list, list-instruments | [`references/orderbooks.md`](references/orderbooks.md) |
| `trades` | list | [`references/trades.md`](references/trades.md) |
| `trading-pairs` | list | [`references/trading-pairs.md`](references/trading-pairs.md) |
| `withdraws` | retrieve, list, cancel-withdrawal, create-withdrawal, create-krw-withdrawal, list-coin-addresses, retrieve-chance | [`references/withdraws.md`](references/withdraws.md) |
| `deposits` | retrieve, list, create-coin-address, deposit-krw, list-coin-addresses, retrieve-chance, retrieve-coin-address | [`references/deposits.md`](references/deposits.md) |
| `travel-rule` | list-vasps, verify-deposit-by-txid, verify-deposit-by-uuid | [`references/travel-rule.md`](references/travel-rule.md) |
| `accounts` / `api-keys` / `wallet-status` | list | [`references/account.md`](references/account.md) |
| Output & Filtering | --format, --transform, GJSON, debug, auto-paging | [`references/output.md`](references/output.md) |
| Korean ↔ English Glossary | Term translations, field name Korean ↔ English mapping | [`references/glossary.md`](references/glossary.md) |
| CLI Setup & Credentials | Installation, environment selection, API key setup, config set | [`references/setup.md`](references/setup.md) |

For flags not listed in reference files, run: `upbit <resource> <command> --help`

## Environment

```bash
upbit accounts list                   # kr (default)
upbit accounts list --environment sg  # sg | id | th
upbit accounts list --base-url <url>  # custom base URL
```
