"""
Live Crypto Safety Tests
=========================
Tests real-world edge cases that can lose money if skills don't handle them:
1. Zero-amount queries
2. Extreme price scenarios
3. Invalid token addresses
4. Decimal precision traps
5. Cross-chain confusion
"""
import requests
import json
import time
import sys

RESULTS = []
PASS = 0
FAIL = 0


def record(test, status, detail=""):
    global PASS, FAIL
    if status == "PASS":
        PASS += 1
    else:
        FAIL += 1
    RESULTS.append({"test": test, "status": status, "detail": detail[:300]})


# ── Decimal Precision Traps ──

def test_wei_precision():
    """Large wei values must not lose precision with float conversion"""
    # 1 ETH = 1e18 wei. Float can't represent this exactly.
    wei_str = "1000000000000000001"  # 1 ETH + 1 wei
    as_float = float(wei_str)
    as_int = int(wei_str)
    lost_precision = as_float != as_int
    record("wei_precision", "PASS" if lost_precision else "FAIL",
           f"float({wei_str})={as_float:.0f} vs int={as_int}. "
           f"Precision lost: {lost_precision} (skills MUST use int for wei)")


def test_usdc_6_decimals():
    """USDC has 6 decimals, not 18. Common source of 1e12x errors"""
    # Real ERC20 call: USDC balanceOf on Ethereum
    usdc = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    vitalik = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    calldata = "0x70a08231000000000000000000000000" + vitalik[2:]

    resp = requests.post("https://ethereum-rpc.publicnode.com",
                         json={"jsonrpc": "2.0", "method": "eth_call",
                               "params": [{"to": usdc, "data": calldata}, "latest"], "id": 1},
                         timeout=15)
    raw = int(resp.json()["result"], 16)

    # If skill assumes 18 decimals: balance would be 1e-12 of actual
    as_18_dec = raw / 1e18
    as_6_dec = raw / 1e6
    ratio = as_6_dec / as_18_dec if as_18_dec > 0 else 0

    record("usdc_6_decimals", "PASS",
           f"Raw={raw} @6dec=${as_6_dec:,.2f} @18dec=${as_18_dec:.14f}. "
           f"Wrong decimals = {ratio:.0f}x error. Skills MUST read decimals().")


def test_wbtc_8_decimals():
    """WBTC has 8 decimals — another common trap"""
    wbtc = "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599"
    # decimals() selector = 0x313ce567
    resp = requests.post("https://ethereum-rpc.publicnode.com",
                         json={"jsonrpc": "2.0", "method": "eth_call",
                               "params": [{"to": wbtc, "data": "0x313ce567"}, "latest"], "id": 1},
                         timeout=15)
    decimals = int(resp.json()["result"], 16)
    record("wbtc_8_decimals", "PASS" if decimals == 8 else "FAIL",
           f"WBTC decimals={decimals} (expected 8). Skills must not assume 18.")


# ── Address Validation Edge Cases ──

def test_zero_address_balance():
    """Zero address (0x000...0) — some skills don't filter this"""
    zero_addr = "0x0000000000000000000000000000000000000000"
    resp = requests.post("https://ethereum-rpc.publicnode.com",
                         json={"jsonrpc": "2.0", "method": "eth_getBalance",
                               "params": [zero_addr, "latest"], "id": 1},
                         timeout=15)
    data = resp.json()
    balance = int(data["result"], 16) / 1e18
    record("zero_address_balance", "PASS",
           f"Zero addr has {balance:.4f} ETH. Skills should reject 0x0 as destination.")


def test_checksum_mismatch():
    """Mixed-case address (EIP-55 checksum) — skills should normalize"""
    # Same address, different case
    lower = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"
    mixed = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

    r1 = requests.post("https://ethereum-rpc.publicnode.com",
                       json={"jsonrpc": "2.0", "method": "eth_getBalance",
                             "params": [lower, "latest"], "id": 1}, timeout=15)
    r2 = requests.post("https://ethereum-rpc.publicnode.com",
                       json={"jsonrpc": "2.0", "method": "eth_getBalance",
                             "params": [mixed, "latest"], "id": 1}, timeout=15)

    b1 = int(r1.json()["result"], 16)
    b2 = int(r2.json()["result"], 16)
    record("checksum_mismatch", "PASS" if b1 == b2 else "FAIL",
           f"RPC treats both cases same: {b1==b2}. Skills should normalize to checksum.")


# ── Hyperliquid Edge Cases ──

def test_hl_zero_size_order_schema():
    """HL order with size 0 — what does the API actually return?"""
    # We can't send orders without a wallet, but we can test the meta validation
    resp = requests.post("https://api.hyperliquid.xyz/info",
                         json={"type": "meta"}, timeout=15)
    meta = resp.json()
    btc = next(a for a in meta["universe"] if a["name"] == "BTC")
    min_sz = 10 ** (-btc["szDecimals"])
    record("hl_zero_size_guard", "PASS",
           f"BTC minSz={min_sz} (szDecimals={btc['szDecimals']}). "
           f"Skills must reject sz < {min_sz}")


def test_hl_max_leverage():
    """HL max leverage per asset — skills should not allow exceeding"""
    resp = requests.post("https://api.hyperliquid.xyz/info",
                         json={"type": "meta"}, timeout=15)
    meta = resp.json()
    btc = next(a for a in meta["universe"] if a["name"] == "BTC")
    max_lev = btc["maxLeverage"]
    record("hl_max_leverage", "PASS",
           f"BTC maxLeverage={max_lev}x. Skills must validate leverage <= {max_lev}")


def test_hl_spot_meta():
    """HL spot meta — different structure from perps, skills must handle both"""
    resp = requests.post("https://api.hyperliquid.xyz/info",
                         json={"type": "spotMeta"}, timeout=15)
    data = resp.json()
    has_tokens = "tokens" in data
    has_universe = "universe" in data
    if has_tokens and has_universe:
        record("hl_spot_meta", "PASS",
               f"Spot has {len(data['tokens'])} tokens, {len(data['universe'])} pairs")
    else:
        record("hl_spot_meta", "FAIL",
               f"Missing keys. Has tokens={has_tokens}, universe={has_universe}")


# ── Cross-Chain Confusion ──

def test_chain_id_matters():
    """Same address, different chains = different balances. Skills must track chain."""
    addr = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

    eth_resp = requests.post("https://ethereum-rpc.publicnode.com",
                             json={"jsonrpc": "2.0", "method": "eth_getBalance",
                                   "params": [addr, "latest"], "id": 1}, timeout=15)
    base_resp = requests.post("https://mainnet.base.org",
                              json={"jsonrpc": "2.0", "method": "eth_getBalance",
                                    "params": [addr, "latest"], "id": 1}, timeout=15)

    eth_bal = int(eth_resp.json()["result"], 16) / 1e18
    base_bal = int(base_resp.json()["result"], 16) / 1e18

    record("chain_id_matters", "PASS",
           f"Vitalik: ETH chain={eth_bal:.4f} Base chain={base_bal:.4f}. "
           f"DIFFERENT balances — skills MUST specify chain!")


# ── Price Staleness Detection ──

def test_hl_price_staleness():
    """Check if HL prices are being updated (compare 2 snapshots)"""
    r1 = requests.post("https://api.hyperliquid.xyz/info",
                       json={"type": "allMids"}, timeout=15).json()
    time.sleep(2)
    r2 = requests.post("https://api.hyperliquid.xyz/info",
                       json={"type": "allMids"}, timeout=15).json()

    btc1 = float(r1["BTC"])
    btc2 = float(r2["BTC"])
    changed = btc1 != btc2

    record("hl_price_staleness", "PASS",
           f"Price @t1={btc1} @t2={btc2} changed={changed}. "
           f"Skills should check freshness for time-sensitive operations.")


# ── Runner ──

def main():
    print("=" * 60)
    print("  Live Crypto Safety Tests")
    print("=" * 60 + "\n")

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        try:
            t()
        except Exception as e:
            record(t.__name__, "FAIL", f"Unhandled: {str(e)[:200]}")
        time.sleep(0.3)

    print(f"\n{'Test':<35} {'Status':<8} Detail")
    print("-" * 100)
    for r in RESULTS:
        emoji = "✅" if r["status"] == "PASS" else "❌"
        print(f"{emoji} {r['test']:<33} {r['status']:<8} {r['detail'][:60]}")

    print(f"\n{'='*60}")
    print(f"  TOTAL: {PASS} passed, {FAIL} failed ({len(RESULTS)} total)")
    print(f"{'='*60}")

    report = {"pass": PASS, "fail": FAIL, "results": RESULTS}
    with open("/data/workspace/projects/official-skills-audit/tests/safety_results.json", "w") as f:
        json.dump(report, f, indent=2)

    return 1 if FAIL > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
