"""
Coinglass — Eliminate `return None` Error Pattern
===================================================
问题: coinglass 有 112 处 `return None` on error，小模型收到 None 后
无法区分 "无数据" vs "API 错误" vs "参数错误"。

修复策略: 所有 API 调用函数应该 return 统一的 error dict 而不是 None。
tool 层再决定如何格式化给模型。

影响范围: 6 个文件，61 个 except 块
"""

# ── Pattern: Replace return None with structured error ──

BEFORE_PATTERN = '''
    try:
        response = proxied_get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        return None
'''

AFTER_PATTERN = '''
    try:
        response = proxied_get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        # Coinglass wraps data in {"code": "0", "data": ...}
        if isinstance(data, dict):
            if data.get("code") not in ("0", 0, None):
                return {
                    "_error": True,
                    "code": data.get("code"),
                    "message": data.get("msg", "Unknown API error"),
                    "suggestion": "Check parameters or API status"
                }
            # Unwrap if wrapped
            if "data" in data and data.get("code") in ("0", 0):
                return data["data"]
        return data
    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, 'status_code', None)
        return {
            "_error": True,
            "code": f"HTTP_{status}" if status else "HTTP_ERROR",
            "message": f"Coinglass API returned HTTP {status}: {e}",
            "suggestion": _suggestion_for_status(status)
        }
    except requests.exceptions.RequestException as e:
        return {
            "_error": True,
            "code": "CONNECTION_ERROR",
            "message": f"Failed to connect to Coinglass: {type(e).__name__}: {e}",
            "suggestion": "Check network connectivity. Retry in 30 seconds."
        }
    except json.JSONDecodeError as e:
        return {
            "_error": True,
            "code": "PARSE_ERROR",
            "message": f"Invalid JSON from Coinglass API: {e}",
            "suggestion": "API may be returning an error page. Try again later."
        }
    except Exception as e:
        return {
            "_error": True,
            "code": "UNKNOWN",
            "message": f"{type(e).__name__}: {e}",
            "suggestion": "Unexpected error. Report if persistent."
        }
'''


# ── Helper function to add to each tools file ──

HELPER = '''
def _suggestion_for_status(status: int) -> str:
    """Map HTTP status to actionable suggestion."""
    if status == 401:
        return "API key may be invalid or expired. Check COINGLASS_API_KEY."
    if status == 403:
        return "Access denied. This endpoint may require a paid plan."
    if status == 429:
        return "Rate limited. Wait 60 seconds before retrying."
    if status in (500, 502, 503):
        return "Coinglass server error. Try again in 1-2 minutes."
    if status == 404:
        return "Endpoint not found. The API may have changed."
    return f"HTTP {status} error. Check Coinglass API status."


def _check_cg_response(data) -> str:
    """
    Tool-level helper: check if an API response is an error dict.
    Returns error message string if error, empty string if OK.

    Usage in tool execute():
        data = get_funding_rate("BTC")
        err = _check_cg_response(data)
        if err:
            return ToolResult(success=False, error=err)
        # proceed with data...
    """
    if data is None:
        return "❌ coinglass: API returned empty response. Service may be down."
    if isinstance(data, dict) and data.get("_error"):
        code = data.get("code", "UNKNOWN")
        msg = data.get("message", "Unknown error")
        suggestion = data.get("suggestion", "")
        parts = [f"❌ [{code}] coinglass: {msg}"]
        if suggestion:
            parts.append(f"  → {suggestion}")
        return "\\n".join(parts)
    return ""  # No error
'''


# ── Files to patch ──

FILES_AND_RETURN_NONE_COUNT = {
    "coinglass/tools/bitcoin_etf.py": 18,
    "coinglass/tools/funding_rate.py": 8,
    "coinglass/tools/futures_market.py": 22,
    "coinglass/tools/hyperliquid.py": 14,
    "coinglass/tools/liquidation.py": 20,
    "coinglass/tools/market_data.py": 16,
    "coinglass/tools/open_interest.py": 14,
}

# NOTE: Each file follows the same pattern — apply AFTER_PATTERN to replace
# every `except ... return None` block. The helper functions go at file top.


# ── Migration script ──

MIGRATION_SCRIPT = '''#!/bin/bash
# Semi-automated migration: adds _error checking at tool level
# Run from repo root: bash patches/coinglass/migrate.sh

echo "Coinglass error handling migration"
echo "==================================="

# For each tool file, count current `return None` patterns
for f in coinglass/tools/*.py; do
    count=$(grep -c "return None" "$f" 2>/dev/null || echo 0)
    if [ "$count" -gt "0" ]; then
        echo "  $f: $count return-None patterns to fix"
    fi
done

echo ""
echo "Manual steps:"
echo "1. Add _suggestion_for_status() and _check_cg_response() to each file"
echo "2. Replace each try/except block with AFTER_PATTERN"
echo "3. In tool execute() methods, add _check_cg_response() guard"
echo "4. Run test suite to verify no regressions"
'''
