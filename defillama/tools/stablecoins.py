"""DefiLlama Stablecoins API."""
import logging
from typing import Any, Dict, List, Optional

try:
    from core.http_client import proxied_get
except ImportError:
    import requests
    def proxied_get(url, **kw):
        return requests.get(url, **kw)

logger = logging.getLogger(__name__)


def get_stablecoins(top_n: int = 20) -> Optional[Dict]:
    """Get stablecoin market data."""
    try:
        resp = proxied_get("https://stablecoins.llama.fi/stablecoins", timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        assets = data.get("peggedAssets", [])
        
        # Sort by market cap
        assets.sort(
            key=lambda x: x.get("circulating", {}).get("peggedUSD", 0) or 0,
            reverse=True
        )
        assets = assets[:top_n]
        
        total_mcap = sum(
            a.get("circulating", {}).get("peggedUSD", 0) or 0 for a in assets
        )
        
        return {
            "total_market_cap": total_mcap,
            "stablecoins": [{
                "name": a.get("name"),
                "symbol": a.get("symbol"),
                "market_cap": a.get("circulating", {}).get("peggedUSD"),
                "chains": a.get("chains", [])[:5],
                "price": a.get("price"),
            } for a in assets],
        }
    except Exception as e:
        logger.error(f"get_stablecoins error: {e}")
        return None
