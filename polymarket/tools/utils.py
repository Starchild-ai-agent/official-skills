"""
Polymarket Utilities
Shared functionality for CLOB API interactions
"""
import os
import time
import hmac
import hashlib
import base64
import json
import re
import requests as _requests

# API Endpoints
BASE = "https://clob.polymarket.com"
GAMMA = "https://gamma-api.polymarket.com"
DATA_API = "https://data-api.polymarket.com"

# Contracts (Polygon)
CTF_EXCHANGE = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
CTF_EXCHANGE_NEG = "0xC5d563A36AE78145C45a50134d48A1215220f80a"
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
CHAIN_ID = 137

# Signature types
EOA = 0  # Direct EOA signing (we use this)
GNOSIS_SAFE = 2  # Proxy wallet


def _load_env():
    """Load environment variables from .env file"""
    env = {}
    try:
        env_path = os.path.join(os.getcwd(), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        env[k.strip()] = v.strip()
    except Exception:
        pass
    return env


# Dynamic credential loading - reads fresh from env/file every time
def _get_credential(key):
    """Get credential from environment or .env file (dynamic, not cached)"""
    # First check environment variables
    value = os.environ.get(key)
    if value:
        return value
    # Then check .env file
    env = _load_env()
    return env.get(key, "")


# Credential getters (call these instead of using globals)
API_KEY = lambda: _get_credential("POLY_API_KEY")
SECRET = lambda: _get_credential("POLY_SECRET")
PASSPHRASE = lambda: _get_credential("POLY_PASSPHRASE")
WALLET = lambda: _get_credential("POLY_WALLET")


# HTTP Helpers
# Auto-detecting VPN with caching
_vpn_cache = {"enabled": False, "region": None, "tested": False}
_vpn_cache_file = os.path.join(os.getcwd(), ".polymarket_vpn_cache.json")

def _load_vpn_cache():
    """Load cached VPN region from disk"""
    try:
        if os.path.exists(_vpn_cache_file):
            with open(_vpn_cache_file, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {"enabled": False, "region": None}

def _save_vpn_cache(enabled, region):
    """Save VPN region to disk cache"""
    try:
        with open(_vpn_cache_file, "w") as f:
            json.dump({"enabled": enabled, "region": region}, f)
    except Exception:
        pass

def _test_vpn_regions():
    """Test all VPN regions and return fastest working one"""
    regions = ["br", "ar", "mx", "my", "th", "au", "za"]
    import concurrent.futures

    def test_region(region):
        try:
            proxy = {
                "https": f"http://{region}:x@sc-vpn.internal:8080",
                "http": f"http://{region}:x@sc-vpn.internal:8080",
            }
            start = time.time()
            r = _requests.get(
                f"{BASE}/sampling-simplified-markets",
                proxies=proxy,
                timeout=5
            )
            elapsed = time.time() - start
            if r.status_code == 200:
                return (region, elapsed)
        except Exception:
            pass
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as executor:
        results = executor.map(test_region, regions)
        working = [r for r in results if r is not None]
        if working:
            # Return fastest working region
            return sorted(working, key=lambda x: x[1])[0][0]

    return None

def _get_vpn_proxy():
    """
    Auto-detecting VPN proxy:
    1. Check cache for previously working region
    2. If no cache, test all regions and pick fastest
    3. Return None if VPN not needed or unavailable
    """
    global _vpn_cache

    # Manual override: POLY_DISABLE_VPN=true forces direct access
    if _get_credential("POLY_DISABLE_VPN") == "true":
        return None

    # Manual override: POLY_VPN_REGION=xx forces specific region
    manual_region = _get_credential("POLY_VPN_REGION")
    if manual_region:
        return {
            "https": f"http://{manual_region}:x@sc-vpn.internal:8080",
            "http": f"http://{manual_region}:x@sc-vpn.internal:8080",
        }

    # First time: load from disk cache
    if not _vpn_cache["tested"]:
        cached = _load_vpn_cache()
        _vpn_cache["enabled"] = cached.get("enabled", False)
        _vpn_cache["region"] = cached.get("region")
        _vpn_cache["tested"] = True

    # If cache says VPN needed and has a region, use it
    if _vpn_cache["enabled"] and _vpn_cache["region"]:
        return {
            "https": f"http://{_vpn_cache['region']}:x@sc-vpn.internal:8080",
            "http": f"http://{_vpn_cache['region']}:x@sc-vpn.internal:8080",
        }

    return None

def _enable_vpn_auto():
    """
    Enable VPN automatically by testing regions.
    Called when 403 geo-block is detected.
    """
    global _vpn_cache

    region = _test_vpn_regions()
    if region:
        _vpn_cache["enabled"] = True
        _vpn_cache["region"] = region
        _save_vpn_cache(True, region)
        return {
            "https": f"http://{region}:x@sc-vpn.internal:8080",
            "http": f"http://{region}:x@sc-vpn.internal:8080",
        }

    return None


def clob_get(url, **kw):
    """
    GET request to CLOB API with auto VPN fallback.
    Tries direct first, auto-enables VPN on 403 geo-block.
    """
    kw.setdefault("timeout", 30)
    proxy = _get_vpn_proxy()
    if proxy:
        kw.setdefault("proxies", proxy)

    r = _requests.get(url, **kw)

    # Auto-enable VPN on geo-block and retry
    if r.status_code == 403 and not proxy:
        proxy = _enable_vpn_auto()
        if proxy:
            kw["proxies"] = proxy
            r = _requests.get(url, **kw)

    return r


def clob_post(url, **kw):
    """
    POST request to CLOB API with auto VPN fallback.
    Tries direct first, auto-enables VPN on 403 geo-block.
    """
    kw.setdefault("timeout", 30)
    proxy = _get_vpn_proxy()
    if proxy:
        kw.setdefault("proxies", proxy)

    r = _requests.post(url, **kw)

    # Auto-enable VPN on geo-block and retry
    if r.status_code == 403 and not proxy:
        proxy = _enable_vpn_auto()
        if proxy:
            kw["proxies"] = proxy
            r = _requests.post(url, **kw)

    return r


def clob_delete(url, **kw):
    """
    DELETE request to CLOB API with auto VPN fallback.
    Tries direct first, auto-enables VPN on 403 geo-block.
    """
    kw.setdefault("timeout", 30)
    proxy = _get_vpn_proxy()
    if proxy:
        kw.setdefault("proxies", proxy)

    r = _requests.delete(url, **kw)

    # Auto-enable VPN on geo-block and retry
    if r.status_code == 403 and not proxy:
        proxy = _enable_vpn_auto()
        if proxy:
            kw["proxies"] = proxy
            r = _requests.delete(url, **kw)

    return r


def gamma_get(url, **kw):
    """GET request to Gamma API (no VPN - not geo-blocked)"""
    kw.setdefault("timeout", 30)
    return _requests.get(url, **kw)


# HMAC L2 Authentication
def _hmac_sig(secret, timestamp, method, path, body=None):
    """Generate HMAC signature for L2 authentication"""
    secret_bytes = base64.urlsafe_b64decode(secret)
    message = str(timestamp) + method.upper() + path
    if body:
        message += body
    sig = hmac.new(secret_bytes, message.encode(), hashlib.sha256)
    return base64.urlsafe_b64encode(sig.digest()).decode()


def l2_headers(method, path, body=None):
    """Build L2 authenticated headers"""
    api_key = API_KEY()
    secret = SECRET()
    passphrase = PASSPHRASE()
    wallet = WALLET()

    if not all([api_key, secret, passphrase, wallet]):
        raise ValueError(
            "Missing credentials. Set POLY_API_KEY, POLY_SECRET, POLY_PASSPHRASE, POLY_WALLET in .env"
        )

    ts = int(time.time())
    sig = _hmac_sig(secret, ts, method.upper(), path, body)
    return {
        "POLY_ADDRESS": wallet,
        "POLY_SIGNATURE": sig,
        "POLY_TIMESTAMP": str(ts),
        "POLY_API_KEY": api_key,
        "POLY_PASSPHRASE": passphrase,
        "Content-Type": "application/json",
    }


# URL Parsing
def parse_polymarket_url(url_or_slug):
    """
    Parse Polymarket URL or slug
    Returns: (event_slug, market_slug or None)
    """
    url_or_slug = url_or_slug.strip()
    m = re.match(
        r"https?://(?:www\.)?polymarket\.com/event/([^/?#]+)(?:/([^/?#]+))?",
        url_or_slug,
    )
    if m:
        return m.group(1), m.group(2)
    parts = url_or_slug.strip("/").split("/")
    return (parts[0], parts[1] if len(parts) > 1 else None)


# Market Enrichment
def enrich_market(market):
    """Enrich market data with live prices"""
    outcomes = (
        json.loads(market.get("outcomes", "[]"))
        if isinstance(market.get("outcomes"), str)
        else market.get("outcomes", [])
    )
    prices = (
        json.loads(market.get("outcomePrices", "[]"))
        if isinstance(market.get("outcomePrices"), str)
        else market.get("outcomePrices", [])
    )
    token_ids = (
        json.loads(market.get("clobTokenIds", "[]"))
        if isinstance(market.get("clobTokenIds"), str)
        else market.get("clobTokenIds", [])
    )

    enriched = {
        "question": market.get("question"),
        "slug": market.get("slug"),
        "condition_id": market.get("conditionId"),
        "description": (market.get("description") or "")[:300],
        "end_date": market.get("endDate"),
        "volume": float(market.get("volume", 0) or 0),
        "active": market.get("active"),
        "closed": market.get("closed"),
        "accepting_orders": market.get("acceptingOrders"),
        "tick_size": market.get("orderPriceMinTickSize", 0.01),
        "min_order_size": market.get("orderMinSize", 5),
        "outcomes": [],
    }

    for i, outcome in enumerate(outcomes):
        entry = {
            "outcome": outcome,
            "gamma_price": float(prices[i]) if i < len(prices) else None,
            "token_id": token_ids[i] if i < len(token_ids) else None,
        }
        if entry["token_id"]:
            try:
                entry["buy_price"] = get_price(entry["token_id"], "BUY")
                entry["sell_price"] = get_price(entry["token_id"], "SELL")
                entry["midpoint"] = get_midpoint(entry["token_id"])
            except Exception:
                pass
        enriched["outcomes"].append(entry)

    return enriched


# Price APIs
def get_price(token_id, side="BUY"):
    """Get current price for a token"""
    r = clob_get(f"{BASE}/price", params={"token_id": token_id, "side": side})
    return float(r.json().get("price", 0)) if r.status_code == 200 else None


def get_midpoint(token_id):
    """Get midpoint price for a token"""
    r = clob_get(f"{BASE}/midpoint", params={"token_id": token_id})
    return float(r.json().get("mid", 0)) if r.status_code == 200 else None


def get_orderbook(token_id):
    """Get orderbook for a token"""
    r = clob_get(f"{BASE}/book", params={"token_id": token_id})
    r.raise_for_status()
    return r.json()
