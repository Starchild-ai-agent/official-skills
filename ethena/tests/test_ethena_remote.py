"""
Ethena Remote Verification Tests
=================================
Tests that can be independently verified on-chain or via public dashboards.

Verification URLs (open in browser to cross-check):
  Rate:    https://etherscan.io/token/0x9D39A5DE30e57443BfF2A8307A4256c8797A3497#readContract
  APY:     https://app.ethena.fi/  (Dashboard → Current APY)
  TVL:     https://defillama.com/protocol/ethena
  Cooldown: etherscan → sUSDe → Read → cooldownDuration()

Usage:
  python tests/test_ethena_remote.py
  python tests/test_ethena_remote.py --wallet 0xYOUR_WALLET

Requirements: requests, pycryptodome (for selector verification)
"""
import sys
import os
import json
import time
import argparse
import requests

# Allow running from skill root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

RPC_URL   = "https://ethereum.publicnode.com"
SUSDE     = "0x9D39A5DE30e57443BfF2A8307A4256c8797A3497"
USDE      = "0x4c9EDD5852cd905f086C759E8383e09bff1E68B3"
DEFILLAMA = "https://yields.llama.fi/chart/66985a81-4b3f-417b-8e53-b6e9cee0d83a"

PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️  WARN"


def eth_call(to, data):
    r = requests.post(RPC_URL, json={
        "jsonrpc": "2.0", "method": "eth_call",
        "params": [{"to": to, "data": data}, "latest"], "id": 1
    }, timeout=15)
    result = r.json().get("result", "0x0")
    if not result or result == "0x":
        return 0
    return int(result, 16)


def encode_addr(addr):
    return addr.lower().replace("0x", "").zfill(64)


def separator(label):
    print(f"\n{'='*55}")
    print(f"  {label}")
    print(f"{'='*55}")


# ─────────────────────────────────────────────────────────────
# T01: Exchange Rate
# Verify: Etherscan → sUSDe contract → Read → totalAssets / totalSupply
# ─────────────────────────────────────────────────────────────
def test_rate():
    separator("T01 · sUSDe/USDe Exchange Rate")

    ta = eth_call(SUSDE, "0x01e1d114") / 1e18
    ts = eth_call(SUSDE, "0x18160ddd") / 1e18
    rate = ta / ts if ts else 0

    print(f"  totalAssets  : {ta:>18,.4f} USDe")
    print(f"  totalSupply  : {ts:>18,.4f} sUSDe")
    print(f"  rate         : {rate:.8f}  (1 sUSDe = {rate:.6f} USDe)")
    print(f"  cumulative Δ : +{(rate-1)*100:.2f}%")

    ok = 1.0 < rate < 2.0 and ta > 1e9 and ts > 1e9
    print(f"\n  {PASS if ok else FAIL} rate={rate:.6f}, TVL={ta/1e9:.2f}B USDe")
    print(f"  🔍 Cross-check: https://etherscan.io/token/0x9D39A5DE30e57443BfF2A8307A4256c8797A3497#readContract")
    return ok, {"rate": rate, "total_assets": ta, "total_supply": ts}


# ─────────────────────────────────────────────────────────────
# T02: Cooldown Duration
# Verify: Etherscan → sUSDe → Read → cooldownDuration()
# ─────────────────────────────────────────────────────────────
def test_cooldown():
    separator("T02 · Cooldown Duration (on-chain)")

    cd = eth_call(SUSDE, "0x35269315")
    hours = cd / 3600
    days  = cd / 86400

    print(f"  cooldownDuration : {cd}s = {hours:.1f}h = {days:.1f}d")
    print(f"  (SKILL.md used to say '7 days' — now queries live)")

    ok = 3600 <= cd <= 7 * 86400   # sanity: between 1h and 7d
    status = PASS if ok else FAIL
    if cd == 86400:
        print(f"\n  {PASS} Confirmed 24h cooldown (as of last check)")
    elif ok:
        print(f"\n  {WARN} Cooldown changed to {hours:.1f}h — update docs")
    else:
        print(f"\n  {FAIL} Unexpected cooldown: {cd}s")

    print(f"  🔍 Cross-check: Etherscan → sUSDe Read → cooldownDuration()")
    return ok, {"cooldown_seconds": cd, "cooldown_hours": hours}


# ─────────────────────────────────────────────────────────────
# T03: APY from DefiLlama
# Verify: https://defillama.com/protocol/ethena  or  app.ethena.fi
# ─────────────────────────────────────────────────────────────
def test_apy():
    separator("T03 · sUSDe APY (DefiLlama)")

    # Try chart endpoint first, fallback to pools list
    r = requests.get(DEFILLAMA, timeout=15)
    data = r.json().get("data", [])

    if data:
        latest = data[-1]
        apy = latest.get("apy", 0)
        apy_7d  = sum(d["apy"] for d in data[-7:])  / min(7,  len(data))
        apy_30d = sum(d["apy"] for d in data[-30:]) / min(30, len(data))
        tvl     = latest.get("tvlUsd", 0)
    else:
        # Fallback: scan pools list for sUSDe on Ethereum
        r2 = requests.get("https://yields.llama.fi/pools", timeout=15)
        pools = r2.json().get("data", [])
        pool = next((p for p in pools
                     if "susde" in p.get("symbol","").lower()
                     and p.get("chain","") == "Ethereum"), None)
        if not pool:
            print(f"  {FAIL} No sUSDe pool found in DefiLlama")
            return False, {}
        apy     = pool.get("apy", 0)
        apy_7d  = pool.get("apy7d") or apy
        apy_30d = pool.get("apy30d") or apy
        tvl     = pool.get("tvlUsd", 0)
        latest  = {"timestamp": "pools-list"}

    print(f"  APY (current) : {apy:.2f}%")
    print(f"  APY (7d avg)  : {apy_7d:.2f}%")
    print(f"  APY (30d avg) : {apy_30d:.2f}%")
    print(f"  TVL           : ${tvl/1e9:.2f}B")
    print(f"  date          : {latest.get('timestamp','')}")

    ok = 0.0 < apy < 50.0 and tvl > 1e9
    print(f"\n  {PASS if ok else FAIL} APY={apy:.2f}%, TVL=${tvl/1e9:.2f}B")
    print(f"  🔍 Cross-check: https://app.ethena.fi  or  https://defillama.com/protocol/ethena")
    return ok, {"apy": apy, "apy_7d": apy_7d, "apy_30d": apy_30d, "tvl": tvl}


# ─────────────────────────────────────────────────────────────
# T04: Calldata Correctness
# Verify: paste calldata into https://calldata.swiss  or  https://abi.hashex.org
# ─────────────────────────────────────────────────────────────
def test_calldata():
    separator("T04 · Calldata Generation Integrity")

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from scripts.ethena_ops import approve_calldata, deposit_calldata, cooldown_calldata, unstake_calldata, to_wei

    DUMMY_RECEIVER = "0x95df79E2c8Cc11Cd3B759D055A1896F3882D38E8"
    amount_wei = to_wei("100")

    approve = approve_calldata(amount_wei)
    deposit = deposit_calldata(amount_wei, DUMMY_RECEIVER)
    cooldown = cooldown_calldata(amount_wei)
    unstake  = unstake_calldata(DUMMY_RECEIVER)

    checks = [
        ("approve selector",  approve["data"][:10],  "0x095ea7b3"),
        ("approve to",        approve["to"],          "0x4c9EDD5852cd905f086C759E8383e09bff1E68B3"),
        ("deposit selector",  deposit["data"][:10],  "0x6e553f65"),
        ("deposit to",        deposit["to"],          "0x9D39A5DE30e57443BfF2A8307A4256c8797A3497"),
        ("cooldown selector", cooldown["data"][:10], "0xcdac52ed"),
        ("unstake selector",  unstake["data"][:10],  "0xf2888dbb"),
    ]

    all_ok = True
    for label, got, expected in checks:
        ok = got.lower() == expected.lower()
        all_ok = all_ok and ok
        print(f"  {'✅' if ok else '❌'} {label:22s} got={got}  expected={expected}")

    # Print sample calldata for manual verification
    print(f"\n  Sample: approve 100 USDe")
    print(f"    to:   {approve['to']}")
    print(f"    data: {approve['data'][:50]}...")
    print(f"  🔍 Cross-check: https://calldata.swiss → paste data field")

    return all_ok, {}


# ─────────────────────────────────────────────────────────────
# T05: Wallet Balance Query (optional — requires --wallet flag)
# Verify: check Etherscan token balance for the address
# ─────────────────────────────────────────────────────────────
def test_wallet_balance(wallet: str):
    separator(f"T05 · Wallet Balance for {wallet[:10]}...")

    enc = encode_addr(wallet)

    usde_raw  = eth_call(USDE,  f"0x70a08231{enc}")
    susde_raw = eth_call(SUSDE, f"0x70a08231{enc}")
    cd_end    = eth_call(SUSDE, f"0x525f3146{enc}")

    usde_bal  = usde_raw  / 1e18
    susde_bal = susde_raw / 1e18

    ta = eth_call(SUSDE, "0x01e1d114") / 1e18
    ts = eth_call(SUSDE, "0x18160ddd") / 1e18
    rate = ta / ts if ts else 1.0
    susde_in_usde = susde_bal * rate

    print(f"  USDe balance  : {usde_bal:,.6f}")
    print(f"  sUSDe balance : {susde_bal:,.6f}")
    print(f"  sUSDe→USDe   : {susde_in_usde:,.6f} (rate={rate:.6f})")
    print(f"  cooldown_end  : {cd_end} {'(active)' if cd_end > 0 else '(none)'}")
    print(f"\n  🔍 Cross-check: https://etherscan.io/address/{wallet}#tokentxns")
    print(f"       USDe: https://etherscan.io/token/0x4c9EDD5852cd905f086C759E8383e09bff1E68B3?a={wallet}")
    print(f"      sUSDe: https://etherscan.io/token/0x9D39A5DE30e57443BfF2A8307A4256c8797A3497?a={wallet}")

    return True, {"usde": usde_bal, "susde": susde_bal, "cooldown_end": cd_end}


# ─────────────────────────────────────────────────────────────
# T06: Vesting Amount (rewards in transit)
# Verify: Etherscan → sUSDe → Read → vestingAmount()
# ─────────────────────────────────────────────────────────────
def test_vesting():
    separator("T06 · Vesting Amount (rewards in transit)")

    va = eth_call(SUSDE, "0x00728f76") / 1e18

    print(f"  vestingAmount : {va:,.4f} USDe")
    print(f"  (rewards being linearly distributed over 8h window)")
    print(f"\n  {PASS} vestingAmount queried")
    print(f"  🔍 Cross-check: Etherscan → sUSDe → Read → vestingAmount()")

    return True, {"vesting_amount": va}


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Ethena remote verification tests")
    parser.add_argument("--wallet", default=None, help="Wallet address for T05 balance test")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    print("\n🟣 Ethena Skill — Remote Verification Tests")
    print(f"   RPC: {RPC_URL}")
    print(f"   sUSDe: {SUSDE}")

    results = {}
    total = ok_count = 0

    for name, fn, kwargs in [
        ("T01_rate",     test_rate,     {}),
        ("T02_cooldown", test_cooldown, {}),
        ("T03_apy",      test_apy,      {}),
        ("T04_calldata", test_calldata, {}),
        ("T06_vesting",  test_vesting,  {}),
    ]:
        ok, data = fn(**kwargs)
        results[name] = {"ok": ok, **data}
        total += 1
        if ok:
            ok_count += 1
        time.sleep(0.3)  # be polite to public RPC

    if args.wallet:
        ok, data = test_wallet_balance(args.wallet)
        results["T05_wallet"] = {"ok": ok, **data}
        total += 1
        if ok:
            ok_count += 1

    separator(f"Summary: {ok_count}/{total} passed")
    for name, r in results.items():
        status = PASS if r["ok"] else FAIL
        print(f"  {status}  {name}")

    if args.json:
        print("\n" + json.dumps(results, indent=2))

    sys.exit(0 if ok_count == total else 1)


if __name__ == "__main__":
    main()
