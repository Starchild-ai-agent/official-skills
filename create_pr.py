import os
import requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
if not GITHUB_TOKEN:
    for env_path in ["/data/workspace/projects/.env", "/data/workspace/.env"]:
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if line.startswith("GITHUB_TOKEN="):
                        GITHUB_TOKEN = line.strip().split("=", 1)[1]
            if GITHUB_TOKEN:
                break

if not GITHUB_TOKEN:
    print("❌ No GITHUB_TOKEN found")
    exit(1)

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

PR_BODY = """## Comprehensive Skills Audit — 1127 Tests, 6 Patches, 28 Skills

### Summary

Full quality audit of all 28 official skills. Delivered a pytest-based test framework with **1127 passing tests**, **6 production-ready patches**, and **13 code quality findings**.

### 🧪 Test Suite (24 files, 1127 passed, 0 failed)

| Category | Tests | Coverage |
|----------|-------|----------|
| Code Quality | 596 | Python syntax, imports, docstrings, module structure across all skills with code |
| Skill Quality | 310 | SKILL.md docs, YAML frontmatter, required sections, markdown links for all 28 skills |
| Patch Validation | 77 | Edge cases, unicode, concurrency, boundary conditions for all 6 patches |
| Live API | 50 | Real endpoint connectivity + patch chain verification (CoinGecko, Hyperliquid) |
| Validators | 27 | Chain ID, EVM address, token amount, slippage validation |
| Security | 10 | Hardcoded secrets, eval/exec detection, path traversal |
| Cross-Skill | 10 | Consistency patterns, error handling, retry logic |
| Legacy Suites | ~47 | Crypto workflows, error handling, response formats |

### 🛡️ Production Patches (`patches/`)

| Patch | Problem | Fix |
|-------|---------|-----|
| `error_format_normalizer` | Inconsistent error structures | Unified `{error, source, raw}` format |
| `liquidation_data_fixer` | CoinGlass nested/variant structures | Normalizes to flat schema |
| `analysis_calculator` | Division-by-zero in ratio calculations | Safe math with fallbacks |
| `response_truncator` | LLM responses exceed context windows | Model-aware truncation |
| `unified_error_handler` | No standard error contract | Consistent error envelope |
| `error_handler_with_retry` | Transient API failures crash workflows | Exponential backoff + circuit breaker |

Shared modules: `validators.py`, `retry.py`, `crypto_safety.py`, `errors.py`, `response.py`

### 🔍 Key Finding: `sys.exit()` in Library Code

13 tool files use `sys.exit()` instead of raising exceptions. Flagged as `xfail` — functional but should be refactored for better agent runtime error handling.

### 📋 Required Real APIs

| API | Status | Notes |
|-----|--------|-------|
| CoinGecko Pro | ✅ Working | Via sc-proxy |
| Hyperliquid | ✅ Working | Public API |
| Coinglass | ⚠️ Needs key | 500 errors on funding endpoint |
| Birdeye | ⚠️ Untested | Needs API key |
| TAAPI | ⚠️ Untested | Needs API key |
| LunarCrush | ⚠️ Untested | Needs API key |
| Twelve Data | ⚠️ Untested | Needs API key |

### How to Run

```bash
# All tests (no API keys needed for unit tests)
python -m pytest tests/ -v

# Skip live API tests
python -m pytest tests/ -v -k "not live"

# Only code quality
python -m pytest tests/test_code_quality.py -v
```
"""

data = {
    "title": "feat: comprehensive skill audit — 1127 tests, 6 patches, 28 skills",
    "body": PR_BODY,
    "head": "AaronBoat:feat/audit-v2-rebased",
    "base": "main"
}

url = "https://api.github.com/repos/Starchild-ai-agent/official-skills/pulls"
response = requests.post(url, headers=headers, json=data)

if response.status_code == 201:
    pr = response.json()
    print(f"✅ PR Created! URL: {pr['html_url']}")
    print(f"   PR #{pr['number']}: {pr['title']}")
elif response.status_code == 422:
    print(f"⚠️ PR may already exist: {response.status_code}")
    print(response.json().get("errors", response.text))
else:
    print(f"❌ Failed: {response.status_code}")
    print(response.text[:500])
