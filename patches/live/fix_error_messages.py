"""
FIX-3: Error Message Reclassification

BUG-3: Invalid coin symbols trigger "Check API KEY" error messages.
This patch post-processes error strings to give accurate diagnosis.
"""


# Known patterns of misleading errors
ERROR_PATTERNS = [
    {
        "match": r"Failed to fetch .+\. Check (\w+_API_KEY)",
        "conditions": {
            "has_invalid_symbol": True
        },
        "replacement": "Symbol '{symbol}' not found. Use cg_supported_coins() to see valid symbols.",
        "category": "invalid_input"
    },
    {
        "match": r"Check (\w+_API_KEY)",
        "conditions": {
            "http_status": 500
        },
        "replacement": (
            "Server error from upstream API (HTTP 500). "
            "This usually means invalid parameters, not an API key issue. "
            "Verify your inputs."
        ),
        "category": "upstream_error"
    }
]

# Coins we know are valid (cached; expandable)
KNOWN_VALID_COINS = {
    "BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "AVAX", "DOT", "LINK",
    "MATIC", "UNI", "AAVE", "ARB", "OP", "APT", "SUI", "NEAR", "ATOM",
    "FIL", "LTC", "BCH", "ETC", "TRX", "SHIB", "PEPE", "WIF", "BONK",
    "HYPE", "JUP", "RENDER", "INJ", "FET", "TAO", "WLD", "TIA", "SEI"
}


def reclassify_error(error_msg: str, symbol: str = None) -> dict:
    """
    Takes a raw error message and returns a structured, accurate diagnosis.

    Returns:
        {
            "original": str,        # raw error
            "fixed": str,           # corrected message
            "category": str,        # error type
            "is_reclassified": bool # whether we changed it
        }
    """
    if not isinstance(error_msg, str):
        return {"original": str(error_msg), "fixed": str(error_msg),
                "category": "unknown", "is_reclassified": False}

    # Check if this is a misleading "API KEY" error
    if "Check" in error_msg and "API_KEY" in error_msg:
        # Is the symbol potentially invalid?
        if symbol and symbol.upper() not in KNOWN_VALID_COINS:
            return {
                "original": error_msg,
                "fixed": f"Symbol '{symbol}' not recognized. Use cg_supported_coins() to verify valid symbols. "
                         "Common symbols: BTC, ETH, SOL, XRP, DOGE, etc.",
                "category": "invalid_symbol",
                "is_reclassified": True
            }
        else:
            # Symbol looks valid — might actually be an API issue
            return {
                "original": error_msg,
                "fixed": (
                    f"API error occurred. If symbol '{symbol}' is correct, "
                    "this may be a temporary upstream issue. Retry in 30s."
                ),
                "category": "possible_api_error",
                "is_reclassified": True
            }

    return {"original": error_msg, "fixed": error_msg,
            "category": "other", "is_reclassified": False}


# ─── Self-test ───────────────────────────────────────────
if __name__ == "__main__":
    # Test 1: Invalid coin with misleading API KEY error
    result = reclassify_error(
        "❌ Error: Failed to fetch open interest. Check COINGLASS_API_KEY.",
        symbol="INVALIDCOIN999"
    )
    assert result["is_reclassified"] is True
    assert result["category"] == "invalid_symbol"
    assert "not recognized" in result["fixed"]
    print(f"✅ BUG-3 test 1: '{result['category']}' → {result['fixed'][:60]}...")

    # Test 2: Valid coin with same error (keep as API issue)
    result2 = reclassify_error(
        "❌ Error: Failed to fetch open interest. Check COINGLASS_API_KEY.",
        symbol="BTC"
    )
    assert result2["category"] == "possible_api_error"
    print(f"✅ BUG-3 test 2: '{result2['category']}' (correctly preserved as API issue)")

    # Test 3: Non-matching error (pass through)
    result3 = reclassify_error("Network timeout after 30s", symbol="BTC")
    assert result3["is_reclassified"] is False
    print("✅ BUG-3 test 3: non-matching error passed through correctly")

    print("\n🎯 All error reclassification patches pass self-test")
