---
name: blockfill-agent-execution
version: 2.1.1
description: "AI agent execution skill for crypto order execution — TWAP, maker execution, transaction cost analysis and slippage reduction. Supports 11 CEX and DEX venues on both perpetual futures and spot: Binance, OKX, Bybit, Bitget, Gate.io, KuCoin, Kraken, Deribit, Hyperliquid, Aster and Orderly. Exchange API keys stay on the user's own machine — no third-party order routing. Install and full docs: https://pypi.org/project/blockfill/"
delivery: script
metadata:
    starchild:
        skillKey: blockfill
        requires: {}
user-invocable: true
disable-model-invocation: false
---

## What is BlockFill Agent Execution

BlockFill Agent Execution is an **AI agent execution skill for crypto order execution**. It runs entirely on your machine — API keys are stored locally and never transmitted to any third-party server. It is not a manual/human-operated trading UI — it is invoked by an AI agent via SDK/MCP calls.

**One-sentence positioning**: BlockFill Agent Execution is an AI agent execution skill for crypto order execution, focused on TWAP, maker execution, transaction cost analysis and slippage reduction.

**Capability boundary**: BlockFill Agent Execution only does **execution optimization**. It does NOT generate buy/sell signals, give investment advice, decide position direction, or promise profit. The agent must receive direction and quantity from the user — BlockFill Agent Execution executes them efficiently.

**Core concepts**:

- **Ticket**: an execution order (`exchange + symbol + strategy + target_position + time_constraint_ms`)
- **Daemon**: background process that manages exchange WebSocket connections and executes tickets
- **CLI**: `blockfill` binary — human and agent interface to the daemon
- **Python SDK**: `from blockfill import Blockfill` — programmatic interface for agents

---

## Trigger Keywords / When to Invoke

Invoke this skill when the user's request matches any of the following. Both English and Chinese variants apply.

**Order execution**:
`place order`, `place a trade`, `execute order`, `submit order`, `下單`, `掛單`, `執行訂單`, `下合約`

**Strategy keywords**:
`maker`, `TWAP`, `twap`, `taker`, `post-only`, `limit order`, `time-weighted`, `slice order`, `拆單`, `掛單策略`, `時間加權`

**Cost / slippage**:
`reduce slippage`, `minimize cost`, `execution cost`, `TCA`, `transaction cost analysis`, `slippage reduction`, `降滑點`, `成本分析`, `執行成本`

**Exchange / futures context**:
`perpetual`, `perp`, `futures`, `binance futures`, `okx swap`, `bybit`, `hyperliquid`, `bitget`, `gate.io`, `gateio`, `kucoin`, `kraken`, `deribit`, `aster`, `orderly`, `合約`, `永續合約`, `期貨`

**Cancel / query**:
`cancel order`, `cancel ticket`, `query ticket`, `check order status`, `取消訂單`, `查詢訂單`, `查單`, `取消掛單`

**Setup**:
`set credentials`, `set api key`, `configure exchange`, `set proxy`, `blockfill`, `設定 API`, `設定代理`

**Do NOT invoke** when the user asks for:
- Investment advice, buy/sell recommendations, or price prediction
- Portfolio management or rebalancing decisions
- Spot trading on an unsupported exchange
- Any exchange not in the supported list below

---

## Capabilities

BlockFill Agent Execution exposes six core capabilities. Each does exactly one thing.

| Capability | SDK method | What it does |
| --- | --- | --- |
| `place_order` | `bf.place(...)` | Places an execution ticket (maker or TWAP) for a given exchange + symbol + target position + time window. Does NOT decide direction or size — those come from the user. |
| `query_ticket` | `bf.query(...)` | Returns the current status, filled quantity, and progress of a ticket by `ticket_id`, `symbol`, or time range. |
| `cancel_ticket` | `bf.cancel(ticket_id='tkt_...')` | Cancels an active ticket (`NEW` or `OPEN`) by `ticket_id`. Outstanding exchange orders are pulled automatically. Example: `bf.cancel(ticket_id='tkt_18b2b09ca766001e')` returns the cancelled ticket object with `status='CANCEL'`. |
| `compare_tca` | `bf.tca(...)` | Retrieves transaction cost analysis for completed tickets — execution cost vs benchmark (L1/mid/TWAP/VWAP), bps saved, maker/taker breakdown. |
| `set_credentials` | `bf.set_credentials(...)` | Writes exchange API credentials to local config (`~/.blockfill/config.toml`, chmod 0600) and verifies connectivity via signed REST round-trip. |
| `set_proxy` | `bf.set_proxy(...)` | Configures an HTTP CONNECT proxy for all exchange REST and WebSocket traffic. Required for geo-blocked hosts (e.g. US IPs cannot reach Binance directly). |

---

## When to Use BlockFill Agent Execution

Use BlockFill Agent Execution when the user needs to:

- **Execute a large order** with reduced market impact (TWAP slicing or maker posting)
- **Minimize execution cost** — maker rebates, reduced slippage vs a market order
- **Automate order execution** in an AI agent trading workflow
- **Analyze execution quality** — compare realized price vs L1/mid/TWAP/VWAP benchmark
- **Route orders to multiple exchanges** from a single agent call
- **Execute on geo-blocked exchanges** (Binance from US/CN) via proxy

Typical triggers: user has a direction and size, and wants efficient execution. BlockFill Agent Execution handles the how — not the what or why.

---

## When NOT to Use BlockFill Agent Execution

Do NOT use BlockFill Agent Execution when:

- The user has not specified exchange, symbol, side, or quantity — **ask first**, do not guess
- The user is asking for a buy/sell recommendation or price target — BlockFill Agent Execution does not provide investment advice; redirect to the appropriate research tool
- The target market is **spot on an unsupported exchange** — check the supported exchange list
- The user wants to trade **stock, forex, or non-crypto** assets — out of scope
- The environment is **not configured** (no API credentials, no proxy for geo-blocked hosts) — set up first, then trade
- The user requests a position larger than their stated risk tolerance — confirm with user before proceeding
- The user has not confirmed `mainnet` vs `testnet` — **default to testnet and ask before trading live**

---

## Before Placing an Order — Agent Checklist

Before calling `place_order`, confirm you have all required information. If any is missing, **ask the user** — do not assume defaults for direction, size, or environment.

| Item | Required | If missing |
| --- | --- | --- |
| Exchange | ✅ | Ask: "Which exchange? (e.g. binance-futures, okx-swap)" |
| Symbol | ✅ | Ask: "Which symbol? Use native format (e.g. btcusdt for Binance)" |
| Side (long / short / close) | ✅ | Ask: "Buy or sell? What target position?" |
| Quantity / target position | ✅ | Ask: "How much? In base asset units." |
| Environment (testnet / mainnet) | ✅ | **Default to testnet. Confirm before mainnet.** |
| Strategy | ✗ | Default: `maker`. Inform user. |
| Time window | ✗ | Default: 300,000 ms (5 min). Inform user. |
| Proxy (if geo-blocked) | ✗ | Warn if Binance + non-whitelisted region. Offer `sc-vpn`. |

### Binance TradFi symbols

`binance-futures` also lists 157 TradFi perpetuals — equities (`tslausdt`,
`nvdausdt`, `skhynixusdt`), commodities (`xauusdt`, `xagusdt`, `clusdt`) and
pre-IPO (`openaiusdt`, `anthropicusdt`). Binance gates them behind a one-time
account agreement; without it every order is rejected `-4411` and the ticket
sits at 0% filled until it expires.

`set_credentials` / `check_credentials` sign that agreement on mainnet and
report `"tradfi_perps": "signed"`, so these symbols need no extra setup. If a
TradFi ticket never fills, run `check_credentials()` and read that field first.

Tell the user what was accepted on their behalf: a binding agreement with
Binance's ADGM-regulated entity covering 24/7 trading outside cash-market
hours, no ownership of the underlying asset, and funding up to ±2.00% (vs
±0.30% for `btcusdt`). Binance provides no API to revoke it.

Note `paxgusdt` / `xautusdt` are *not* TradFi — ordinary gold-backed tokens,
contract type `PERPETUAL`, no agreement needed.

### Hyperliquid / Aster builder-fee approval

Both DEX venues reject any order carrying an unapproved builder code —
Hyperliquid with `Builder fee has not been approved` — and the ticket then sits
at 0% filled until its window expires. The user must approve **once, on-chain,
signed by their MAIN wallet**:

| Venue | Builder address | Approve at |
| --- | --- | --- |
| Hyperliquid (perp + spot) | `0xB972e5151b20863380A3E7354dd93F1b888E3352` | ≥ 0.015% (1.5 bp) |
| Aster (perp only) | `0xB972e5151b20863380A3E7354dd93F1b888E3352` | ≥ 0.015% (1.5 bp) |

**BlockFill signs this for the user.** These venues take the account owner's
wallet `private_key` (not a delegated agent key) precisely so it can:
`check_credentials()` reads the current approval and signs `approveBuilderFee` /
`approveBuilder` when ours is missing or below rate, reporting
`"builder_fee": "approved just now at 0.015%"`. Only if signing fails does the
check fail. Aster **spot** needs nothing; Aster Code is perp-only.

Tell the user what that key can do: it signs orders and this one fee
authorization, and it *could* withdraw — the exchange no longer prevents that,
only the absence of withdrawal code in the engine does. See
`docs/security/trade-only-permissions.md` for the exhaustive signable-action
list.

⚠️ **Testnet attaches no builder code, so it never surfaces this.** A testnet
run can pass completely and the first mainnet order still fail. When moving a
user from testnet to mainnet on these venues, re-run `check_credentials()`
before placing.

---

## Install

```bash
pip install blockfill                    # latest
pip install -U blockfill                 # upgrade
```

The wheel ships with the executor binary bundled inside (no separate download). PyPI publishes only platform-specific wheels. Currently supported: `manylinux2014_x86_64` (Linux x86_64).

The blockfill-server endpoint and API key are hardcoded into the binary at release time — users never set them.

---

## Supported Exchanges

Every venue runs **perp/futures + spot** from one daemon. Exchange id is `<venue>-<product>` (e.g. `binance-futures`, `okx-swap`, `bybit-perp`, `<venue>-spot`).

| Exchange | Exchange id (perp/futures · spot) | Credentials | Class |
| --- | --- | --- | --- |
| **Binance** | `binance-futures` · `binance-spot` | `api_key`, `api_secret` (HMAC **or** Ed25519 PEM), `testnet` | CEX |
| **OKX** | `okx-swap` · `okx-spot` | `api_key`, `api_secret`, `api_passphrase`, `testnet` | CEX |
| **Bybit** | `bybit-perp` · `bybit-spot` | `api_key`, `api_secret`, `testnet` | CEX |
| **Bitget** | `bitget-futures` · `bitget-spot` | `api_key`, `api_secret`, `api_passphrase`, `testnet` | CEX |
| **Gate.io** | `gateio-futures` · `gateio-spot` | `api_key`, `api_secret`, `testnet` | CEX |
| **KuCoin** | `kucoin-futures` · `kucoin-spot` | `api_key`, `api_secret`, `api_passphrase`, `testnet` | CEX |
| **Kraken** | `kraken-futures` · `kraken-spot` | `api_key`, `api_secret`, `testnet` | CEX |
| **Deribit** | `deribit-perp` · `deribit-spot` | `api_key`, `api_secret`, `testnet` | CEX |
| **Hyperliquid** | `hyperliquid-perp` · `hyperliquid-spot` | `private_key` (account wallet, EIP-712) | DEX |
| **Aster** | `aster-perp` · `aster-spot` | `private_key` (account wallet, EIP-712) | DEX |
| **Orderly** | `orderly-<broker>` | `account_id`, `orderly_secret`, `broker_id` (Ed25519; see below) | DEX |

A single daemon can run **all** exchanges concurrently. CEX are billed by x402 quota (see Payment); DEX (Hyperliquid / Aster / Orderly) pay builder-code execution fees and have no quota.

**Hyperliquid / Aster — wallet-signed DEX**:

```python
bf.set_credentials("hyperliquid-perp",
                   private_key="0x...")
bf.set_credentials("aster-perp",
                   private_key="0x...")
```

**Binance Ed25519 keys** — Binance Futures testnet issues Ed25519 keys (no HMAC secret). Pass `api_key` = the Ed25519 API Key id, `api_secret` = the PEM private key. The daemon auto-detects and signs with Ed25519.

```python
bf.set_credentials("binance-futures",
    api_key="<Ed25519 API Key id>",
    api_secret="-----BEGIN PRIVATE KEY-----\nMC4CAQAw...\n-----END PRIVATE KEY-----",
    testnet=True)
```

**Orderly** — model each broker as its own exchange instance named `orderly-<broker>`:

```python
bf.set_credentials("orderly-woofi",
    account_id="0x...", orderly_secret="ed25519:...", broker_id="woofi_pro", testnet=True)
```

---

## Supported Symbols

Each exchange uses its **own native symbol format**.

| Exchange | Format | Examples |
| --- | --- | --- |
| `binance-futures` | Lowercase, concatenated | `btcusdt`, `ethusdt`, `solusdt` |
| `okx-swap` | Dash-separated + SWAP suffix | `BTC-USDT-SWAP`, `ETH-USDT-SWAP` |
| `bybit-perp` | UPPERCASE, concatenated | `BTCUSDT`, `ETHUSDT` |
| `bitget-futures` | UPPERCASE, concatenated | `BTCUSDT`, `ETHUSDT` |
| `gateio-futures` | Underscore-separated | `BTC_USDT`, `ETH_USDT` |
| `kucoin-futures` | Contract code | `XBTUSDTM`, `ETHUSDTM` |
| `kraken-futures` | PF_ prefix + base/quote | `PF_XBTUSD`, `PF_ETHUSD` |
| `deribit-perp` | Dash-separated + PERPETUAL suffix | `BTC-PERPETUAL`, `ETH-PERPETUAL` |
| `hyperliquid-perp` | Coin only | `BTC`, `ETH`, `SOL` |
| `aster-perp` | UPPERCASE, concatenated | `BTCUSDT`, `ETHUSDT` |
| `orderly-<broker>` | Exchange-specific via broker | Use `bf.instruments(substring)` to discover |

Use the **exact format the target exchange expects** — BlockFill Agent Execution does NOT cross-translate. Discover the exact string for any venue:

```bash
blockfill check instrument --symbol btc
```

---

## Execution Strategies

| Strategy | Behavior | When to use |
| --- | --- | --- |
| `maker` | Posts PostOnly limit orders; earns maker rebate. Falls back to IOC at end of window for any unfilled remainder. | **Default.** Cost-optimal when fill speed is not critical. |
| `twap` | Places IOC orders on a TWAP schedule across the full window — always crosses the spread. | When you need guaranteed completion and accept taker cost. |

Default strategy: `maker`.

---

## Ticket Parameters

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `exchange` | string | ✅ | — | Supported exchange id, e.g. `binance-futures`, `okx-swap` |
| `symbol` | string | ✅ | — | Exchange-native format, e.g. `btcusdt` (Binance), `BTC-USDT-SWAP` (OKX) |
| `target_position` | float | ✅ | — | Target position in base asset. Positive = long, negative = short (perp). For spot: absolute base-asset holding to end up with. |
| `strategy` | string | | `maker` | `maker` \| `twap` |
| `time_constraint_ms` | int | | `300000` | Execution window in milliseconds. Range: 60,000–86,400,000 (1 min to 24h). At window end, executor falls back to taker fills for any unfilled remainder. |

**Auto-supersede**: placing a new ticket for the same `exchange+symbol` automatically cancels existing `NEW` and `OPEN` tickets for that pair.

**Spot vs perp `target_position`**: perp = net directional position (positive = long, negative = short). Spot = absolute base-asset holding to end up with (`target=0.001` on a 1.0 BTC balance **sells** 0.999; to add, set `target = current_holding + delta`).

---

## Ticket Schema

```json
{
    "ticket_id": "tkt_18b2b09ca766001e",
    "status": "OPEN",
    "exchange": "binance-futures",
    "symbol": "btcusdt",
    "strategy": "maker",
    "target_position": 0.5,
    "init_position": 0.0,
    "executed_position": 0.13,
    "time_constraint_ms": 300000,
    "start_time_ms": 1779287926007,
    "last_update_time_ms": 1779287935063,
    "is_expired": false,
    "cancel_reason": null
}
```

| Field | Type | Description |
| --- | --- | --- |
| `ticket_id` | string | `tkt_<hex>` |
| `status` | string | `NEW` \| `OPEN` \| `COMPLETE` \| `CANCEL` |
| `exchange` | string | Exchange id used |
| `symbol` | string | Native symbol format |
| `strategy` | string | `maker` \| `twap` |
| `target_position` | float | Requested net position |
| `init_position` | float \| null | Position at activation (null while NEW) |
| `executed_position` | float | Net delta filled so far |
| `time_constraint_ms` | int | Execution window in ms |
| `start_time_ms` | int \| null | Set when executor activates (NEW → OPEN) |
| `last_update_time_ms` | int \| null | Refreshed on every state change |
| `is_expired` | bool | True when window elapsed; status stays OPEN until cancelled |
| `cancel_reason` | string \| null | `external` \| `superseded` \| `stale` \| `rejected` \| `min_notional` \| `risk_breach` \| `insufficient_margin` \| `paused` |

> **Note**: The ticket has no `avg_price` or `cost` field. For execution cost, opportunity cost, and benchmark comparisons, call `compare_tca` (`bf.tca(...)`) — it returns `execution_cost_usd`, `opportunity_cost_usd`, and benchmarks (l1/mid/twap/vwap) per ticket.

---

## Quickstart (Testnet)

```python
from blockfill import Blockfill

bf = Blockfill()

# Step 1: Set credentials (SDK default is testnet=False/MAINNET — agents MUST pass testnet=True explicitly for sandboxed testing)
bf.set_credentials(
    exchange="binance-futures",
    api_key="...",
    api_secret="...",
    testnet=True,      # ALWAYS start with testnet
)

# Step 2: Start daemon (~50s warmup while it fetches market data)
bf.start()
bf.status()  # DaemonStatus(running=True, ready_exchanges=['binance-futures'], ...)

# Step 3: Place a ticket
ticket = bf.place(
    exchange="binance-futures",
    symbol="btcusdt",
    target_position=0.1,      # base asset units (BTC)
    strategy="maker",         # default
    time_constraint_ms=60_000,  # 60 seconds
)
print(ticket.ticket_id, ticket.status)
```

---

## Diagnostics

```python
bf.check_credentials() -> None
# Hits a SIGNED REST endpoint per configured exchange; prints one line each:
# ✓ <name> / ✗ <name> <reason>.
# Detects: wrong key/secret, IP whitelist mismatch, testnet/mainnet mix-up,
# network/proxy/geo block. Auto-invoked at end of set_credentials().

bf.positions() -> list[dict]
# Aggregated positions from each running executor.
# Each entry: {exchange, symbol, size, entry_price, update_ts_ms}

bf.open_orders() -> list[dict]
# Active orders on each configured exchange right now.

bf.nav() -> dict
# Net Asset Value across all running executors.
# {exchanges: [{exchange, nav, wallet_balance, margin_value, unrealized_pnl}],
#  total_nav, exchanges_queried}

bf.tca(ticket_id=None, symbol=None, from_ms=None, to_ms=None, limit=100,
       history=False) -> list[dict]
# Transaction cost analysis for completed tickets.
# history=False: active session (in-memory).
# history=True:  persistent across all sessions (blockfill-server).
# Each entry: benchmarks (l1/mid/twap/vwap), fills, maker/taker breakdown,
# execution_cost_usd, opportunity_cost_usd, duration_ms.

bf.instruments(substring) -> list[dict]
# Per-exchange instrument lookup — returns native-format symbols matching
# substring. Use this to find the exact symbol string before placing.
```

---

## Proxy / Geo-bypass

For hosts that can't reach Binance directly (US IPs return HTTP 451), route exchange REST and WebSocket traffic through an HTTP CONNECT proxy.

**Starchild users** — free `sc-vpn` skill, 18 countries, 500 GB/month:

```python
bf.set_proxy("http://jp:x@sc-vpn.internal:8080")   # Japan (lowest latency for Binance)
bf.set_proxy("http://sg:x@sc-vpn.internal:8080")   # Singapore
bf.set_proxy("http://hk:x@sc-vpn.internal:8080")   # Hong Kong
bf.set_proxy()                                      # clear proxy
```

| Asia-Pacific | Europe | Americas |
| --- | --- | --- |
| `jp` Japan | `uk` United Kingdom | `ca` Canada |
| `sg` Singapore | `de` Germany | `br` Brazil |
| `hk` Hong Kong | `fr` France | `mx` Mexico |
| `kr` South Korea | `nl` Netherlands | |
| `tw` Taiwan | `ch` Switzerland | |
| `au` Australia | `it` Italy | |
| `in` India | `es` Spain | |
| | `se` Sweden | |

Any HTTP CONNECT proxy also works:

```python
bf.set_proxy("http://user:pass@proxy.example.com:8080")
```

`set_proxy` restarts the daemon so the new setting takes effect. The proxy covers **both REST and WebSocket** — every exchange WS connection is tunneled.

Verify reachability before placing real orders:

```python
bf.set_proxy("http://jp:x@sc-vpn.internal:8080")
bf.set_credentials("binance-futures", api_key=..., api_secret=...)
# set_credentials auto-runs check_credentials() — a ✓ proves both proxy + auth work.
```

---

## Failure Modes

When something fails, diagnose in this order: **credentials → proxy → environment → symbol → margin**.

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `check_credentials` prints `✗ <exchange> IP not whitelisted` | API key bound to a different IP than your current outbound IP | Add your outbound IP (or proxy IP) to the exchange API key whitelist |
| `check_credentials` prints `✗ <exchange> connection refused` / HTTP 451 | Geo-block (e.g. US IP → Binance) | Set a proxy: `bf.set_proxy("http://jp:x@sc-vpn.internal:8080")` |
| `check_credentials` prints `✗ <exchange> invalid signature` | Wrong `api_secret`, or wrong key type (HMAC vs Ed25519) | Re-check credentials; Binance testnet uses Ed25519, not HMAC |
| Ticket stays `NEW` for >30s | Exchange not in `ready_exchanges` (executor still warming up, or failed init) | Check `bf.status()` → `ready_exchanges`; check `blockfill logs` for init error |
| Ticket `cancel_reason: min_notional` | Order size × price < exchange minimum notional | Increase quantity or use a larger notional |
| Ticket `cancel_reason: insufficient_margin` | Not enough margin for the position | Reduce quantity or add margin |
| Ticket `cancel_reason: rejected` | Exchange rejected the order (symbol suspended, invalid params) | Check symbol with `bf.instruments(substring)`; verify symbol format |
| `status` shows `ready_exchanges: []` after >90s | Daemon failed to init one or more exchanges | Run `blockfill stop && blockfill start`; check logs for error |
| NAV = 0 for Binance spot (testnet) | Testnet does not support `getUserAsset` endpoint | Expected — testnet NAV uses market-ticker routing instead |

For persistent issues, see [GitLab Issues](https://gitlab.com/quantech-services-group/blockfill-agent-execution/-/issues) or [Telegram support](https://t.me/blockfill_support). See `docs/troubleshooting.md` for the full knowledge base.

---

## Payment — x402 Quota

Quota is tracked per **(account, exchange)** pair. Every pair starts with a **free tier**; quota is charged when each ticket's TCA finalizes. When the free tier runs out, buy more by paying **USDC on Base** via [x402](https://github.com/coinbase/x402) — gasless EIP-3009 `transferWithAuthorization`. The daemon holds the wallet key and signs locally; only the signature leaves the machine, never the key.

```python
bf.set_payment("0x<64-hex private key>")     # store EVM wallet key
bf.topup("binance-futures", usdc=1.0)        # → {exchange, usdc, quota_balance, tx_hash}
```

CEX exchanges (Binance, OKX, Bybit, Bitget, Gate.io, KuCoin, Kraken, Deribit) use quota. DEX (Hyperliquid, Aster, Orderly) pay builder-code execution fees directly — no quota.

The blockfill-server only ever sees the signature and a **de-identified (SHA-256 hashed) account id** — never your exchange API key or wallet key.

---

## Typical Agent Flow

```python
from blockfill import Blockfill
import os

bf = Blockfill()

# (Optional) configure proxy first if in a geo-blocked region
# bf.set_proxy("http://jp:x@sc-vpn.internal:8080")

# Set creds — SDK automatically verifies via signed REST
bf.set_credentials(
    "binance-futures",
    api_key=os.environ["BINANCE_API_KEY"],
    api_secret=os.environ["BINANCE_API_SECRET"],
    testnet=True,           # always confirm testnet vs mainnet with user
)

# Start daemon
bf.start()  # auto-waits ~50s for warmup

# Place ticket
ticket = bf.place(
    exchange="binance-futures",
    symbol="btcusdt",
    target_position=0.1,   # +0.1 BTC long
    strategy="maker",
    time_constraint_ms=300_000,
)

# Monitor
import time
while ticket.status in ("NEW", "OPEN"):
    time.sleep(5)
    ticket = bf.query(ticket_id=ticket.ticket_id)[0]
    print(f"filled: {ticket.executed_position} / {ticket.target_position}")

# TCA
tca = bf.tca(ticket_id=ticket.ticket_id)
print(tca)

bf.stop()
```

---

## Support

- **GitLab Issues**: <https://gitlab.com/quantech-services-group/blockfill-agent-execution/-/issues>
- **Telegram**: [@blockfill_support](https://t.me/blockfill_support)
