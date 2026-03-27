"""
Polymarket Utilities
Shared constants, credential loading, VPN auto-detection, HTTP helpers.
Merged from official v2.4 + local v3.9 best practices.
"""
import os
import time
import hmac
import hashlib
import base64
import json
import re
import logging
import requests as _requests
import concurrent.futures

logger = logging.getLogger(__name__)

# ── API Endpoints ──
BASE = "https://clob.polymarket.com"
GAMMA = "https://gamma-api.polymarket.com"
DATA_API = "https://data-api.polymarket.com"

# ── Contracts (Polygon) ──
CTF_EXCHANGE = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
CTF_EXCHANGE_NEG = "0xC5d563A36AE78145C45a50134d48A1215220f80a"
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
CTF_TOKEN = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
CHAIN_ID = 137

# ── Signature types ──
EOA = 0  # Direct EOA signing (we use this)


# ── Credential loading (dynamic, never cached stale) ──

def _load_env():
    """Load environment variables from workspace .env file."""
    env = {}
    for path in ["/data/workspace/.env"]:
        try:
            if os.path.exists(path):
                with open(path) as f:
                    for line in f:
                        line = line.strip()
                        if line and "=" in line and not line.startswith("#"):
                            k, v = line.split("=", 1)
                            env[k.strip()] = v.strip()
        except Exception:
            pass
    return env


def _get_credential(key):
    """Get credential from environment or .env file (fresh read every time)."""
    value = os.environ.get(key)
    if value:
        return value
    return _load_env().get(key, "")


# Credential getters — call these, don't cache the return value
API_KEY = lambda: _get_credential("POLY_API_KEY")
SECRET = lambda: _get_credential("POLY_SECRET")
PASSPHRASE = lambda: _get_credential("POLY_PASSPHRASE")
WALLET = lambda: _get_credential("POLY_WALLET")


# ── VPN Auto-Detection ──

_VPN_REGIONS = ["br", "ar", "mx", "my", "th", "au", "za"]
_vpn_cache_file = os.path.join(os.getcwd(), ".polymarket_vpn_cache.json")


def _load_vpn_cache():
    try:
        if os.path.exists(_vpn_cache_file):
            with open(_vpn_cache_file) as f:
                return json.load(f)
    except Exception:
        pass
    return {"enabled": False, "region": None}


def _save_vpn_cache(enabled, region):
    try:
        with open(_vpn_cache_file, "w") as f:
            json.dump({"enabled": enabled, "region": region}, f)
    except Exception:
        pass


def _test_vpn_regions():
    """Test all VPN regions in parallel, return fastest working one."""
    def test_region(region):
        try:
            proxy = {
                "https": f"http://{region}:x@sc-vpn.internal:8080",
                "http": f"http://{region}:x@sc-vpn.internal:8080",
            }
            start = time.time()
            r = _requests.get(f"{BASE}/sampling-simplified-markets", proxies=proxy, timeout=5)
            elapsed = time.time() - start
            if r.status_code == 200:
                return (region, elapsed)
        except Exception:
            pass
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as executor:
        results = executor.map(test_region, _VPN_REGIONS)
        working = [r for r in results if r is not None]
        if working:
            return sorted(working, key=lambda x: x[1])[0][0]
    return None


def _get_vpn_proxy():
    """
    Auto-detecting VPN proxy:
    1. Check env override (POLY_VPN_REGION)
    2. Check disk cache
    3. Auto-detect fastest region
    """
    if os.environ.get("POLY_DISABLE_VPN", "").lower() == "true":
        return None

    forced = os.environ.get("POLY_VPN_REGION", "").strip()
    if forced:
        return {
            "https": f"http://{forced}:x@sc-vpn.internal:8080",
            "http": f"http://{forced}:x@sc-vpn.internal:8080",
        }

    cache = _load_vpn_cache()
    if cache.get("enabled") and cache.get("region"):
        r = cache["region"]
        return {
            "https": f"http://{r}:x@sc-vpn.internal:8080",
            "http": f"http://{r}:x@sc-vpn.internal:8080",
        }

    return None


def _auto_vpn_request(method, url, **kwargs):
    """
    Make HTTP request with automatic VPN fallback on 403.
    1. Try direct
    2. If 403 → try cached VPN
    3. If still 403 → auto-detect and cache
    """
    timeout = kwargs.pop("timeout", 25)

    # Try direct first
    try:
        r = _requests.request(method, url, timeout=timeout, **kwargs)
        if r.status_code != 403:
            return r
    except Exception:
        pass

    # Try cached VPN
    proxy = _get_vpn_proxy()
    if proxy:
        try:
            r = _requests.request(method, url, timeout=timeout, proxies=proxy, **kwargs)
            if r.status_code != 403:
                return r
        except Exception:
            pass

    # Auto-detect
    region = _test_vpn_regions()
    if region:
        _save_vpn_cache(True, region)
        proxy = {
            "https": f"http://{region}:x@sc-vpn.internal:8080",
            "http": f"http://{region}:x@sc-vpn.internal:8080",
        }
        return _requests.request(method, url, timeout=timeout, proxies=proxy, **kwargs)

    # Last resort: return whatever we got
    return _requests.request(method, url, timeout=timeout, **kwargs)


# ── HTTP Helpers (CLOB + Gamma) ──

def _build_hmac_signature(secret, timestamp, method, path, body=None):
    """Build HMAC-SHA256 signature for CLOB L2 auth.
    Message format: timestamp + METHOD + path [+ body] (concatenated, NO separators).
    """
    message = str(timestamp) + method.upper() + path
    if body:
        message += body
    key = base64.urlsafe_b64decode(secret)
    sig = hmac.new(key, message.encode(), hashlib.sha256)
    return base64.urlsafe_b64encode(sig.digest()).decode()


def l2_headers(method, path, body=None):
    """Build authenticated L2 headers for private CLOB endpoints."""
    api_key = API_KEY()
    secret = SECRET()
    passphrase = PASSPHRASE()
    wallet = WALLET()

    if not all([api_key, secret, passphrase, wallet]):
        raise ValueError(
            "Missing credentials. Set POLY_API_KEY, POLY_SECRET, POLY_PASSPHRASE, POLY_WALLET in .env"
        )

    ts = str(int(time.time()))
    sig = _build_hmac_signature(secret, ts, method, path, body)
    return {
        "POLY_ADDRESS": wallet,
        "POLY_SIGNATURE": sig,
        "POLY_TIMESTAMP": ts,
        "POLY_API_KEY": api_key,
        "POLY_PASSPHRASE": passphrase,
        "Content-Type": "application/json",
    }


def clob_get(url, headers=None, params=None):
    """GET request to CLOB with VPN fallback."""
    return _auto_vpn_request("GET", url, headers=headers, params=params)


def clob_post(url, headers=None, data=None, json_data=None):
    """POST request to CLOB with VPN fallback."""
    return _auto_vpn_request("POST", url, headers=headers, data=data, json=json_data)


def clob_delete(url, headers=None, data=None):
    """DELETE request to CLOB with VPN fallback."""
    return _auto_vpn_request("DELETE", url, headers=headers, data=data)


def gamma_get(url, params=None):
    """GET request to Gamma API (public, no auth)."""
    return _auto_vpn_request("GET", url, params=params)


# ── URL Parsing ──

def parse_polymarket_url(url_or_slug):
    """Parse a Polymarket URL or slug into (event_slug, market_slug)."""
    s = (url_or_slug or "").strip().rstrip("/")
    m = re.search(r"polymarket\.com/event/([^/?#]+)(?:/([^/?#]+))?", s)
    if m:
        return m.group(1), m.group(2)
    if "/" in s:
        parts = s.rsplit("/", 1)
        return parts[0], parts[1] if len(parts) > 1 else None
    return s, None


# ── Market Enrichment ──

def enrich_market(m):
    """Enrich a Gamma market dict with structured outcome data."""
    enriched = {
        "question": m.get("question"),
        "slug": m.get("slug"),
        "condition_id": m.get("conditionId") or m.get("condition_id"),
        "active": m.get("active", False),
        "closed": m.get("closed", False),
        "volume": m.get("volume"),
        "liquidity": m.get("liquidity"),
        "neg_risk": m.get("negRisk", False),
        "outcomes": [],
    }

    outcomes = m.get("outcomes", [])
    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
        except Exception:
            outcomes = []

    prices = m.get("outcomePrices", [])
    if isinstance(prices, str):
        try:
            prices = json.loads(prices)
        except Exception:
            prices = []

    token_ids = m.get("clobTokenIds", [])
    if isinstance(token_ids, str):
        try:
            token_ids = json.loads(token_ids)
        except Exception:
            token_ids = []

    for i, name in enumerate(outcomes):
        entry = {"name": name}
        if i < len(prices):
            try:
                entry["price"] = float(prices[i])
            except Exception:
                pass
        if i < len(token_ids):
            entry["token_id"] = token_ids[i]
        # Optionally fetch live prices
        try:
            entry["buy_price"] = get_price(entry["token_id"], "BUY")
            entry["sell_price"] = get_price(entry["token_id"], "SELL")
            entry["midpoint"] = get_midpoint(entry["token_id"])
        except Exception:
            pass
        enriched["outcomes"].append(entry)

    return enriched


def get_price(token_id, side="BUY"):
    """Get current price for a token."""
    r = clob_get(f"{BASE}/price", params={"token_id": token_id, "side": side})
    return float(r.json().get("price", 0)) if r.status_code == 200 else None


def get_midpoint(token_id):
    """Get midpoint price for a token."""
    r = clob_get(f"{BASE}/midpoint", params={"token_id": token_id})
    return float(r.json().get("mid", 0)) if r.status_code == 200 else None


def get_orderbook(token_id):
    """Get orderbook for a token."""
    r = clob_get(f"{BASE}/book", params={"token_id": token_id})
    r.raise_for_status()
    return r.json()
