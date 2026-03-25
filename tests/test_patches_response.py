"""
Suite B: Response Format Patch Validation
Tests shared/response.py — standardized response wrapper for all skills
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'patches'))

from shared.response import ok, fail, fmt_price, fmt_balance, fmt_table

PASSED = 0
FAILED = 0

def run_check(name, fn):
    global PASSED, FAILED
    try:
        fn()
        PASSED += 1
        print(f"  ✅ {name}")
    except Exception as e:
        FAILED += 1
        print(f"  ❌ {name}: {e}")

print("\n🧪 Suite B: Response Format Patch\n")

# B1: ok() with dict
def t_ok_dict():
    r = ok(data={"price": 1234.56, "change": "+5.2%"}, summary="BTC at $1,234.56")
    assert r["status"] == "ok"
    assert r["summary"] == "BTC at $1,234.56"
    assert r["price"] == 1234.56
    assert r["change"] == "+5.2%"
run_check("ok() with dict merges data into result", t_ok_dict)

# B2: ok() with list
def t_ok_list():
    items = [{"coin": "BTC"}, {"coin": "ETH"}]
    r = ok(data=items, summary="Top coins")
    assert r["status"] == "ok"
    assert r["count"] == 2
    assert r["items"] == items
run_check("ok() with list wraps as items + count", t_ok_list)

# B3: ok() with scalar
def t_ok_scalar():
    r = ok(data=42.5)
    assert r["status"] == "ok"
    assert r["value"] == 42.5
run_check("ok() with scalar wraps as value", t_ok_scalar)

# B4: fail() basic
def t_fail_basic():
    r = fail("hyperliquid/hl_order", "Insufficient margin")
    assert "❌" in r
    assert "hyperliquid/hl_order" in r
    assert "Insufficient margin" in r
run_check("fail() includes tool name + reason", t_fail_basic)

# B5: fail() with got/need/suggestion
def t_fail_full():
    r = fail("test/tool", "Bad value", got=100, need=500, suggestion="Increase funds", code="MARGIN_LOW")
    assert "Got: 100" in r
    assert "Expected: 500" in r
    assert "Increase funds" in r
    assert "MARGIN_LOW" in r
run_check("fail() includes got, need, suggestion, code", t_fail_full)

# B6: fmt_price high value
def t_price_high():
    r = fmt_price("BTC", 67543.21, change_24h=3.5, volume_24h=2_500_000_000)
    assert "$67,543.21" in r
    assert "+3.5%" in r
    assert "2.5B" in r
run_check("fmt_price formats high value with commas + volume", t_price_high)

# B7: fmt_price low value (< $1)
def t_price_low():
    r = fmt_price("SHIB", 0.0000234)
    assert "$0.000023" in r
run_check("fmt_price shows 6 decimals for sub-$1 tokens", t_price_low)

# B8: fmt_price negative change
def t_price_neg():
    r = fmt_price("ETH", 3500.0, change_24h=-2.3)
    assert "-2.3%" in r
    # Should NOT have a + prefix
    assert "+−" not in r and "+-" not in r
run_check("fmt_price negative change has no + prefix", t_price_neg)

# B9: fmt_balance
def t_balance():
    balances = [
        {"symbol": "ETH", "amount": 1.5, "usd_value": 5250.0, "chain": "ethereum"},
        {"symbol": "USDC", "amount": 1000, "usd_value": 1000.0, "chain": "base"},
    ]
    r = fmt_balance(balances, title="My Wallet")
    assert "My Wallet" in r
    assert "ETH" in r
    assert "$6,250.00" in r  # Total
    assert "| Asset |" in r  # Table header
run_check("fmt_balance creates markdown table with total", t_balance)

# B10: fmt_balance empty
def t_balance_empty():
    r = fmt_balance([], title="Empty")
    assert "No assets found" in r
run_check("fmt_balance handles empty list gracefully", t_balance_empty)

# B11: fmt_table generic
def t_table():
    rows = [
        {"symbol": "BTC", "funding": "0.01%", "oi": "$5B"},
        {"symbol": "ETH", "funding": "-0.005%", "oi": "$2B"},
    ]
    r = fmt_table(rows, title="Funding Rates")
    assert "Funding Rates" in r
    assert "| symbol |" in r or "| BTC |" in r
    lines = r.strip().split('\n')
    assert len(lines) >= 4  # title + header + separator + 2 rows
run_check("fmt_table creates markdown table from dict list", t_table)

# B12: fmt_table caps at 50 rows
def t_table_cap():
    rows = [{"n": i} for i in range(100)]
    r = fmt_table(rows)
    assert "50 more rows" in r
run_check("fmt_table caps at 50 rows with overflow message", t_table_cap)

# B13: fmt_table empty
def t_table_empty():
    r = fmt_table([], title="Empty Data")
    assert "No data" in r
run_check("fmt_table handles empty gracefully", t_table_empty)

# B14: ok() preserves summary for small models
def t_ok_summary_priority():
    r = ok(data={"complex": {"nested": "data"}}, summary="BTC is $67K, up 3%")
    # Small model should be able to grab summary directly
    assert "summary" in r
    assert r["summary"] == "BTC is $67K, up 3%"
run_check("ok() summary field is directly accessible for small models", t_ok_summary_priority)

print(f"\n{'='*50}")
print(f"Results: {PASSED}/{PASSED+FAILED} passed")
print(f"{'='*50}")


# ---- pytest-compatible entry point ----
def test_all_checks_pass():
    """Wraps the standalone test suite for pytest discovery."""
    assert FAILED == 0, f"{FAILED} check(s) failed — run this file standalone for details"
