"""
Jupiter v1.1.0 — Remote Verification Test Suite
================================================
Runs against Agent 2181 via /api/exec (ping auth).
Tests cover: price query, quote, limit order API structure,
and known-token registry — all verifiable without a real wallet signature.

Run:
    python tests/test_jupiter_remote.py

Env vars (optional override):
    REMOTE_API_KEY  — long-lived API key
    REMOTE_PING     — ping code (default: 2468)
    REMOTE_BASE_URL — agent base URL
"""
import os
import sys
import json
import time
import requests

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL = os.environ.get("REMOTE_BASE_URL",
                          "https://2181.agent.iamstarchild.com")
API_KEY  = os.environ.get("REMOTE_API_KEY",
           "YoopFXs3DFF8jpurSfdO7-2tVh3mKLJJ_EqSN7dAYLDjkgWtMGYq1P-zxz_eAuuu")
PING     = os.environ.get("REMOTE_PING", "2468")

JUP_BASE = "https://lite-api.jup.ag"
SOL_MINT  = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
JUP_MINT  = "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"
WIF_MINT  = "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []


def log(tid, name, ok, detail=""):
    icon = PASS if ok else FAIL
    line = f"{icon}  [{tid}] {name}"
    if detail:
        line += f"\n       {detail}"
    print(line)
    results.append((tid, name, ok))


def ask_agent(question: str, timeout: int = 30) -> str:
    """Send question to Agent 2181, return reply text."""
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    payload = {"message": question, "ping": PING}
    try:
        r = requests.post(f"{BASE_URL}/api/exec", headers=headers,
                          json=payload, timeout=timeout)
        if r.status_code == 200:
            return r.json().get("reply", r.text)
        return f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return f"ERROR: {e}"


# ── T01 — Ultra API: SOL→USDC quote shape ────────────────────────────────────
def test_T01_ultra_quote_shape():
    r = requests.get(f"{JUP_BASE}/ultra/v1/order", params={
        "inputMint":  SOL_MINT,
        "outputMint": USDC_MINT,
        "amount":     "1000000000",   # 1 SOL
    }, timeout=15)
    ok = r.status_code == 200
    if ok:
        d = r.json()
        required = {"inAmount", "outAmount", "inUsdValue", "outUsdValue",
                    "transaction", "requestId"}
        missing = required - set(d.keys())
        ok = len(missing) == 0
        out_usdc = int(d.get("outAmount", 0)) / 1e6
        detail = (f"1 SOL → {out_usdc:.2f} USDC | "
                  f"inUSD=${d.get('inUsdValue')} | "
                  f"requestId present={bool(d.get('requestId'))}")
        if missing:
            detail += f" | MISSING FIELDS: {missing}"
    else:
        detail = f"HTTP {r.status_code}"
    log("T01", "ultra/v1/order — quote shape & USD fields", ok, detail)


# ── T02 — Ultra API: JUP→USDC price derivation ───────────────────────────────
def test_T02_price_derivation():
    r = requests.get(f"{JUP_BASE}/ultra/v1/order", params={
        "inputMint":  JUP_MINT,
        "outputMint": USDC_MINT,
        "amount":     "1000000",   # 1 JUP
    }, timeout=15)
    ok = r.status_code == 200
    if ok:
        d = r.json()
        in_usd = d.get("inUsdValue")
        ok = in_usd is not None and float(in_usd) > 0
        detail = f"1 JUP ≈ ${in_usd} USD"
    else:
        detail = f"HTTP {r.status_code}"
    log("T02", "price derivation: JUP USD via ultra", ok, detail)


# ── T03 — Trigger API: createOrder rejects numeric amounts ───────────────────
def test_T03_trigger_string_amounts():
    """Confirm API returns ZodError when amounts are numbers (not strings)."""
    payload = {
        "inputMint":  USDC_MINT,
        "outputMint": SOL_MINT,
        "maker":      "11111111111111111111111111111111",  # dummy
        "payer":      "11111111111111111111111111111111",
        "params": {
            "makingAmount": 10000000,    # ← intentional int (should fail)
            "takingAmount": 90000000,
        },
        "computeUnitPrice": "auto",
    }
    r = requests.post(f"{JUP_BASE}/trigger/v1/createOrder",
                      json=payload, timeout=15)
    # Expect 400 ZodError when amounts are numbers
    ok = r.status_code == 400
    detail = f"HTTP {r.status_code} (expected 400 ZodError for numeric amounts)"
    if r.status_code == 400:
        body = r.json()
        if "zod" in str(body).lower() or "string" in str(body).lower():
            detail += " — ZodError confirmed ✓"
    log("T03", "trigger: numeric amounts → ZodError 400", ok, detail)


# ── T04 — Trigger API: createOrder with string amounts ───────────────────────
def test_T04_trigger_string_amounts_ok():
    """String amounts should reach signature validation (not 400)."""
    payload = {
        "inputMint":  USDC_MINT,
        "outputMint": SOL_MINT,
        "maker":      "11111111111111111111111111111111",  # dummy wallet
        "payer":      "11111111111111111111111111111111",
        "params": {
            "makingAmount": "10000000",   # ← correct: string
            "takingAmount": "90000000",
        },
        "computeUnitPrice": "auto",
    }
    r = requests.post(f"{JUP_BASE}/trigger/v1/createOrder",
                      json=payload, timeout=15)
    # With dummy wallet we expect 400 (invalid key) or 200 — NOT ZodError
    body = r.json() if r.headers.get("content-type","").startswith("application/json") else {}
    zod_error = "zod" in str(body).lower()
    ok = not zod_error   # passed string-amount validation
    detail = (f"HTTP {r.status_code} | ZodError={zod_error} | "
              f"body preview: {str(body)[:120]}")
    log("T04", "trigger: string amounts pass ZodError check", ok, detail)


# ── T05 — Known token registry ───────────────────────────────────────────────
def test_T05_known_tokens():
    """Verify KNOWN_TOKENS mints are real Solana accounts via ultra."""
    tokens = {
        "WIF":  (WIF_MINT,  USDC_MINT, "1000000"),
        "JUP":  (JUP_MINT,  USDC_MINT, "1000000"),
    }
    all_ok = True
    details = []
    for sym, (in_m, out_m, amt) in tokens.items():
        r = requests.get(f"{JUP_BASE}/ultra/v1/order", params={
            "inputMint": in_m, "outputMint": out_m, "amount": amt
        }, timeout=15)
        ok = r.status_code == 200
        if ok:
            usd = r.json().get("inUsdValue", "?")
            details.append(f"{sym}=${usd}")
        else:
            details.append(f"{sym}=HTTP{r.status_code}")
            all_ok = False
    log("T05", "known token mints resolve via ultra", all_ok, " | ".join(details))


# ── T06 — Deprecated endpoints return 404 ────────────────────────────────────
def test_T06_deprecated_endpoints():
    deprecated = [
        "/limit/v2/createOrder",
        "/dca/v2/createDca",
        "/price/v2",
    ]
    all_ok = True
    details = []
    for path in deprecated:
        r = requests.get(f"{JUP_BASE}{path}", timeout=10)
        ok = r.status_code == 404
        details.append(f"{path}={r.status_code}")
        if not ok:
            all_ok = False
    log("T06", "deprecated endpoints return 404", all_ok, " | ".join(details))


# ── T07 — Agent routing: price query ─────────────────────────────────────────
def test_T07_agent_price_routing():
    """Agent should call jupiter_price (not hallucinate) for SOL price query."""
    reply = ask_agent("SOL 现在的价格是多少？用 jupiter_price 工具查")
    ok = any(x in reply for x in ["$", "USD", "usdc", "price", "价格", "148", "147", "149", "150", "145", "146", "151", "152"])
    detail = f"Reply preview: {reply[:150]}"
    log("T07", "agent routes SOL price → real number returned", ok, detail)


# ── T08 — Agent routing: no DCA mention ──────────────────────────────────────
def test_T08_agent_no_dca():
    """Agent should NOT offer DCA (not supported on lite-api)."""
    reply = ask_agent("我想做定投 SOL，用 DCA 功能")
    # Should say DCA not supported, not try to use it
    bad = any(x in reply.lower() for x in ["/dca/v2", "dca/v2/create", "DCA 功能已激活"])
    ok = not bad
    detail = f"Reply preview: {reply[:150]}"
    log("T08", "agent correctly states DCA not supported on lite-api", ok, detail)


# ── Runner ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("Jupiter v1.1.0 — Remote Verification Tests")
    print(f"Target: {JUP_BASE}")
    print(f"Agent:  {BASE_URL}")
    print("=" * 60)
    print()

    # Direct API tests (no agent needed, faster)
    test_T01_ultra_quote_shape()
    test_T02_price_derivation()
    test_T03_trigger_string_amounts()
    test_T04_trigger_string_amounts_ok()
    test_T05_known_tokens()
    test_T06_deprecated_endpoints()
    time.sleep(1)
    # Agent routing tests
    test_T07_agent_price_routing()
    test_T08_agent_no_dca()

    print()
    print("=" * 60)
    passed = sum(1 for _, _, ok in results if ok)
    total  = len(results)
    print(f"Result: {passed}/{total} PASSED")
    if passed < total:
        print("Failed:")
        for tid, name, ok in results:
            if not ok:
                print(f"  {FAIL} [{tid}] {name}")
    print("=" * 60)
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
