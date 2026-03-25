import os
import requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
if not GITHUB_TOKEN:
    with open("/data/workspace/projects/.env", "r") as f:
        for line in f:
            if line.startswith("GITHUB_TOKEN="):
                GITHUB_TOKEN = line.strip().split("=", 1)[1]

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

data = {
    "title": "feat: comprehensive audit, tests, and crypto safety patches v2",
    "body": """## Summary of Changes

This PR introduces a comprehensive test suite and critical safety improvements across the official skills repository, focusing on error handling, security, and small-model efficiency.

### 🧪 Test Framework Additions (117 Tests Passing)
- Added `tests/` directory with 16 test modules covering:
  - **Error Handling**: Validates robust exception catching and return formats
  - **Crypto Safety**: Ensures required safety checks (slippage, allowance, tx verification)
  - **Live Endpoints**: Verifies API connectivity with exponential backoff
  - **Cross-Skill Consistency**: Enforces uniform patterns across all skills
  - **Security Audit**: Checks for hardcoded secrets, injection risks, and path traversal
- Added `conftest.py` for shared pytest fixtures.

### 🛡️ Production Patches
- `patches/shared/`:
  - `errors.py`: Standardized error return structures.
  - `crypto_safety.py`: Core safety validators for EVM transactions.
  - `response.py`: Uniform JSON-serializable response formatting.
  - `retry.py`: Exponential backoff decorators for rate limits.
  - `validators.py`: Input validation for addresses and amounts.
- **Twitter Skill**: Added rate limit (HTTP 429) handling and retry logic to `client.py` (via patch).

All 117 tests are currently passing. Ready for review.""",
    "head": "AaronBoat:feat/audit-v2-rebased",
    "base": "main"
}

url = "https://api.github.com/repos/Starchild-ai-agent/official-skills/pulls"
response = requests.post(url, headers=headers, json=data)

if response.status_code == 201:
    print(f"✅ PR Created Successfully! URL: {response.json()['html_url']}")
else:
    print(f"❌ Failed to create PR: {response.status_code}")
    print(response.text)
