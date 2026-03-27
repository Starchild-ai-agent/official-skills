#!/usr/bin/env python3
"""Shared helpers for script-based 1inch skill (no platform tool imports)."""

from __future__ import annotations

import json
import os
import subprocess
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict

import requests

NATIVE_TOKEN = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
ROUTER_ADDRESS = "0x111111125421cA6dc452d289314280a0f8842A65"

SUPPORTED_CHAINS = {
    "ethereum": 1,
    "arbitrum": 42161,
    "base": 8453,
    "optimism": 10,
    "polygon": 137,
    "bsc": 56,
    "avalanche": 43114,
    "gnosis": 100,
}


def _build_requests_proxies(require_proxy: bool = False, service_name: str = "") -> Dict[str, str]:
    """Build proxy dict from env. Prefer explicit HTTP(S)_PROXY, fallback to PROXY_HOST/PORT."""
    http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")

    if http_proxy or https_proxy:
        out: Dict[str, str] = {}
        if http_proxy:
            out["http"] = http_proxy
        if https_proxy:
            out["https"] = https_proxy
        # If only one is set, mirror it for both protocols for reliability.
        if "http" not in out and "https" in out:
            out["http"] = out["https"]
        if "https" not in out and "http" in out:
            out["https"] = out["http"]
        return out

    host = os.getenv("PROXY_HOST", "").strip()
    port = os.getenv("PROXY_PORT", "").strip()
    if host and port:
        # IPv6 hosts must be wrapped in [] in proxy URLs
        if ":" in host and not (host.startswith("[") and host.endswith("]")):
            host_fmt = f"[{host}]"
        else:
            host_fmt = host
        proxy_url = f"http://{host_fmt}:{port}"
        return {"http": proxy_url, "https": proxy_url}

    if require_proxy:
        target = f" for {service_name}" if service_name else ""
        raise RuntimeError(
            "sc-proxy is required" + target + ", but no proxy env found. "
            "Set HTTP_PROXY/HTTPS_PROXY or PROXY_HOST+PROXY_PORT."
        )

    return {}


def resolve_chain_id(chain: str) -> int:
    key = chain.strip().lower()
    if key not in SUPPORTED_CHAINS:
        raise ValueError(f"Unknown chain '{chain}'. Supported: {', '.join(sorted(SUPPORTED_CHAINS))}")
    return SUPPORTED_CHAINS[key]


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def _oidc_token(audience: str) -> str:
    """Get Fly OIDC token via unix socket using curl (no external libs required)."""
    cmd = [
        "curl",
        "-sS",
        "--fail",
        "--unix-socket",
        "/.fly/api",
        "-X",
        "POST",
        "-H",
        "Content-Type: application/json",
        "http://localhost/v1/tokens/oidc",
        "-d",
        json.dumps({"aud": audience}),
    ]
    try:
        out = subprocess.check_output(cmd, text=True).strip()
    except FileNotFoundError as e:
        raise RuntimeError("curl not found; required for Fly OIDC token") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to fetch Fly OIDC token: {e}") from e

    if not out:
        raise RuntimeError("Empty OIDC token response from Fly API")
    return out


def wallet_service_url() -> str:
    return os.getenv("WALLET_SERVICE_URL", "https://wallet-service-dev.fly.dev").rstrip("/")


def wallet_request(method: str, path: str, json_body: Dict[str, Any] | None = None, timeout: int = 30) -> Dict[str, Any]:
    url = f"{wallet_service_url()}{path}"
    audience = os.getenv("WALLET_OIDC_AUDIENCE", wallet_service_url())
    token = _oidc_token(audience)
    headers = {"Authorization": f"Bearer {token}"}
    proxies = _build_requests_proxies()

    resp = requests.request(
        method=method.upper(),
        url=url,
        headers=headers,
        json=json_body,
        timeout=timeout,
        proxies=proxies or None,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Wallet API {resp.status_code}: {resp.text}")

    ctype = (resp.headers.get("content-type") or "").lower()
    if "application/json" in ctype:
        return resp.json()
    text = resp.text.strip()
    return {"raw": text}


def get_evm_wallet_address() -> str:
    data = wallet_request("GET", "/agent/wallet")
    wallets = data if isinstance(data, list) else data.get("wallets", [])
    for w in wallets:
        if isinstance(w, dict) and w.get("chain_type") == "ethereum" and w.get("wallet_address"):
            return w["wallet_address"]
    raise RuntimeError("No ethereum wallet found in /agent/wallet")


def oneinch_get(chain_id: int, path: str, params: Dict[str, Any] | None = None, timeout: int = 20) -> Dict[str, Any]:
    api_key = _require_env("ONEINCH_API_KEY")
    base = f"https://api.1inch.com/swap/v6.1/{chain_id}"
    url = f"{base}{path}"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    # 1inch must go through sc-proxy in this environment
    proxies = _build_requests_proxies(require_proxy=True, service_name="1inch API")

    resp = requests.get(
        url,
        params=params or {},
        headers=headers,
        timeout=timeout,
        proxies=proxies,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"1inch API {resp.status_code}: {resp.text}")
    return resp.json()


def fetch_tokens(chain_id: int) -> Dict[str, Dict[str, Any]]:
    data = oneinch_get(chain_id, "/tokens")
    token_map = data.get("tokens", data)
    if not isinstance(token_map, dict):
        raise RuntimeError("Unexpected /tokens response format")
    return token_map


def build_symbol_index(token_map: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for addr, t in token_map.items():
        if not isinstance(t, dict):
            continue
        symbol = (t.get("symbol") or "").upper()
        if symbol and symbol not in out:
            row = dict(t)
            row["address"] = row.get("address") or addr
            out[symbol] = row
    return out


def resolve_token(token_input: str, token_map: Dict[str, Dict[str, Any]], symbol_index: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    raw = token_input.strip()
    if not raw:
        raise ValueError("Empty token input")

    if raw.lower() in {"native", "eth", NATIVE_TOKEN.lower()}:
        return {"address": NATIVE_TOKEN, "symbol": "NATIVE", "name": "Native Token", "decimals": 18}

    if raw.startswith("0x") and len(raw) == 42:
        # 1inch token map keys are typically lowercase; accept checksum/mixed-case input.
        hit = token_map.get(raw) or token_map.get(raw.lower()) or token_map.get(raw.upper())
        if hit:
            row = dict(hit)
            row["address"] = row.get("address") or raw
            return row
        return {"address": raw, "symbol": "UNKNOWN", "name": "Custom Token", "decimals": 18}

    sym = raw.upper()
    if sym in symbol_index:
        return symbol_index[sym]

    raise ValueError(f"Token '{token_input}' not found in 1inch token list")


def to_wei(amount_human: str, decimals: int) -> str:
    q = Decimal(amount_human)
    if q <= 0:
        raise ValueError("amount must be > 0")
    scale = Decimal(10) ** int(decimals)
    wei = (q * scale).quantize(Decimal("1"), rounding=ROUND_DOWN)
    return str(int(wei))


def from_wei(amount_wei: str, decimals: int) -> str:
    n = Decimal(amount_wei)
    scale = Decimal(10) ** int(decimals)
    return str((n / scale).normalize())


def check_allowance(chain_id: int, token_address: str, wallet: str) -> int:
    if token_address.lower() == NATIVE_TOKEN.lower():
        return 2**256 - 1
    data = oneinch_get(
        chain_id,
        "/approve/allowance",
        params={"tokenAddress": token_address, "walletAddress": wallet},
    )
    val = data.get("allowance", "0")
    return int(val)


def approve_tx(chain_id: int, token_address: str, amount: str | None = None) -> Dict[str, Any]:
    params = {"tokenAddress": token_address}
    if amount is not None:
        params["amount"] = amount
    return oneinch_get(chain_id, "/approve/transaction", params=params)


def quote(chain_id: int, src: str, dst: str, amount_wei: str) -> Dict[str, Any]:
    return oneinch_get(chain_id, "/quote", params={"src": src, "dst": dst, "amount": amount_wei})


def swap_tx(chain_id: int, src: str, dst: str, amount_wei: str, from_addr: str, slippage: float = 1.0) -> Dict[str, Any]:
    return oneinch_get(
        chain_id,
        "/swap",
        params={
            "src": src,
            "dst": dst,
            "amount": amount_wei,
            "from": from_addr,
            "slippage": str(slippage),
        },
    )


def wallet_broadcast(chain_id: int, to: str, data: str, value: str = "0") -> Dict[str, Any]:
    payload = {
        "to": to,
        "amount": value or "0",
        "data": data,
        "chain_id": chain_id,
    }
    return wallet_request("POST", "/agent/transfer", payload)


def compact_token(t: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "address": t.get("address"),
        "symbol": t.get("symbol"),
        "name": t.get("name"),
        "decimals": t.get("decimals"),
    }


def print_json(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))
