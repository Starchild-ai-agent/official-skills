# Official Skills Quality Audit

Comprehensive quality audit and improvement patches for [Starchild official-skills](https://github.com/Starchild-ai-agent/official-skills).

## Quick Start

```bash
pip install pytest pytest-cov
cd projects/official-skills-audit
python -m pytest tests/ -v --cov=patches --cov-report=term-missing
```

## Results

- **194 tests** — all passing
- **97% code coverage** on patch modules  
- **0 security issues** found in repo scan

## Structure

```
patches/shared/          # Cross-skill improvements
  errors.py              # Structured error hierarchy (replaces silent failures)
  response.py            # Unified response format
  retry.py               # Exponential backoff + circuit breaker
  validators.py          # Input validation (addresses, amounts, chains)
  crypto_safety.py       # Pre-trade safety checks (slippage, gas, finality)

patches/1inch/           # 1inch-specific patches
patches/aave/            # Aave-specific patches

tests/                   # Full test suite (20 files, 194 tests)
```

## Why This Matters

Current skills fail silently (`try/except: return None`), which makes small-model agents unable to diagnose or recover from errors. These patches add:

1. **Structured errors** → models can read error codes and take corrective action
2. **Unified responses** → consistent JSON format across all skills
3. **Smart retry** → automatic recovery from transient failures
4. **Input validation** → catch bad inputs before they hit the chain
5. **Safety checks** → slippage/gas/finality guards for crypto operations

See [QUALITY_REPORT.md](./QUALITY_REPORT.md) for the full analysis (中文).
