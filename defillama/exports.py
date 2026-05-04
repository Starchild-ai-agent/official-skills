"""
DefiLlama skill exports — common DeFi analytics endpoints.

Usage from a bash block (script-mode skill):
    python3 - <<'EOF'
    import sys
    sys.path.insert(0, "/data/workspace/skills/defillama")
    from exports import protocols, yield_pools
    print(protocols()[:3])
    EOF

Imports from sidecar.proxy_client (NOT core.http_client) so this skill
stays runnable without the agent platform's core/* modules on PYTHONPATH.
"""
import os
import sys

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

FREE_BASE = "https://api.llama.fi"
BRIDGE_BASE = "https://bridges.llama.fi"
_TIMEOUT = 25


def _get(url, params=None):
    r = proxied_get(url, params=params, timeout=_TIMEOUT)
    r.raise_for_status()
    return r.json()


def _pro_base():
    key = os.environ.get("DEFILLAMA_API_KEY", "")
    return f"https://pro-api.llama.fi/{key}"


# --- TVL ---

def protocols():
    """Get all protocols with TVL data. Sort by 'tvl' for ranking."""
    return _get(f"{FREE_BASE}/protocols")


def protocol(slug):
    """Get single protocol detail (TVL history, chains, etc.)."""
    return _get(f"{FREE_BASE}/protocol/{slug}")


def chains():
    """Get all chains with TVL."""
    return _get(f"{FREE_BASE}/v2/chains")


def chain_tvl_history(chain):
    """Get historical TVL for a chain."""
    return _get(f"{FREE_BASE}/v2/historicalChainTvl/{chain}")


def global_tvl_history():
    """Get global DeFi TVL history."""
    return _get(f"{FREE_BASE}/v2/historicalChainTvl")


# --- DEX ---

def dex_overview(exclude_chart=True):
    """Get DEX volume overview (all chains)."""
    params = {"excludeTotalDataChart": str(exclude_chart).lower(),
              "excludeTotalDataChartBreakdown": str(exclude_chart).lower()}
    return _get(f"{FREE_BASE}/overview/dexs", params=params)


def dex_overview_chain(chain, exclude_chart=True):
    """Get DEX volume overview for a specific chain."""
    params = {"excludeTotalDataChart": str(exclude_chart).lower(),
              "excludeTotalDataChartBreakdown": str(exclude_chart).lower()}
    return _get(f"{FREE_BASE}/overview/dexs/{chain}", params=params)


# --- Fees / Revenue ---

def fees_overview(exclude_chart=True):
    """Get protocol fees overview."""
    params = {"excludeTotalDataChart": str(exclude_chart).lower(),
              "excludeTotalDataChartBreakdown": str(exclude_chart).lower()}
    return _get(f"{FREE_BASE}/overview/fees", params=params)


def fees_overview_chain(chain, exclude_chart=True):
    """Get protocol fees for a specific chain."""
    params = {"excludeTotalDataChart": str(exclude_chart).lower(),
              "excludeTotalDataChartBreakdown": str(exclude_chart).lower()}
    return _get(f"{FREE_BASE}/overview/fees/{chain}", params=params)


# --- Yields (Pro) ---

def yield_pools():
    """Get all yield pools (pro endpoint). Returns {data: [...pools]}."""
    return _get(f"{_pro_base()}/yields/pools")


def yield_chart(pool_id):
    """Get historical APY chart for a pool (pro endpoint)."""
    return _get(f"{_pro_base()}/yields/chart/{pool_id}")


# --- Stablecoins ---

def stablecoins(include_prices=True):
    """Get all stablecoins with mcap data."""
    params = {"includePrices": str(include_prices).lower()}
    return _get(f"{FREE_BASE}/stablecoins", params=params)


def stablecoin_chains():
    """Get stablecoin distribution across chains."""
    return _get(f"{FREE_BASE}/stablecoinchains")


# --- Bridges ---

def bridges():
    """Get all bridges."""
    return _get(f"{BRIDGE_BASE}/bridges")


def bridge_volume(bridge_id, start_timestamp=None, end_timestamp=None):
    """Get bridge volume history."""
    params = {}
    if start_timestamp:
        params["starttimestamp"] = start_timestamp
    if end_timestamp:
        params["endtimestamp"] = end_timestamp
    return _get(f"{BRIDGE_BASE}/bridge/{bridge_id}", params=params)


def bridge_chain_volume(chain):
    """Get bridge volume for a specific chain."""
    return _get(f"{BRIDGE_BASE}/bridgevolume/{chain}")


# --- Prices ---

def current_prices(coins):
    """Get current prices for coins. coins = comma-separated "chain:address" strings.
    Example: "ethereum:0x...,coingecko:bitcoin"
    """
    return _get(f"{FREE_BASE}/prices/current/{coins}")


def historical_prices(coins, timestamp):
    """Get historical prices at a timestamp."""
    return _get(f"{FREE_BASE}/prices/historical/{timestamp}/{coins}")
