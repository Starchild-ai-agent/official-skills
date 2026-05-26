#!/usr/bin/env python3
"""
Polymarket Auth — check credentials, output EIP-712 for derive if missing.

Usage:
  python3 auth.py --check                    # just check if creds exist & valid
  python3 auth.py --prepare <wallet_address>  # build ClobAuth EIP-712 for signing
  python3 auth.py --save <signature> <wallet> <timestamp>  # derive + save to .env

Full flow (agent):
  1. bash: python3 auth.py --check
  2. If missing: python3 auth.py --prepare 0xWALLET → get EIP-712 JSON
  3. wallet_sign_typed_data(domain, types, primaryType, message)
  4. bash: python3 auth.py --save 0xSIG 0xWALLET TIMESTAMP
"""
import sys, json, argparse, time
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import (
    BASE, CHAIN_ID, cred, ensure_credentials,
    clob_get, clob_post, save_env_var, die,
)

def check():
    ok, msg = ensure_credentials()
    if not ok:
        print(f"❌ {msg}")
        return False
    
    # Verify creds work by checking balance
    from common import l2_headers
    r = clob_get("/balance-allowance",
        headers=l2_headers("GET", "/balance-allowance"),
        params={"asset_type": "COLLATERAL", "signature_type": 0},
    )
    if r.status_code == 200:
        bal = r.json().get("balance", "0")
        print(f"✅ Credentials valid. Balance: ${int(bal)/1_000_000:.2f}")
        return True
    else:
        print(f"⚠️  Credentials exist but may be stale ({r.status_code}). Re-derive recommended.")
        return False

def prepare(wallet):
    ts = str(int(time.time()))
    payload = {
        "domain": {"name": "ClobAuthDomain", "version": "1", "chainId": CHAIN_ID},
        "types": {"ClobAuth": [
            {"name": "address", "type": "address"},
            {"name": "timestamp", "type": "string"},
            {"name": "nonce", "type": "uint256"},
            {"name": "message", "type": "string"},
        ]},
        "primaryType": "ClobAuth",
        "message": {
            "address": wallet,
            "timestamp": ts,
            "nonce": 0,
            "message": "This message attests that I control the given wallet",
        },
        "meta": {"wallet": wallet, "timestamp": ts},
    }
    outfile = "/tmp/poly_auth.json"
    with open(outfile, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"AUTH READY: sign with wallet_sign_typed_data")
    print(f"  File: {outfile}")
    print(f"  Timestamp: {ts}")
    print(f"  Then: python3 auth.py --save <signature> {wallet} {ts}")

def save(signature, wallet, timestamp):
    # --- Defensive validation BEFORE hitting the API ---
    # 1. Signature shape
    if not signature or not signature.startswith("0x") or len(signature) != 132:
        die(
            f"Invalid signature: expected 132-char 0x... hex, got len={len(signature) if signature else 0}.\n"
            "  Cause: wallet_sign_typed_data likely returned undefined or you pasted the wrong value.\n"
            "  Fix:   restart from --prepare, sign the EIP-712 from /tmp/poly_auth.json with wallet_sign_typed_data,\n"
            "         then pass the resulting 0x-prefixed signature here."
        )

    # 2. Wallet shape
    if not wallet or not wallet.startswith("0x") or len(wallet) != 42:
        die(f"Invalid wallet: expected 42-char 0x... hex, got {wallet!r}")

    # 3. Timestamp shape + staleness
    try:
        ts_int = int(timestamp)
    except (TypeError, ValueError):
        die(f"Invalid timestamp: must be an integer (epoch seconds), got {timestamp!r}")
    if ts_int <= 0:
        die(f"Invalid timestamp: must be > 0, got {ts_int}")
    age = int(time.time()) - ts_int
    if age > 300:
        die(
            f"Timestamp expired: {age}s old (max 300s).\n"
            "  Cause: signature + timestamp must both come from the SAME --prepare call, used within 5 minutes.\n"
            f"  Fix:   re-run `python3 auth.py --prepare {wallet}`, re-sign, then --save within 5 min."
        )
    if age < -60:
        die(
            f"Timestamp from the future ({-age}s ahead).\n"
            "  Cause: you likely reused a timestamp from a different prepare call.\n"
            f"  Fix:   re-run `python3 auth.py --prepare {wallet}` to get a fresh timestamp."
        )

    # 4. Wallet consistency with the prepare call that produced this timestamp
    try:
        with open("/tmp/poly_auth.json") as f:
            prep = json.load(f)
        prep_wallet = prep.get("meta", {}).get("wallet", "")
        prep_ts = prep.get("meta", {}).get("timestamp", "")
        if prep_wallet and prep_wallet.lower() != wallet.lower():
            die(
                f"Wallet mismatch: --prepare was called with {prep_wallet}, but --save received {wallet}.\n"
                "  Cause: the signature was produced for a different wallet than the one you're saving for.\n"
                f"  Fix:   re-run `python3 auth.py --prepare {wallet}` and re-sign with the matching wallet."
            )
        if prep_ts and str(prep_ts) != str(ts_int):
            die(
                f"Timestamp mismatch: --prepare produced timestamp {prep_ts}, but --save received {ts_int}.\n"
                "  Cause: signature and timestamp are from different prepare calls — they must come as a pair.\n"
                f"  Fix:   re-run `python3 auth.py --prepare {wallet}`, re-sign, then --save with the new pair."
            )
    except FileNotFoundError:
        # No prep file — skip consistency check but warn. User may be running --save with values from a
        # previous session; staleness check above already enforces the 5-min window.
        pass
    except (json.JSONDecodeError, KeyError):
        pass  # Corrupt prep file — skip check, rely on API-side validation.

    headers = {
        "POLY_ADDRESS": wallet,
        "POLY_SIGNATURE": signature,
        "POLY_TIMESTAMP": str(ts_int),
        "POLY_NONCE": "0",
        "Content-Type": "application/json",
    }

    # Try derive first
    r = clob_get("/auth/derive-api-key", headers=headers)
    if r.status_code != 200:
        r = clob_post("/auth/api-key", headers=headers)

    if r.status_code != 200:
        # Structured hint for the most common cause
        hint = ""
        body = (r.text or "").lower()
        if r.status_code == 401:
            hint = (
                "\n  Most likely cause: signature does NOT match (wallet, timestamp) pair Polymarket expects.\n"
                "  Restart from --prepare to get a fresh pair, sign with the EXACT wallet that owns the address,\n"
                "  and submit within 5 minutes. Do NOT mix timestamps/signatures across prepare calls."
            )
        elif r.status_code == 403 and "geo" in body:
            hint = "\n  Cause: geo-block. Set POLY_VPN_REGION=ar (or another supported region) and retry."
        die(f"Auth failed ({r.status_code}): {r.text}{hint}")

    data = r.json()
    api_key = data.get("apiKey", "")
    secret = data.get("secret", "")
    passphrase = data.get("passphrase", "")

    if not all([api_key, secret, passphrase]):
        die(f"Incomplete credentials: {json.dumps(data)}")

    save_env_var("POLY_API_KEY", api_key)
    save_env_var("POLY_SECRET", secret)
    save_env_var("POLY_PASSPHRASE", passphrase)
    save_env_var("POLY_WALLET", wallet)

    print(f"✅ Credentials saved to .env")
    print(f"  API_KEY: {api_key[:8]}...")
    print(f"  WALLET: {wallet}")

def main():
    parser = argparse.ArgumentParser(description="Polymarket Auth")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--prepare", metavar="WALLET")
    group.add_argument("--save", nargs=3, metavar=("SIG", "WALLET", "TIMESTAMP"))
    args = parser.parse_args()

    if args.check:
        sys.exit(0 if check() else 1)
    elif args.prepare:
        prepare(args.prepare)
    elif args.save:
        save(*args.save)

if __name__ == "__main__":
    main()
