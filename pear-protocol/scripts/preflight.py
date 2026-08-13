#!/usr/bin/env python3
"""Pear/Hyperliquid execution preflight + post-trade verification.

Usage:
  python3 preflight.py check [--notional 20] [--leverage 1]
      Run all pre-execution checks. Exit 0 = safe to execute, 1 = blocked.
  python3 preflight.py verify <execution_id> --trade-account <id>
      Post-trade receipt: execution status, venue errors, fills, position.

Checks performed by `check`:
  1. Gateway auth (API key valid)
  2. Trade account connected
  3. Builder-fee approval on-chain (maxBuilderFee > 0 for Pear's builder)
  4. Balance breakdown: HL perp equity vs spot balance (flags funds stuck
     in spot / account-mode issues)
  5. Available margin vs requested notional
"""
import argparse
import json
import sys

sys.path.insert(0, "/app")
try:
    from core.http_client import proxied_post  # noqa: F401
    _HAVE_PROXY = True
except Exception:
    _HAVE_PROXY = False

import os
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
import gateway  # reuse auth + request helpers

HL_INFO = "https://api.hyperliquid.xyz/info"


def hl_info(payload: dict) -> dict | list:
    if _HAVE_PROXY:
        r = proxied_post(HL_INFO, json=payload, timeout=20)
        r.raise_for_status()
        return r.json()
    import urllib.request
    req = urllib.request.Request(HL_INFO, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=20).read().decode())


def mcp_call(tool: str, args: dict) -> dict:
    import subprocess
    out = subprocess.run(
        [sys.executable, os.path.join(_here, "pear_mcp.py"), "call", tool, json.dumps(args)],
        capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"MCP {tool} failed: {out.stderr.strip()[:200]}")
    d = json.loads(out.stdout)
    return json.loads(d["content"][0]["text"])


def check(notional: float, leverage: float) -> int:
    ok = True

    def report(name, passed, detail):
        nonlocal ok
        mark = "✅" if passed else "❌"
        if not passed:
            ok = False
        print(f"{mark} {name}: {detail}")

    # 1. auth
    try:
        key = gateway.load_env_key()
        if not key:
            report("auth", False, "no PEAR_API_KEY — run gateway.py ensure-key")
            return 1
        report("auth", True, f"API key {key[:10]}…")
    except Exception as e:
        report("auth", False, str(e)[:120])
        return 1

    # 2. trade account
    try:
        accounts = mcp_call("list_trade_accounts", {}).get("accounts", [])
    except Exception:
        st, resp = gateway.http_get(
            "/trade-accounts", headers={"x-api-key": gateway.load_env_key()})
        accounts = (resp or {}).get("accounts", resp if isinstance(resp, list) else []) \
            if st == 200 else []
    if not accounts:
        report("trade account", False,
               "none connected — follow the trade-account recipe in SKILL.md")
        return 1
    acct = accounts[0]
    ta_id = acct.get("id")
    master = (acct.get("exchangeIdentifier")
              or acct.get("metadata", {}).get("mainAccountAddress", ""))
    report("trade account", True, f"{ta_id} (master {master[:8]}…)")

    # 3. builder fee
    try:
        fee = mcp_call("get_fee_recipient", {"connector": "hyperliquid"})
        builder = fee.get("feeRecipient") or fee.get("recipient")
    except Exception:
        builder = None
    if builder and master:
        max_fee = hl_info({"type": "maxBuilderFee", "user": master, "builder": builder})
        report("builder fee", int(max_fee or 0) > 0,
               f"maxBuilderFee={max_fee} for {builder[:8]}… "
               + ("" if int(max_fee or 0) > 0 else
                  "— NOT APPROVED: run step 4 of the trade-account recipe "
                  "(note: ~1-2 min cache delay after approving)"))
    else:
        report("builder fee", False, "could not resolve builder or master address")

    # 4. balances (separated)
    perp = hl_info({"type": "clearinghouseState", "user": master})
    spot = hl_info({"type": "spotClearinghouseState", "user": master})
    equity = float(perp.get("marginSummary", {}).get("accountValue", 0))
    withdrawable = float(perp.get("withdrawable", 0))
    spot_usdc = sum(float(b["total"]) for b in spot.get("balances", [])
                    if b.get("coin") == "USDC")
    print(f"   balances — perp equity: ${equity:.2f} | withdrawable: "
          f"${withdrawable:.2f} | spot USDC: ${spot_usdc:.2f}")
    if equity == 0 and spot_usdc > 0:
        report("account mode", False,
               f"${spot_usdc:.2f} sits in SPOT but perp equity is $0 — funds "
               "not usable as margin. Transfer spot→perp or enable unified "
               "account abstraction (required for xyz:* builder-DEX markets).")
    else:
        report("account mode", True, "perp margin available")

    # 5. margin vs request
    required = notional / max(leverage, 1e-9)
    headroom = equity - required
    report("margin", headroom > 0.5,
           f"required ≈ ${required:.2f} for ${notional:.2f} @ {leverage}x, "
           f"equity ${equity:.2f}, headroom ${headroom:.2f}"
           + ("" if headroom > 0.5 else " — insufficient buffer for fees/slippage"))

    print("\nPREFLIGHT:", "PASS — safe to execute" if ok else "FAIL — fix ❌ items first")
    return 0 if ok else 1


def verify(execution_id: str, ta_id: str) -> int:
    print(f"execution: {execution_id}")
    try:
        ex = mcp_call("get_execution",
                      {"tradeAccountId": ta_id, "params": {"executionId": execution_id}})
    except Exception:
        ex = mcp_call("get_execution", {"tradeAccountId": ta_id, "executionId": execution_id})
    status = ex.get("status") or ex.get("execution", {}).get("status")
    errors = (ex.get("errors") or ex.get("venueErrors")
              or ex.get("execution", {}).get("errors") or [])
    legs = ex.get("legs") or ex.get("execution", {}).get("legs") or []
    filled = sum(float(l.get("filledQuantity", 0) or 0) for l in legs) if legs else \
        float(ex.get("filledQuantity", 0) or 0)
    print(f"status: {status} | filledQuantity: {filled} | venue errors: {errors or 'none'}")

    pos = mcp_call("get_position", {"tradeAccountId": ta_id, "params": {}})
    positions = pos.get("positions", pos if isinstance(pos, list) else [])
    print(f"open positions: {len(positions)}")
    for p in positions[:5]:
        print("  -", json.dumps(p)[:160])

    really_filled = filled > 0 and not errors and len(positions) > 0
    print("\nRECEIPT:", "FILLED ✅" if really_filled else
          "NOT FILLED ❌ — status:executed alone does NOT mean a trade happened")
    return 0 if really_filled else 1


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--notional", type=float, default=20.0)
    c.add_argument("--leverage", type=float, default=1.0)
    v = sub.add_parser("verify")
    v.add_argument("execution_id")
    v.add_argument("--trade-account", required=True)
    a = ap.parse_args()
    if a.cmd == "check":
        sys.exit(check(a.notional, a.leverage))
    sys.exit(verify(a.execution_id, a.trade_account))


if __name__ == "__main__":
    main()
