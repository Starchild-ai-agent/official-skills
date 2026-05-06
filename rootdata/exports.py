"""
RootData skill exports (script-mode).

Usage:
    python3 - <<'EOF'
    import sys
    sys.path.insert(0, "/data/workspace/skills/rootdata")
    from exports import rd_search, rd_hot_index
    print(rd_search(query="berachain")[:1])
    print(rd_hot_index(days=1)[:3])
    EOF
"""

import os
import requests

BASE = "https://api.rootdata.com/open/skill"
TIMEOUT = 30


def _headers(language: str = "en"):
    key = os.environ.get("ROOTDATA_SKILL_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "ROOTDATA_SKILL_KEY is not set. Call rd_init_key() and persist the returned api_key first."
        )
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "language": language,
    }


def _post(path: str, body: dict, language: str = "en"):
    r = requests.post(
        f"{BASE}/{path}",
        headers=_headers(language=language),
        json=body,
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and data.get("result") != 200:
        # upstream returns {result: <code>, error: ...} even on some non-200 cases
        raise RuntimeError(f"RootData API error: {data}")
    return data.get("data") if isinstance(data, dict) and "data" in data else data


def rd_init_key():
    """Initialize anonymous RootData key via /init. Returns {'api_key', 'message'}"""
    r = requests.post(f"{BASE}/init", json={}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def rd_search(query: str, precise_x_search: bool = False, language: str = "en"):
    """Search entities by keyword. type: 1=project, 2=institution, 3=person."""
    return _post(
        "ser_inv",
        {"query": query, "precise_x_search": bool(precise_x_search)},
        language=language,
    )


def rd_id_map(type: int, language: str = "en"):
    """Get all IDs by type: 1=project, 2=institution, 3=person."""
    return _post("id_map", {"type": int(type)}, language=language)


def rd_project_detail(
    project_id: int = None,
    contract_address: str = None,
    include_investors: bool = True,
    language: str = "en",
):
    """Project detail by project_id or contract_address."""
    body = {"include_investors": bool(include_investors)}
    if project_id is not None:
        body["project_id"] = int(project_id)
    if contract_address:
        body["contract_address"] = contract_address
    if "project_id" not in body and "contract_address" not in body:
        raise ValueError("rd_project_detail requires project_id or contract_address")
    return _post("get_item", body, language=language)


def rd_funding_rounds(
    page: int = 1,
    page_size: int = 20,
    project_id: int = None,
    start_time: str = None,
    end_time: str = None,
    min_amount: float = None,
    max_amount: float = None,
    language: str = "en",
):
    """Funding rounds (past 365 days; max 3 investors per round)."""
    body = {"page": int(page), "page_size": int(page_size)}
    if project_id is not None:
        body["project_id"] = int(project_id)
    if start_time is not None:
        body["start_time"] = start_time
    if end_time is not None:
        body["end_time"] = end_time
    if min_amount is not None:
        body["min_amount"] = min_amount
    if max_amount is not None:
        body["max_amount"] = max_amount
    return _post("get_fac", body, language=language)


def rd_hot_index(days: int = 1, language: str = "en"):
    """Trending projects. days: 1=today, 7=this week."""
    if days not in (1, 7):
        raise ValueError("rd_hot_index days must be 1 or 7")
    return _post("hot_index", {"days": days}, language=language)


def rd_job_changes(
    recent_joinees: bool = True,
    recent_resignations: bool = True,
    language: str = "en",
):
    """Recent hires/departures. Max 20 entries per category."""
    return _post(
        "job_changes",
        {
            "recent_joinees": bool(recent_joinees),
            "recent_resignations": bool(recent_resignations),
        },
        language=language,
    )
