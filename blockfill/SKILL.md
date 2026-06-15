---
name: blockfill-agent-execution
version: 1.0.2
description: "AI-agent-ready Python SDK and local execution engine for crypto perpetual futures order execution. Work large orders through TWAP and maker-style strategies on Binance Futures and OKX Swap while exchange API keys stay on your own machine — self-custodial, no third-party order routing. Declare a target position and BlockFill executes it; place, query, and cancel execution tickets from one Python API."
delivery: script
metadata:
    starchild:
        skillKey: blockfill
        requires: {}
user-invocable: true
disable-model-invocation: false
---

## What is BlockFill Agent Execution

BlockFill Agent Execution is an **AI-agent-ready Python SDK and local execution engine** for crypto perpetual futures order execution. It enables AI agents, trading systems, and developers to execute large crypto perpetual futures orders through TWAP and maker-style strategies on **Binance Futures** and **OKX Swap**, while keeping exchange API keys on the user's own machine.

You declare a target position; BlockFill works the order over a time window using `maker` (PostOnly resting + IOC fallback) or `twap` (taker-sliced) strategies, cutting execution slippage vs. naïve market orders. One Python API, one local daemon, two exchanges supported today — one `bf.place(...)` call per target position.

**Why BlockFill Agent Execution**:

- **Self-custodial by design** — exchange API keys stay on your machine (`~/.blockfill/config.toml`, chmod 0600). The local daemon signs orders locally and sends them directly to the exchange — no key custody, no order routing, no order-flow visibility by a third party.
- **Designed for AI agents** — built to be called by AI agents, trading copilots, MCP servers, and strategy systems. The agent decides the trading intent; BlockFill is the execution layer that turns it into placed orders.
- **Smart execution** — built-in `maker`/`twap` strategies handle order slicing and timing automatically, cutting execution slippage vs. naïve market orders.
- **Multi-exchange** — Binance Futures and OKX Swap from a single daemon.
- **One simple API** — `from blockfill import Blockfill`, then one `bf.place(...)` call per target position to place, query, and cancel execution tickets.

**Key concepts**:

- **Ticket**: an execution order (`exchange + symbol + strategy + target_position + time_constraint_ms`)
- **Daemon**: local background process that signs and places orders through your own exchange API keys, and supervises per-exchange connections
- **Python SDK**: `from blockfill import Blockfill` — programmatic interface for AI agents and scripts

---

## Install

```bash
pip install blockfill                    # latest
pip install -U blockfill                 # upgrade (pip never auto-upgrades)
```

The wheel ships with the executor binary bundled inside (no separate
download). PyPI publishes only platform-specific wheels — incompatible
hosts get a clean `No matching distribution`. Currently:

- `manylinux2014_x86_64` (Linux x86_64)
- `manylinux2014_aarch64` (Linux arm64)
- `macosx_11_0_arm64` (Apple Silicon)
- `macosx_10_15_x86_64` (Intel macOS)

The qtex endpoint and API key are hardcoded into the binary at release time —
users never set them.

---

## Supported exchanges

| Exchange                 | Value             | Credentials                                          | Multi-exchange in one daemon |
| ------------------------ | ----------------- | ---------------------------------------------------- | ---------------------------- |
| Binance Futures (USDT-M) | `binance-futures` | `api_key`, `api_secret`, `testnet`                   | ✓                            |
| OKX Swap                 | `okx-swap`        | `api_key`, `api_secret`, `api_passphrase`, `testnet` | ✓                            |

A single daemon can run **both** exchanges concurrently. Add credentials for
each one — the daemon spawns a per-exchange executor.

---

## Supported symbols

Each exchange uses its **own native symbol format** — they are not the same.

| Exchange          | Format                                                | Examples                                                            |
| ----------------- | ----------------------------------------------------- | ------------------------------------------------------------------- |
| `binance-futures` | Lowercase, concatenated (Binance native)              | `btcusdt`, `ethusdt`, `solusdt`, `dogeusdt`                         |
| `okx-swap`        | Dash-separated, includes contract suffix (OKX native) | `BTC-USDT-SWAP`, `ETH-USDT-SWAP`, `SOL-USDT-SWAP`, `DOGE-USDT-SWAP` |

Use the exact format the target exchange expects — BlockFill does NOT
cross-translate.

---

## Execution strategies

Two strategies are supported via the public ticket API:

| Strategy | Behavior                                                                                                                                                                                     | When to use                                                                  |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `maker`  | **Passive maker.** Posts PostOnly limit orders that sit on the book and earn the maker rebate. In the last segment of the time window, falls back to IOC to clean up any unfilled remainder. | Default. Cost-optimal when fill speed is not critical.                       |
| `twap`   | **Pure-taker TWAP.** Places IOC orders on a TWAP schedule across the full time window — no PostOnly phase. Always crosses the spread.                                                        | When you need guaranteed completion within the window and accept taker cost. |

Default: `maker`.

---

## Ticket parameters

| Parameter            | Type   | Required | Default  | Description                                                                                                                             |
| -------------------- | ------ | -------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `exchange`           | string | ✅       | —        | `binance-futures` or `okx-swap`                                                                                                         |
| `symbol`             | string | ✅       | —        | Lowercase, e.g. `btcusdt`                                                                                                               |
| `target_position`    | float  | ✅       | —        | Target position in base asset. Positive = long, negative = short                                                                        |
| `strategy`           | string |          | `maker`  | `maker` \| `twap`                                                                                                                       |
| `time_constraint_ms` | int    |          | `300000` | Execution window in ms (10,000–86,400,000). At the end of the window the executor falls back to taker fills for any unfilled remainder. |

**Auto-supersede**: placing a new ticket for the same `exchange+symbol` automatically cancels existing **NEW and OPEN** tickets for that pair (`cancel_reason: "superseded"`). The superseded ticket remains visible in queries with `status: CANCEL`.

---

## Ticket schema

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

| Field                 | Type           | Description                                                                                                                 |
| --------------------- | -------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `ticket_id`           | string         | `tkt_<hex>`                                                                                                                 |
| `status`              | string         | `NEW` \| `OPEN` \| `COMPLETE` \| `CANCEL`                                                                                   |
| `exchange`            | string         | `binance-futures` \| `okx-swap`                                                                                             |
| `symbol`              | string         | Lowercase symbol                                                                                                            |
| `strategy`            | string         | `maker` \| `twap`                                                                                                           |
| `target_position`     | float          | Requested net position                                                                                                      |
| `init_position`       | float \| null  | Exchange position at activation time (null while NEW)                                                                       |
| `executed_position`   | float          | Net delta filled so far                                                                                                     |
| `time_constraint_ms`  | int            | Execution time limit                                                                                                        |
| `start_time_ms`       | int \| null    | Set when executor activates (NEW → OPEN)                                                                                    |
| `last_update_time_ms` | int \| null    | Refreshed on every state change                                                                                             |
| `is_expired`          | bool           | Flag-only; status stays OPEN until separately cancelled                                                                     |
| `cancel_reason`       | string \| null | `external` \| `superseded` \| `stale` \| `rejected` \| `min_notional` \| `risk_breach` \| `insufficient_margin` \| `paused` |

---

## Two-step quickstart

```python
from blockfill import Blockfill

bf = Blockfill()

# 1. Set credentials. SDK writes ~/.blockfill/config.toml (chmod 0600) then
#    auto-runs `check_credentials` — a signed REST round-trip that confirms
#    api_key+secret are valid AND the host can reach the exchange. If you're
#    behind a region block (e.g. US → binance), set a proxy first:
#       bf.set_proxy("http://jp:x@sc-vpn.internal:8080")
bf.set_credentials(
    exchange="binance-futures",
    api_key="...",
    api_secret="...",
    testnet=True,
)

# 2. Start daemon. ~50s warmup while it fetches market data.
bf.start()
bf.status()  # DaemonStatus(running=True, ready_exchanges=['binance-futures'], proxy=None, ...)
```

Then place tickets:

```python
ticket = bf.place(
    exchange="binance-futures",
    symbol="btcusdt",
    target_position=0.1,
    time_constraint_ms=60_000,
)
print(ticket.ticket_id, ticket.status)
```

---

## Diagnostics

```python
bf.check_credentials() -> None
# Hits a SIGNED REST endpoint per configured exchange and prints one line
# each: ✓ <name> / ✗ <name> <reason>. Detects wrong key/secret, IP
# whitelist mismatch, testnet/mainnet mix-up, network/proxy/geo block.
# Doesn't raise — printed output IS the signal. Auto-invoked at the end
# of `set_credentials()` so typos surface immediately.

bf.positions() -> list[dict]
# Aggregated positions from each running executor.
# Each entry: {exchange, symbol, size, entry_price, update_ts_ms}
# `symbol` is native format ("DOGE-USDT-SWAP", "btcusdt") and `exchange`
# is the config-key string ("okx-swap", "binance-futures") — same strings
# you pass to bf.place(exchange=..., symbol=...).

bf.open_orders() -> list[dict]
# Active orders on each configured exchange right now.

bf.instruments(substring) -> list[dict]
# Per-exchange instrument lookup. Returns native-format symbols matching
# `substring` so you don't have to guess the exact string format.
```

---

## Proxy / Geo-bypass

For hosts that can't reach Binance directly (US IPs are blocked, returns
HTTP 451), route exchange REST traffic through an HTTP CONNECT proxy.

**Starchild users** — the free **`sc-vpn`** skill provides a managed proxy
across 18 countries (500 GB/month, no credentials needed). Pick a country
code and pass the URL:

```python
bf.set_proxy("http://jp:x@sc-vpn.internal:8080")   # Japan
bf.set_proxy("http://sg:x@sc-vpn.internal:8080")   # Singapore
bf.set_proxy("http://hk:x@sc-vpn.internal:8080")   # Hong Kong
bf.set_proxy()                                     # clear
```

Country codes (ISO-2):

| Asia-Pacific          | Europe                          | Americas             |
| --------------------- | ------------------------------- | -------------------- |
| `jp` Japan            | `uk` United Kingdom             | `ca` Canada          |
| `sg` Singapore        | `de` Germany                    | `br` Brazil          |
| `hk` Hong Kong        | `fr` France                     | `mx` Mexico          |
| `kr` South Korea      | `nl` Netherlands                |                      |
| `tw` Taiwan           | `ch` Switzerland                |                      |
| `au` Australia        | `it` Italy                      |                      |
| `in` India            | `es` Spain                      |                      |
|                       | `se` Sweden                     |                      |

For binance, `jp` / `sg` / `hk` give the lowest latency. See the
[sc-vpn skill repo](https://github.com/Starchild-ai-agent/official-skills/tree/main/sc-vpn)
for the authoritative country list.

`set_proxy` auto-restarts the daemon so the new setting takes effect — the
proxy is read once at startup and stashed in a global.

You can also pass any HTTP CONNECT proxy URL (e.g. a residential provider):

```python
bf.set_proxy("http://user:pass@proxy.example.com:8080")
```

WebSocket proxy is on the TODO list — until then, WS streams go direct and
will fail on geo-blocked hosts.

Verify the proxy actually reaches the exchange before placing real orders:

```python
bf.set_proxy("http://jp:x@sc-vpn.internal:8080")
# `set_credentials` automatically runs check_credentials() through the new
# proxy and prints the result — a ✓ proves reachability AND auth in one shot.
bf.set_credentials("binance-futures", api_key=..., api_secret=...)
```

---

## Typical agent flow

```python
from blockfill import Blockfill

bf = Blockfill()

# (Optional) configure a proxy first if you're in a geo-blocked region.
# bf.set_proxy("http://jp:x@sc-vpn.internal:8080")

# Set creds — SDK automatically verifies via signed REST. If your host can't
# reach the exchange, or creds are wrong, this raises RuntimeError.
bf.set_credentials("binance-futures",
                   api_key=os.environ["BINANCE_API_KEY"],
                   api_secret=os.environ["BINANCE_API_SECRET"],
                   testnet=False)

# Run.
bf.start()                  # auto-waits ~50s for warmup
ticket = bf.place(exchange="binance-futures", symbol="btcusdt", target_position=0.1)
# ... wait for fills, query state ...
print(bf.positions())
bf.stop()
```
