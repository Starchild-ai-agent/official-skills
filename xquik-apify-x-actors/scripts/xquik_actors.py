"""Run Xquik's public Apify Actors through the Apify API."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_API_BASE = "https://api.apify.com/v2"
_ACTORS = {
    "tweet": "xquik~x-tweet-scraper",
    "follower": "xquik~x-follower-scraper",
}


def _get_token() -> str:
    token = os.environ.get("APIFY_TOKEN", "").strip()
    if not token:
        raise RuntimeError("APIFY_TOKEN missing. Add it first.")
    return token


def _actor_selector(actor: str) -> str:
    try:
        return _ACTORS[actor]
    except KeyError as exc:
        raise ValueError("Unknown Actor. Use 'tweet' or 'follower'.") from exc


def _request_json(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
    authenticated: bool = True,
) -> Any:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Accept": "application/json"}
    if authenticated:
        headers["Authorization"] = f"Bearer {_get_token()}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
    request = Request(
        url,
        data=body,
        method=method,
        headers=headers,
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(
            f"Apify request failed with HTTP {exc.code}. Check the Actor input."
        ) from exc
    except URLError as exc:
        raise RuntimeError("Apify request failed. Check network access.") from exc


def get_actor_info(actor: str) -> dict[str, Any]:
    """Return current Apify metadata for the Tweet or Follower Actor."""
    selector = _actor_selector(actor)
    response = _request_json(
        "GET",
        f"{_API_BASE}/acts/{selector}",
        authenticated=False,
    )
    if not isinstance(response, dict):
        raise RuntimeError("Apify returned invalid metadata. Try again later.")
    return response


def _validate_run(
    input_data: dict[str, Any],
    *,
    confirmed: bool,
    timeout: int,
    max_total_charge_usd: float | None,
) -> None:
    if confirmed is not True:
        raise PermissionError("Run approval missing. Ask the user first.")
    if not isinstance(input_data, dict):
        raise TypeError("Invalid Actor input. Pass a dictionary.")
    max_items = input_data.get("maxItems")
    if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items <= 0:
        raise ValueError("Result cap missing. Set a positive maxItems value.")
    valid_timeout = (
        isinstance(timeout, int)
        and not isinstance(timeout, bool)
        and 1 <= timeout <= 300
    )
    if not valid_timeout:
        raise ValueError("Invalid timeout. Use 1 through 300 seconds.")
    if max_total_charge_usd is not None:
        if (
            isinstance(max_total_charge_usd, bool)
            or not isinstance(max_total_charge_usd, (int, float))
            or max_total_charge_usd <= 0
        ):
            raise ValueError("Invalid spending cap. Use a positive amount.")


def _run_actor(
    actor: str,
    input_data: dict[str, Any],
    *,
    confirmed: bool,
    timeout: int,
    max_total_charge_usd: float | None,
) -> list[dict[str, Any]]:
    _validate_run(
        input_data,
        confirmed=confirmed,
        timeout=timeout,
        max_total_charge_usd=max_total_charge_usd,
    )
    query: dict[str, str | int] = {"clean": "true", "timeout": timeout}
    if max_total_charge_usd is not None:
        query["maxTotalChargeUsd"] = str(max_total_charge_usd)
    selector = _actor_selector(actor)
    url = (
        f"{_API_BASE}/acts/{selector}/run-sync-get-dataset-items?"
        f"{urlencode(query)}"
    )
    response = _request_json(
        "POST",
        url,
        payload=dict(input_data),
        timeout=timeout + 30,
    )
    if not isinstance(response, list) or not all(
        isinstance(item, dict) for item in response
    ):
        raise RuntimeError("Apify returned invalid results. Inspect the run.")
    return response


def run_tweet_scraper(
    input_data: dict[str, Any],
    *,
    confirmed: bool = False,
    timeout: int = 300,
    max_total_charge_usd: float | None = None,
) -> list[dict[str, Any]]:
    """Run Xquik's X Tweet Scraper after explicit approval."""
    return _run_actor(
        "tweet",
        input_data,
        confirmed=confirmed,
        timeout=timeout,
        max_total_charge_usd=max_total_charge_usd,
    )


def run_follower_scraper(
    input_data: dict[str, Any],
    *,
    confirmed: bool = False,
    timeout: int = 300,
    max_total_charge_usd: float | None = None,
) -> list[dict[str, Any]]:
    """Run Xquik's X Follower Scraper after explicit approval."""
    return _run_actor(
        "follower",
        input_data,
        confirmed=confirmed,
        timeout=timeout,
        max_total_charge_usd=max_total_charge_usd,
    )
