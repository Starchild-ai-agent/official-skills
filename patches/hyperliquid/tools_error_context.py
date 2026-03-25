"""
Hyperliquid tools.py — Structured Error Context Upgrade
========================================================
All 21 tool functions use the same pattern:
    except Exception as e:
        return ToolResult(success=False, error=str(e))

str(e) is often cryptic: "float() argument must be a string or a number, not 'NoneType'"
Small models can't diagnose from that.

UPGRADE PATTERN:
    except Exception as e:
        return ToolResult(success=False, error=_format_error("hl_account", e, context))

Where _format_error classifies and enriches the error message.
"""

# ── Add this helper function at the top of tools.py ──

HELPER_FUNCTION = '''
def _format_error(tool_name: str, error: Exception, context: dict = None) -> str:
    """
    Format exception into small-model-friendly error message.
    Classifies common Hyperliquid errors and adds actionable suggestions.
    """
    err_str = str(error)
    err_type = type(error).__name__
    ctx_str = ""
    if context:
        ctx_str = " | ".join(f"{k}={v}" for k, v in context.items() if v is not None)

    # ── Classification ──
    classified = _classify_hl_error(err_str, err_type)

    parts = [f"❌ {tool_name}: {classified['message']}"]
    if ctx_str:
        parts.append(f"  Context: {ctx_str}")
    if classified.get('suggestion'):
        parts.append(f"  → {classified['suggestion']}")
    if classified.get('code'):
        parts.append(f"  Error code: {classified['code']}")

    return "\\n".join(parts)


def _classify_hl_error(err_str: str, err_type: str) -> dict:
    """Classify Hyperliquid errors into actionable categories."""
    err_lower = err_str.lower()

    # Asset not found
    if 'asset' in err_lower and ('not found' in err_lower or 'unknown' in err_lower):
        return {
            "code": "ASSET_NOT_FOUND",
            "message": err_str,
            "suggestion": "Check coin symbol. Use exact ticker (e.g., 'BTC' not 'bitcoin'). "
                         "For spot: use base symbol (e.g., 'PURR' not 'PURR/USDC')"
        }

    # Insufficient margin/balance
    if 'insufficient' in err_lower or 'not enough' in err_lower or 'margin' in err_lower:
        return {
            "code": "INSUFFICIENT_MARGIN",
            "message": err_str,
            "suggestion": "Check available balance with hl_account. "
                         "Reduce position size or deposit more USDC."
        }

    # Price/size validation
    if 'price' in err_lower and ('invalid' in err_lower or 'must be' in err_lower):
        return {
            "code": "INVALID_PRICE",
            "message": err_str,
            "suggestion": "Price must match tick size. Use hl_market to check "
                         "min price increment for this asset."
        }
    if 'size' in err_lower and ('min' in err_lower or 'too small' in err_lower):
        return {
            "code": "SIZE_TOO_SMALL",
            "message": err_str,
            "suggestion": "Order size below minimum. Use hl_market to check "
                         "minimum order size for this asset."
        }

    # Rate limiting
    if '429' in err_str or 'rate limit' in err_lower:
        return {
            "code": "RATE_LIMITED",
            "message": "Hyperliquid API rate limit hit",
            "suggestion": "Wait 5-10 seconds and retry. Reduce request frequency."
        }

    # Connection issues
    if 'timeout' in err_lower or 'connection' in err_lower:
        return {
            "code": "CONNECTION_ERROR",
            "message": f"Connection to Hyperliquid failed: {err_str}",
            "suggestion": "Retry in a few seconds. If persistent, Hyperliquid API may be down."
        }

    # Nonce/signing errors
    if 'nonce' in err_lower or 'signature' in err_lower or 'signing' in err_lower:
        return {
            "code": "SIGNING_ERROR",
            "message": err_str,
            "suggestion": "This is usually a transient issue. Retry the operation."
        }

    # Order already cancelled/filled
    if 'cancel' in err_lower and ('not found' in err_lower or 'already' in err_lower):
        return {
            "code": "ORDER_NOT_ACTIVE",
            "message": err_str,
            "suggestion": "Order may already be filled or cancelled. "
                         "Check hl_open_orders and hl_fills."
        }

    # Type errors (usually from None responses)
    if err_type in ('TypeError', 'AttributeError') and 'none' in err_lower:
        return {
            "code": "NULL_RESPONSE",
            "message": f"Unexpected null value: {err_str}",
            "suggestion": "The API returned an unexpected format. "
                         "This may be a transient issue — retry once."
        }

    # Default: include raw error but still structured
    return {
        "code": "UNKNOWN",
        "message": f"{err_type}: {err_str}",
        "suggestion": "Unexpected error. Check parameters and retry."
    }
'''


# ── Example: How to patch each tool function ──

EXAMPLE_BEFORE = '''
    async def execute(self, ctx: ToolContext, dex: str = "", **kwargs) -> ToolResult:
        try:
            client = _get_client()
            address = await _get_address()
            data = await client.get_account_state(address, dex=dex if dex else None)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
'''

EXAMPLE_AFTER = '''
    async def execute(self, ctx: ToolContext, dex: str = "", **kwargs) -> ToolResult:
        try:
            client = _get_client()
            address = await _get_address()
            data = await client.get_account_state(address, dex=dex if dex else None)
            return ToolResult(success=True, output=data)
        except Exception as e:
            return ToolResult(success=False, error=_format_error(
                "hl_account", e, {"dex": dex, "address": address[:10] + "..."}
            ))
'''


# ── Full list of tools to patch (tool_name, context_vars) ──

TOOLS_TO_PATCH = [
    ("hl_account", {"dex": "dex"}),
    ("hl_balances", {}),
    ("hl_open_orders", {"dex": "dex"}),
    ("hl_market", {"coin": "coin"}),
    ("hl_orderbook", {"coin": "coin"}),
    ("hl_fills", {"coin": "coin"}),
    ("hl_candles", {"coin": "coin", "interval": "interval"}),
    ("hl_funding", {"coin": "coin"}),
    ("hl_order", {"coin": "coin", "side": "side", "size": "sz", "price": "px"}),
    ("hl_spot_order", {"coin": "coin", "side": "side", "size": "sz"}),
    ("hl_tpsl_order", {"coin": "coin", "side": "side", "tp": "tp_px", "sl": "sl_px"}),
    ("hl_cancel", {"coin": "coin", "oid": "oid"}),
    ("hl_cancel_all", {"coin": "coin"}),
    ("hl_modify", {"oid": "oid", "coin": "coin"}),
    ("hl_leverage", {"coin": "coin", "leverage": "leverage"}),
    ("hl_transfer_usd", {"amount": "amount", "direction": "direction"}),
    ("hl_withdraw", {"amount": "amount", "destination": "destination"}),
    ("hl_deposit", {"amount": "amount"}),
]
