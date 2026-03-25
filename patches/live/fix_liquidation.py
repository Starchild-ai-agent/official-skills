"""
FIX-1 & FIX-2: Liquidation Data Quality Patches

BUG-1: cg_liquidations returns long/short = 0 but per-exchange totals exist
BUG-2: cg_liquidation_analysis says "shorts dominate" when all data is 0

These patches are post-processing wrappers that fix the output AFTER
the tool call returns. They don't modify upstream — they fix what
the agent sees.
"""

def fix_liquidation_data(raw_result: dict) -> dict:
    """
    Fix BUG-1: When long/short splits are 0 but exchange totals exist,
    compute the actual total and flag the split as unavailable.
    
    Strategy: Sum per-exchange totals to get real total.
    Mark long/short as "unavailable" instead of misleading 0.
    """
    if not isinstance(raw_result, dict):
        return raw_result
    
    exchanges = raw_result.get("exchanges", [])
    top_total = raw_result.get("total_liquidations_usd", 0)
    top_long = raw_result.get("long_liquidations_usd", 0)
    top_short = raw_result.get("short_liquidations_usd", 0)
    
    # Calculate real total from exchange data
    computed_total = sum(
        ex.get("total_liquidations_usd", 0) for ex in exchanges
    )
    
    # Only apply fix when: splits are 0 BUT exchange totals exist
    if top_long == 0 and top_short == 0 and computed_total > 0:
        raw_result["total_liquidations_usd"] = round(computed_total, 2)
        raw_result["long_liquidations_usd"] = None  # explicit "unknown"
        raw_result["short_liquidations_usd"] = None
        raw_result["long_percent"] = None
        raw_result["short_percent"] = None
        raw_result["_patch_note"] = (
            f"Long/short split unavailable from upstream. "
            f"Total recomputed from {len(exchanges)} exchanges: "
            f"${computed_total:,.0f}"
        )
    
    return raw_result


def fix_liquidation_analysis(raw_result: dict) -> dict:
    """
    Fix BUG-2: When analysis says "shorts dominate" with 0 data,
    replace with honest "data_unavailable" assessment.
    """
    result = fix_liquidation_data(raw_result)  # apply BUG-1 fix first
    
    analysis = result.get("analysis", {})
    if not analysis:
        return result
    
    total = result.get("total_liquidations_usd", 0)
    long_val = result.get("long_liquidations_usd")
    short_val = result.get("short_liquidations_usd")
    
    # If we can't determine the split, fix the analysis
    if long_val is None or short_val is None:
        result["analysis"] = {
            "sentiment": "Long/short breakdown unavailable",
            "dominant_side": "unknown",
            "imbalance": None,
            "total_liquidated_usd": total,
            "_patch_note": (
                "Upstream API does not provide long/short split. "
                "Only aggregate totals per exchange are available. "
                "Do NOT use this for directional sentiment."
            )
        }
    elif long_val == 0 and short_val == 0 and total == 0:
        result["analysis"] = {
            "sentiment": "No liquidation data available",
            "dominant_side": "unknown",
            "imbalance": 0,
            "_patch_note": "Zero liquidation data returned. Market may be calm or data delayed."
        }
    
    return result


# ─── Self-test ───────────────────────────────────────────
if __name__ == "__main__":
    import json
    
    # Simulate BUG-1: exchange totals exist but splits are 0
    test_input = {
        "symbol": "BTC",
        "total_liquidations_usd": 0,
        "long_liquidations_usd": 0,
        "short_liquidations_usd": 0,
        "long_percent": 0,
        "short_percent": 0,
        "exchanges": [
            {"exchange": "Hyperliquid", "long_liquidations_usd": 0, "short_liquidations_usd": 0, "total_liquidations_usd": 19309486.50},
            {"exchange": "Binance", "long_liquidations_usd": 0, "short_liquidations_usd": 0, "total_liquidations_usd": 11303323.10},
        ]
    }
    
    fixed = fix_liquidation_data(test_input.copy())
    assert fixed["total_liquidations_usd"] > 30000000, f"Expected >$30M, got {fixed['total_liquidations_usd']}"
    assert fixed["long_liquidations_usd"] is None, "Should be None, not 0"
    assert "_patch_note" in fixed, "Missing patch note"
    print(f"✅ BUG-1 fix: total recomputed to ${fixed['total_liquidations_usd']:,.0f}")
    
    # Simulate BUG-2: analysis says "shorts" with no data
    test_analysis = {
        **test_input,
        "analysis": {
            "sentiment": "Balanced liquidations",
            "dominant_side": "shorts",
            "imbalance": 0
        }
    }
    
    fixed2 = fix_liquidation_analysis(test_analysis.copy())
    assert fixed2["analysis"]["dominant_side"] == "unknown", f"Expected 'unknown', got '{fixed2['analysis']['dominant_side']}'"
    assert "unavailable" in fixed2["analysis"]["sentiment"].lower()
    print(f"✅ BUG-2 fix: dominant_side corrected to '{fixed2['analysis']['dominant_side']}'")
    
    print("\n🎯 All liquidation patches pass self-test")
