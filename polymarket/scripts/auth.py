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
import os
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
    if not isinstance(signature, str) or not signature.strip() or signature == "undefined":
        die("Invalid signature: must be a non-empty hex string from wallet_sign_typed_data")

    try:
        ts_int = int(timestamp)
    except (TypeError, ValueError):
        die("Invalid timestamp: must be integer from the latest --prepare")

    if ts_int <= 0:
        die("Invalid timestamp: must be > 0")

    now = int(time.time())
    if abs(now - ts_int) > 600:
        die("Timestamp expired: rerun --prepare, re-sign, then --save with the new timestamp")

    auth_file = "/tmp/poly_auth.json"
    if os.path.exists(auth_file):
        try:
            with open(auth_file, "r") as f:
                prepared = json.load(f)
            prepared_wallet = ((prepared.get("meta") or {}).get("wallet") or "").lower()
            prepared_ts = str(((prepared.get("meta") or {}).get("timestamp") or ""))
            if prepared_wallet and wallet.lower() != prepared_wallet:
                die("Wallet mismatch: --save wallet must match the latest --prepare wallet")
            if prepared_ts and str(ts_int) != prepared_ts:
                die("Timestamp mismatch: --save timestamp must match the latest --prepare timestamp")
        except Exception as e:
            die(f"Failed to validate /tmp/poly_auth.json: {e}")

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
        die(
            f"Auth failed ({r.status_code}): {r.text} | "
            "Likely causes: signature/timestamp mismatch, wallet mismatch vs --prepare, or expired timestamp. "
            "Fix: rerun --prepare <wallet>, sign that exact payload, then --save with same wallet+timestamp."
        )
    
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
