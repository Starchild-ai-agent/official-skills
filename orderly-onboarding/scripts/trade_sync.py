#!/usr/bin/env python3
"""Orderly trade sync — index fills for the *execution* wallet into trade analytics.

Flow (idempotent, safe to re-run / schedule):
  1. Resolve the execution wallet address:
       --address / ORDERLY_WALLET_ADDRESS, else agent Privy EVM wallet.
       Never invent an address — wallet_address in events MUST be the
       address that actually holds the Orderly account / placed the trades
       (agent Privy OR user's own third-party wallet).
  2. Look up the Orderly account for BROKER_ID under that address.
  3. Prefer private GET /v1/trades when a read-scope ed25519 key is available
     for that account (agent can mint one via EIP-712 only for its own wallet;
     third-party wallets need an existing key file).
  4. Else fall back to Public Info API (zero-auth) by address — covers
     third-party / login wallets without keys.
  5. Fire-and-forget report to POST {AI_AGENT_API_URL}/v1/trade-events
     (server dedupes on (user_id, dedupe_key)).

Requires: pynacl, base58; wallet service only needed for agent-wallet key mint.
Usage:
  python3 scripts/trade_sync.py [--broker woofi_pro] [--days 90]
  python3 scripts/trade_sync.py --address 0xUserWallet --broker woofi_pro
"""
import argparse
import asyncio
import base64
import hashlib
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

BASE = "https://api-evm.orderly.org"
PUBLIC_QUERY = "https://api.orderly.org/v1/public/query"
CHAIN_ID = 42161  # Arbitrum (registration chain; account is omnichain)
WORKSPACE = os.environ.get("WORKSPACE_DIR", "/data/workspace")


def key_file_for(account_id: str) -> str:
    """Per-account key path so agent + third-party accounts don't clobber each other."""
    safe = (account_id or "unknown").replace("/", "_")[:32]
    return os.path.join(WORKSPACE, f".orderly_key_{safe}.json")


DOMAIN = {
    "name": "Orderly",
    "version": "1",
    "chainId": CHAIN_ID,
    "verifyingContract": "0xCcCCccccCCCCcCCCCCCcCcCccCcCCCcCcccccccC",
}
EIP712_DOMAIN = [
    {"name": "name", "type": "string"},
    {"name": "version", "type": "string"},
    {"name": "chainId", "type": "uint256"},
    {"name": "verifyingContract", "type": "address"},
]


def http(method, path, body=None, headers=None, base=BASE):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        base + path if path.startswith("/") else path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {"success": False, "error": str(e)}


async def sign712(primary, types, message):
    from core.wallet_runtime import wallet_request  # Starchild agent runtime

    payload = {
        "domain": DOMAIN,
        "types": {"EIP712Domain": EIP712_DOMAIN, **types},
        "primaryType": primary,
        "message": message,
    }
    result = await wallet_request("POST", "/agent/sign-typed-data", payload)
    return result.get("signature") or result.get("data", {}).get("signature")


async def get_agent_wallet_address():
    from core.wallet_runtime import wallet_request

    data = await wallet_request("GET", "/agent/wallet", None)
    wallets = data if isinstance(data, list) else data.get("wallets", [])
    for w in wallets:
        if w.get("chain_type") == "ethereum":
            return w["wallet_address"]
    raise RuntimeError("no ethereum agent wallet")


async def resolve_execution_address(cli_address: str | None) -> tuple[str, bool]:
    """Return (execution_wallet, is_agent_wallet).

    Priority: --address > ORDERLY_WALLET_ADDRESS > agent Privy EVM wallet.
    """
    addr = (cli_address or os.environ.get("ORDERLY_WALLET_ADDRESS") or "").strip()
    agent = None
    try:
        agent = await get_agent_wallet_address()
    except Exception:
        agent = None

    if addr:
        is_agent = bool(agent and addr.lower() == agent.lower())
        return addr, is_agent
    if agent:
        return agent, True
    raise RuntimeError(
        "no execution wallet: pass --address / set ORDERLY_WALLET_ADDRESS, "
        "or run on a machine with an agent EVM wallet"
    )


def lookup_account(addr, broker):
    st, acc = http("GET", f"/v1/get_account?address={addr}&broker_id={broker}")
    return acc.get("data", {}).get("account_id")


async def ensure_account(addr, broker, can_sign: bool):
    account_id = lookup_account(addr, broker)
    if account_id:
        return account_id
    if not can_sign:
        raise RuntimeError(
            f"no Orderly account for {addr} under broker={broker}; "
            "cannot register without agent-wallet EIP-712 signature for that address"
        )
    st, n = http("GET", "/v1/registration_nonce")
    msg = {
        "brokerId": broker,
        "chainId": CHAIN_ID,
        "timestamp": int(time.time() * 1000),
        "registrationNonce": int(n["data"]["registration_nonce"]),
    }
    sig = await sign712(
        "Registration",
        {
            "Registration": [
                {"name": "brokerId", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "timestamp", "type": "uint64"},
                {"name": "registrationNonce", "type": "uint256"},
            ]
        },
        msg,
    )
    st, reg = http(
        "POST",
        "/v1/register_account",
        {"message": msg, "signature": sig, "userAddress": addr},
    )
    if not reg.get("success"):
        raise RuntimeError(f"register_account failed: {reg}")
    return reg["data"]["account_id"]


async def ensure_key(addr, broker, account_id, can_sign: bool):
    path = key_file_for(account_id)
    if os.path.exists(path):
        k = json.load(open(path))
        if k.get("account_id") == account_id and k.get("expiration", 0) > time.time() * 1000:
            return k
    # legacy single-file path from v1.1.0
    legacy = os.path.join(WORKSPACE, ".orderly_key.json")
    if os.path.exists(legacy):
        k = json.load(open(legacy))
        if k.get("account_id") == account_id and k.get("expiration", 0) > time.time() * 1000:
            return k
    if not can_sign:
        return None  # caller falls back to public API
    sk = nacl.signing.SigningKey.generate()
    pub = "ed25519:" + base58.b58encode(bytes(sk.verify_key)).decode()
    exp = int(time.time() * 1000) + 364 * 86400 * 1000
    msg = {
        "brokerId": broker,
        "chainId": CHAIN_ID,
        "orderlyKey": pub,
        "scope": "read",
        "timestamp": int(time.time() * 1000),
        "expiration": exp,
    }
    sig = await sign712(
        "AddOrderlyKey",
        {
            "AddOrderlyKey": [
                {"name": "brokerId", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "orderlyKey", "type": "string"},
                {"name": "scope", "type": "string"},
                {"name": "timestamp", "type": "uint64"},
                {"name": "expiration", "type": "uint64"},
            ]
        },
        msg,
    )
    st, ak = http(
        "POST",
        "/v1/orderly_key",
        {"message": msg, "signature": sig, "userAddress": addr},
    )
    if not ak.get("success"):
        raise RuntimeError(f"orderly_key failed: {ak}")
    k = {
        "account_id": account_id,
        "pub": pub,
        "seed_b58": base58.b58encode(bytes(sk)).decode(),
        "expiration": exp,
        "wallet_address": addr,
    }
    with open(path, "w") as f:
        json.dump(k, f)
    os.chmod(path, 0o600)
    return k


def signed_get(key, path):
    sk = nacl.signing.SigningKey(base58.b58decode(key["seed_b58"]))
    ts = str(int(time.time() * 1000))
    sig = base64.urlsafe_b64encode(sk.sign((ts + "GET" + path).encode()).signature).decode()
    return http(
        "GET",
        path,
        headers={
            "orderly-timestamp": ts,
            "orderly-account-id": key["account_id"],
            "orderly-key": key["pub"],
            "orderly-signature": sig,
        },
    )


def synthetic_trade_id(ts_ms, symbol, side, price, size):
    """Stable fallback id when the API row carries no trade/match id.

    Archived Public Info rows sometimes omit id/trade_id/match_id. Without this
    every such fill would collapse into the same dedupe_key and the server's
    unique index would keep only one row per wallet.
    """
    basis = f"{ts_ms}:{symbol or ''}:{side or ''}:{price}:{size}"
    return "h" + hashlib.sha1(basis.encode()).hexdigest()[:20]


def map_fill_private(t, addr, account_id, broker):
    price = float(t.get("executed_price") or 0)
    size = float(t.get("executed_quantity") or 0)
    trade_id = t.get("id") or synthetic_trade_id(
        t.get("executed_timestamp") or 0,
        t.get("symbol"),
        (t.get("side") or "").lower(),
        price,
        size,
    )
    return {
        "source": "orderly_sync",
        "venue": f"orderly:{broker}",
        "event_type": "fill",
        "wallet_address": addr,  # execution wallet, not always agent
        "account_id": account_id,
        "symbol": t.get("symbol"),
        "side": (t.get("side") or "").lower(),
        "price": str(t.get("executed_price", "")),
        "size": str(t.get("executed_quantity", "")),
        "notional_usd": str(round(price * size, 6)),
        "fee": str(t.get("fee", "")),
        "fee_currency": t.get("fee_asset"),
        "order_id": str(t.get("order_id", "")),
        "dedupe_key": f"orderly:{account_id}:{trade_id}",
        "occurred_at": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ",
            time.gmtime((t.get("executed_timestamp") or 0) / 1000),
        ),
        "raw": {"trade_id": trade_id, "broker": broker},
    }


def map_fill_public(t, addr, account_id, broker):
    """Public Info `trades` rows — field names vary slightly by archive/realtime."""
    price = float(t.get("executed_price") or t.get("price") or 0)
    size = float(t.get("executed_quantity") or t.get("quantity") or t.get("size") or 0)
    trade_id = t.get("id") or t.get("trade_id") or t.get("match_id")
    side = (t.get("side") or "").lower()
    ts_ms = t.get("executed_timestamp") or t.get("timestamp") or 0
    if isinstance(ts_ms, str):
        try:
            ts_ms = int(ts_ms)
        except ValueError:
            ts_ms = 0
    if not trade_id:
        trade_id = synthetic_trade_id(ts_ms, t.get("symbol"), side, price, size)
    return {
        "source": "orderly_public_sync",
        "venue": f"orderly:{broker}",
        "event_type": "fill",
        "wallet_address": addr,
        "account_id": account_id or t.get("account_id"),
        "symbol": t.get("symbol"),
        "side": side,
        "price": str(price),
        "size": str(size),
        "notional_usd": str(round(price * size, 6)),
        "fee": str(t.get("fee", "")),
        "fee_currency": t.get("fee_asset") or t.get("fee_currency"),
        "order_id": str(t.get("order_id", "") or ""),
        "dedupe_key": f"orderly:{(account_id or addr).lower()}:{trade_id}",
        "occurred_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts_ms / 1000))
        if ts_ms
        else None,
        "raw": {"trade_id": trade_id, "broker": broker, "public": True},
    }


def fetch_private_fills(key, start_ms):
    page = 1
    while True:
        st, res = signed_get(key, f"/v1/trades?size=500&page={page}&start_t={start_ms}")
        if not res.get("success"):
            raise RuntimeError(f"trades fetch failed: {res}")
        rows = (res.get("data") or {}).get("rows") or []
        yield from rows
        if len(rows) < 500:
            break
        page += 1


def fetch_public_fills(addr):
    cursor = None
    while True:
        body = {"type": "trades", "address": addr}
        if cursor:
            body["cursor"] = cursor
        req = urllib.request.Request(
            PUBLIC_QUERY,
            data=json.dumps(body).encode(),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                res = json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"public trades failed: {e.read()}") from e
        data = res.get("data") or {}
        if isinstance(data, list):
            rows, next_c = data, None
        else:
            rows = data.get("rows") or data.get("trades") or data.get("list") or []
            next_c = data.get("next_cursor")
        for t in rows:
            yield t
        if not next_c:
            break
        cursor = next_c


async def main():
    ap = argparse.ArgumentParser(
        description="Sync Orderly fills for the execution wallet into trade_events"
    )
    ap.add_argument("--broker", default="woofi_pro")
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument(
        "--address",
        default=None,
        help="Execution wallet (0x…). Defaults to ORDERLY_WALLET_ADDRESS or agent wallet. "
        "Use the wallet that actually trades — not always the agent Privy wallet.",
    )
    ap.add_argument(
        "--public-only",
        action="store_true",
        help="Force Public Info API (no private key). Good for third-party wallets.",
    )
    args = ap.parse_args()

    addr, is_agent = await resolve_execution_address(args.address)
    can_sign = is_agent and not args.public_only

    account_id = lookup_account(addr, args.broker)
    if not account_id and can_sign:
        account_id = await ensure_account(addr, args.broker, can_sign=True)
    if not account_id and not args.public_only:
        print(f"no Orderly account for {addr} broker={args.broker}; trying public API")

    start = int((time.time() - args.days * 86400) * 1000)
    events = []
    mode = "none"

    key = None
    if account_id and not args.public_only:
        key = await ensure_key(addr, args.broker, account_id, can_sign=can_sign)

    if key:
        mode = "private"
        for t in fetch_private_fills(key, start):
            events.append(map_fill_private(t, addr, account_id, args.broker))
    else:
        mode = "public"
        for t in fetch_public_fills(addr):
            events.append(map_fill_public(t, addr, account_id, args.broker))

    print(
        f"wallet={addr} account={(account_id or 'n/a')[:12]}… "
        f"mode={mode} is_agent={is_agent} fills={len(events)}"
    )
    if events:
        # blocking=True is REQUIRED here: this is a short-lived script and a
        # background daemon thread would be killed on exit before the POST.
        sent = report_trade_events(events, blocking=True)
        print(f"reported {sent}/{len(events)} events (server dedupes on user_id+dedupe_key)")
        if sent < len(events):
            print("WARNING: some batches failed — re-run is safe (idempotent)")


if __name__ == "__main__":
    asyncio.run(main())
