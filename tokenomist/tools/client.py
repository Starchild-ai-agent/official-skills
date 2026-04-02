"""
Tokenomist API client (Tokenomist API wrapper).

- Uses latest endpoint versions by default:
  - Token List API v4
  - Allocations API v2
  - Daily Emission API v2
  - Unlock Events API v4
- Uses core/http_client.py proxied_get so traffic goes through sc-proxy
  when proxy is configured.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.http_client import proxied_get

logger = logging.getLogger(__name__)

BASE_URL = "https://api.tokenomist.ai"
DEFAULT_TIMEOUT = 30


class TokenomistApiError(Exception):
    """Tokenomist API request failed."""


class TokenomistClient:
    def __init__(self, api_key: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT):
        self.api_key = api_key or os.environ.get("TOKENMIST_API_KEY", "")
        self.timeout = timeout
        if not self.api_key:
            logger.warning("TOKENMIST_API_KEY not set. Tokenomist API calls will fail.")

    def _headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "x-api-key": self.api_key,
        }

    def _request(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.api_key:
            raise TokenomistApiError("TOKENMIST_API_KEY is required")

        url = f"{BASE_URL}{path}"
        try:
            resp = proxied_get(url, headers=self._headers(), params=params or {}, timeout=self.timeout)
        except Exception as e:
            raise TokenomistApiError(f"Request failed: {e}") from e

        if resp.status_code >= 400:
            body = resp.text
            raise TokenomistApiError(f"Tokenomist API {resp.status_code}: {body}")

        try:
            data = resp.json()
        except Exception as e:
            raise TokenomistApiError(f"Invalid JSON response: {e}") from e

        # API-level status check
        if isinstance(data, dict) and data.get("status") is False:
            raise TokenomistApiError(f"API status=false response: {data}")

        return data

    @staticmethod
    def _validate_date_yyyy_mm_dd(value: Optional[str], field_name: str) -> None:
        if not value:
            return
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError as e:
            raise TokenomistApiError(f"{field_name} must be YYYY-MM-DD, got: {value}") from e

    # ---- Canonical latest-version endpoints ----

    def token_list_v4(self) -> Dict[str, Any]:
        return self._request("/v4/token/list")

    def allocations_v2(self, token_id: str) -> Dict[str, Any]:
        if not token_id:
            raise TokenomistApiError("token_id is required")
        return self._request("/v2/allocations", params={"tokenId": token_id})

    def daily_emission_v2(
        self,
        token_id: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not token_id:
            raise TokenomistApiError("token_id is required")
        self._validate_date_yyyy_mm_dd(start, "start")
        self._validate_date_yyyy_mm_dd(end, "end")
        params: Dict[str, Any] = {"tokenId": token_id}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        return self._request("/v2/daily-emission", params=params)

    def unlock_events_v4(
        self,
        token_id: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not token_id:
            raise TokenomistApiError("token_id is required")
        self._validate_date_yyyy_mm_dd(start, "start")
        self._validate_date_yyyy_mm_dd(end, "end")
        params: Dict[str, Any] = {"tokenId": token_id}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        return self._request("/v4/unlock/events", params=params)


def normalize_token_index(token_list_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = token_list_payload.get("data", []) if isinstance(token_list_payload, dict) else []
    if not isinstance(data, list):
        return []

    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "symbol": item.get("symbol"),
                "listedMethod": item.get("listedMethod"),
                "marketCap": item.get("marketCap"),
                "circulatingSupply": item.get("circulatingSupply"),
                "maxSupply": item.get("maxSupply"),
                "websiteUrl": item.get("websiteUrl"),
                "hasStandardAllocation": item.get("hasStandardAllocation"),
                "hasFundraising": item.get("hasFundraising"),
                "hasBurn": item.get("hasBurn"),
                "hasBuyback": item.get("hasBuyback"),
                "latestFundraisingRound": item.get("latestFundraisingRound"),
                "lastUpdatedDate": item.get("lastUpdatedDate"),
            }
        )
    return out


def resolve_token_id(
    token_index: List[Dict[str, Any]],
    query: str,
) -> Dict[str, Any]:
    if not query:
        raise TokenomistApiError("query is required")

    q = query.strip().lower()

    exact_id = [x for x in token_index if str(x.get("id", "")).lower() == q]
    if exact_id:
        return {"match_type": "exact_id", "token": exact_id[0], "candidates": []}

    exact_symbol = [x for x in token_index if str(x.get("symbol", "")).lower() == q]
    if len(exact_symbol) == 1:
        return {"match_type": "exact_symbol", "token": exact_symbol[0], "candidates": []}
    if len(exact_symbol) > 1:
        return {
            "match_type": "ambiguous_symbol",
            "token": None,
            "candidates": exact_symbol[:10],
        }

    exact_name = [x for x in token_index if str(x.get("name", "")).lower() == q]
    if len(exact_name) == 1:
        return {"match_type": "exact_name", "token": exact_name[0], "candidates": []}
    if len(exact_name) > 1:
        return {
            "match_type": "ambiguous_name",
            "token": None,
            "candidates": exact_name[:10],
        }

    fuzzy = [
        x
        for x in token_index
        if q in str(x.get("id", "")).lower()
        or q in str(x.get("symbol", "")).lower()
        or q in str(x.get("name", "")).lower()
    ]
    if len(fuzzy) == 1:
        return {"match_type": "fuzzy_single", "token": fuzzy[0], "candidates": []}

    return {"match_type": "fuzzy_many", "token": None, "candidates": fuzzy[:10]}
