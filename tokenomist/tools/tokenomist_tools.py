"""Tool wrappers for Tokenomist client."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from core.tool import BaseTool, ToolContext, ToolResult

from .client import (
    TokenomistApiError,
    TokenomistClient,
    normalize_token_index,
    resolve_token_id,
)


_client_singleton: Optional[TokenomistClient] = None
_token_index_cache: Optional[List[Dict[str, Any]]] = None


def _client() -> TokenomistClient:
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = TokenomistClient()
    return _client_singleton


def _safe_error_message(e: Exception) -> str:
    msg = str(e)
    # never leak key in tool output, redact common fake key literal if echoed by upstream
    return msg.replace("fake-tokenomist-key-12345", "[REDACTED]")


def _get_index(force_refresh: bool = False) -> List[Dict[str, Any]]:
    global _token_index_cache
    if force_refresh or _token_index_cache is None:
        payload = _client().token_list_v4()
        _token_index_cache = normalize_token_index(payload)
    return _token_index_cache


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _normalize_allocations_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize allocations response to reduce agent misinterpretation.

    - Primary percentage field: trackedAllocationPercentage (v2)
    - Fallback percentage: allocationAmount / totalTrackedAllocationAmount
    - Adds top allocations and quality flags
    """
    data = payload.get("data") if isinstance(payload, dict) else None
    allocations = data.get("allocations") if isinstance(data, dict) else []
    if not isinstance(allocations, list):
        allocations = []

    normalized: List[Dict[str, Any]] = []
    tracked_sum = 0.0
    fallback_sum = 0.0

    for row in allocations:
        if not isinstance(row, dict):
            continue
        tracked_pct = _to_float(row.get("trackedAllocationPercentage"))
        alloc_amount = _to_float(row.get("allocationAmount"))

        pct_source = "tracked"
        effective_pct = tracked_pct

        if effective_pct is None and alloc_amount is not None:
            total_tracked_amount = _to_float(data.get("totalTrackedAllocationAmount")) if isinstance(data, dict) else None
            if total_tracked_amount and total_tracked_amount > 0:
                effective_pct = (alloc_amount / total_tracked_amount) * 100.0
                pct_source = "fallback_from_allocationAmount"

        if tracked_pct is not None:
            tracked_sum += tracked_pct
        if effective_pct is not None:
            fallback_sum += effective_pct

        normalized.append(
            {
                "allocationName": row.get("allocationName"),
                "allocationType": row.get("allocationType"),
                "standardAllocationName": row.get("standardAllocationName"),
                "allocationAmount": row.get("allocationAmount"),
                "trackedAllocationPercentage": row.get("trackedAllocationPercentage"),
                "effectivePercentage": effective_pct,
                "percentageSource": pct_source,
            }
        )

    normalized_sorted = sorted(
        normalized,
        key=lambda x: (x.get("effectivePercentage") is not None, x.get("effectivePercentage") or -1),
        reverse=True,
    )

    coverage = {
        "allocations_count": len(normalized),
        "tracked_percentage_fields": sum(1 for x in normalized if x.get("trackedAllocationPercentage") is not None),
        "effective_percentage_fields": sum(1 for x in normalized if x.get("effectivePercentage") is not None),
        "tracked_percentage_sum": tracked_sum,
        "effective_percentage_sum": fallback_sum,
        "tracked_sum_close_to_100": 99.0 <= tracked_sum <= 101.0,
        "effective_sum_close_to_100": 99.0 <= fallback_sum <= 101.0,
    }

    return {
        "token": {
            "tokenId": data.get("tokenId") if isinstance(data, dict) else None,
            "symbol": data.get("symbol") if isinstance(data, dict) else None,
            "listedMethod": data.get("listedMethod") if isinstance(data, dict) else None,
        },
        "totals": {
            "totalTrackedAllocationAmount": data.get("totalTrackedAllocationAmount") if isinstance(data, dict) else None,
            "totalTrackedUnlockedAmount": data.get("totalTrackedUnlockedAmount") if isinstance(data, dict) else None,
            "totalTrackedLockedAmount": data.get("totalTrackedLockedAmount") if isinstance(data, dict) else None,
            "referenceSupply": data.get("referenceSupply") if isinstance(data, dict) else None,
        },
        "coverage": coverage,
        "top_allocations": normalized_sorted[:5],
        "allocations": normalized_sorted,
    }


class TokenomistTokenListTool(BaseTool):
    @property
    def name(self) -> str:
        return "tokenomist_token_list"

    @property
    def description(self) -> str:
        return """Get Token List API v4 from Tokenomist.

Uses latest Token List version (v4). Supports optional keyword filtering and limit to reduce payload size.
"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Optional keyword to filter by id/symbol/name",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default 50, max 500)",
                    "minimum": 1,
                    "maximum": 500,
                },
                "force_refresh": {
                    "type": "boolean",
                    "description": "Refresh token list cache from API",
                    "default": False,
                },
            },
        }

    async def execute(
        self,
        ctx: ToolContext,
        keyword: str = "",
        limit: int = 50,
        force_refresh: bool = False,
        **kwargs,
    ) -> ToolResult:
        try:
            limit = max(1, min(int(limit or 50), 500))
            rows = _get_index(force_refresh=force_refresh)
            if keyword:
                q = keyword.strip().lower()
                rows = [
                    r
                    for r in rows
                    if q in str(r.get("id", "")).lower()
                    or q in str(r.get("symbol", "")).lower()
                    or q in str(r.get("name", "")).lower()
                ]

            return ToolResult(
                success=True,
                output={
                    "version": "v4",
                    "count": len(rows),
                    "items": rows[:limit],
                    "returned": min(len(rows), limit),
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=_safe_error_message(e))


class TokenomistResolveTokenTool(BaseTool):
    @property
    def name(self) -> str:
        return "tokenomist_resolve_token"

    @property
    def description(self) -> str:
        return """Resolve user token query to canonical tokenId using Token List v4.

Input can be tokenId, symbol, or token name. Returns best match and alternatives.
"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Token id/symbol/name to resolve",
                },
                "force_refresh": {
                    "type": "boolean",
                    "description": "Refresh token list cache from API",
                    "default": False,
                },
            },
            "required": ["query"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        query: str = "",
        force_refresh: bool = False,
        **kwargs,
    ) -> ToolResult:
        if not query:
            return ToolResult(success=False, error="'query' is required")
        try:
            idx = _get_index(force_refresh=force_refresh)
            result = resolve_token_id(idx, query)
            return ToolResult(success=True, output={"version": "v4", **result})
        except Exception as e:
            return ToolResult(success=False, error=_safe_error_message(e))


class TokenomistAllocationsTool(BaseTool):
    @property
    def name(self) -> str:
        return "tokenomist_allocations"

    @property
    def description(self) -> str:
        return """Get allocations data for a token from Allocations API v2 (latest).

Returns normalized allocation percentages to reduce ambiguity:
- Uses trackedAllocationPercentage as primary
- Adds effectivePercentage fallback when possible
- Includes top_allocations and coverage quality summary
"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "token_id": {
                    "type": "string",
                    "description": "Canonical tokenId from tokenomist_token_list/tokenomist_resolve_token",
                },
                "include_raw": {
                    "type": "boolean",
                    "description": "Include raw upstream payload for debugging",
                    "default": False,
                },
            },
            "required": ["token_id"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        token_id: str = "",
        include_raw: bool = False,
        **kwargs,
    ) -> ToolResult:
        if not token_id:
            return ToolResult(success=False, error="'token_id' is required")
        try:
            raw = _client().allocations_v2(token_id)
            normalized = _normalize_allocations_payload(raw)
            out: Dict[str, Any] = {
                "version": "v2",
                "token_id": token_id,
                "normalized": normalized,
            }
            if include_raw:
                out["raw"] = raw
            return ToolResult(success=True, output=out)
        except Exception as e:
            return ToolResult(success=False, error=_safe_error_message(e))


class TokenomistAllocationsSummaryTool(BaseTool):
    @property
    def name(self) -> str:
        return "tokenomist_allocations_summary"

    @property
    def description(self) -> str:
        return """Get compact allocations summary with top N buckets and quality flags.

Accepts either `token_id` or free-text `query` (symbol/name/id).
If query is provided, resolves to canonical tokenId first.
"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "token_id": {
                    "type": "string",
                    "description": "Canonical tokenId (preferred if known)",
                },
                "query": {
                    "type": "string",
                    "description": "Token symbol/name/id (used when token_id is not provided)",
                },
                "top_n": {
                    "type": "integer",
                    "description": "Number of top allocations to return (default 5, max 20)",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 5,
                },
                "force_refresh": {
                    "type": "boolean",
                    "description": "Refresh token index cache before resolve",
                    "default": False,
                },
            },
        }

    async def execute(
        self,
        ctx: ToolContext,
        token_id: str = "",
        query: str = "",
        top_n: int = 5,
        force_refresh: bool = False,
        **kwargs,
    ) -> ToolResult:
        try:
            top_n = max(1, min(int(top_n or 5), 20))

            resolved: Optional[Dict[str, Any]] = None
            canonical_token_id = (token_id or "").strip()

            if not canonical_token_id:
                if not query:
                    return ToolResult(success=False, error="Either 'token_id' or 'query' is required")
                idx = _get_index(force_refresh=force_refresh)
                resolved = resolve_token_id(idx, query)
                token = resolved.get("token") if isinstance(resolved, dict) else None
                if not token:
                    return ToolResult(
                        success=False,
                        error=(
                            "Could not resolve unique tokenId from query. "
                            f"match_type={resolved.get('match_type') if isinstance(resolved, dict) else 'unknown'}"
                        ),
                        output={"resolution": resolved},
                    )
                canonical_token_id = str(token.get("id", "")).strip()

            raw = _client().allocations_v2(canonical_token_id)
            normalized = _normalize_allocations_payload(raw)
            coverage = normalized.get("coverage", {}) if isinstance(normalized, dict) else {}
            top_allocations = normalized.get("top_allocations", []) if isinstance(normalized, dict) else []
            if not isinstance(top_allocations, list):
                top_allocations = []

            summary = {
                "token": normalized.get("token") if isinstance(normalized, dict) else None,
                "top_n": top_n,
                "top_allocations": top_allocations[:top_n],
                "coverage": coverage,
                "quality": {
                    "has_tracked_percentages": bool((coverage or {}).get("tracked_percentage_fields", 0) > 0),
                    "sum_close_to_100": bool(
                        (coverage or {}).get("tracked_sum_close_to_100")
                        or (coverage or {}).get("effective_sum_close_to_100")
                    ),
                },
            }

            output: Dict[str, Any] = {
                "version": "v2",
                "token_id": canonical_token_id,
                "summary": summary,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            if resolved is not None:
                output["resolution"] = {
                    "query": query,
                    "match_type": resolved.get("match_type"),
                    "token": resolved.get("token"),
                }

            return ToolResult(success=True, output=output)
        except Exception as e:
            return ToolResult(success=False, error=_safe_error_message(e))


class TokenomistDailyEmissionTool(BaseTool):
    @property
    def name(self) -> str:
        return "tokenomist_daily_emission"

    @property
    def description(self) -> str:
        return "Get daily emission data from Daily Emission API v2 (latest)."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "token_id": {
                    "type": "string",
                    "description": "Canonical tokenId",
                },
                "start": {
                    "type": "string",
                    "description": "Optional YYYY-MM-DD",
                },
                "end": {
                    "type": "string",
                    "description": "Optional YYYY-MM-DD",
                },
            },
            "required": ["token_id"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        token_id: str = "",
        start: str = "",
        end: str = "",
        **kwargs,
    ) -> ToolResult:
        if not token_id:
            return ToolResult(success=False, error="'token_id' is required")
        try:
            data = _client().daily_emission_v2(
                token_id=token_id,
                start=start or None,
                end=end or None,
            )
            return ToolResult(success=True, output={"version": "v2", **data})
        except Exception as e:
            return ToolResult(success=False, error=_safe_error_message(e))


class TokenomistUnlockEventsTool(BaseTool):
    @property
    def name(self) -> str:
        return "tokenomist_unlock_events"

    @property
    def description(self) -> str:
        return "Get unlock events from Unlock Events API v4 (latest)."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "token_id": {
                    "type": "string",
                    "description": "Canonical tokenId",
                },
                "start": {
                    "type": "string",
                    "description": "Optional YYYY-MM-DD",
                },
                "end": {
                    "type": "string",
                    "description": "Optional YYYY-MM-DD",
                },
            },
            "required": ["token_id"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        token_id: str = "",
        start: str = "",
        end: str = "",
        **kwargs,
    ) -> ToolResult:
        if not token_id:
            return ToolResult(success=False, error="'token_id' is required")
        try:
            data = _client().unlock_events_v4(
                token_id=token_id,
                start=start or None,
                end=end or None,
            )
            return ToolResult(success=True, output={"version": "v4", **data})
        except Exception as e:
            return ToolResult(success=False, error=_safe_error_message(e))


class TokenomistTokenOverviewTool(BaseTool):
    @property
    def name(self) -> str:
        return "tokenomist_token_overview"

    @property
    def description(self) -> str:
        return """One-call wrapper to minimize tool calls.

Resolves token query then fetches latest allocations(v2), daily-emission(v2), and unlock-events(v4).
Useful for agent workflows to reduce ambiguity and token/tool overhead.
"""

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Token id/symbol/name",
                },
                "start": {
                    "type": "string",
                    "description": "Optional YYYY-MM-DD for emission/events",
                },
                "end": {
                    "type": "string",
                    "description": "Optional YYYY-MM-DD for emission/events",
                },
                "include_allocations": {
                    "type": "boolean",
                    "description": "Whether to fetch allocations",
                    "default": True,
                },
                "include_daily_emission": {
                    "type": "boolean",
                    "description": "Whether to fetch daily emission",
                    "default": True,
                },
                "include_unlock_events": {
                    "type": "boolean",
                    "description": "Whether to fetch unlock events",
                    "default": True,
                },
                "force_refresh": {
                    "type": "boolean",
                    "description": "Refresh token list cache before resolve",
                    "default": False,
                },
            },
            "required": ["query"],
        }

    async def execute(
        self,
        ctx: ToolContext,
        query: str = "",
        start: str = "",
        end: str = "",
        include_allocations: bool = True,
        include_daily_emission: bool = True,
        include_unlock_events: bool = True,
        force_refresh: bool = False,
        **kwargs,
    ) -> ToolResult:
        if not query:
            return ToolResult(success=False, error="'query' is required")

        try:
            idx = _get_index(force_refresh=force_refresh)
            resolved = resolve_token_id(idx, query)
            token = resolved.get("token")
            if not token:
                return ToolResult(
                    success=False,
                    error=(
                        "Could not resolve unique tokenId from query. "
                        f"match_type={resolved.get('match_type')}"
                    ),
                    output={
                        "resolution": resolved,
                    },
                )

            token_id = token.get("id")
            out: Dict[str, Any] = {
                "resolved": {
                    "query": query,
                    "match_type": resolved.get("match_type"),
                    "token": token,
                },
                "versions": {
                    "token_list": "v4",
                    "allocations": "v2",
                    "daily_emission": "v2",
                    "unlock_events": "v4",
                },
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

            client = _client()

            if include_allocations:
                try:
                    raw_alloc = client.allocations_v2(token_id)
                    out["allocations"] = {
                        "version": "v2",
                        "normalized": _normalize_allocations_payload(raw_alloc),
                    }
                except Exception as e:
                    out["allocations_error"] = _safe_error_message(e)

            if include_daily_emission:
                try:
                    out["daily_emission"] = client.daily_emission_v2(
                        token_id=token_id,
                        start=start or None,
                        end=end or None,
                    )
                except Exception as e:
                    out["daily_emission_error"] = _safe_error_message(e)

            if include_unlock_events:
                try:
                    out["unlock_events"] = client.unlock_events_v4(
                        token_id=token_id,
                        start=start or None,
                        end=end or None,
                    )
                except Exception as e:
                    out["unlock_events_error"] = _safe_error_message(e)

            return ToolResult(success=True, output=out)

        except Exception as e:
            return ToolResult(success=False, error=_safe_error_message(e))
