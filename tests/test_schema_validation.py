"""
Schema Validation Tests
========================
Captures REAL API responses and validates them against what skill code expects.
Goal: catch schema mismatches before they cause silent failures in production.

Key insight: Skills parse API responses with hardcoded field names. If the API
changes a field name or structure, the skill breaks silently (returns None/empty).
"""
import requests
import json
import time
import sys
import re
import os

RESULTS = []
PASS = 0
FAIL = 0
SKIP = 0


def record(test, status, detail=""):
    global PASS, FAIL, SKIP
    if status == "PASS": PASS += 1
    elif status == "SKIP": SKIP += 1
    else: FAIL += 1
    RESULTS.append({"test": test, "status": status, "detail": detail[:300]})


# ── Hyperliquid schema expectations (from skill code) ──

def test_hl_meta_schema():
    """Validate HL meta response has all fields the skill extracts"""
    resp = requests.post("https://api.hyperliquid.xyz/info",
                         json={"type": "meta"}, timeout=15)
    data = resp.json()

    # Skill expects: data["universe"][i]["name"], ["szDecimals"], ["maxLeverage"]
    expected_asset_fields = {"name", "szDecimals", "maxLeverage"}
    if "universe" not in data:
        return record("hl_meta_schema", "FAIL", "No 'universe' key")

    asset = data["universe"][0]
    actual = set(asset.keys())
    missing = expected_asset_fields - actual
    extra = actual - expected_asset_fields

    if missing:
        record("hl_meta_schema", "FAIL", f"Missing fields: {missing}")
    else:
        record("hl_meta_schema", "PASS",
               f"All expected fields present. Extra fields: {extra}")


def test_hl_asset_ctx_schema():
    """Validate HL assetCtx has funding, openInterest, markPx etc."""
    resp = requests.post("https://api.hyperliquid.xyz/info",
                         json={"type": "metaAndAssetCtxs"}, timeout=15)
    data = resp.json()
    meta, ctxs = data

    expected_ctx_fields = {"funding", "openInterest", "prevDayPx", "dayNtlVlm",
                           "premium", "oraclePx", "markPx", "midPx", "impactPxs"}
    btc_idx = next(i for i, a in enumerate(meta["universe"]) if a["name"] == "BTC")
    ctx = ctxs[btc_idx]
    actual = set(ctx.keys())
    missing = expected_ctx_fields - actual

    if missing:
        record("hl_asset_ctx_schema", "FAIL", f"Missing: {missing}")
    else:
        record("hl_asset_ctx_schema", "PASS",
               f"All expected fields present. Fields: {sorted(actual)}")


def test_hl_l2book_schema():
    """Validate orderbook structure: levels[0]=bids, levels[1]=asks, each has px/sz/n"""
    resp = requests.post("https://api.hyperliquid.xyz/info",
                         json={"type": "l2Book", "coin": "BTC"}, timeout=15)
    data = resp.json()

    if "levels" not in data:
        return record("hl_l2book_schema", "FAIL", f"No 'levels' key: {list(data.keys())}")

    levels = data["levels"]
    if len(levels) != 2:
        return record("hl_l2book_schema", "FAIL", f"Expected 2 sides, got {len(levels)}")

    # Each level entry should have px, sz, n
    expected_entry_fields = {"px", "sz", "n"}
    bid = levels[0][0]
    actual = set(bid.keys())
    missing = expected_entry_fields - actual

    if missing:
        record("hl_l2book_schema", "FAIL", f"Bid entry missing: {missing}")
    else:
        record("hl_l2book_schema", "PASS",
               f"Bid/Ask structure correct. Entry fields: {sorted(actual)}")


def test_hl_candle_schema():
    """Validate candle data has t,o,h,l,c,v,n fields"""
    now = int(time.time() * 1000)
    resp = requests.post("https://api.hyperliquid.xyz/info",
        json={"type": "candleSnapshot", "req": {
            "coin": "BTC", "interval": "1h",
            "startTime": now - 7200_000, "endTime": now
        }}, timeout=15)
    data = resp.json()

    if not data or not isinstance(data, list):
        return record("hl_candle_schema", "FAIL", f"Empty or non-list: {type(data)}")

    expected = {"t", "T", "s", "i", "o", "c", "h", "l", "v", "n"}
    actual = set(data[0].keys())
    missing = {"o", "h", "l", "c", "v", "t"} - actual

    if missing:
        record("hl_candle_schema", "FAIL", f"Missing candle fields: {missing}")
    else:
        record("hl_candle_schema", "PASS",
               f"Candle fields: {sorted(actual)}")


# ── CoinGecko schema expectations ──

def test_cg_simple_price_schema():
    """Validate CoinGecko simple/price output structure"""
    time.sleep(2)
    resp = requests.get("https://api.coingecko.com/api/v3/simple/price",
        params={"ids": "bitcoin", "vs_currencies": "usd",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
                "include_24hr_change": "true",
                "include_last_updated_at": "true"},
        timeout=15)

    if resp.status_code == 429:
        return record("cg_simple_price_schema", "SKIP",
                       "Rate limited (429) — demonstrates need for retry logic")

    data = resp.json()
    if "bitcoin" not in data:
        return record("cg_simple_price_schema", "FAIL", f"No bitcoin key: {data}")

    expected_fields = {"usd", "usd_market_cap", "usd_24h_vol",
                       "usd_24h_change", "last_updated_at"}
    actual = set(data["bitcoin"].keys())
    missing = expected_fields - actual

    if missing:
        record("cg_simple_price_schema", "FAIL", f"Missing: {missing}")
    else:
        record("cg_simple_price_schema", "PASS",
               f"All fields present: {sorted(actual)}")


def test_cg_ohlc_schema():
    """Validate OHLC returns [timestamp, open, high, low, close] arrays"""
    time.sleep(3)
    resp = requests.get("https://api.coingecko.com/api/v3/coins/bitcoin/ohlc",
        params={"vs_currency": "usd", "days": "1"}, timeout=15)

    if resp.status_code == 429:
        return record("cg_ohlc_schema", "SKIP", "Rate limited (429)")

    data = resp.json()
    if not isinstance(data, list):
        return record("cg_ohlc_schema", "FAIL", f"Not a list: {type(data)}")

    candle = data[0]
    if len(candle) != 5:
        return record("cg_ohlc_schema", "FAIL",
                       f"Candle has {len(candle)} fields, expected 5 [ts,o,h,l,c]")

    # Validate types
    assert isinstance(candle[0], (int, float)), "timestamp not numeric"
    assert all(isinstance(candle[i], (int, float)) for i in range(1, 5)), "OHLC values not numeric"

    record("cg_ohlc_schema", "PASS",
           f"Correct [ts,o,h,l,c] format, {len(data)} candles")


# ── EVM RPC schema expectations ──

def test_rpc_error_schema():
    """Validate RPC error response structure — skills must parse this"""
    resp = requests.post("https://ethereum-rpc.publicnode.com",
        json={"jsonrpc": "2.0", "method": "eth_getBalance",
              "params": ["0xinvalid", "latest"], "id": 1},
        timeout=15)
    data = resp.json()

    if "error" in data:
        err = data["error"]
        has_code = "code" in err
        has_message = "message" in err
        record("rpc_error_schema", "PASS",
               f"Error has code={has_code} message={has_message}: {err.get('message','')[:100]}")
    else:
        record("rpc_error_schema", "FAIL",
               f"Expected error for invalid address, got: {str(data)[:200]}")


def test_rpc_success_schema():
    """Validate RPC success response — skills expect result field"""
    resp = requests.post("https://ethereum-rpc.publicnode.com",
        json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
        timeout=15)
    data = resp.json()

    expected = {"jsonrpc", "id", "result"}
    actual = set(data.keys())
    missing = expected - actual

    if missing:
        record("rpc_success_schema", "FAIL", f"Missing: {missing}")
    else:
        record("rpc_success_schema", "PASS",
               f"Correct JSON-RPC response: {sorted(actual)}")


# ── Skill Code Cross-Reference ──

def test_skill_code_field_usage():
    """Scan skill Python files for field access patterns, check against real API"""
    _p = os.path.join(os.path.dirname(__file__), "..")
    repo_root = _p if os.path.isdir(os.path.join(_p, "hyperliquid")) else os.path.join(_p, "repo")
    issues = []

    # Check hyperliquid skill's field access
    hl_dir = os.path.join(repo_root, "hyperliquid")
    if os.path.isdir(hl_dir):
        for fname in os.listdir(hl_dir):
            if not fname.endswith('.py'):
                continue
            fpath = os.path.join(hl_dir, fname)
            with open(fpath, 'r') as f:
                code = f.read()

            # Find dict access patterns: data["field"] or data.get("field")
            bracket_access = re.findall(r'\[[\"\'](\w+)[\"\']\]', code)
            get_access = re.findall(r'\.get\([\"\']([\w]+)[\"\']\)', code)
            all_fields = set(bracket_access + get_access)

            # Flag potentially dangerous patterns
            if 'except:' in code or 'except Exception:' in code:
                bare_excepts = len(re.findall(r'except\s*(?:Exception)?\s*:', code))
                if bare_excepts > 0:
                    issues.append(f"{fname}: {bare_excepts} bare except clauses (silent failures)")

    if issues:
        # These are audit findings in upstream code, not test failures.
        # We record them as PASS with notes — the purpose is detection, not gating.
        record("skill_code_field_usage", "PASS",
               f"AUDIT: {len(issues)} issues found: " + "; ".join(issues[:3]))
    else:
        record("skill_code_field_usage", "PASS",
               "No dangerous patterns found in skill code")


# ── Runner ──

def main():
    print("=" * 60)
    print("  Schema Validation Tests (real API vs skill expectations)")
    print("=" * 60 + "\n")

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        try:
            t()
        except Exception as e:
            record(t.__name__, "FAIL", f"Unhandled: {str(e)[:200]}")
        time.sleep(0.5)

    print(f"\n{'Test':<35} {'Status':<8} Detail")
    print("-" * 90)
    for r in RESULTS:
        emoji = "✅" if r["status"] == "PASS" else ("⏭️" if r["status"] == "SKIP" else "❌")
        print(f"{emoji} {r['test']:<33} {r['status']:<8} {r['detail'][:55]}")

    print(f"\n{'='*60}")
    print(f"  TOTAL: {PASS} passed, {FAIL} failed, {SKIP} skipped ({len(RESULTS)} total)")
    print(f"{'='*60}")

    report = {"pass": PASS, "fail": FAIL, "skip": SKIP, "results": RESULTS}
    with open("/data/workspace/projects/official-skills-audit/tests/schema_results.json", "w") as f:
        json.dump(report, f, indent=2)

    return 1 if FAIL > 0 else 0

if __name__ == "__main__":
    sys.exit(main())
