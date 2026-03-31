"""DefiLlama Fees & DEX Volume APIs."""
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


def _parse_overview(url: str, top_n: int = 20, chain: str = None) -> Optional[Dict]:
    """Shared parser for /overview/fees and /overview/dexs."""
    try:
        params = {}
        if chain:
            params["chain"] = chain
        resp = proxied_get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        
        result = {
            "total24h": data.get("total24h"),
            "total48hto24h": data.get("total48hto24h"),
            "total7d": data.get("total7d"),
            "total30d": data.get("total30d"),
            "chain": chain or "all",
        }
        
        # Parse protocol breakdown
        protocols = data.get("protocols", [])
        if not protocols:
            # Try breakdown24h format
            breakdown = data.get("breakdown24h", {})
            if breakdown:
                flat = []
                for proto_name, chains_data in breakdown.items():
                    total = sum(v for v in chains_data.values() if isinstance(v, (int, float)))
                    flat.append({"name": proto_name, "total24h": total})
                protocols = sorted(flat, key=lambda x: x.get("total24h", 0) or 0, reverse=True)[:top_n]
        else:
            protocols = sorted(protocols, key=lambda x: x.get("total24h", 0) or 0, reverse=True)[:top_n]
        
        result["protocols"] = [{
            "name": p.get("name", p.get("defillamaId", "?")),
            "total24h": p.get("total24h"),
            "total7d": p.get("total7d"),
            "total30d": p.get("total30d"),
            "change_1d": p.get("change_1d"),
            "category": p.get("category"),
            "chains": p.get("chains", [])[:5] if isinstance(p.get("chains"), list) else [],
        } for p in protocols]
        
        return result
    except Exception as e:
        logger.error(f"_parse_overview error for {url}: {e}")
        return None


def get_fees_overview(top_n: int = 20, chain: str = None) -> Optional[Dict]:
    """Get protocol fees/revenue overview. Top N by 24h fees."""
    return _parse_overview(f"{BASE}/overview/fees", top_n=top_n, chain=chain)


def get_dex_volume_overview(top_n: int = 20, chain: str = None) -> Optional[Dict]:
    """Get DEX volume overview. Top N by 24h volume."""
    return _parse_overview(f"{BASE}/overview/dexs", top_n=top_n, chain=chain)
