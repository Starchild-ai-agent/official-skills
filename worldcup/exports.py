"""
World Cup 2026 skill — script exports.

Self-contained thin client for the ai-agent worldcup endpoints
(/api/clawd/worldcup/*), authenticated with the container JWT. No platform
internals imported, so the skill is portable.

Usage (from bash or a task script):
    from core.skill_tools import worldcup
    print(worldcup.get_today_matches())
    print(worldcup.place_bet(42, "win_draw_loss", {"choice": "home"}, 100))

Auth/config (env, injected in every clawd container):
    AI_AGENT_API_URL   base URL of ai-agent
    CONTAINER_JWT      bearer token (10-year TTL)
"""
import json
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional


def _base() -> str:
    return os.environ.get("AI_AGENT_API_URL", "http://localhost:8001").rstrip("/")


def _jwt() -> str:
    jwt = os.environ.get("CONTAINER_JWT", "") or os.environ.get("USER_JWT", "")
    if not jwt:
        raise RuntimeError(
            "no CONTAINER_JWT in env — worldcup needs the container identity token"
        )
    return jwt


def _request(method: str, path: str, params: Optional[dict] = None,
             body: Optional[dict] = None) -> Dict[str, Any]:
    url = _base() + path
    if params:
        clean = {k: v for k, v in params.items() if v is not None}
        if clean:
            url += "?" + urllib.parse.urlencode(clean)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {_jwt()}")
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {"success": True, "data": None}
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode()[:300]
        except Exception:
            pass
        return {"success": False, "error": f"HTTP {e.code}: {detail}"}
    except Exception as e:
        return {"success": False, "error": f"{type(e).__name__}: {e}"}


# ─── Matches ────────────────────────────────────────────────────────────────

def get_today_matches() -> Dict[str, Any]:
    """Today's matches with the user's prediction status."""
    return _request("GET", "/api/clawd/worldcup/matches/today")


def get_upcoming_matches(limit: int = 10) -> Dict[str, Any]:
    """Next scheduled matches."""
    return _request("GET", "/api/clawd/worldcup/matches/upcoming", params={"limit": limit})


def get_live_matches() -> Dict[str, Any]:
    """Matches in progress now."""
    return _request("GET", "/api/clawd/worldcup/matches/live")


def get_finished_matches(limit: int = 20) -> Dict[str, Any]:
    """Recently finished matches (most recent first)."""
    return _request("GET", "/api/clawd/worldcup/matches/finished", params={"limit": limit})


def get_match_detail(match_id: int) -> Dict[str, Any]:
    """One match in full by ID."""
    return _request("GET", f"/api/clawd/worldcup/matches/{match_id}")


# ─── Betting ──────────────────────────────────────────────────────────────────

def place_bet(match_id: int, predict_type: str, prediction: dict, stake: int) -> Dict[str, Any]:
    """Place a prediction.

    predict_type / prediction payload shapes:
      win_draw_loss -> {"choice": "home"|"draw"|"away"}
      exact_score   -> {"home": N, "away": N}
      total_goals   -> {"range": "0-1"|"2-3"|"4+"}
      first_goal    -> {"team": "TEAM_CODE"}   e.g. "BRA"
    stake: points, multiple of 10, min 10, max 10000.
    """
    return _request("POST", "/api/clawd/worldcup/predict", body={
        "match_id": match_id,
        "predict_type": predict_type,
        "prediction": prediction,
        "stake": stake,
    })


def cancel_prediction(prediction_id: int) -> Dict[str, Any]:
    """Cancel an unsettled prediction (refunds the stake)."""
    return _request("DELETE", f"/api/clawd/worldcup/predictions/{prediction_id}")


def get_betting_status() -> Dict[str, Any]:
    """Point balance, pending stakes, and min/max stake limits."""
    return _request("GET", "/api/clawd/worldcup/betting-status")


# ─── Predictions ──────────────────────────────────────────────────────────────

def get_my_predictions(match_id: Optional[int] = None, settled_only: bool = False) -> Dict[str, Any]:
    """The user's prediction history (optional match_id filter)."""
    params: Dict[str, Any] = {}
    if match_id is not None:
        params["match_id"] = match_id
    if settled_only:
        params["settled_only"] = "true"
    return _request("GET", "/api/clawd/worldcup/predictions", params=params or None)


def get_prediction_detail(prediction_id: int) -> Dict[str, Any]:
    """One prediction in full by ID."""
    return _request("GET", f"/api/clawd/worldcup/predictions/{prediction_id}")


# ─── Stats & leaderboard ──────────────────────────────────────────────────────

def get_my_stats() -> Dict[str, Any]:
    """The user's betting stats (win rate, total staked, etc.)."""
    return _request("GET", "/api/clawd/worldcup/stats")


def get_leaderboard(limit: int = 50, sort_by: str = "points") -> Dict[str, Any]:
    """Top predictors. sort_by: 'points' | 'accuracy'."""
    return _request("GET", "/api/clawd/worldcup/leaderboard",
                    params={"limit": limit, "sort_by": sort_by})
