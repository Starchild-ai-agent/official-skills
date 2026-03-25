"""
Test config — paths and constants
"""
import os

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "repo")
SKILLS_WITH_CODE = [
    "1inch", "aave", "birdeye", "coingecko", "coinglass",
    "debank", "hyperliquid", "lunarcrush", "polymarket",
    "taapi", "twelvedata", "twitter"
]
CRYPTO_CORE_SKILLS = ["hyperliquid", "coingecko", "coinglass", "1inch", "aave", "debank", "birdeye"]

# Scoring weights (small-model friendliness)
WEIGHTS = {
    "error_handling": 25,    # Silent failures kill small models
    "return_format": 25,     # Inconsistent formats confuse small models
    "skill_doc": 25,         # Bad docs = wrong tool selection
    "tool_interface": 25,    # Unclear params = wrong calls
}
