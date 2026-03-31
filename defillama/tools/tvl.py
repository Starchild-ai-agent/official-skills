"""DefiLlama TVL APIs — protocols, chains, history."""
import logging
from typing import Any, Dict, List, Optional

try:
    from core.http_client import proxied_get
except ImportError:
    import requests
    def proxied_get(url, **kw):
        return requests.get(url, **kw)

logger = logging.getLogger(__name__)
BASE = "https://api.llama.fi"


def get_protocols_tvl(top_n: int = 20) -> Optional[List[Dict]]:
    """Get top N protocols by TVL."""
    try:
        resp = proxied_get(f"{BASE}/protocols", timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not isinstance(data, list):
            return None
        # Sort by TVL descending, take top N
        sorted_data = sorted(data, key=lambda x: x.get("tvl", 0) or 0, reverse=True)[:top_n]
        # Trim fields
        return [{
            "name": p.get("name"),
            "slug": p.get("slug"),
            "tvl": p.get("tvl"),
            "chain": p.get("chain"),
            "chains": p.get("chains", [])[:5],
            "category": p.get("category"),
            "change_1d": p.get("change_1d"),
            "change_7d": p.get("change_7d"),
            "mcap": p.get("mcap"),
        } for p in sorted_data]
    except Exception as e:
        logger.error(f"get_protocols_tvl error: {e}")
        return None


def get_protocol_detail(slug: str) -> Optional[Dict]:
    """Get detailed data for a specific protocol."""
    try:
        resp = proxied_get(f"{BASE}/protocol/{slug}", timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        # Trim: keep core fields, last 30 days of TVL history
        tvl_hist = data.get("tvl", [])
        result = {
            "name": data.get("name"),
            "slug": slug,
            "description": (data.get("description") or "")[:300],
            "tvl": data.get("tvl", [{}])[-1].get("totalLiquidityUSD") if tvl_hist else None,
            "chain": data.get("chain"),
            "chains": data.get("chains", []),
            "category": data.get("category"),
            "url": data.get("url"),
            "tvl_history_30d": [
                {"date": d.get("date"), "tvl": d.get("totalLiquidityUSD")}
                for d in tvl_hist[-30:]
            ],
        }
        # Add chain TVL breakdown if available
        chain_tvls = data.get("currentChainTvls", {})
        if chain_tvls:
            result["chain_tvls"] = dict(sorted(
                chain_tvls.items(), key=lambda x: x[1] or 0, reverse=True
            )[:10])
        return result
    except Exception as e:
        logger.error(f"get_protocol_detail error: {e}")
        return None


def get_chains_tvl() -> Optional[List[Dict]]:
    """Get TVL for all chains."""
    try:
        resp = proxied_get(f"{BASE}/v2/chains", timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not isinstance(data, list):
            return None
        sorted_data = sorted(data, key=lambda x: x.get("tvl", 0) or 0, reverse=True)[:30]
        return [{
            "name": c.get("name"),
            "tvl": c.get("tvl"),
            "tokenSymbol": c.get("tokenSymbol"),
        } for c in sorted_data]
    except Exception as e:
        logger.error(f"get_chains_tvl error: {e}")
        return None


def get_chain_tvl_history(chain: str, days: int = 30) -> Optional[Dict]:
    """Get historical TVL for a specific chain."""
    try:
        resp = proxied_get(f"{BASE}/v2/historicalChainTvl/{chain}", timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not isinstance(data, list):
            return None
        # Last N days only
        trimmed = data[-days:] if len(data) > days else data
        return {
            "chain": chain,
            "days": len(trimmed),
            "history": [{"date": d.get("date"), "tvl": d.get("tvl")} for d in trimmed],
        }
    except Exception as e:
        logger.error(f"get_chain_tvl_history error: {e}")
        return None
