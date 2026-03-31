"""DefiLlama Yield Pools API."""
import logging
from typing import Any, Dict, List, Optional

try:
    from core.http_client import proxied_get
except ImportError:
    import requests
    def proxied_get(url, **kw):
        return requests.get(url, **kw)

logger = logging.getLogger(__name__)


def get_yield_pools(
    min_apy: float = 0,
    min_tvl: float = 0,
    stablecoin_only: bool = False,
    chain: str = None,
    top_n: int = 30,
) -> Optional[List[Dict]]:
    """Get yield pools with filtering."""
    try:
        resp = proxied_get("https://yields.llama.fi/pools", timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json().get("data", [])
        
        # Filter
        filtered = []
        for p in data:
            apy = p.get("apy") or 0
            tvl = p.get("tvlUsd") or 0
            if apy < min_apy or tvl < min_tvl:
                continue
            if stablecoin_only and not p.get("stablecoin"):
                continue
            if chain and p.get("chain", "").lower() != chain.lower():
                continue
            filtered.append(p)
        
        # Sort by APY desc, take top N
        filtered.sort(key=lambda x: x.get("apy", 0) or 0, reverse=True)
        filtered = filtered[:top_n]
        
        return [{
            "pool": p.get("pool"),
            "project": p.get("project"),
            "symbol": p.get("symbol"),
            "chain": p.get("chain"),
            "apy": round(p.get("apy", 0), 2),
            "tvlUsd": p.get("tvlUsd"),
            "stablecoin": p.get("stablecoin"),
            "ilRisk": p.get("ilRisk"),
            "apyBase": round(p.get("apyBase", 0) or 0, 2),
            "apyReward": round(p.get("apyReward", 0) or 0, 2),
        } for p in filtered]
    except Exception as e:
        logger.error(f"get_yield_pools error: {e}")
        return None
