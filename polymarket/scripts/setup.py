#!/usr/bin/env python3
"""
Polymarket One-Time Setup — wrap USDC.e -> pUSD, then approve V2 spenders.

Idempotent: skips steps already done on-chain. Safe to re-run.

Usage:
  python3 setup.py                # check only, print what's needed
  python3 setup.py --wrap 10      # wrap 10 USDC.e -> pUSD (if pUSD balance < amount)
  python3 setup.py --approve      # approve pUSD + CTF to all 3 V2 spenders (if missing)
  python3 setup.py --all 10       # wrap + approve (one shot for first-time users)

Requires: POLY_WALLET set, wallet has USDC.e on Polygon.
Gas is sponsored via the Privy/Alchemy paymaster — user pays nothing.
"""
import sys, json, time, argparse
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import cred, ensure_credentials, die
from core.skill_tools import wallet as wallet_tool
from core.http_client import proxied_post

# --- Contracts (Polygon mainnet, CLOB V2) ---
USDCE   = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
PUSD    = "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"
ONRAMP  = "0x93070a847efEf7F70739046A929D47a521F5B8ee"
CTF     = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
SPENDERS = [
    "0xE111180000d2663C0091e4f400237545B87B996B",   # CTF Exchange V2 (binary)
    "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296",   # Neg Risk Adapter
    "0xe2222d279d744050d28e00520010520000310F59",   # Neg Risk Exchange V2
]
RPC = "https://polygon-bor-rpc.publicnode.com"
MAX_UINT = (1 << 256) - 1

# --- ABI helpers (raw encoding to avoid eth-abi dependency) ---
def _addr(a): return a.lower().replace("0x", "").rjust(64, "0")
def _uint(n): return hex(n)[2:].rjust(64, "0")
def _approve(spender, amt):           return "0x095ea7b3" + _addr(spender) + _uint(amt)
def _wrap(asset, to, amt):            return "0x62355638" + _addr(asset) + _addr(to) + _uint(amt)
def _set_approval_for_all(op, on):    return "0xa22cb465" + _addr(op) + _uint(1 if on else 0)

def _rpc(method, params):
    r = proxied_post(RPC, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                     headers={"SC-CALLER-ID": "chat:polymarket-setup"}).json()
    return r.get("result")

def _balance(token, owner):
    data = "0x70a08231" + _addr(owner)
    res = _rpc("eth_call", [{"to": token, "data": data}, "latest"])
    return int(res, 16) if res else 0

def _allowance(token, owner, spender):
    data = "0xdd62ed3e" + _addr(owner) + _addr(spender)
    res = _rpc("eth_call", [{"to": token, "data": data}, "latest"])
    return int(res, 16) if res else 0

def _is_approved_for_all(ctf, owner, op):
    data = "0xe985e9c5" + _addr(owner) + _addr(op)
    res = _rpc("eth_call", [{"to": ctf, "data": data}, "latest"])
    return bool(int(res, 16)) if res else False

def _send(to, data, label):
    r = wallet_tool.wallet_transfer(to=to, amount="0", chain_id=137, data=data)
    op = r.get("data", {}).get("user_operation_hash") or r.get("data", {}).get("hash")
    print(f"  ✓ {label}: {op}")
    return op

def main():
    parser = argparse.ArgumentParser(description="Polymarket one-time on-chain setup")
    parser.add_argument("--wrap",    type=float, help="wrap N USDC.e -> pUSD if balance short")
    parser.add_argument("--approve", action="store_true", help="approve pUSD + CTF for V2 spenders")
    parser.add_argument("--all",     type=float, help="wrap N + approve (first-time users)")
    args = parser.parse_args()

    ok, msg = ensure_credentials()
    if not ok: die(msg)
    eoa = cred("POLY_WALLET")
    if not eoa: die("POLY_WALLET not set")

    do_wrap    = args.wrap is not None or args.all is not None
    do_approve = args.approve or args.all is not None
    wrap_amt   = args.all if args.all is not None else args.wrap
    check_only = not (do_wrap or do_approve)

    print(f"EOA: {eoa}\n")

    # ── State ──
    usdce  = _balance(USDCE, eoa) / 1e6
    pusd   = _balance(PUSD,  eoa) / 1e6
    pusd_allow = {s: _allowance(PUSD, eoa, s) for s in SPENDERS}
    ctf_allow  = {s: _is_approved_for_all(CTF, eoa, s) for s in SPENDERS}

    print(f"USDC.e balance: {usdce:.4f}")
    print(f"pUSD balance:   {pusd:.4f}")
    print(f"pUSD allowances (need MAX for each):")
    for s in SPENDERS:
        v = pusd_allow[s]
        print(f"  {s}: {'MAX' if v > 10**70 else v}")
    print(f"CTF setApprovalForAll (need True for each):")
    for s in SPENDERS:
        print(f"  {s}: {ctf_allow[s]}")

    needs_wrap    = (do_wrap and wrap_amt and pusd < wrap_amt)
    needs_pusd_ap = [s for s in SPENDERS if pusd_allow[s] < 10**70]
    needs_ctf_ap  = [s for s in SPENDERS if not ctf_allow[s]]

    if check_only:
        print("\n=== Check only. Suggested next step: ===")
        if pusd < 1 and usdce >= 1:
            print(f"  python3 setup.py --all {min(usdce, 100):.2f}")
        elif needs_pusd_ap or needs_ctf_ap:
            print("  python3 setup.py --approve")
        else:
            print("  ✅ Ready to trade.")
        return

    # ── Wrap ──
    if needs_wrap:
        if usdce < wrap_amt:
            die(f"USDC.e balance {usdce} < requested wrap {wrap_amt}. Fund EOA on Polygon first.")
        amt_wei = int(wrap_amt * 1_000_000)
        print(f"\n=== Wrap {wrap_amt} USDC.e -> pUSD ===")
        _send(USDCE,  _approve(ONRAMP, amt_wei),         f"approve USDC.e -> Onramp")
        time.sleep(2)
        _send(ONRAMP, _wrap(USDCE, eoa, amt_wei),        f"wrap {wrap_amt} USDC.e -> pUSD")
        time.sleep(2)
    elif do_wrap:
        print(f"\n=== Wrap skipped: pUSD balance {pusd} already >= {wrap_amt} ===")

    # ── Approvals ──
    if do_approve:
        if not needs_pusd_ap and not needs_ctf_ap:
            print(f"\n=== Approvals already in place ===")
        else:
            print(f"\n=== Approvals: pUSD to {len(needs_pusd_ap)} spenders + CTF to {len(needs_ctf_ap)} spenders ===")
            for s in needs_pusd_ap:
                _send(PUSD, _approve(s, MAX_UINT), f"approve pUSD MAX -> {s[:10]}...")
                time.sleep(2)
            for s in needs_ctf_ap:
                _send(CTF,  _set_approval_for_all(s, True), f"setApprovalForAll CTF -> {s[:10]}...")
                time.sleep(2)

    print("\n=== Verify post-setup ===")
    print("  python3 setup.py        # re-check")
    print("  python3 status.py       # confirm CLOB sees pUSD + allowances")

if __name__ == "__main__":
    main()
