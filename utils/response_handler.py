"""
Starchild Response Handler — Middleware Interceptor
=====================================================
Sits between raw API tool output and Agent consumption.
Enforces: schema normalization, size budgets, error reclassification.

Usage:
    from utils.response_handler import intercept
    clean = intercept(tool_name, raw_response)
"""

import json

# ─────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────
MAX_RESPONSE_CHARS = 8000          # Hard ceiling for LLM context
MAX_LIST_ITEMS_DEFAULT = 10        # Default truncation for lists
MAX_LIST_ITEMS_SMALL_MODEL = 5     # For gemini-flash / gpt-4o-mini


KNOWN_LARGE_TOOLS = {
    "cg_whale_transfers": 5,
    "cg_coin_netflow": 10,
    "cg_hyperliquid_whale_positions": 10,
    "cg_hyperliquid_whale_alerts": 10,
    "funding_rate": None,           # handled by field filter
    "cg_coins_market_data": 10,
}

# ─────────────────────────────────────────────────
# Module A: Liquidation Zero-Value Isolation
# ─────────────────────────────────────────────────


def process_liquidation_data(data: dict) -> dict:
    """
    Immutable Logic Module A.
    Prevents false signals when liquidation data is missing or incomplete.
    """
    total = data.get("total_liquidations_usd", 0)
    longs = data.get("long_liquidations_usd", 0)
    shorts = data.get("short_liquidations_usd", 0)

    # Case 1: No data at all
    if total == 0 and longs == 0 and shorts == 0:
        # Check exchange-level data for hidden totals
        exchanges = data.get("exchanges", [])
        recomputed = sum(
            float(e.get("total_liquidation_usd", 0) or
                  e.get("liquidation_usd", 0) or 0)
            for e in exchanges if isinstance(e, dict)
        )
        if recomputed > 0:
            return {
                **data,
                "total_liquidations_usd": recomputed,
                "dominant_side": "unknown",
                "sentiment": "data_partial",
                "interpretation": (
                    f"${recomputed:,.0f} total liquidations detected from exchange breakdown, "
                    "but long/short split unavailable from upstream API."
                ),
                "_patch": "module_a_recomputed"
            }
        return {
            **data,
            "sentiment": "neutral",
            "dominant_side": "none",
            "interpretation": "No significant liquidations detected in this time window.",
            "_patch": "module_a_zero"
        }

    # Case 2: Total > 0 but split is zero (structural data loss)
    if total > 0 and longs == 0 and shorts == 0:
        return {
            **data,
            "total_liquidations_usd": total,
            "dominant_side": "unknown",
            "sentiment": "data_partial",
            "interpretation": (
                f"${total:,.0f} total liquidations detected but exchange breakdown "
                "unavailable. Monitoring total volume only."
            ),
            "_patch": "module_a_partial"
        }

    # Case 3: Normal — both sides have data
    if total > 0 and (longs > 0 or shorts > 0):
        long_ratio = longs / total if total > 0 else 0
        short_ratio = shorts / total if total > 0 else 0
        if long_ratio > 0.65:
            side, sentiment = "longs", "bearish_pressure"
        elif short_ratio > 0.65:
            side, sentiment = "shorts", "bullish_pressure"
        else:
            side, sentiment = "balanced", "neutral"
        return {
            **data,
            "dominant_side": side,
            "long_ratio": round(long_ratio, 4),
            "short_ratio": round(short_ratio, 4),
            "sentiment": sentiment,
            "interpretation": (
                f"${total:,.0f} liquidated — "
                f"{long_ratio:.0%} longs / {short_ratio:.0%} shorts. "
                f"{'Long squeeze dominant.' if side == 'longs' else 'Short squeeze dominant.' if side == 'shorts' else 'Balanced liquidations.'}"  # noqa: E501
            ),
            "_patch": "module_a_normal"
        }

    return {**data, "_patch": "module_a_passthrough"}


# ─────────────────────────────────────────────────
# Module B: Response Size Budget Enforcer
# ─────────────────────────────────────────────────
def enforce_model_budget(data, tool_name=None, max_items=None):
    """
    Immutable Logic Module B.
    Truncates large list responses for LLM context safety.
    """
    if max_items is None:
        max_items = KNOWN_LARGE_TOOLS.get(tool_name, MAX_LIST_ITEMS_DEFAULT)
    if max_items is None:
        max_items = MAX_LIST_ITEMS_DEFAULT

    # Handle dict with 'data' key (Coinglass format)
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
        inner = data["data"]
        if len(inner) > max_items:
            data = {
                **data,
                "data": inner[:max_items],
                "_truncation": {
                    "total_found": len(inner),
                    "displayed": max_items,
                    "notice": (
                        f"Results truncated from {len(inner)} to "
                        f"{max_items} for LLM context. "
                        "Use symbol/limit filters for more."
                    )
                }
            }
        return data

    # Handle raw list
    if isinstance(data, list) and len(data) > max_items:
        return {
            "results": data[:max_items],
            "metadata": {
                "total_found": len(data),
                "displayed": max_items,
                "notice": (
                    f"Results truncated from {len(data)} to "
                    f"{max_items} for LLM context. "
                    "Use specific filters for more."
                )
            }
        }

    # Final char-level guard
    serialized = json.dumps(data, default=str) if not isinstance(data, str) else data
    if len(serialized) > MAX_RESPONSE_CHARS:
        if isinstance(data, dict):
            # Try to slim down by removing heavy nested arrays
            slimmed = {}
            for k, v in data.items():
                if isinstance(v, list) and len(v) > max_items:
                    slimmed[k] = v[:max_items]
                    slimmed[f"_{k}_truncated"] = f"{len(v)} → {max_items}"
                else:
                    slimmed[k] = v
            return slimmed
        return serialized[:MAX_RESPONSE_CHARS] + "\n... [TRUNCATED]"

    return data


# ─────────────────────────────────────────────────
# Module C: Error Attribution Redirector
# ─────────────────────────────────────────────────

# Fallback coin list for when cg_supported_coins() is unavailable
TOP_COINS_FALLBACK = {
    "BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "AVAX", "DOT", "LINK",
    "MATIC", "UNI", "ATOM", "LTC", "BCH", "NEAR", "FIL", "APT", "ARB",
    "OP", "SUI", "SEI", "TIA", "JUP", "WLD", "PEPE", "WIF", "BONK",
    "SHIB", "FET", "RNDR", "INJ", "TRX", "TON", "HBAR", "VET", "ALGO",
    "FTM", "SAND", "MANA", "AXS", "CRV", "AAVE", "MKR", "SNX", "COMP",
    "LDO", "RPL", "SSV", "PENDLE", "GMX", "DYDX", "1INCH", "SUSHI",
    "BNB", "ETC", "XLM", "EOS", "IOTA", "XTZ", "THETA", "GRT",
    "HYPE", "KAITO", "AI16Z", "VIRTUAL", "TAO", "RENDER", "ONDO",
}


def handle_api_error(error_msg: str, symbol: str = None, tool_name: str = None) -> dict:
    """
    Immutable Logic Module C.
    Reclassifies misleading errors. In sc-proxy environment,
    API key errors are almost always parameter errors.
    """
    msg_lower = error_msg.lower() if error_msg else ""

    # Pattern 1: Symbol validation
    if symbol and symbol.upper() not in TOP_COINS_FALLBACK:
        return {
            "status": "error",
            "category": "invalid_symbol",
            "message": f"Symbol '{symbol}' not recognized. Verify with cg_supported_coins().",
            "original_error": error_msg,
            "_patch": "module_c"
        }

    # Pattern 2: Misleading "API Key" errors (sc-proxy handles keys)
    if "api key" in msg_lower or "check.*key" in msg_lower or "apikey" in msg_lower:
        return {
            "status": "error",
            "category": "param_error",
            "message": (
                "Target resource not found or input parameter "
                "invalid. In Starchild environment, API keys are "
                "managed by sc-proxy — this is likely a parameter issue."
            ),
            "original_error": error_msg,
            "_patch": "module_c"
        }

    # Pattern 3: Rate limiting
    if "429" in msg_lower or "rate limit" in msg_lower or "too many" in msg_lower:
        return {
            "status": "error",
            "category": "rate_limit",
            "message": "Rate limited. Wait 30 seconds and retry.",
            "original_error": error_msg,
            "_patch": "module_c"
        }

    # Pattern 4: Network
    if any(kw in msg_lower for kw in ["timeout", "timed out", "connection", "network", "dns", "502", "503"]):
        return {
            "status": "error",
            "category": "network",
            "message": "Network or upstream service issue. Retry in 60 seconds.",
            "original_error": error_msg,
            "_patch": "module_c"
        }

    # Default
    return {
        "status": "error",
        "category": "unknown",
        "message": error_msg,
        "_patch": "module_c"
    }


# ─────────────────────────────────────────────────
# Module D: Funding Rate APR Normalizer
# ─────────────────────────────────────────────────

# Known funding intervals by exchange (hours)
EXCHANGE_INTERVALS = {
    "Binance": 8, "OKX": 8, "Bybit": 8, "Gate": 8, "Bitget": 8,
    "MEXC": 8, "BingX": 8, "CoinEx": 8, "BitMart": 8, "LBank": 8,
    "Phemex": 8, "XT": 8, "Coinbase": 8,
    "Hyperliquid": 1, "dYdX": 1, "Vertex": 1, "Aevo": 1, "Drift": 1,
    "Kraken": 1, "Bitfinex": 8,
    "HTX": 8, "KuCoin": 8,
}

DEFAULT_INTERVAL = 8  # Assume 8h if unknown


def normalize_funding(rate: float, interval_hrs: float = None, exchange: str = None) -> dict:
    """
    Immutable Logic Module D.
    Normalizes funding rates to 8h equivalent and annualized APR.
    """
    if interval_hrs is None:
        interval_hrs = EXCHANGE_INTERVALS.get(exchange, DEFAULT_INTERVAL)

    rate_8h = rate * (8.0 / interval_hrs)
    apr = rate_8h * 3.0 * 365.0  # 3 funding events per day × 365 days

    return {
        "raw_rate": rate,
        "interval": f"{interval_hrs}h",
        "normalized_8h": round(rate_8h, 8),
        "normalized_8h_pct": f"{rate_8h:.6%}",
        "annualized_apr": round(apr, 4),
        "annualized_apr_pct": f"{apr:.2%}",
        "exchange": exchange,
        "_patch": "module_d"
    }


def normalize_funding_response(funding_data: dict) -> dict:
    """
    Apply Module D to an entire funding_rate() response.
    Adds normalized fields to every exchange entry.
    """
    if not isinstance(funding_data, dict) or "data" not in funding_data:
        return funding_data

    for coin_entry in funding_data.get("data", []):
        for margin_type in ["uMarginList", "cMarginList"]:
            for entry in coin_entry.get(margin_type, []):
                exchange = entry.get("exchangeName", "")
                raw_rate = entry.get("rate", 0)
                if raw_rate is None:
                    continue
                try:
                    raw_rate = float(raw_rate)
                except (ValueError, TypeError):
                    continue
                norm = normalize_funding(raw_rate, exchange=exchange)
                entry["normalized_8h"] = norm["normalized_8h"]
                entry["annualized_apr"] = norm["annualized_apr"]
                entry["annualized_apr_pct"] = norm["annualized_apr_pct"]
                entry["funding_interval_h"] = norm["interval"]
                entry["_patch"] = "module_d"

    return funding_data


# ─────────────────────────────────────────────────
# Master Interceptor
# ─────────────────────────────────────────────────
def intercept(tool_name: str, response, symbol: str = None) -> dict:
    """
    Master middleware — routes response through applicable modules.

    Usage:
        raw = cg_liquidations(symbol="BTC")
        clean = intercept("cg_liquidations", raw, symbol="BTC")
    """
    result = response

    # Error interception (Module C)
    error_keywords = ["error", "failed", "❌", "traceback", "exception"]
    if isinstance(result, str) and any(kw in result.lower() for kw in error_keywords):
        return handle_api_error(result, symbol=symbol, tool_name=tool_name)

    if isinstance(result, dict) and result.get("status") == "error":
        return handle_api_error(
            result.get("message", str(result)),
            symbol=symbol, tool_name=tool_name
        )

    # Liquidation processing (Module A)
    if tool_name in ("cg_liquidations", "cg_liquidation_analysis"):
        if isinstance(result, dict):
            result = process_liquidation_data(result)

    # Funding normalization (Module D)
    if tool_name in ("funding_rate",):
        if isinstance(result, dict):
            result = normalize_funding_response(result)

    # Size guard (Module B) — always last
    result = enforce_model_budget(result, tool_name=tool_name)

    return result
