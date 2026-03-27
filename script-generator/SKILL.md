---
name: script-generator
version: 1.0.0
description: Write and schedule trading scripts for strategy automation. Use when the user needs a recurring monitor, price alert, indicator script, or any automated data pipeline.

metadata:
  starchild:
    emoji: "⚙️"

user-invocable: true
disable-model-invocation: false
---

# Script Generator

Write working trading scripts, test them, schedule them. No templates, no placeholders.

## Process

1. Write script in `scripts/`
2. **Test immediately:** `bash("python3 scripts/<name>.py")` — show real output
3. Schedule: `schedule_task(command="python3 scripts/<name>.py", schedule="...")`

## Rules

- **No placeholders.** Every script must actually run. Test before declaring done.
- **`command` mode, not `task`.** Scripts run as subprocesses — no agent overhead.
- **Print to stdout** — that becomes the push notification content.
- **Paths relative to workspace.** Write `scripts/foo.py`, schedule `python3 scripts/foo.py`. Don't prefix `workspace/`.
- **Env vars inherited.** Use `os.getenv("TAAPI_API_KEY")` etc. No dotenv loading needed.

## API Reference

Scripts call APIs directly with `requests` + `os.getenv()`. No internal imports.

| Service | Base URL | Auth | Env Var |
|---------|----------|------|---------|
| TaAPI | `https://api.taapi.io` | Query `secret` | `TAAPI_API_KEY` |
| Coinglass | `https://open-api.coinglass.com/public/v2` | Header `coinglassSecret` | `COINGLASS_API_KEY` |
| LunarCrush | `https://lunarcrush.com/api4` | Header `Authorization: Bearer` | `LUNARCRUSH_API_KEY` |
| CoinGecko | `https://pro-api.coingecko.com/api/v3` | Header `x-cg-pro-api-key` | `COINGECKO_API_KEY` |

## Indicator Keys (TaAPI)

| Indicator | Keys |
|-----------|------|
| rsi, ema, sma, adx, cci, atr, obv, mfi, psar | `value` |
| macd | `valueMACD`, `valueMACDSignal`, `valueMACDHist` |
| bbands | `valueUpperBand`, `valueMiddleBand`, `valueLowerBand` |
| stoch | `valueK`, `valueD` |
| dmi | `adx`, `pdi`, `mdi` |
| ichimoku | `conversion`, `base`, `spanA`, `spanB`, `lagging` |
