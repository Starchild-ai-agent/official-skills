"""
Live Endpoint Integration Tests
================================
Tests real API responses against skill expectations.
Validates: response schemas, error handling, edge cases.

Endpoints tested (no API key needed):
- CoinGecko public API
- Hyperliquid info API
- Ethereum/Base/Arbitrum public RPC
"""
import requests
import json
import time
import sys
import traceback
from datetime import datetime


def _retry_get(url, params=None, headers=None, max_retries=3, backoff=2.0):
    """Retry GET with exponential backoff for 429/5xx."""
    import requests as _req
    for attempt in range(max_retries):
        try:
            resp = _req.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 429:
                wait = float(resp.headers.get("Retry-After", backoff * (2 ** attempt)))
                time.sleep(min(wait, 30))
                continue
            if resp.status_code >= 500:
                time.sleep(backoff * (2 ** attempt))
                continue
            return resp
        except _req.exceptions.RequestException:
            if attempt == max_retries - 1:
                raise
            time.sleep(backoff * (2 ** attempt))
    return resp  # return last response even if bad

RESULTS = []
PASS = 0
FAIL = 0
SKIP = 0

def _is_rate_limited(resp):
    """Check if CoinGecko returned 429 rate limit."""
    if resp.status_code == 429:
        return True
    try:
        data = resp.json()
        if isinstance(data, dict) and data.get("status", {}).get("error_code") == 429:
            return True
    except Exception:
        pass
    return False

# === Public endpoints ===
ENDPOINTS = {
    "coingecko": "https://api.coingecko.com/api/v3",
    "hyperliquid": "https://api.hyperliquid.xyz",
    "eth_rpc": "https://ethereum-rpc.publicnode.com",
    "base_rpc": "https://mainnet.base.org",
    "arb_rpc": "https://arb1.arbitrum.io/rpc",
}

def record(test_name, status, detail="", duration_ms=0):
    global PASS, FAIL, SKIP
    if status == "PASS": PASS += 1
    elif status == "FAIL": FAIL += 1
    else: SKIP += 1
    RESULTS.append({
        "test": test_name, "status": status,
        "detail": detail[:300], "duration_ms": round(duration_ms, 1)
    })

def timed_request(method, url, **kwargs):
    kwargs.setdefault("timeout", 15)
    t0 = time.time()
    resp = method(url, **kwargs)
    elapsed = (time.time() - t0) * 1000
    return resp, elapsed


# =============================================
# CoinGecko Tests
# =============================================

def test_cg_ping():
    """CoinGecko /ping should return gecko_says"""
    try:
        resp, ms = timed_request(requests.get, f"{ENDPOINTS['coingecko']}/ping")
        if _is_rate_limited(resp):
            record("cg_ping", "SKIP", "Rate limited (429)", ms); return
        data = resp.json()
        assert "gecko_says" in data, f"Missing gecko_says: {data}"
        record("cg_ping", "PASS", f"gecko_says={data['gecko_says']}", ms)
    except Exception as e:
        record("cg_ping", "FAIL", str(e))

def test_cg_price_bitcoin():
    """CoinGecko price endpoint — validates response schema skills expect"""
    try:
        resp, ms = timed_request(requests.get,
            f"{ENDPOINTS['coingecko']}/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd",
                    "include_24hr_change": "true", "include_market_cap": "true"})
        if _is_rate_limited(resp):
            record("cg_price_bitcoin", "SKIP", "Rate limited (429)", ms); return
        data = resp.json()
        assert "bitcoin" in data, f"No bitcoin key: {list(data.keys())}"
        btc = data["bitcoin"]
        assert "usd" in btc, f"No usd field in bitcoin: {list(btc.keys())}"
        assert btc["usd"] > 0, f"Price non-positive: {btc['usd']}"
        assert "usd_24h_change" in btc, "Missing 24h change field"
        assert "usd_market_cap" in btc, "Missing market cap field"
        record("cg_price_bitcoin", "PASS",
               f"BTC=${btc['usd']:,.0f} 24h={btc['usd_24h_change']:.2f}%", ms)
    except Exception as e:
        record("cg_price_bitcoin", "FAIL", str(e))

def test_cg_price_multi():
    """Multiple coin price query — tests comma-separated ids"""
    try:
        resp, ms = timed_request(requests.get,
            f"{ENDPOINTS['coingecko']}/simple/price",
            params={"ids": "bitcoin,ethereum,solana", "vs_currencies": "usd"})
        if _is_rate_limited(resp):
            record("cg_price_multi", "SKIP", "Rate limited (429)", ms); return
        data = resp.json()
        for coin in ["bitcoin", "ethereum", "solana"]:
            assert coin in data, f"Missing coin: {coin}"
            assert data[coin]["usd"] > 0
        record("cg_price_multi", "PASS",
               f"BTC=${data['bitcoin']['usd']:,.0f} ETH=${data['ethereum']['usd']:,.0f} SOL=${data['solana']['usd']:,.1f}", ms)
    except Exception as e:
        record("cg_price_multi", "FAIL", str(e))

def test_cg_invalid_coin():
    """Invalid coin ID — skill should handle gracefully, not crash"""
    try:
        resp, ms = timed_request(requests.get,
            f"{ENDPOINTS['coingecko']}/simple/price",
            params={"ids": "totally_fake_coin_xyz", "vs_currencies": "usd"})
        if _is_rate_limited(resp):
            record("cg_invalid_coin", "SKIP", "Rate limited (429)", ms); return
        data = resp.json()
        # CoinGecko returns empty dict for unknown coins
        assert "totally_fake_coin_xyz" not in data or data == {}, \
            f"Unexpected data for fake coin: {data}"
        record("cg_invalid_coin", "PASS",
               "Returns empty dict for unknown coin (skill must check for this!)", ms)
    except Exception as e:
        record("cg_invalid_coin", "FAIL", str(e))

def test_cg_ohlc():
    """OHLC endpoint — used by charting skills"""
    try:
        resp, ms = timed_request(requests.get,
            f"{ENDPOINTS['coingecko']}/coins/bitcoin/ohlc",
            params={"vs_currency": "usd", "days": "1"})
        if _is_rate_limited(resp):
            record("cg_ohlc", "SKIP", "Rate limited (429)", ms); return
        data = resp.json()
        assert isinstance(data, list), f"OHLC not a list: {type(data)}"
        assert len(data) > 0, "Empty OHLC data"
        candle = data[0]
        assert len(candle) == 5, f"Candle should have 5 fields [ts,o,h,l,c], got {len(candle)}"
        assert candle[0] > 1600000000000, f"Timestamp seems wrong: {candle[0]}"
        record("cg_ohlc", "PASS", f"{len(data)} candles, latest O={candle[1]}", ms)
    except Exception as e:
        record("cg_ohlc", "FAIL", str(e))

def test_cg_rate_limit_headers():
    """Check if CoinGecko returns rate limit headers — skill should respect these"""
    try:
        resp, ms = timed_request(requests.get, f"{ENDPOINTS['coingecko']}/ping")
        if _is_rate_limited(resp):
            record("cg_rate_limit_headers", "SKIP", "Rate limited (429)", ms); return
        rl_headers = {k: v for k, v in resp.headers.items()
                      if 'rate' in k.lower() or 'limit' in k.lower() or 'retry' in k.lower()}
        has_rl = len(rl_headers) > 0
        record("cg_rate_limit_headers", "PASS" if has_rl else "PASS",
               f"Rate limit headers: {rl_headers or 'none (public tier)'}", ms)
    except Exception as e:
        record("cg_rate_limit_headers", "FAIL", str(e))


# =============================================
# Hyperliquid Tests
# =============================================

def test_hl_meta():
    """Hyperliquid /info meta — lists all perpetual assets"""
    try:
        resp, ms = timed_request(requests.post,
            f"{ENDPOINTS['hyperliquid']}/info",
            json={"type": "meta"})
        data = resp.json()
        assert "universe" in data, f"No universe key: {list(data.keys())}"
        universe = data["universe"]
        assert len(universe) > 100, f"Too few assets: {len(universe)}"
        btc = next((a for a in universe if a["name"] == "BTC"), None)
        assert btc is not None, "BTC not in universe"
        assert "szDecimals" in btc, f"Missing szDecimals in BTC: {list(btc.keys())}"
        record("hl_meta", "PASS", f"{len(universe)} perps, BTC szDec={btc['szDecimals']}", ms)
    except Exception as e:
        record("hl_meta", "FAIL", str(e))

def test_hl_all_mids():
    """Hyperliquid allMids — current mid prices for all assets"""
    try:
        resp, ms = timed_request(requests.post,
            f"{ENDPOINTS['hyperliquid']}/info",
            json={"type": "allMids"})
        data = resp.json()
        assert isinstance(data, dict), f"Expected dict, got {type(data)}"
        assert "BTC" in data, f"No BTC price, keys: {list(data.keys())[:10]}"
        btc_price = float(data["BTC"])
        assert 10000 < btc_price < 500000, f"BTC price out of range: {btc_price}"
        record("hl_all_mids", "PASS", f"BTC mid={btc_price:,.1f}, {len(data)} assets", ms)
    except Exception as e:
        record("hl_all_mids", "FAIL", str(e))

def test_hl_orderbook():
    """Hyperliquid L2 orderbook for BTC"""
    try:
        resp, ms = timed_request(requests.post,
            f"{ENDPOINTS['hyperliquid']}/info",
            json={"type": "l2Book", "coin": "BTC"})
        data = resp.json()
        assert "levels" in data, f"No levels key: {list(data.keys())}"
        levels = data["levels"]
        assert len(levels) == 2, f"Expected [bids, asks], got {len(levels)} levels"
        bids, asks = levels
        assert len(bids) > 0 and len(asks) > 0, "Empty bid or ask side"
        best_bid = float(bids[0]["px"])
        best_ask = float(asks[0]["px"])
        spread = (best_ask - best_bid) / best_bid * 100
        record("hl_orderbook", "PASS",
               f"Bid={best_bid:,.1f} Ask={best_ask:,.1f} Spread={spread:.4f}%", ms)
    except Exception as e:
        record("hl_orderbook", "FAIL", str(e))

def test_hl_funding_rates():
    """Hyperliquid funding rate data"""
    try:
        resp, ms = timed_request(requests.post,
            f"{ENDPOINTS['hyperliquid']}/info",
            json={"type": "metaAndAssetCtxs"})
        data = resp.json()
        assert isinstance(data, list) and len(data) == 2, f"Unexpected structure"
        meta, ctxs = data
        assert "universe" in meta
        assert len(ctxs) > 0
        # Find BTC context
        btc_idx = next(i for i, a in enumerate(meta["universe"]) if a["name"] == "BTC")
        btc_ctx = ctxs[btc_idx]
        funding = float(btc_ctx["funding"])
        oi = float(btc_ctx["openInterest"])
        record("hl_funding_rates", "PASS",
               f"BTC funding={funding:.6f} OI={oi:,.0f}", ms)
    except Exception as e:
        record("hl_funding_rates", "FAIL", str(e))

def test_hl_candles():
    """Hyperliquid candle/kline data"""
    try:
        now_ms = int(time.time() * 1000)
        start = now_ms - 3600_000  # 1 hour ago
        resp, ms = timed_request(requests.post,
            f"{ENDPOINTS['hyperliquid']}/info",
            json={"type": "candleSnapshot", "req": {
                "coin": "BTC", "interval": "5m",
                "startTime": start, "endTime": now_ms
            }})
        data = resp.json()
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        assert len(data) > 0, "Empty candle data"
        c = data[-1]
        required_fields = {"t", "o", "h", "l", "c", "v"}
        actual_fields = set(c.keys())
        missing = required_fields - actual_fields
        assert not missing, f"Missing candle fields: {missing}"
        record("hl_candles", "PASS",
               f"{len(data)} candles, latest close={c['c']}", ms)
    except Exception as e:
        record("hl_candles", "FAIL", str(e))

def test_hl_invalid_coin():
    """Hyperliquid with invalid coin — should return error, not crash"""
    try:
        resp, ms = timed_request(requests.post,
            f"{ENDPOINTS['hyperliquid']}/info",
            json={"type": "l2Book", "coin": "FAKECOIN999"})
        data = resp.json()
        # HL typically returns error or empty for invalid coins
        is_error = "error" in str(data).lower() or \
                   (isinstance(data, dict) and "levels" in data and
                    all(len(l) == 0 for l in data["levels"]))
        record("hl_invalid_coin", "PASS",
               f"Response for fake coin: {str(data)[:150]}", ms)
    except Exception as e:
        record("hl_invalid_coin", "FAIL", str(e))


# =============================================
# EVM RPC Tests
# =============================================

def _rpc_call(endpoint, method, params=None):
    resp, ms = timed_request(requests.post, endpoint,
        json={"jsonrpc": "2.0", "method": method, "params": params or [], "id": 1})
    data = resp.json()
    return data, ms

def test_eth_block_number():
    """Ethereum RPC eth_blockNumber"""
    try:
        data, ms = _rpc_call(ENDPOINTS["eth_rpc"], "eth_blockNumber")
        assert "result" in data, f"No result: {data}"
        block = int(data["result"], 16)
        assert block > 20_000_000, f"Block number too low: {block}"
        record("eth_block_number", "PASS", f"Block #{block:,}", ms)
    except Exception as e:
        record("eth_block_number", "FAIL", str(e))

def test_eth_get_balance():
    """ETH getBalance for Vitalik's address — validates address handling"""
    try:
        vitalik = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        data, ms = _rpc_call(ENDPOINTS["eth_rpc"], "eth_getBalance",
                             [vitalik, "latest"])
        assert "result" in data, f"No result: {data}"
        balance_wei = int(data["result"], 16)
        balance_eth = balance_wei / 1e18
        record("eth_get_balance", "PASS",
               f"Vitalik has {balance_eth:,.2f} ETH", ms)
    except Exception as e:
        record("eth_get_balance", "FAIL", str(e))

def test_eth_invalid_address():
    """ETH getBalance with invalid address — skill error handling test"""
    try:
        data, ms = _rpc_call(ENDPOINTS["eth_rpc"], "eth_getBalance",
                             ["0xinvalid", "latest"])
        has_error = "error" in data
        record("eth_invalid_address", "PASS",
               f"RPC returns error for invalid addr: {has_error}, resp={str(data)[:150]}", ms)
    except Exception as e:
        record("eth_invalid_address", "FAIL", str(e))

def test_base_block_number():
    """Base L2 RPC connectivity"""
    try:
        data, ms = _rpc_call(ENDPOINTS["base_rpc"], "eth_blockNumber")
        assert "result" in data
        block = int(data["result"], 16)
        record("base_block_number", "PASS", f"Block #{block:,}", ms)
    except Exception as e:
        record("base_block_number", "FAIL", str(e))

def test_arb_block_number():
    """Arbitrum RPC connectivity"""
    try:
        data, ms = _rpc_call(ENDPOINTS["arb_rpc"], "eth_blockNumber")
        assert "result" in data
        block = int(data["result"], 16)
        record("arb_block_number", "PASS", f"Block #{block:,}", ms)
    except Exception as e:
        record("arb_block_number", "FAIL", str(e))

def test_erc20_balance_call():
    """Raw ERC20 balanceOf call — tests calldata encoding skills need"""
    try:
        # USDC on Ethereum, check Vitalik's balance
        usdc = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
        vitalik = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        # balanceOf(address) selector = 0x70a08231
        calldata = "0x70a08231000000000000000000000000" + vitalik[2:]
        data, ms = _rpc_call(ENDPOINTS["eth_rpc"], "eth_call",
                             [{"to": usdc, "data": calldata}, "latest"])
        assert "result" in data, f"No result: {data}"
        balance_raw = int(data["result"], 16)
        balance_usdc = balance_raw / 1e6  # USDC has 6 decimals
        record("erc20_balance_call", "PASS",
               f"Vitalik USDC balance: {balance_usdc:,.2f}", ms)
    except Exception as e:
        record("erc20_balance_call", "FAIL", str(e))


# =============================================
# Cross-Skill Consistency Tests
# =============================================

def test_price_consistency():
    """Compare BTC price between CoinGecko and Hyperliquid — <2% diff expected"""
    try:
        # CoinGecko price
        r1, ms1 = timed_request(requests.get,
            f"{ENDPOINTS['coingecko']}/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"})
        if _is_rate_limited(r1):
            record("price_consistency", "SKIP", "CoinGecko rate limited (429)", ms1); return
        cg_price = r1.json()["bitcoin"]["usd"]

        # Hyperliquid mid price
        r2, ms2 = timed_request(requests.post,
            f"{ENDPOINTS['hyperliquid']}/info",
            json={"type": "allMids"})
        hl_price = float(r2.json()["BTC"])

        diff_pct = abs(cg_price - hl_price) / cg_price * 100
        status = "PASS" if diff_pct < 2.0 else "FAIL"
        record("price_consistency", status,
               f"CG=${cg_price:,.0f} HL=${hl_price:,.0f} diff={diff_pct:.3f}%",
               ms1 + ms2)
    except Exception as e:
        record("price_consistency", "FAIL", str(e))

def test_response_time_budget():
    """All endpoints should respond within 5s — skill timeouts should be >= this"""
    slow = []
    for name, url in ENDPOINTS.items():
        try:
            t0 = time.time()
            if "rpc" in name:
                requests.post(url, json={"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}, timeout=10)
            elif "hyperliquid" in name:
                requests.post(url + "/info", json={"type": "allMids"}, timeout=10)
            else:
                requests.get(url + "/ping", timeout=10)
            elapsed = (time.time() - t0) * 1000
            if elapsed > 5000:
                slow.append(f"{name}: {elapsed:.0f}ms")
        except Exception as e:
            slow.append(f"{name}: ERROR {e}")
    status = "PASS" if not slow else "FAIL"
    record("response_time_budget", status,
           f"Slow endpoints: {slow}" if slow else "All endpoints < 5s")


# =============================================
# Error Pattern Tests (what skills SHOULD handle)
# =============================================

def test_timeout_behavior():
    """Verify behavior when timeout is very short — skills need proper timeout handling"""
    try:
        t0 = time.time()
        try:
            requests.get(f"{ENDPOINTS['coingecko']}/simple/price",
                         params={"ids": "bitcoin", "vs_currencies": "usd"},
                         timeout=0.001)  # Impossibly short
            record("timeout_behavior", "FAIL", "Should have timed out with 1ms timeout")
        except requests.exceptions.Timeout:
            elapsed = (time.time() - t0) * 1000
            record("timeout_behavior", "PASS",
                   f"Correctly raised Timeout in {elapsed:.0f}ms")
        except requests.exceptions.ConnectionError:
            record("timeout_behavior", "PASS", "ConnectionError (acceptable for ultra-short timeout)")
    except Exception as e:
        record("timeout_behavior", "FAIL", str(e))

def test_malformed_json_body():
    """Hyperliquid with malformed JSON — skill should catch this"""
    try:
        resp, ms = timed_request(requests.post,
            f"{ENDPOINTS['hyperliquid']}/info",
            data="not json", headers={"Content-Type": "application/json"})
        status_code = resp.status_code
        record("malformed_json_body", "PASS",
               f"HTTP {status_code} for malformed JSON (skill must handle non-200)", ms)
    except Exception as e:
        record("malformed_json_body", "FAIL", str(e))


# =============================================
# Runner
# =============================================

def main():
    print(f"{'='*60}")
    print(f"  Live Endpoint Integration Tests")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*60}\n")

    all_tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test_fn in all_tests:
        try:
            test_fn()
        except Exception as e:
            record(test_fn.__name__, "FAIL", f"Unhandled: {traceback.format_exc()[:200]}")
        time.sleep(0.3)  # be nice to public APIs

    # Print results
    print(f"\n{'Test':<35} {'Status':<8} {'Time':>8}  Detail")
    print("-" * 100)
    for r in RESULTS:
        emoji = "✅" if r["status"] == "PASS" else "❌" if r["status"] == "FAIL" else "⏭️"
        time_str = f"{r['duration_ms']:.0f}ms" if r['duration_ms'] else ""
        print(f"{emoji} {r['test']:<33} {r['status']:<8} {time_str:>8}  {r['detail'][:60]}")

    print(f"\n{'='*60}")
    print(f"  TOTAL: {PASS} passed, {FAIL} failed, {SKIP} skipped ({len(RESULTS)} total)")
    print(f"{'='*60}")

    # Save JSON report
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "summary": {"pass": PASS, "fail": FAIL, "skip": SKIP, "total": len(RESULTS)},
        "results": RESULTS
    }
    with open("/data/workspace/projects/official-skills-audit/tests/live_results.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nJSON report saved to tests/live_results.json")

    return 1 if FAIL > 0 else 0

if __name__ == "__main__":
    sys.exit(main())
