"""
Integration test: Apply all patches to REAL tool output data.
Data captured from live Starchild tool calls on 2026-03-25.
"""
import sys

from fix_liquidation import fix_liquidation_data, fix_liquidation_analysis
from fix_error_messages import reclassify_error
from fix_funding_rate import normalize_funding_rates
from fix_error_format import normalize_error

print("=" * 70)
print("  INTEGRATION TEST — REAL DATA PATCHES")
print("=" * 70)

results = {"pass": 0, "fail": 0, "tests": []}


def test(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results["pass" if condition else "fail"] += 1
    results["tests"].append({"name": name, "status": status, "detail": detail})
    icon = "✅" if condition else "❌"
    print(f"  {icon} {name}" + (f" — {detail}" if detail else ""))


# ─── FIX-1: BTC Liquidation Data ───
print("\n🔧 FIX-1: Liquidation Long/Short Split")
btc_liq = {
    "symbol": "BTC", "total_liquidations_usd": 0,
    "long_liquidations_usd": 0, "short_liquidations_usd": 0,
    "long_percent": 0, "short_percent": 0,
    "exchanges": [
        {"exchange": "Hyperliquid", "long_liquidations_usd": 0,
            "short_liquidations_usd": 0, "total_liquidations_usd": 19309486.50839},
        {
            "exchange": "Bybit",
            "long_liquidations_usd": 0,
            "short_liquidations_usd": 0,
            "total_liquidations_usd": 15334106.2764
        },
        {
            "exchange": "HTX",
            "long_liquidations_usd": 0,
            "short_liquidations_usd": 0,
            "total_liquidations_usd": 13219810.8396
        },
        {"exchange": "Binance", "long_liquidations_usd": 0,
            "short_liquidations_usd": 0, "total_liquidations_usd": 11303323.10456},
        {"exchange": "Bitget", "long_liquidations_usd": 0,
            "short_liquidations_usd": 0, "total_liquidations_usd": 10888181.02209332},
        {
            "exchange": "Gate",
            "long_liquidations_usd": 0,
            "short_liquidations_usd": 0,
            "total_liquidations_usd": 9571298.88745
        },
        {
            "exchange": "OKX",
            "long_liquidations_usd": 0,
            "short_liquidations_usd": 0,
            "total_liquidations_usd": 4300397.56458
        },
    ]
}

fixed = fix_liquidation_data(btc_liq.copy())
computed_total = sum(ex["total_liquidations_usd"] for ex in btc_liq["exchanges"])

test("Total recomputed from exchanges",
     abs(fixed["total_liquidations_usd"] - computed_total) < 1,
     f"${fixed['total_liquidations_usd']:,.0f}")

test("Long/short marked as unknown (not false 0)",
     fixed["long_liquidations_usd"] is None and fixed["short_liquidations_usd"] is None)

test("Patch note present",
     "_patch_note" in fixed)

# ─── FIX-1 ETH ───
print("\n🔧 FIX-1b: ETH Liquidation Data")
eth_liq = {
    "symbol": "ETH", "total_liquidations_usd": 0,
    "long_liquidations_usd": 0, "short_liquidations_usd": 0,
    "long_percent": 0, "short_percent": 0,
    "exchanges": [
        {"exchange": "Binance", "long_liquidations_usd": 0,
            "short_liquidations_usd": 0, "total_liquidations_usd": 15853863.28789},
        {
            "exchange": "HTX",
            "long_liquidations_usd": 0,
            "short_liquidations_usd": 0,
            "total_liquidations_usd": 9676122.1352
        },
        {
            "exchange": "Bybit",
            "long_liquidations_usd": 0,
            "short_liquidations_usd": 0,
            "total_liquidations_usd": 7419534.0258
        },
    ]
}
fixed_eth = fix_liquidation_data(eth_liq.copy())
test("ETH total recomputed",
     fixed_eth["total_liquidations_usd"] > 32000000,
     f"${fixed_eth['total_liquidations_usd']:,.0f}")

# ─── FIX-2: Analysis Logic ───
print("\n🔧 FIX-2: Liquidation Analysis Guard")
btc_analysis = {
    **btc_liq,
    "analysis": {"sentiment": "Balanced liquidations", "dominant_side": "shorts", "imbalance": 0}
}
fixed_a = fix_liquidation_analysis(btc_analysis.copy())

test("Dominant side corrected to 'unknown'",
     fixed_a["analysis"]["dominant_side"] == "unknown",
     f"was 'shorts' → now '{fixed_a['analysis']['dominant_side']}'")

test("Sentiment reflects data unavailability",
     "unavailable" in fixed_a["analysis"]["sentiment"].lower())

test("Total still recomputed",
     fixed_a["total_liquidations_usd"] > 80000000)

# ─── FIX-3: Error Reclassification ───
print("\n🔧 FIX-3: Error Message Reclassification")
err1 = reclassify_error(
    "❌ Error: Failed to fetch open interest. Check COINGLASS_API_KEY.",
    symbol="INVALIDCOIN999"
)
test("Invalid symbol detected", err1["category"] == "invalid_symbol")
test("Helpful message provided", "not recognized" in err1["fixed"])

err2 = reclassify_error(
    "❌ Error: Failed to fetch open interest. Check COINGLASS_API_KEY.",
    symbol="BTC"
)
test("Valid symbol → kept as API issue", err2["category"] == "possible_api_error")

# ─── FIX-5: Error Format Normalization ───
print("\n🔧 FIX-5: Unified Error Format")
norm1 = normalize_error("❌ Error: Failed to fetch data. Check COINGLASS_API_KEY.",
                        tool_name="cg_open_interest", symbol="FAKECOIN")
test("Normalized has error=True", norm1.get("error") is True)
test("Has category field", "category" in norm1)
test("Has suggestion field", "suggestion" in norm1)

norm2 = normalize_error({"symbol": "BTC", "price": 71000}, tool_name="test")
test("Non-error passes through", norm2 == {"symbol": "BTC", "price": 71000})

# ─── FIX-6: Funding Rate Normalization ───
print("\n🔧 FIX-6: Funding Rate Normalization")
funding_data = {
    "data": [{
        "symbol": "BTC",
        "uMarginList": [
            {"exchangeName": "Binance", "rate": 0.000409, "fundingIntervalHours": 8},
            {"exchangeName": "Kraken", "rate": 0.0001267956944444, "fundingIntervalHours": 1},
            {"exchangeName": "Hyperliquid", "rate": 0.00125, "fundingIntervalHours": 1},
            {"exchangeName": "Bitfinex", "rate": 0.00404},
            {"exchangeName": "HTX", "rate": -0.0120396144722584},
        ],
        "cMarginList": [],
        "uIndexPrice": 71576.27,
    }]
}

normed = normalize_funding_rates(funding_data.copy())
entries = normed["data"][0]["uMarginList"]

test("Binance 8h → unchanged",
     entries[0]["rate_normalized_8h"] == 0.000409)

test("Kraken 1h → 8h normalized",
     abs(entries[1]["rate_normalized_8h"] - 0.0001267956944444 * 8) < 0.0000001,
     f"{entries[1]['rate']} → {entries[1]['rate_normalized_8h']}")

test("Hyperliquid 1h → 8h normalized",
     abs(entries[2]["rate_normalized_8h"] - 0.01) < 0.0000001,
     f"{entries[2]['rate']} → {entries[2]['rate_normalized_8h']}")

test("Bitfinex interval inferred",
     entries[3].get("_interval_inferred") is True)

test("HTX interval inferred",
     entries[4].get("_interval_inferred") is True)

# ─── Summary ───
print("\n" + "=" * 70)
total = results["pass"] + results["fail"]
print(f"  RESULTS: {results['pass']}/{total} passed, {results['fail']} failed")
print("=" * 70)

if results["fail"] > 0:
    print("\n  FAILURES:")
    for t in results["tests"]:
        if t["status"] == "FAIL":
            print(f"    ❌ {t['name']}")
    sys.exit(1)
else:
    print("\n  🎯 ALL INTEGRATION TESTS PASS WITH REAL DATA")
    sys.exit(0)
