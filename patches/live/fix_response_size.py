"""
FIX-4: Response Size Guard for Small Models

BUG-4: Some tool outputs are 25K-400K chars — kills small models.
This patch provides smart truncation that preserves value.
"""

import json

# Token budgets by model class
MODEL_BUDGETS = {
    "small": 2000,   # ~1500 chars — Gemini Flash Lite, GPT-3.5
    "medium": 8000,   # ~6000 chars — Claude Haiku, GPT-4-mini
    "large": 32000,  # ~24000 chars — Claude Sonnet, GPT-4o
}

CHAR_PER_TOKEN = 3.5  # rough average for JSON data


def truncate_response(data, model_class: str = "small", context: str = ""):
    """
    Smart truncation that preserves the most useful information.

    For funding rates: keep top 5 exchanges by relevance (Binance, OKX, Bybit, Coinbase, Hyperliquid)
    For market data: keep top 10 by market cap
    For liquidations: keep top 5 exchanges by volume
    """
    budget_tokens = MODEL_BUDGETS.get(model_class, MODEL_BUDGETS["medium"])
    budget_chars = int(budget_tokens * CHAR_PER_TOKEN)

    raw = json.dumps(data) if not isinstance(data, str) else data

    if len(raw) <= budget_chars:
        return data  # fits fine

    # Deep copy if dict
    if isinstance(data, dict):
        return _truncate_dict(data, budget_chars, context)
    elif isinstance(data, list):
        return _truncate_list(data, budget_chars)
    else:
        return raw[:budget_chars] + f"\n... [truncated, {len(raw) - budget_chars} chars omitted]"


def _truncate_dict(d: dict, budget: int, context: str) -> dict:
    """Smart truncation for dict responses."""
    result = {}

    # Priority keys — always include these
    priority_keys = {"symbol", "code", "msg", "error", "analysis", "sentiment",
                     "total_liquidations_usd", "long_percent", "short_percent",
                     "uIndexPrice", "uPrice"}

    # First pass: include priority keys
    for k in priority_keys:
        if k in d:
            result[k] = d[k]

    # Handle funding rate data specially
    if "data" in d and isinstance(d["data"], list):
        for item in d["data"]:
            if isinstance(item, dict) and "uMarginList" in item:
                # Funding rate response — keep top 5 exchanges
                top_exchanges = {"Binance", "OKX", "Bybit", "Hyperliquid", "Coinbase"}
                item_copy = {k: v for k, v in item.items() if k != "uMarginList" and k != "cMarginList"}

                u_list = item.get("uMarginList", [])
                c_list = item.get("cMarginList", [])

                item_copy["uMarginList"] = [
                    ex for ex in u_list
                    if ex.get("exchangeName") in top_exchanges
                ][:5]
                item_copy["cMarginList"] = [
                    ex for ex in c_list
                    if ex.get("exchangeName") in top_exchanges
                ][:3]

                omitted_u = len(u_list) - len(item_copy["uMarginList"])
                omitted_c = len(c_list) - len(item_copy["cMarginList"])
                item_copy["_truncated"] = f"{omitted_u} USDT-margin + {omitted_c} coin-margin exchanges omitted"

                result["data"] = [item_copy]
                return result

    # Handle exchanges list
    if "exchanges" in d and isinstance(d["exchanges"], list):
        exs = d["exchanges"]
        # Sort by total, keep top 5
        sorted_exs = sorted(exs, key=lambda x: x.get("total_liquidations_usd", 0), reverse=True)[:5]
        result["exchanges"] = sorted_exs
        result["_truncated"] = f"Showing top 5 of {len(exs)} exchanges"

    # Add remaining keys that fit
    current_size = len(json.dumps(result))
    for k, v in d.items():
        if k not in result and current_size < budget:
            trial = json.dumps(v)
            if current_size + len(trial) < budget:
                result[k] = v
                current_size += len(trial)

    return result


def _truncate_list(lst: list, budget: int) -> list:
    """Keep first N items that fit in budget."""
    result = []
    current_size = 2  # []
    for item in lst:
        item_size = len(json.dumps(item))
        if current_size + item_size > budget:
            result.append({"_truncated": f"{len(lst) - len(result)} more items omitted"})
            break
        result.append(item)
        current_size += item_size
    return result


# ─── Self-test ───────────────────────────────────────────
if __name__ == "__main__":
    # Test 1: Funding rate truncation
    large_funding = {
        "code": "0", "msg": "success",
        "data": [{
            "symbol": "BTC",
            "uMarginList": [
                {"exchangeName": "Binance", "rate": 0.0004, "fundingIntervalHours": 8},
                {"exchangeName": "OKX", "rate": -0.005, "fundingIntervalHours": 8},
                {"exchangeName": "Bybit", "rate": 0.007, "fundingIntervalHours": 8},
                {"exchangeName": "Hyperliquid", "rate": 0.00125, "fundingIntervalHours": 1},
                {"exchangeName": "Coinbase", "rate": 0.0012, "fundingIntervalHours": 1},
                {"exchangeName": "MEXC", "rate": 0.0004, "fundingIntervalHours": 8},
                {"exchangeName": "BingX", "rate": 0.0075, "fundingIntervalHours": 8},
                {"exchangeName": "Gate", "rate": 0.0037, "fundingIntervalHours": 8},
                {"exchangeName": "Kraken", "rate": 0.000127, "fundingIntervalHours": 1},
                {"exchangeName": "dYdX", "rate": -0.00276, "fundingIntervalHours": 1},
            ] * 2,  # 20 exchanges
            "cMarginList": [
                {"exchangeName": "Binance", "rate": 0.001225},
                {"exchangeName": "OKX", "rate": -0.0025},
                {"exchangeName": "Bitmex", "rate": 0.01},
            ] * 3,
            "uIndexPrice": 71576.27,
            "uPrice": 71549.0,
        }]
    }

    truncated = truncate_response(large_funding, "small")
    u_count = len(truncated["data"][0]["uMarginList"])
    assert u_count <= 5, f"Expected ≤5 exchanges, got {u_count}"
    assert "_truncated" in truncated["data"][0]

    original_size = len(json.dumps(large_funding))
    truncated_size = len(json.dumps(truncated))
    reduction = (1 - truncated_size / original_size) * 100
    print(f"✅ BUG-4 test 1: funding rate {original_size} → {truncated_size} chars ({reduction:.0f}% reduction)")

    # Test 2: Liquidation exchange truncation
    large_liqs = {
        "symbol": "BTC",
        "total_liquidations_usd": 86000000,
        "exchanges": [{"exchange": f"Ex{i}", "total_liquidations_usd": 10000000 - i * 1000} for i in range(20)]
    }
    truncated2 = truncate_response(large_liqs, "small")
    assert len(truncated2["exchanges"]) <= 5
    print(f"✅ BUG-4 test 2: liquidations {len(large_liqs['exchanges'])} → {len(truncated2['exchanges'])} exchanges")

    # Test 3: Small response passes through unchanged
    small = {"symbol": "BTC", "price": 71000}
    result = truncate_response(small, "small")
    assert result == small
    print("✅ BUG-4 test 3: small response passed through unchanged")

    print("\n🎯 All response truncation patches pass self-test")
