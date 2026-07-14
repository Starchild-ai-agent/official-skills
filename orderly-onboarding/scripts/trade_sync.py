#!/usr/bin/env python3
"""Orderly trade sync — index this account's Orderly fills into Starchild trade analytics.

Flow (idempotent, safe to re-run / schedule):
  1. Resolve the agent wallet address (Privy wallet service).
  2. Look up (or register, free) the Orderly account for BROKER_ID.
  3. Ensure a read-scope ed25519 Orderly key (persisted in workspace/.orderly_key.json).
  4. Page through private GET /v1/trades and map every fill to a trade event.
  5. Fire-and-forget report to POST {AI_AGENT_API_URL}/v1/trade-events
     (server dedupes on (user, dedupe_key), so re-syncs never duplicate).

Requires: pynacl, base58, running on a Starchild agent machine (wallet service).
Usage:    python3 scripts/trade_sync.py [--broker woofi_pro] [--days 90]
"""
import argparse
import asyncio
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

import base58
import nacl.signing

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _trade_report import report_trade_events  # noqa: E402

from core.wallet_runtime import wallet_request  # Starchild agent runtime

BASE = "https://api-evm.orderly.org"
CHAIN_ID = 42161  # Arbitrum (registration chain; account is omnichain)
KEY_FILE = os.path.join(os.environ.get("WORKSPACE_DIR", "/data/workspace"), ".orderly_key.json")

DOMAIN = {"name": "Orderly", "version": "1", "chainId": CHAIN_ID,
          "verifyingContract": "0xCcCCccccCCCCcCCCCCCcCcCccCcCCCcCcccccccC"}
EIP712_DOMAIN = [
    {"name": "name", "type": "string"}, {"name": "version", "type": "string"},
    {"name": "chainId", "type": "uint256"}, {"name": "verifyingContract", "type": "address"},
]


def http(method, path, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


async def sign712(primary, types, message):
    payload = {"domain": DOMAIN, "types": {"EIP712Domain": EIP712_DOMAIN, **types},
               "primaryType": primary, "message": message}
    result = await wallet_request("POST", "/agent/sign-typed-data", payload)
    sig = result.get("signature") or result.get("data", {}).get("signature")
    return sig


async def get_wallet_address():
    data = await wallet_request("GET", "/agent/wallet", None)
    wallets = data if isinstance(data, list) else data.get("wallets", [])
    for w in wallets:
        if w.get("chain_type") == "ethereum":
            return w["wallet_address"]
    raise RuntimeError("no ethereum agent wallet")


async def ensure_account(addr, broker):
    st, acc = http("GET", f"/v1/get_account?address={addr}&broker_id={broker}")
    account_id = acc.get("data", {}).get("account_id")
    if account_id:
        return account_id
    st, n = http("GET", "/v1/registration_nonce")
    msg = {"brokerId": broker, "chainId": CHAIN_ID,
           "timestamp": int(time.time() * 1000),
           "registrationNonce": int(n["data"]["registration_nonce"])}
    sig = await sign712("Registration", {"Registration": [
        {"name": "brokerId", "type": "string"}, {"name": "chainId", "type": "uint256"},
        {"name": "timestamp", "type": "uint64"}, {"name": "registrationNonce", "type": "uint256"},
    ]}, msg)
    st, reg = http("POST", "/v1/register_account",
                   {"message": msg, "signature": sig, "userAddress": addr})
    if not reg.get("success"):
        raise RuntimeError(f"register_account failed: {reg}")
    return reg["data"]["account_id"]


async def ensure_key(addr, broker, account_id):
    if os.path.exists(KEY_FILE):
        k = json.load(open(KEY_FILE))
        if k.get("account_id") == account_id and k.get("expiration", 0) > time.time() * 1000:
            return k
    sk = nacl.signing.SigningKey.generate()
    pub = "ed25519:" + base58.b58encode(bytes(sk.verify_key)).decode()
    exp = int(time.time() * 1000) + 364 * 86400 * 1000
    msg = {"brokerId": broker, "chainId": CHAIN_ID, "orderlyKey": pub,
           "scope": "read", "timestamp": int(time.time() * 1000), "expiration": exp}
    sig = await sign712("AddOrderlyKey", {"AddOrderlyKey": [
        {"name": "brokerId", "type": "string"}, {"name": "chainId", "type": "uint256"},
        {"name": "orderlyKey", "type": "string"}, {"name": "scope", "type": "string"},
        {"name": "timestamp", "type": "uint64"}, {"name": "expiration", "type": "uint64"},
    ]}, msg)
    st, ak = http("POST", "/v1/orderly_key",
                  {"message": msg, "signature": sig, "userAddress": addr})
    if not ak.get("success"):
        raise RuntimeError(f"orderly_key failed: {ak}")
    k = {"account_id": account_id, "pub": pub,
         "seed_b58": base58.b58encode(bytes(sk)).decode(), "expiration": exp}
    with open(KEY_FILE, "w") as f:
        json.dump(k, f)
    os.chmod(KEY_FILE, 0o600)
    return k


def signed_get(key, path):
    sk = nacl.signing.SigningKey(base58.b58decode(key["seed_b58"]))
    ts = str(int(time.time() * 1000))
    sig = base64.urlsafe_b64encode(sk.sign((ts + "GET" + path).encode()).signature).decode()
    return http("GET", path, headers={
        "orderly-timestamp": ts, "orderly-account-id": key["account_id"],
        "orderly-key": key["pub"], "orderly-signature": sig})


def map_fill(t, addr, account_id, broker):
    return {
        "source": "orderly_sync", "venue": f"orderly:{broker}", "event_type": "fill",
        "wallet_address": addr, "account_id": account_id,
        "symbol": t.get("symbol"), "side": (t.get("side") or "").lower(),
        "price": str(t.get("executed_price", "")), "size": str(t.get("executed_quantity", "")),
        "notional_usd": str(round(float(t.get("executed_price", 0)) * float(t.get("executed_quantity", 0)), 6)),
        "fee": str(t.get("fee", "")), "fee_currency": t.get("fee_asset"),
        "order_id": str(t.get("order_id", "")),
        "dedupe_key": f"orderly:{account_id}:{t.get('id')}",
        "occurred_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t.get("executed_timestamp", 0) / 1000)),
        "raw": {"trade_id": t.get("id")},
    }


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--broker", default="woofi_pro")
    ap.add_argument("--days", type=int, default=90)
    args = ap.parse_args()

    addr = await get_wallet_address()
    account_id = await ensure_account(addr, args.broker)
    key = await ensure_key(addr, args.broker, account_id)

    start = int((time.time() - args.days * 86400) * 1000)
    events, page = [], 1
    while True:
        st, res = signed_get(key, f"/v1/trades?size=500&page={page}&start_t={start}")
        if not res.get("success"):
            raise RuntimeError(f"trades fetch failed: {res}")
        rows = res["data"]["rows"]
        events += [map_fill(t, addr, account_id, args.broker) for t in rows]
        if len(rows) < 500:
            break
        page += 1

    print(f"account={account_id[:10]}… fills={len(events)}")
    if events:
        report_trade_events(events)
        print("reported (fire-and-forget; server dedupes)")


if __name__ == "__main__":
    asyncio.run(main())
