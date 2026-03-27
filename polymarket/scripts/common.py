"""
Polymarket Common — shared by all scripts.
VPN auto-detect, credential management, HMAC auth, HTTP helpers.
"""
import os, sys, time, json, hmac, hashlib, base64, random
import requests
import concurrent.futures

# ── Endpoints ──
BASE = "https://clob.polymarket.com"
GAMMA = "https://gamma-api.polymarket.com"
DATA_API = "https://data-api.polymarket.com"

# ── Contracts ──
CTF_EXCHANGE = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
CTF_EXCHANGE_NEG = "0xC5d563A36AE78145C45a50134d48A1215220f80a"
CHAIN_ID = 137
EOA = 0

ENV_FILE = "/data/workspace/.env"
VPN_CACHE = "/data/workspace/.polymarket_vpn_cache.json"

# ── Credential Loading ──

def load_env():
    """Read .env file into dict."""
    env = {}
    try:
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return env

def save_env_var(key, value):
    """Write/update a single key in .env file."""
    lines = []
    found = False
    try:
        with open(ENV_FILE) as f:
            lines = f.readlines()
    except FileNotFoundError:
        pass
    
    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}\n")
    
    with open(ENV_FILE, "w") as f:
        f.writelines(new_lines)
    os.environ[key] = value

def cred(key):
    """Get credential from env or .env file."""
    v = os.environ.get(key)
    if v:
        return v
    return load_env().get(key, "")

def ensure_credentials():
    """Check credentials exist. Returns (ok, message)."""
    keys = ["POLY_API_KEY", "POLY_SECRET", "POLY_PASSPHRASE", "POLY_WALLET"]
    missing = [k for k in keys if not cred(k)]
    if missing:
        return False, f"Missing: {', '.join(missing)}. Run: polymarket_auth() first."
    return True, "OK"

# ── VPN ──

VPN_REGIONS = ["ar", "br", "mx", "my", "th", "au", "za"]

def _load_vpn_cache():
    try:
        with open(VPN_CACHE) as f:
            return json.load(f)
    except Exception:
        return {}

def _save_vpn_cache(region):
    try:
        with open(VPN_CACHE, "w") as f:
            json.dump({"region": region, "ts": time.time()}, f)
    except Exception:
        pass

def _vpn_proxy(region):
    return {
        "https": f"http://{region}:x@sc-vpn.internal:8080",
        "http": f"http://{region}:x@sc-vpn.internal:8080",
    }

def detect_vpn():
    """Return best VPN proxy dict, or None."""
    # Manual override
    forced = os.environ.get("POLY_VPN_REGION", "").strip() or cred("POLY_VPN_REGION")
    if forced:
        return _vpn_proxy(forced)
    
    # Disk cache (valid for 1 hour)
    cache = _load_vpn_cache()
    if cache.get("region") and time.time() - cache.get("ts", 0) < 3600:
        return _vpn_proxy(cache["region"])
    
    # Parallel probe
    def test(r):
        try:
            t0 = time.time()
            resp = requests.get(f"{BASE}/time", proxies=_vpn_proxy(r), timeout=5)
            if resp.status_code == 200:
                return (r, time.time() - t0)
        except Exception:
            pass
        return None
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as ex:
        results = [x for x in ex.map(test, VPN_REGIONS) if x]
    
    if results:
        best = sorted(results, key=lambda x: x[1])[0][0]
        _save_vpn_cache(best)
        return _vpn_proxy(best)
    return None

# ── HTTP with auto VPN ──

def clob_request(method, path, headers=None, data=None, json_data=None, params=None):
    """HTTP request to CLOB with auto VPN on 403."""
    url = f"{BASE}{path}" if path.startswith("/") else path
    kw = {"timeout": 30}
    if headers: kw["headers"] = headers
    if data: kw["data"] = data
    if json_data: kw["json"] = json_data
    if params: kw["params"] = params

    # Try direct
    try:
        r = requests.request(method, url, **kw)
        if r.status_code != 403:
            return r
    except Exception:
        pass

    # VPN fallback
    proxy = detect_vpn()
    if proxy:
        kw["proxies"] = proxy
        return requests.request(method, url, **kw)
    
    # Last resort direct
    return requests.request(method, url, **kw)

def clob_get(path, **kw):
    return clob_request("GET", path, **kw)

def clob_post(path, **kw):
    return clob_request("POST", path, **kw)

def clob_delete(path, **kw):
    return clob_request("DELETE", path, **kw)

def gamma_get(path, params=None):
    url = f"{GAMMA}{path}" if path.startswith("/") else path
    return requests.get(url, params=params, timeout=30)

# ── HMAC Auth ──

def hmac_sig(timestamp, method, path, body=None):
    secret = cred("POLY_SECRET")
    key = base64.urlsafe_b64decode(secret)
    msg = str(timestamp) + method.upper() + path
    if body:
        msg += body
    sig = hmac.new(key, msg.encode(), hashlib.sha256)
    return base64.urlsafe_b64encode(sig.digest()).decode()

def l2_headers(method, path, body=None):
    ts = str(int(time.time()))
    return {
        "POLY_ADDRESS": cred("POLY_WALLET"),
        "POLY_SIGNATURE": hmac_sig(ts, method, path, body),
        "POLY_TIMESTAMP": ts,
        "POLY_API_KEY": cred("POLY_API_KEY"),
        "POLY_PASSPHRASE": cred("POLY_PASSPHRASE"),
        "Content-Type": "application/json",
    }

# ── Helpers ──

def fmt_usd(raw):
    """Convert raw USDC (6 decimals) string to float."""
    try:
        return int(raw) / 1_000_000
    except Exception:
        return 0.0

def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)
