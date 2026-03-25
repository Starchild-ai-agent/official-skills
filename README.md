# Official Skills Audit — Patches & Test Suite

Automated quality patches and comprehensive test suite for [Starchild official-skills](https://github.com/Starchild-ai-agent/official-skills).

## What's Here

### `patches/` — Improvement Code

Shared utility modules that all skills can use:

| Module | Purpose |
|--------|---------|
| `shared/errors.py` | Unified error hierarchy (SkillError → APIError, ValidationError, RateLimitError) |
| `shared/response.py` | Consistent response formatting (tables, truncation, numeric normalization) |
| `shared/validators.py` | Input validation (ETH addresses, amounts, chain IDs, slippage) |
| `shared/retry.py` | Smart retry with exponential backoff + jitter |
| `shared/crypto_safety.py` | DeFi safety checks (slippage, gas, approvals, health factors) |
| `1inch/swap_safety.py` | Pre-swap safety validation for 1inch |
| `aave/lending_safety.py` | Lending safety checks for AAVE |
| `coinglass/api_error_handling.py` | CoinGlass API error normalization |
| `hyperliquid/*.py` | Hyperliquid error context enhancement |

### `tests/` — 194 Automated Tests

```
194 passed, 0 failed, ~20s runtime
```

See **[TESTING_GUIDE.md](./TESTING_GUIDE.md)** for full walkthrough (中英双语).

## Quick Start

```bash
pip install pytest requests
python -m pytest tests/ -v
```

## Coverage

```bash
pip install pytest-cov
python -m pytest tests/ --cov=patches --cov-report=term-missing
```

Target: 96%+ on `patches/` code.

## License

Same as upstream [official-skills](https://github.com/Starchild-ai-agent/official-skills).
