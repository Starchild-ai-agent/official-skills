"""
Lighter API Client

Provides:
- LighterRestClient: async httpx client for read-only REST endpoints
- LighterSignerClient: wrapper around lighter-sdk SignerClient for signed transactions
- SecretValue: opaque wrapper preventing key leakage in logs/output
- Credential file support: ~/.lighter/lighter-agent-kit/credentials
- Symbol resolution: human symbols (BTC, ETH/USDC) to market_index
- Market metadata: auto-scaling human units to integer ticks/lots

Singleton pattern -- call get_rest_client() / get_signer_client() to obtain instances.
"""
import hashlib
import inspect
import json
import os
import logging
import subprocess
import sys
import tempfile
import time
import types
import warnings
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import httpx

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://mainnet.zklighter.elliot.ai"  # legacy alias; see NETWORKS
DEFAULT_API_KEY_INDEX = 2

# Lighter runs as separate deployments ("networks"). Each has its own API host,
# accounts, API keys, contracts and market list. Credentials are NOT portable
# between them. The user must pick one via LIGHTER_NETWORK (or give an explicit
# LIGHTER_API_URL).
NETWORKS: Dict[str, Dict[str, Any]] = {
    "ethereum": {
        "label": "Lighter on Ethereum (app.lighter.xyz)",
        "base_url": "https://mainnet.zklighter.elliot.ai",
        "ws_url": "wss://mainnet.zklighter.elliot.ai/stream",
        "l1_chain_id": 1,
        "signing_chain_id": 304,
        "app_url": "https://app.lighter.xyz",
        "api_keys_url": "https://app.lighter.xyz/apikeys",
        "docs_url": "https://apidocs.lighter.xyz/docs/get-started",
        "quote_assets": ["USDC"],
    },
    "robinhood": {
        "label": "Lighter on Robinhood Chain (robinhoodchain.lighter.xyz)",
        "base_url": "https://api.rh.lighter.xyz",
        "ws_url": "wss://api.rh.lighter.xyz/stream",
        "l1_chain_id": 4663,
        "signing_chain_id": 466324,
        "app_url": "https://robinhoodchain.lighter.xyz",
        "api_keys_url": "https://robinhoodchain.lighter.xyz/apikeys",
        "docs_url": "https://apidocs.rh.lighter.xyz/docs/get-started",
        "quote_assets": ["USDG"],
    },
    "ethereum-testnet": {
        "label": "Lighter Ethereum testnet",
        "base_url": "https://testnet.zklighter.elliot.ai",
        "ws_url": "wss://testnet.zklighter.elliot.ai/stream",
        "l1_chain_id": 11155111,
        "signing_chain_id": 300,
        "app_url": "https://testnet.app.lighter.xyz",
        "api_keys_url": "https://testnet.app.lighter.xyz/apikeys",
        "docs_url": "https://apidocs.lighter.xyz/docs/get-started",
        "quote_assets": ["USDC"],
    },
    "robinhood-testnet": {
        "label": "Lighter Robinhood Chain testnet",
        "base_url": "https://api.rh-testnet.lighter.xyz",
        "ws_url": "wss://api.rh-testnet.lighter.xyz/stream",
        "l1_chain_id": None,
        "signing_chain_id": 300,
        "app_url": None,
        "api_keys_url": None,
        "docs_url": "https://apidocs.rh.lighter.xyz/docs/get-started",
        "quote_assets": ["USDG"],
    },
}

_NETWORK_ALIASES = {
    "eth": "ethereum", "ethereum": "ethereum", "mainnet": "ethereum", "lighter": "ethereum",
    "rh": "robinhood", "robinhood": "robinhood", "robinhoodchain": "robinhood",
    "robinhood-chain": "robinhood", "robinhood_chain": "robinhood",
    "testnet": "ethereum-testnet", "ethereum-testnet": "ethereum-testnet",
    "rh-testnet": "robinhood-testnet", "robinhood-testnet": "robinhood-testnet",
}


class LighterNetworkNotSelected(RuntimeError):
    """Raised when neither LIGHTER_NETWORK nor LIGHTER_API_URL is configured."""

# Singletons
_rest_client: Optional["LighterRestClient"] = None
_signer_client: Optional[Any] = None  # lighter.SignerClient
_credentials: Optional[Dict[str, Any]] = None
_lighter_sdk_ready = False

# Keys whose values must never appear in logs, tracebacks, or agent output
_SECRET_NAMES = frozenset({"LIGHTER_PRIVATE_KEY", "LIGHTER_API_PRIVATE_KEY", "LIGHTER_ETH_PRIVATE_KEY"})

# Path to the lighter-agent-kit-main skill (sibling directory)
_SKILL_DIR = Path(__file__).resolve().parent
_AGENT_KIT_DIR = _SKILL_DIR.parent / "lighter-agent-kit-main"
_PY_TAG = f"py{sys.version_info.major}.{sys.version_info.minor}"
_VENDOR_DIR = str(_AGENT_KIT_DIR / ".vendor" / _PY_TAG)
_LOCKFILE = str(_AGENT_KIT_DIR / "requirements.lock")


# ═══════════════════════════════════════════════════════════════════
# lighter-sdk bootstrap (uses lighter-agent-kit-main's vendoring)
# ═══════════════════════════════════════════════════════════════════

def _stub_eth_account():
    """Inject a stub for eth_account to avoid 26MB of transitive deps.
    lighter-sdk's signer_client.py has a top-level import of eth_account."""
    if "eth_account" in sys.modules:
        return
    mod = types.ModuleType("eth_account")
    mod.Account = None
    msgs = types.ModuleType("eth_account.messages")
    msgs.encode_defunct = None
    mod.messages = msgs
    sys.modules.setdefault("eth_account", mod)
    sys.modules.setdefault("eth_account.messages", msgs)


def _prepend_vendor():
    """Add the agent-kit vendor dir to sys.path if it exists."""
    if os.path.isdir(_VENDOR_DIR) and _VENDOR_DIR not in sys.path:
        sys.path.insert(0, _VENDOR_DIR)


def _install_deps():
    """pip-install deps from lighter-agent-kit-main/requirements.lock into its .vendor/."""
    if not os.path.isfile(_LOCKFILE):
        logger.warning(f"requirements.lock not found at {_LOCKFILE}")
        return False
    os.makedirs(_VENDOR_DIR, exist_ok=True)
    try:
        subprocess.run(
            [
                sys.executable, "-m", "pip", "install",
                "--target", _VENDOR_DIR,
                "--quiet",
                "--disable-pip-version-check",
                "--only-binary=:all:",
                "--no-binary=lighter-sdk",
                "--no-deps",
                "-r", _LOCKFILE,
            ],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        detail = (e.stderr or b"").decode(errors="replace").strip()[-400:]
        logger.warning(f"lighter-sdk install failed: {detail}")
        return False
    except Exception as e:
        logger.warning(f"lighter-sdk install failed: {e}")
        return False


def ensure_lighter_sdk():
    """Make `import lighter` work. Uses lighter-agent-kit-main's vendor dir.

    1. Stubs eth_account (saves 26MB)
    2. Checks vendor dir
    3. If not vendored, pip-installs from requirements.lock
    """
    global _lighter_sdk_ready
    if _lighter_sdk_ready:
        return True

    # Suppress third-party noise during import
    warnings.filterwarnings("ignore")
    warnings.simplefilter("ignore", ResourceWarning)
    logging.getLogger("aiohttp").setLevel(logging.CRITICAL)
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)
    logging.getLogger("urllib3").setLevel(logging.CRITICAL)

    _stub_eth_account()
    _prepend_vendor()

    try:
        import lighter  # noqa: F401
        _lighter_sdk_ready = True
        return True
    except ImportError:
        pass

    # Try installing
    if _install_deps():
        _prepend_vendor()
        try:
            import lighter  # noqa: F401
            _lighter_sdk_ready = True
            return True
        except ImportError:
            pass

    logger.warning("lighter-sdk not available. Trading and paper trading tools will be unavailable.")
    return False


# ═══════════════════════════════════════════════════════════════════
# SecretValue
# ═══════════════════════════════════════════════════════════════════

class SecretValue:
    """Opaque wrapper that keeps secret strings out of Debug/Display output."""

    __slots__ = ("_val",)

    def __init__(self, val: str):
        self._val = val

    def expose(self) -> str:
        """Return the plaintext secret. Callers must not log the result."""
        return self._val

    def __repr__(self):
        return "SecretValue([REDACTED])"

    def __str__(self):
        return "[REDACTED]"

    def __bool__(self):
        return bool(self._val)


# ═══════════════════════════════════════════════════════════════════
# Credential file support
# ═══════════════════════════════════════════════════════════════════

def _credentials_dir() -> Path:
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / "lighter-agent-kit"
    return Path.home() / ".lighter" / "lighter-agent-kit"


def _credentials_path() -> Path:
    return _credentials_dir() / "credentials"


def _strip_optional_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _load_credentials() -> Dict[str, Any]:
    global _credentials
    if _credentials is not None:
        return _credentials

    path = _credentials_path()
    if not path.is_file():
        _credentials = {}
        return _credentials

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        _credentials = {}
        return _credentials

    creds = {}
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        value = _strip_optional_quotes(value.strip())
        if key and value:
            creds[key] = SecretValue(value) if key in _SECRET_NAMES else value
    _credentials = creds
    return _credentials


def get_config_value(name: str, default=None):
    """Resolve a setting from env first, then the per-user credentials file.

    Returns a SecretValue for keys in _SECRET_NAMES, forcing callers
    to explicitly call .expose() before passing the plaintext anywhere.
    """
    value = os.environ.get(name)
    if value:
        return SecretValue(value) if name in _SECRET_NAMES else value

    # Also check the alternate env var name (LIGHTER_PRIVATE_KEY vs LIGHTER_API_PRIVATE_KEY)
    alt_names = {
        "LIGHTER_PRIVATE_KEY": "LIGHTER_API_PRIVATE_KEY",
        "LIGHTER_API_PRIVATE_KEY": "LIGHTER_PRIVATE_KEY",
    }
    if name in alt_names:
        value = os.environ.get(alt_names[name])
        if value:
            return SecretValue(value) if name in _SECRET_NAMES or alt_names[name] in _SECRET_NAMES else value

    # Values from the credentials file are already wrapped by _load_credentials()
    creds = _load_credentials()
    value = creds.get(name)
    if value:
        return value
    if name in alt_names:
        value = creds.get(alt_names[name])
        if value:
            return value

    return default


def get_account_index() -> Optional[int]:
    """Get LIGHTER_ACCOUNT_INDEX from env or credentials file."""
    val = get_config_value("LIGHTER_ACCOUNT_INDEX")
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def get_api_key_index() -> int:
    """Get LIGHTER_API_KEY_INDEX from env or credentials file."""
    val = get_config_value("LIGHTER_API_KEY_INDEX")
    if val is not None:
        try:
            return int(val)
        except (TypeError, ValueError):
            pass
    return DEFAULT_API_KEY_INDEX


def normalize_network(name: Optional[str]) -> Optional[str]:
    """Map a user-supplied network name/alias to a NETWORKS key, or None."""
    if not name:
        return None
    return _NETWORK_ALIASES.get(str(name).strip().lower())


def network_for_url(url: str) -> Optional[str]:
    """Best-effort reverse lookup: which known network serves this base URL?"""
    u = (url or "").strip().lower().rstrip("/")
    for key, cfg in NETWORKS.items():
        if cfg["base_url"].lower() == u:
            return key
    if "rh-testnet.lighter" in u:
        return "robinhood-testnet"
    if "rh.lighter" in u:
        return "robinhood"
    if "testnet.zklighter" in u:
        return "ethereum-testnet"
    if "zklighter.elliot" in u:
        return "ethereum"
    return None


def get_network() -> Optional[str]:
    """Selected network key from LIGHTER_NETWORK (env or credentials file).

    Falls back to inferring from an explicit LIGHTER_API_URL / LIGHTER_HOST.
    Returns None if the user has not picked one.
    """
    raw = get_config_value("LIGHTER_NETWORK")
    if raw:
        key = normalize_network(raw)
        if key is None:
            raise LighterNetworkNotSelected(
                f"Unknown LIGHTER_NETWORK={raw!r}. Valid values: {', '.join(NETWORKS)}"
            )
        return key
    explicit = get_config_value("LIGHTER_API_URL") or get_config_value("LIGHTER_HOST")
    if explicit:
        return network_for_url(explicit)
    return None


def _network_not_selected_error() -> LighterNetworkNotSelected:
    return LighterNetworkNotSelected(
        "No Lighter network selected. Lighter runs as separate deployments with "
        "separate accounts and API keys. Ask the user which one they use and set "
        "LIGHTER_NETWORK=ethereum (app.lighter.xyz) or LIGHTER_NETWORK=robinhood "
        "(robinhoodchain.lighter.xyz) in the environment or credentials file. "
        "Run lighter_get_network to see the options."
    )


def get_base_url() -> str:
    """Resolve the REST base URL.

    Precedence: explicit LIGHTER_API_URL / LIGHTER_HOST > LIGHTER_NETWORK.
    Raises LighterNetworkNotSelected if neither is set — the user must pick.
    """
    val = get_config_value("LIGHTER_API_URL") or get_config_value("LIGHTER_HOST")
    if val:
        return val
    key = get_network()
    if key is None:
        raise _network_not_selected_error()
    return NETWORKS[key]["base_url"]


def get_signing_chain_id() -> Optional[int]:
    """Chain ID used for L2 transaction signing on the selected network."""
    key = get_network()
    if key is None:
        key = network_for_url(get_base_url())
    return NETWORKS[key]["signing_chain_id"] if key else None


def get_network_info() -> Dict[str, Any]:
    """Describe the current selection (safe to show to the user)."""
    try:
        key = get_network()
    except LighterNetworkNotSelected as e:
        key, err = None, str(e)
    else:
        err = None
    explicit = get_config_value("LIGHTER_API_URL") or get_config_value("LIGHTER_HOST")
    info: Dict[str, Any] = {
        "selected": key is not None or bool(explicit),
        "network": key,
        "base_url": explicit or (NETWORKS[key]["base_url"] if key else None),
        "source": "LIGHTER_API_URL" if explicit else ("LIGHTER_NETWORK" if key else None),
        "available": {k: {"label": v["label"], "base_url": v["base_url"], "app_url": v["app_url"]}
                      for k, v in NETWORKS.items()},
    }
    if key:
        info["details"] = NETWORKS[key]
    if err:
        info["error"] = err
    return info


def reset_clients() -> None:
    """Drop cached REST/signer clients (e.g. after the network changes)."""
    global _rest_client, _signer_client
    _rest_client = None
    _signer_client = None


# ═══════════════════════════════════════════════════════════════════
# Symbol Resolution
# ═══════════════════════════════════════════════════════════════════

_SYMBOL_CACHE_TTL = 300  # 5 minutes
_symbol_cache: Dict[str, dict] = {}  # host -> {"expires_at", "symbols"}


def _symbol_cache_path(host: str) -> Path:
    normalized = host.strip().lower().rstrip("/")
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return _credentials_dir() / f"symbol-cache-{digest}.json"


async def _fetch_symbols_from_api(rest_client: "LighterRestClient") -> Dict[str, Dict[str, int]]:
    """Fetch symbol map from /api/v1/orderBooks."""
    data = await rest_client.get_order_books(market_id=255, filter_type="all")
    symbols: Dict[str, Dict[str, int]] = {"perp": {}, "spot": {}}
    for ob in data.get("order_books", []):
        mt = ob.get("market_type", "")
        if mt in symbols:
            symbols[mt][ob.get("symbol", "")] = ob.get("market_id", 0)
    return symbols


async def get_symbol_map(rest_client: "LighterRestClient") -> Dict[str, Dict[str, int]]:
    """Get symbol map with 5-minute cache (memory + disk)."""
    host = rest_client.base_url
    now = int(time.time())

    # Check memory cache
    cached = _symbol_cache.get(host)
    if cached and now < cached.get("expires_at", 0):
        return cached["symbols"]

    # Check disk cache
    cache_path = _symbol_cache_path(host)
    if cache_path.is_file():
        try:
            disk = json.loads(cache_path.read_text(encoding="utf-8"))
            if disk.get("host") == host and now < disk.get("expires_at", 0):
                _symbol_cache[host] = disk
                return disk["symbols"]
        except (json.JSONDecodeError, OSError):
            pass

    # Fetch fresh
    symbols = await _fetch_symbols_from_api(rest_client)
    entry = {"host": host, "expires_at": now + _SYMBOL_CACHE_TTL, "symbols": symbols}
    _symbol_cache[host] = entry

    # Write to disk
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=cache_path.parent, prefix=f"{cache_path.name}.", suffix=".tmp", text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(entry, separators=(",", ":")))
        os.replace(tmp, cache_path)
    except OSError:
        pass

    return symbols


async def resolve_symbol(
    symbol_or_index: str,
    rest_client: "LighterRestClient",
) -> Tuple[int, str, str]:
    """Resolve a symbol or market_index to (market_index, market_type, symbol).

    Symbol convention:
    - Bare ticker (no /)  -> perp     (e.g. BTC)
    - Contains /          -> spot     (e.g. ETH/USDC)
    - Numeric string      -> market_index escape hatch
    """
    # Try as numeric market_index
    try:
        market_index = int(symbol_or_index)
        symbols = await get_symbol_map(rest_client)
        for mt in ("perp", "spot"):
            for sym, mid in symbols.get(mt, {}).items():
                if mid == market_index:
                    return (market_index, mt, sym)
        return (market_index, "perp", str(market_index))
    except ValueError:
        pass

    symbol = symbol_or_index.upper()
    market_type = "spot" if "/" in symbol else "perp"
    symbols = await get_symbol_map(rest_client)

    if symbol in symbols.get(market_type, {}):
        return (symbols[market_type][symbol], market_type, symbol)

    # Force refresh and retry
    _symbol_cache.pop(rest_client.base_url, None)
    symbols = await get_symbol_map(rest_client)
    if symbol in symbols.get(market_type, {}):
        return (symbols[market_type][symbol], market_type, symbol)

    raise ValueError(
        f"Unknown symbol '{symbol}'. Use lighter_get_markets to discover available markets."
    )


def normalize_side(side: str, market_type: str) -> str:
    """Normalize side to canonical form. perp: long/short, spot: buy/sell."""
    side = side.lower()
    if side not in ("buy", "sell", "long", "short"):
        raise ValueError(f"Invalid side '{side}'; use buy|sell|long|short")
    if market_type == "perp":
        return "long" if side in ("buy", "long") else "short"
    return "buy" if side in ("buy", "long") else "sell"


def side_to_is_ask(side: str) -> bool:
    """Convert normalized side to is_ask boolean for SDK."""
    return side in ("sell", "short")


# ═══════════════════════════════════════════════════════════════════
# Market Metadata (for auto-scaling)
# ═══════════════════════════════════════════════════════════════════

async def get_market_decimals(
    rest_client: "LighterRestClient", market_id: int,
) -> Tuple[int, int]:
    """Return (size_decimals, price_decimals) for a market."""
    data = await rest_client.get_order_books(market_id=255, filter_type="all")
    for ob in data.get("order_books", []):
        if ob.get("market_id") == market_id:
            return ob.get("supported_size_decimals", 0), ob.get("supported_price_decimals", 0)
    raise ValueError(f"Market {market_id} not found")


def scale_to_raw(value: float, decimals: int) -> int:
    """Scale a human-unit value to integer raw units."""
    return int(round(value * (10 ** decimals)))


def format_scaled(scaled_int: int, decimals: int) -> str:
    """Format an integer-scaled value back to human decimal form."""
    return f"{scaled_int / (10 ** decimals):.{decimals}f}"


# ═══════════════════════════════════════════════════════════════════
# REST Client
# ═══════════════════════════════════════════════════════════════════

class LighterRestClient:
    """Async HTTP client for Lighter read-only REST API."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or get_base_url()).rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={"Accept": "application/json"},
        )

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        resp = await self._client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    async def post_form(self, path: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        resp = await self._client.post(path, data=data)
        resp.raise_for_status()
        return resp.json()

    # -- Market Data --

    async def get_order_books(self, market_id: int = 255, filter_type: str = "all") -> Dict:
        return await self.get("/api/v1/orderBooks", {"market_id": market_id, "filter": filter_type})

    async def get_order_book_details(self, market_id: int = 255, filter_type: str = "all") -> Dict:
        return await self.get("/api/v1/orderBookDetails", {"market_id": market_id, "filter": filter_type})

    async def get_order_book_orders(self, market_id: int, limit: int = 50) -> Dict:
        return await self.get("/api/v1/orderBookOrders", {"market_id": market_id, "limit": min(limit, 250)})

    async def get_recent_trades(self, market_id: int, limit: int = 50) -> Dict:
        return await self.get("/api/v1/recentTrades", {"market_id": market_id, "limit": min(limit, 100)})

    async def get_candles(
        self, market_id: int, resolution: str, count_back: int = 100,
        start_timestamp: Optional[int] = None, end_timestamp: Optional[int] = None,
    ) -> Dict:
        params: Dict[str, Any] = {
            "market_id": market_id,
            "resolution": resolution,
            "count_back": min(count_back, 500),
        }
        now_ms = int(time.time() * 1000)
        params["end_timestamp"] = end_timestamp or now_ms
        params["start_timestamp"] = start_timestamp or 0
        return await self.get("/api/v1/candles", params)

    async def get_exchange_stats(self) -> Dict:
        return await self.get("/api/v1/exchangeStats")

    async def get_funding_rates(self) -> Dict:
        return await self.get("/api/v1/funding-rates")

    async def get_fundings(
        self, market_id: int, resolution: str = "1h", count_back: int = 100,
        start_timestamp: Optional[int] = None, end_timestamp: Optional[int] = None,
    ) -> Dict:
        now_ms = int(time.time() * 1000)
        return await self.get("/api/v1/fundings", {
            "market_id": market_id,
            "resolution": resolution,
            "count_back": min(count_back, 500),
            "end_timestamp": end_timestamp or now_ms,
            "start_timestamp": start_timestamp or 0,
        })

    async def get_asset_details(self, asset_id: int = 0) -> Dict:
        return await self.get("/api/v1/assetDetails", {"asset_id": asset_id})

    # -- Account --

    async def get_account(self, by: str = "index", value: str = "") -> Dict:
        return await self.get("/api/v1/account", {"by": by, "value": value})

    async def get_account_active_orders(
        self, account_index: int, market_id: Optional[int] = None, auth: Optional[str] = None,
    ) -> Dict:
        params: Dict[str, Any] = {"account_index": account_index}
        if market_id is not None:
            params["market_id"] = market_id
        if auth:
            params["auth"] = auth
        return await self.get("/api/v1/accountActiveOrders", params)

    # -- Auth --
    _RESOLUTION_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000,
                      "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}

    async def _auth_token(self) -> Optional[str]:
        """Best-effort signed auth token for endpoints that require it.

        Uses the SignerClient's create_auth_token_with_expiry (10 min expiry).
        Returns None when no signer credentials are configured — callers
        then fall through to the unauthenticated request and surface the
        server's own error.
        """
        try:
            from .client import get_signer_client
            signer = get_signer_client()
            if signer is None:
                return None
            # SDK method is sync and returns (auth, error).
            # Pin the configured api_key_index — SDK default (255) won't validate.
            from .client import get_api_key_index
            auth, err = signer.create_auth_token_with_expiry(
                600, api_key_index=get_api_key_index())
            if inspect.isawaitable(auth):
                auth = await auth
            if err:
                logger.warning(f"auth token signing failed: {err}")
                return None
            return auth
        except Exception as e:
            logger.warning(f"auth token unavailable: {type(e).__name__}")
            return None

    async def get_account_inactive_orders(
        self, account_index: int, limit: int = 50,
        market_id: Optional[int] = None, cursor: Optional[str] = None,
        auth: Optional[str] = None,
    ) -> Dict:
        params: Dict[str, Any] = {"account_index": account_index, "limit": min(limit, 100)}
        if market_id is not None:
            params["market_id"] = market_id
        if cursor:
            params["cursor"] = cursor
        # Endpoint requires auth — fetch a signed token if caller didn't pass one
        if not auth:
            auth = await self._auth_token()
        if auth:
            params["auth"] = auth
        return await self.get("/api/v1/accountInactiveOrders", params)

    async def get_trades(
        self, sort_by: str = "timestamp", limit: int = 50,
        account_index: Optional[int] = None, market_id: Optional[int] = None,
        role: str = "all", trade_type: str = "all",
        cursor: Optional[str] = None, auth: Optional[str] = None,
    ) -> Dict:
        params: Dict[str, Any] = {"sort_by": sort_by, "limit": min(limit, 100)}
        if account_index is not None:
            params["account_index"] = account_index
        if market_id is not None:
            params["market_id"] = market_id
        if role != "all":
            params["role"] = role
        if trade_type != "all":
            params["type"] = trade_type
        if cursor:
            params["cursor"] = cursor
        # Endpoint requires auth — fetch a signed token if caller didn't pass one
        if not auth:
            auth = await self._auth_token()
        if auth:
            params["auth"] = auth
        return await self.get("/api/v1/trades", params)

    async def get_pnl(
        self, account_index: int, resolution: str = "1d", count_back: int = 30,
        start_timestamp: Optional[int] = None, end_timestamp: Optional[int] = None,
        ignore_transfers: bool = False, auth: Optional[str] = None,
    ) -> Dict:
        now_ms = int(time.time() * 1000)
        # RH endpoint rejects start_timestamp=0 ("invalid param") even with auth:
        # it requires an explicit real window. Default to the last count_back
        # periods ending at now.
        res_ms = self._RESOLUTION_MS.get(resolution)
        if end_timestamp is None:
            end_timestamp = now_ms
        if start_timestamp is None:
            if res_ms is not None:
                start_timestamp = end_timestamp - count_back * res_ms
            else:
                start_timestamp = end_timestamp - 30 * 86_400_000
        params: Dict[str, Any] = {
            "by": "index",
            "value": str(account_index),
            "resolution": resolution,
            "count_back": count_back,
            "end_timestamp": end_timestamp,
            "start_timestamp": start_timestamp,
        }
        if ignore_transfers:
            params["ignore_transfers"] = True
        # Endpoint requires auth
        if not auth:
            auth = await self._auth_token()
        if auth:
            params["auth"] = auth
        return await self.get("/api/v1/pnl", params)

    async def get_account_limits(self, account_index: int, auth: Optional[str] = None) -> Dict:
        params: Dict[str, Any] = {"account_index": account_index}
        if auth:
            params["auth"] = auth
        return await self.get("/api/v1/accountLimits", params)

    async def get_next_nonce(self, account_index: int, api_key_index: int) -> Dict:
        return await self.get("/api/v1/nextNonce", {
            "account_index": account_index,
            "api_key_index": api_key_index,
        })

    # -- Transactions --

    async def send_tx(self, tx_type: int, tx_info: str, price_protection: bool = True) -> Dict:
        return await self.post_form("/api/v1/sendTx", {
            "tx_type": tx_type,
            "tx_info": tx_info,
            "price_protection": price_protection,
        })

    async def close(self):
        await self._client.aclose()


# ═══════════════════════════════════════════════════════════════════
# Singletons
# ═══════════════════════════════════════════════════════════════════

def get_rest_client() -> LighterRestClient:
    """Get or create the singleton REST client."""
    global _rest_client
    if _rest_client is None:
        _rest_client = LighterRestClient()
    return _rest_client


def get_signer_client():
    """Get or create the singleton SignerClient from lighter-sdk.

    Reads credentials from env vars first, then ~/.lighter/lighter-agent-kit/credentials.
    Uses lighter-agent-kit-main's vendored SDK if available.
    Returns None if SDK is not available or credentials are missing.
    """
    global _signer_client
    if _signer_client is not None:
        return _signer_client

    if not ensure_lighter_sdk():
        return None

    import lighter

    private_key = get_config_value("LIGHTER_PRIVATE_KEY")
    account_index = get_account_index()

    if not private_key or account_index is None:
        logger.warning("LIGHTER_PRIVATE_KEY and LIGHTER_ACCOUNT_INDEX required for trading")
        return None

    api_key_index = get_api_key_index()
    base_url = get_base_url()

    # Expose the secret for the SDK
    key_str = private_key.expose() if isinstance(private_key, SecretValue) else private_key

    signer_kwargs: Dict[str, Any] = dict(
        url=base_url,
        api_private_keys={api_key_index: key_str},
        account_index=account_index,
    )
    # Pin the signing chain ID explicitly rather than relying on the SDK
    # sniffing it from the URL (304 = Ethereum, 466324 = Robinhood Chain).
    chain_id = get_signing_chain_id()
    if chain_id is not None:
        # Only pass it when the installed SDK actually supports the kwarg —
        # pip lighter-sdk 1.0.0's SignerClient does not accept chain_id.
        try:
            import inspect as _inspect
            _sig = _inspect.signature(lighter.SignerClient.__init__)
            if "chain_id" in _sig.parameters:
                signer_kwargs["chain_id"] = chain_id
            else:
                logger.info("SignerClient has no chain_id param; relying on URL sniffing")
        except (TypeError, ValueError):
            signer_kwargs["chain_id"] = chain_id

    _signer_client = lighter.SignerClient(**signer_kwargs)
    logger.info(
        f"Lighter SignerClient initialized (network={get_network()}, chain_id={chain_id}, "
        f"account={account_index}, key_index={api_key_index})"
    )
    return _signer_client
