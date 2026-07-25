---
name: tqx-quant
version: 2.3.3
description: |
  TQX (tqx.trade) HK/US stock quant: factor analysis, strategy backtests, and agent-driven paper trading via tqx-cli.

  Use when the user wants to run factor IC/IR analysis, backtest a Python trading strategy on Hong Kong or US stocks, or set up agent-automated trading (e.g. "backtest a moving-average strategy on AAPL", "analyze a momentum factor on HK stocks", "let the agent trade my paper account").
author: starchild
tags: [quant, backtest, factor-analysis, stocks, tqx, trading]
---

# TQX Quant — Factor Analysis & Strategy Backtest

TQX (https://www.tqx.trade) is a HK/US stock quant platform. This skill drives it through the official `tqx-cli` pip package.

## Official TQX skills (source of truth — read these first)

TQX publishes two official skills. Fetch the raw URLs directly (the repo UI is a JS SPA; only `/-/git/raw/` URLs return content):

**1. tqx-research** — factor analysis, strategy backtest, workflow management (Python `tqx-cli`, email/password login):
- Main: `https://cnb.cool/liangyunzhijing/clis/-/git/raw/main/skills/tqx-research/SKILL.md`
- References (read before generating code — do NOT guess APIs):
  - commands: `.../skills/tqx-research/references/commands.md`
  - strategy templates: `.../skills/tqx-research/references/strategy_templates.md`
  - US API: `.../skills/tqx-research/references/stock_us_api.md`
  - HK API: `.../skills/tqx-research/references/stock_hk_api.md`
  - tqx_data: `.../skills/tqx-research/references/tqx_data_usage.md`
  (replace `...` with `https://cnb.cool/liangyunzhijing/clis/-/git/raw/main`)

**2. tqx-trading** — account/positions/orders/trades queries + authorized order placement (TypeScript `@tqx-ai/cli@0.1.3`, API-key auth, pin the version):
- Main: `https://cnb.cool/liangyunzhijing/clis/-/git/raw/main/skills/tqx-trading/SKILL.md`
- OpenAPI: `https://www.tqx.trade/openapi/v1/openapi.json` (interactive: `/openapi/v1/scalar`)

**Routing rule:** research/backtest/factor work → tqx-research (`tqx-cli`, Python). Live account state & order execution → tqx-trading (`tqx`, TS CLI). They use DIFFERENT CLIs and DIFFERENT auth (email login vs `TQX_API_KEY`) — don't mix them. This skill below adds what the official docs don't cover: verified onboarding, failure-mode table, and agent-automation patterns.

## User onboarding (first-time setup, ~3 minutes)

1. **Register** at https://www.tqx.trade (email signup). A PAPER (simulation) account is provisioned automatically — all workflows below are safe to run on it.
2. **Collect credentials securely**: agents must use `request_env_input` for `TQX_EMAIL` and `TQX_PASSWORD` — never ask for credentials in chat.
3. **Install + login + verify**:

```bash
pip install tqx-cli
tqx-cli login --email "$TQX_EMAIL" --password "$TQX_PASSWORD"
tqx-cli --json balance        # non-error response = onboarding complete
```

Token is cached in `~/.tqx/config.yaml`.

4. **First quick win** (recommended demo): run the "5d momentum" factor analysis from §1 below — completes in ~1–2 min and produces IC/IR/Sharpe numbers you can show immediately.

**⚠️ Token expiry gotcha:** both accessToken AND refresh_token can expire together. Do NOT only match one specific error string — re-login on ANY response containing `LOGIN_REQUIRED`, `均已失效`, or `Please log in to continue`. A strict matcher silently fails and every later call returns auth errors.

## CLI command map

```
factor_create / factor_run / factor_result / factor_list / factor_delete
strategy_create / strategy_run / strategy_result / strategy_list / strategy_delete
backtest_result   # per-backtest detail: summary/account/position/profit/trade/log sections
workflow_list / workflow_stop / balance
```

Add `--json` for machine-readable output.

## 1. Factor analysis (cross-sectional IC/IR)

```bash
tqx-cli --json factor_create --market us --name "5d momentum" \
  --formula "close/ref(close,5)-1" \
  --start-date 20250101 --end-date 20250701 --group-number 2
tqx-cli --json factor_run <factor_id>          # waits and returns results
```

**Result parsing gotcha:** the result JSON has TWO formats depending on backend version — legacy `nodes[].result_json` and current root-level `factor_analysis`. Handle both. Key metrics: IC mean, IR, t-stat, annualized group returns, Sharpe.

## 2. Strategy backtest (panda_backtest engine)

```bash
tqx-cli --json strategy_create --market us --name "AAPL SMA cross" \
  --code "$(cat strategy.py)" \
  --start-date 20250101 --end-date 20250701 \
  --start-capital 1000000 --commission-rate 0.0003 --slippage 0.001 --frequency 1d
tqx-cli --json strategy_run <strategy_id>
```

### Strategy code contract

```python
from panda_backtest.api.api import *            # common trading API — MANDATORY
from panda_backtest.api.stock_us_api import *   # US market data API — MANDATORY
# HK market: from panda_backtest.api.stock_hk_api import *
import tqx_data

def initialize(context):
    # Account ID is per-user — discover it once, do NOT hardcode.
    # The '8888' from CN-market docs does NOT exist for HK/US backtests.
    context.account = list(context.stock_account_dict.keys())[0]
    context.symbol = 'AAPL.NB'   # symbol format: US = TICKER.NB (NOT .US!), HK = 00700.HK
    context.closes = []

def handle_data(context, data):
    account = context.stock_account_dict.get(context.account)
    if account is None:
        return
    bar = data.get(context.symbol)
    # bar CAN be None — with a WRONG suffix it is None EVERY day (silent 0-trade run)
    if bar is None or getattr(bar, 'close', None) is None or float(bar.close) <= 0:
        return
    price = float(bar.close)
    context.closes.append(price)
    if len(context.closes) < 20:
        return
    fast = sum(context.closes[-5:]) / 5
    slow = sum(context.closes[-20:]) / 20
    position = account.positions.get(context.symbol)
    quantity = 0 if position is None else position.quantity
    sellable = 0 if position is None else position.sellable
    if fast > slow and quantity == 0:
        buy_qty = int(account.cash * 0.9 // price)
        if buy_qty > 0:
            order_shares(context.account, context.symbol, buy_qty, style=MarketOrderStyle)
            print(f"BUY {buy_qty} @ {price:.2f}")   # print() = strategy log; SRLog is FORBIDDEN
    elif fast < slow and quantity > 0 and sellable > 0:
        order_shares(context.account, context.symbol, -sellable, style=MarketOrderStyle)
        print(f"SELL {sellable} @ {price:.2f}")
```

Reference run: this exact code on AAPL.NB, 20250101–20251231, produces 18 real fills (check with `backtest_result <backtest_id> --section trade --all-pages`).

Hard rules learned from real failures:

| Symptom | Root cause | Fix |
|---|---|---|
| `禁止使用危险函数 dir()` | Security filter blocks introspection | Never use `dir()`/`eval()`/`exec`; to inspect context, `raise Exception(str(...))` and read the error_detail in run logs |
| `访问了不存在的键` on order | Wrong account ID (e.g. `'8888'`) | Use `list(context.stock_account_dict.keys())[0]` |
| `order_shares() missing 1 required positional argument` | Called with 2 args | Signature is `order_shares(account, symbol, quantity)` |
| `股票X不属于当前股票回测市场` | Wrong symbol suffix | US = `TICKER.NB` (NOT `.US`!), HK = `XXXXX.HK`; `.O`/`.N`/bare tickers are rejected |
| Backtest SUCCESS but 0 trades, 0 log lines, profit = 0.0 | Symbol suffix `.US` (or any wrong suffix) → every bar returns None → defensive guard skips all days silently | Use `TICKER.NB` for US stocks. ALWAYS verify via `backtest_result <id> --section trade` — SUCCESS ≠ trades executed |
| Run FAILED immediately (~0.3s, node failed) | `SRLog` is not a valid API in strategy code | Use plain `print()` for strategy logging (visible in `--section log`) |
| Run status FAILED but NO failed node (all nodes success/pending) | Transient TQX queue/scheduler error, not your code | Resubmit the same workflow once — typically succeeds in ~30s. Only debug strategy code if a node actually failed |
| Backtest SUCCESS but 0 trades, `标的不在当前回测数据集内` | Date range beyond ingested market data (recent months may not be loaded even though the benchmark series exists) | Shift the window earlier (e.g. use last year's range); verify trades>0 in the `trade` section before trusting metrics |
| `frequency` rejected | Only `1d` and `1M` are valid | — |

### Reading results

`strategy_run`/`strategy_result` returns run status + node outputs. For full detail, extract the backtest id from run logs (`BacktestNodeIdentifier:` line) or node output, then:

```bash
tqx-cli --json backtest_result <backtest_id> --section summary   # profit, alpha, beta, sharpe, IR
tqx-cli --json backtest_result <backtest_id> --section trade     # ⚠️ always check trades executed
tqx-cli --json backtest_result <backtest_id> --section log       # per-order rejection reasons
```

**A run can report SUCCESS with zero trades** (orders silently rejected day by day). Always confirm the `trade` section is non-empty before reporting performance numbers.

#### Daily equity curve (`--section profit`)

The `profit` section is the day-by-day NAV series — one row per trading day with `gmt_create` (YYYYMMDD), `strategy_profit` (cumulative strategy return, decimal) and `csi_stock` (cumulative benchmark return, decimal).

```bash
# ⚠️ --all-pages does NOT work for the profit section: it silently returns only page 1 (100 rows).
tqx-cli --json backtest_result <backtest_id> --section profit --page-size 1000
# -> pagination {total: 252, page: 1, page_size: 1000, total_pages: 1}   ✅ full year in one call
```

Two more behaviours to handle (reference: AAPL.NB, full-year 2025 = 252 rows):
- Rows come back **unsorted** — always sort by `gmt_create` ascending before plotting; do not assume the API order.
- Values are **decimals, not percent** (`-0.1174` = −11.74%) and are already cumulative, so plot them directly; don't compound them again.
- The last row must match the `summary` section's total return — use that as your correctness check.

Cache the series locally (one file per run) instead of re-fetching: the call costs ~2–4 s and the data is immutable once the run is done.

### Debugging failed runs

Error details are NOT in the top-level status — fetch run logs and read `error_detail`, which includes the exact strategy line number and exception message:

```python
from tqx_cli.config import load_config
from tqx_cli.auth import require_login
from tqx_cli.workflow import get_run_logs
cfg = load_config(); token, uid, _ = require_login(cfg, cfg.get("_config_path"))
for l in get_run_logs(cfg, token, uid, run_id).get("logs") or []:
    if l.get("error_detail"): print(l["error_detail"])
```

## Cost & pacing

Backtests are billed in TQX compute credits (`tqx-cli balance`). A 6-month daily-frequency single-stock backtest takes ~2 minutes wall time. Poll `strategy_result` every 3s; don't fire concurrent runs of the same workflow.

## 3. Templates (copy-paste starting points)

### T1 — Momentum factor (cross-sectional, whole market)

```bash
tqx-cli --json factor_create --market us --name "5d momentum" \
  --formula "close/ref(close,5)-1" \
  --start-date 20250101 --end-date 20250701 --group-number 5
```

Other verified formulas: mean reversion `-(close/ref(close,5)-1)`, volume surge `volume/mean(volume,20)`.
Factor mode is whole-market cross-sectional only (`--market hk|us`) — it CANNOT target one stock; for single-stock questions use a strategy backtest (T2).

### T2 — Single-stock backtest (SMA cross on AAPL)

Use the strategy code contract in §2 verbatim — it IS the template. Change `context.symbol` and the signal logic only. Keep the None-bar guard and dynamic account discovery.

### T3 — Agent-driven automated trading loop (paper account)

Pattern verified over a 10-round live run (~21 min, end-to-end):

```
loop every N minutes:
  1. fetch live positions + account state
  2. compute signal (factor value or strategy rule)
  3. decide: buy / sell / hold  ← agent reasoning step
  4. place order (paper account, small fixed qty during development)
  5. journal the decision: {ts, reasoning, tool_calls, params, result, position_delta}
```

Hard rules for automation:
- **PAPER account only** until the user explicitly approves real trading; cap order size during development.
- **Journal every decision** (JSONL is enough) — users must be able to audit why each trade happened.
- **Re-login on ANY auth-ish error string** (see token gotcha above); a mid-loop token expiry must self-heal, not kill the loop.
- **Check compute balance before each backtest-class call** to avoid silent overdraft.

### T4 — Studio: ready-to-run companion UI (`templates/studio/`)

A complete, tested web workbench ships with this skill — do NOT build a dashboard from scratch. Copy `templates/studio/` into the user's workspace, start it, and adapt.

**Files:**
| File | Role |
|---|---|
| `server.py` | Stdlib HTTP backend (port 8090, no pip deps). Proxies `tqx-cli`, auto re-login on token expiry, serves all `/api/*` routes |
| `index.html` | Single-file frontend: factor analysis, backtest submit/history, positions, agent decision timeline |
| `agent.py` | Agent trading loop (LLM via `proxied_post` + tool calls), JSONL decision journal |
| `backtests.py` / `strategies.py` / `journal.py` | Disk persistence modules (see data spec below) |
| `styles/index.html` | Alternate theme variant for user selection |

**Run:** `python3 server.py` from the studio dir (background), then `preview(action="serve")` on it. Credentials come from `TQX_EMAIL` / `TQX_PASSWORD` env vars (collect via secure input — never hardcode).

**Design spec (keep when restyling):**
- Minimalist quant-tech aesthetic: dark-first, monospace numerals, dense tables, no decorative graphics. Avoid bright or cyberpunk themes.
- History rows must be loadable: clicking Load on any history record re-displays its full result in the top result area (factor runs → factor metrics/charts via `loadBt`; strategy runs → dedicated strategy-result card via `loadStgBt`: return vs benchmark, annualized, Sharpe, max drawdown, trade count, params + code link). A history table that only lists rows without load-back is incomplete.
- UI exposes only high-frequency params (formula, market, date range, groups, rebalance, direction) + account switcher + NAV curve + decision timeline. Everything complex (custom strategy code, stock pools, commission/slippage) stays in the conversation layer — the agent has the full CLI surface, the UI must not duplicate it.
- Amounts: format gold/cash values with a single dedicated formatter two competing formatters produce inconsistent output. Check dark-mode contrast on every card.

**Persistence & paths (why the two directories):**

`tqx-cli` writes its login config to `/root/.tqx/config.yaml`, which lives on the container's ephemeral layer and is wiped on every machine restart — the agent would silently lose its session. Only `/data/workspace` survives restarts, so the studio mirrors the config into `/data/workspace/.tqx/` and syncs both ways on startup (`sync_tqx_config()` in `server.py`, `_sync_tqx_config()` in `agent.py`).

These paths are intentionally fixed, not a portability oversight: every agent has the identical layout — `/data/workspace` = persistent volume, `/root` = ephemeral. Keep the rule when extending the studio: **anything that must survive a restart is written under the workspace, never under `/root` or `/tmp`.** In-studio state (`data/backtests`, `data/journal`, `data/strategies`) is already `__file__`-relative, so it inherits persistence as long as the studio itself is copied into the workspace. If you ever run this outside a Starchild machine, override the persistent root — nothing else in the code assumes an absolute path.

**Data storage spec:**
- `data/backtests/index.json` + one JSON per run — MUST persist the full strategy code string (not a truncated preview) so any run can be reloaded and re-edited.
- `data/journal/*.jsonl` — one line per agent decision, tagged `source: manual | agent`, append-only, never rewritten.
- `data/strategies/` — named saved strategies. All state is plain JSON on disk; no DB.

**Testing spec (before declaring the studio 'working'):**
1. `curl localhost:8090/api/health` (or any GET route) returns JSON — backend alive.
2. Submit one REAL backtest through the UI and confirm it appears in the history panel with full code + metrics. A rendered page alone is NOT verification.
3. Verify fills exist via `backtest_result <id> --section trade` — SUCCESS status with 0 trades means a symbol-suffix bug (see failure table).
4. Kill/restart `server.py` and confirm history persists (disk, not memory).
