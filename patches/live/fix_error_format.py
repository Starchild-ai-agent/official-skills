"""
FIX-5: Unified Error Response Format

BUG-5: Different tool families return errors in different formats:
  - Coinglass: "❌ Error: Failed to fetch X. Check API_KEY."
  - CoinGecko: HTTP status + raw JSON
  - Hyperliquid: Python exception strings

This normalizer wraps any error into a consistent schema.
"""

import json


def normalize_error(raw_output, tool_name: str = "", symbol: str = "") -> dict:
    """
    Normalize any error output into a unified schema.

    Returns:
        {
            "error": True,
            "tool": str,
            "category": "auth" | "invalid_input" | "rate_limit" | "network" | "upstream" | "unknown",
            "message": str,      # human-readable
            "suggestion": str,   # actionable fix
            "raw": str           # original error for debugging
        }
    """
    if raw_output is None:
        return _build_error(tool_name, "unknown", "Tool returned None",
                            "Check tool parameters and retry", "None")

    raw_str = raw_output if isinstance(raw_output, str) else json.dumps(raw_output)

    # Not an error — pass through
    if not _is_error(raw_str, raw_output):
        return raw_output

    # Classify the error
    category, message, suggestion = _classify(raw_str, symbol)

    return _build_error(tool_name, category, message, suggestion, raw_str[:500])


def _is_error(raw_str: str, raw_output) -> bool:
    """Detect if the output is an error."""
    error_signals = [
        "❌", "error", "failed", "exception", "traceback",
        "timeout", "timed out", "429", "500", "502", "503", "401", "403"
    ]
    if isinstance(raw_output, dict):
        if raw_output.get("error"):
            return True
        if raw_output.get("code") and str(raw_output.get("code")) not in ("0", "200"):
            return True
    return any(signal.lower() in raw_str.lower() for signal in error_signals)


def _classify(raw_str: str, symbol: str) -> tuple:
    """Classify error into category with message and suggestion."""
    raw_lower = raw_str.lower()

    if "api_key" in raw_lower or "api key" in raw_lower or "401" in raw_str or "403" in raw_str:
        if symbol:
            from fix_error_messages import reclassify_error
            result = reclassify_error(raw_str, symbol)
            if result["is_reclassified"]:
                return result["category"], result["fixed"], "Verify symbol is valid"
        return (
            "auth",
            "Authentication issue with upstream API",
            "This is managed by the platform. Retry or contact support."
        )

    if "429" in raw_str or "rate limit" in raw_lower:
        return "rate_limit", "Rate limit exceeded", "Wait 30-60 seconds before retrying"

    if "timeout" in raw_lower or "timed out" in raw_lower:
        return "network", "Request timed out", "Retry. If persistent, upstream may be under load."

    if any(code in raw_str for code in ["500", "502", "503"]):
        return "upstream", "Upstream API server error", "Retry in 30s. Not a local issue."

    if "not found" in raw_lower or "invalid" in raw_lower:
        return "invalid_input", "Invalid parameter", f"Check symbol/parameters. Symbol: '{symbol}'"

    return "unknown", raw_str[:200], "Check parameters and retry"


def _build_error(tool: str, category: str, message: str, suggestion: str, raw: str) -> dict:
    return {
        "error": True,
        "tool": tool,
        "category": category,
        "message": message,
        "suggestion": suggestion,
        "raw": raw
    }


# ─── Self-test ───────────────────────────────────────────
if __name__ == "__main__":
    # Test 1: Coinglass-style error
    r1 = normalize_error("❌ Error: Failed to fetch open interest. Check COINGLASS_API_KEY.",
                         tool_name="cg_open_interest", symbol="INVALIDCOIN999")
    assert r1["error"] is True
    assert r1["category"] == "invalid_symbol"
    print(f"✅ BUG-5 test 1: Coinglass error → category='{r1['category']}'")

    # Test 2: Timeout error
    r2 = normalize_error("Connection timed out after 30s", tool_name="cg_coin_data")
    assert r2["category"] == "network"
    print(f"✅ BUG-5 test 2: Timeout → category='{r2['category']}'")

    # Test 3: Rate limit
    r3 = normalize_error("HTTP 429: Too Many Requests", tool_name="coin_price")
    assert r3["category"] == "rate_limit"
    print(f"✅ BUG-5 test 3: 429 → category='{r3['category']}'")

    # Test 4: Non-error passes through
    r4 = normalize_error({"symbol": "BTC", "price": 71000}, tool_name="coin_price")
    assert r4 == {"symbol": "BTC", "price": 71000}
    print("✅ BUG-5 test 4: Non-error passed through unchanged")

    print("\n🎯 All error normalization patches pass self-test")
