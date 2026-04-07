"""
Tokenomist skill exports — tool names match SKILL.md frontmatter.

Usage in task scripts:
    from core.skill_tools import tokenomist
    tokens = tokenomist.tokenomist_token_list()
    resolved = tokenomist.tokenomist_resolve_token(query="ARB")
    allocs = tokenomist.tokenomist_allocations(query="ARB")
    overview = tokenomist.tokenomist_token_overview(query="ARB")
"""
from client import TokenomistClient, normalize_token_index, resolve_token_id

_client_singleton = None
_token_index_cache = None


def _client():
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = TokenomistClient()
    return _client_singleton


def _get_index(force_refresh=False):
    global _token_index_cache
    if force_refresh or _token_index_cache is None:
        payload = _client().token_list_v4()
        _token_index_cache = normalize_token_index(payload)
    return _token_index_cache


def _resolve_id(query):
    """Resolve query to token_id, raise if ambiguous."""
    index = _get_index()
    result = resolve_token_id(index, query)
    if result["token"]:
        return result["token"]["id"]
    if result["candidates"]:
        names = [f"{c.get('symbol','')} ({c.get('name','')})" for c in result["candidates"][:5]]
        raise ValueError(f"Ambiguous query '{query}': {', '.join(names)}")
    raise ValueError(f"Token not found: '{query}'")


def tokenomist_token_list():
    """Get full token list (v4) with metadata."""
    return _get_index(force_refresh=True)


def tokenomist_resolve_token(query):
    """Resolve a token query (symbol/name/id) to a token_id."""
    index = _get_index()
    return resolve_token_id(index, query)


def tokenomist_allocations(query):
    """Get token allocations (v2). Auto-resolves query to token_id."""
    token_id = _resolve_id(query)
    return _client().allocations_v2(token_id)


def tokenomist_allocations_summary(query):
    """Get allocation summary."""
    return tokenomist_allocations(query)


def tokenomist_daily_emission(query, start=None, end=None):
    """Get daily emission data (v2). Auto-resolves query to token_id."""
    token_id = _resolve_id(query)
    return _client().daily_emission_v2(token_id, start=start, end=end)


def tokenomist_unlock_events(query, start=None, end=None):
    """Get unlock events (v4). Auto-resolves query to token_id."""
    token_id = _resolve_id(query)
    return _client().unlock_events_v4(token_id, start=start, end=end)


def tokenomist_token_overview(query, start=None, end=None,
                               include_allocations=True,
                               include_emission=True,
                               include_events=True):
    """One-call overview: resolve + allocations + emission + events."""
    token_id = _resolve_id(query)
    result = {"token_id": token_id}

    if include_allocations:
        try:
            result["allocations"] = _client().allocations_v2(token_id)
        except Exception as e:
            result["allocations_error"] = str(e)

    if include_emission:
        try:
            result["daily_emission"] = _client().daily_emission_v2(token_id, start=start, end=end)
        except Exception as e:
            result["daily_emission_error"] = str(e)

    if include_events:
        try:
            result["unlock_events"] = _client().unlock_events_v4(token_id, start=start, end=end)
        except Exception as e:
            result["unlock_events_error"] = str(e)

    return result
