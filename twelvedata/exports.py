"""
TwelveData skill exports — script-mode skill.

Usage from a bash block:
    python3 - <<'EOF'
    import sys
    sys.path.insert(0, "/data/workspace/skills/twelvedata")
    from exports import twelvedata_price, twelvedata_time_series
    print(twelvedata_price(symbol="AAPL"))
    EOF

Imports from sidecar.proxy_client (NOT core.http_client) so this skill
stays runnable without the agent platform's core/* modules on PYTHONPATH.
"""
import os

# Make sidecar/ importable when the script is invoked directly via
# `python3 -c` from the agent's bash tool. /app is already on PYTHONPATH
# inside the container (set by entrypoint.sh), so `from sidecar...` works
# in production. The fallback covers local-dev runs from outside /app.
try:
    from sidecar.proxy_client import proxied_get
except ImportError:
    # Local dev / running outside the deployed image: fall back to
    # core.http_client which is identical. Skill still works either way.
    from core.http_client import proxied_get

API_KEY = os.environ.get("TWELVEDATA_API_KEY", "")
BASE = "https://api.twelvedata.com"


def _get(endpoint, params=None):
    """Make a GET request to TwelveData API."""
    if params is None:
        params = {}
    params["apikey"] = API_KEY
    r = proxied_get(f"{BASE}/{endpoint}", params=params)
    r.raise_for_status()
    return r.json()


def twelvedata_time_series(symbol, interval="1day", outputsize=30, start_date=None, end_date=None, prepost=False):
    """Get OHLCV time series data."""
    params = {"symbol": symbol, "interval": interval, "outputsize": outputsize}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if prepost:
        params["prepost"] = "true"
    return _get("time_series", params)


def twelvedata_price(symbol, prepost=False):
    """Get current price for a symbol."""
    params = {"symbol": symbol}
    if prepost:
        params["prepost"] = "true"
    return _get("price", params)


def twelvedata_eod(symbol, date=None, prepost=False):
    """Get end-of-day price."""
    params = {"symbol": symbol}
    if date:
        params["date"] = date
    if prepost:
        params["prepost"] = "true"
    return _get("eod", params)


def twelvedata_quote(symbol, prepost=False):
    """Get detailed quote (price, volume, 52w high/low, change %)."""
    params = {"symbol": symbol}
    if prepost:
        params["prepost"] = "true"
    return _get("quote", params)


def twelvedata_quote_batch(symbols, prepost=False):
    """Get quotes for multiple symbols. symbols: comma-separated string."""
    params = {"symbol": symbols}
    if prepost:
        params["prepost"] = "true"
    return _get("quote", params)


def twelvedata_price_batch(symbols, prepost=False):
    """Get prices for multiple symbols. symbols: comma-separated string."""
    params = {"symbol": symbols}
    if prepost:
        params["prepost"] = "true"
    return _get("price", params)


def twelvedata_search(query):
    """Search for symbols by name or ticker."""
    return _get("symbol_search", {"symbol": query})


def twelvedata_stocks(exchange=None, country=None):
    """Get list of available stocks, optionally filtered."""
    params = {}
    if exchange:
        params["exchange"] = exchange
    if country:
        params["country"] = country
    return _get("stocks", params)


def twelvedata_forex_pairs():
    """Get all available forex pairs."""
    return _get("forex_pairs")


def twelvedata_exchanges():
    """Get list of supported exchanges."""
    return _get("exchanges")
