"""
Shared Coinglass API helper — eliminates return-None error pattern.

Every tools/*.py file repeated the same boilerplate:
  1. _get_api_key() → return None if missing
  2. proxied_get(url, headers, timeout) → return None on any error
  3. check response code → return None if not "0"

This module centralizes that into one `cg_request()` function that:
  - Raises typed exceptions instead of returning None
  - Provides actionable error messages for each failure mode
  - Distinguishes API key errors, rate limits, server errors, parse errors
"""

import os
import json
import requests

try:
    from core.http_client import proxied_get
except ImportError:
    # Fallback for testing outside platform — use plain requests
    def proxied_get(url, params=None, headers=None, timeout=30,
                    **kwargs):
        return requests.get(
            url, params=params, headers=headers, timeout=timeout,
            **kwargs
        )


def _do_get(url, params, headers, timeout):
    """Route the request through sc-proxy, or direct when BYOK.

    sc-proxy injects the PLATFORM key and overwrites any user-supplied
    Coinglass header, so a user's own higher-tier key is useless through
    the proxy. Set COINGLASS_DIRECT=1 (with your own COINGLASS_API_KEY)
    to bypass the proxy and hit open-api-v4.coinglass.com directly.
    """
    if os.environ.get("COINGLASS_DIRECT") == "1":
        return requests.get(url, params=params, headers=headers,
                            timeout=timeout)
    return proxied_get(url, params=params, headers=headers, timeout=timeout)


# ── Coinglass-specific exceptions ───────────────────────────


class CoinglassError(Exception):
    """Base exception for all Coinglass API errors."""

    def __init__(self, message, code="UNKNOWN", suggestion=""):
        self.code = code
        self.suggestion = suggestion
        super().__init__(message)


class CoinglassPlanError(CoinglassError):
    """Endpoint requires a higher Coinglass plan than the key's tier.

    Platform key is Startup tier. For heatmaps / liquidation orders /
    coins-markets / Hyperliquid positions, either use a user-supplied
    higher-tier key with direct (non-proxied) requests, or scrape
    coinglass.com via the Apify skill.
    """

    BYOK_MSG = (
        "This endpoint needs a Coinglass plan above Startup. Options: "
        "(1) user provides their own COINGLASS_API_KEY (Basic or higher) "
        "and the skill calls https://open-api-v4.coinglass.com directly — "
        "sc-proxy overwrites user keys, so BYOK must bypass it; "
        "(2) scrape coinglass.com pages via the Apify skill."
    )

    def __init__(self, endpoint, msg="Upgrade plan"):
        super().__init__(
            f"Plan restriction on '{endpoint}': {msg}",
            code="PLAN_LIMIT",
            suggestion=self.BYOK_MSG,
        )


class CoinglassAPIKeyError(CoinglassError):
    """API key missing or invalid."""
    pass


class CoinglassRateLimitError(CoinglassError):
    """Rate limited by Coinglass."""
    pass


class CoinglassServerError(CoinglassError):
    """Coinglass server returned 5xx."""
    pass


# ── API configuration ──────────────────────────────────────

BASE_URL_V2 = "https://open-api.coinglass.com/public/v2"
BASE_URL_V4 = "https://open-api-v4.coinglass.com"

HEADER_KEY_V2 = "coinglassSecret"
HEADER_KEY_V4 = "CG-API-KEY"


def _get_api_key():
    """Get API key from environment."""
    return os.getenv("COINGLASS_API_KEY")


def _suggestion_for_status(status):
    """Map HTTP status to actionable suggestion."""
    suggestions = {
        401: "API key invalid or expired. Check COINGLASS_API_KEY.",
        403: "Access denied. This endpoint may require a paid plan.",
        404: "Endpoint not found. The API version may have changed.",
        429: "Rate limited. Wait 60 seconds before retrying.",
        500: "Coinglass server error. Retry in 1-2 minutes.",
        502: "Coinglass gateway error. Retry in 1-2 minutes.",
        503: "Coinglass service unavailable. Retry in 1-2 minutes.",
    }
    return suggestions.get(status, f"HTTP {status} error.")


def cg_request(endpoint, params=None, version="v4", timeout=30):
    """
    Make a Coinglass API request with structured error handling.

    Args:
        endpoint: API path (e.g. "api/futures/supported-coins"
                  or "funding" for v2)
        params: Query parameters dict
        version: "v2" or "v4" (default "v4")
        timeout: Request timeout in seconds

    Returns:
        Parsed response data (the "data" field from Coinglass response).

    Raises:
        CoinglassAPIKeyError: API key missing or rejected
        CoinglassRateLimitError: 429 rate limit
        CoinglassServerError: 5xx server error
        CoinglassError: Any other API error
    """
    api_key = _get_api_key()
    if not api_key:
        raise CoinglassAPIKeyError(
            "COINGLASS_API_KEY not set in environment",
            code="NO_API_KEY",
            suggestion="Set COINGLASS_API_KEY in your .env file."
        )

    if version == "v2":
        base_url = BASE_URL_V2
        headers = {"accept": "application/json", HEADER_KEY_V2: api_key}
    else:
        base_url = BASE_URL_V4
        headers = {"accept": "application/json", HEADER_KEY_V4: api_key}

    url = f"{base_url}/{endpoint}"

    def _plan_error(msg: str) -> CoinglassPlanError:
        return CoinglassPlanError(endpoint, msg)

    try:
        response = _do_get(
            url, params, headers, timeout
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, "status_code", None)
        body_msg = ""
        try:
            body_msg = str(e.response.json().get("msg", ""))[:120]
        except Exception:
            body_msg = str(getattr(e.response, "text", ""))[:120]
        suggestion = _suggestion_for_status(status)
        # Coinglass signals plan restrictions via 401 + "Upgrade plan" message
        if status == 401 and "upgrade" in body_msg.lower():
            raise _plan_error(body_msg) from e
        if status == 401:
            raise CoinglassAPIKeyError(
                f"HTTP 401 from Coinglass: {e}", code="HTTP_401",
                suggestion=suggestion
            ) from e
        if status == 429:
            raise CoinglassRateLimitError(
                f"Rate limited by Coinglass: {e}", code="HTTP_429",
                suggestion=suggestion
            ) from e
        if status and status >= 500:
            raise CoinglassServerError(
                f"Coinglass server error: {e}", code=f"HTTP_{status}",
                suggestion=suggestion
            ) from e
        raise CoinglassError(
            f"HTTP {status} from Coinglass: {e}",
            code=f"HTTP_{status}", suggestion=suggestion
        ) from e
    except requests.exceptions.ConnectionError as e:
        raise CoinglassError(
            f"Cannot connect to Coinglass: {e}",
            code="CONNECTION_ERROR",
            suggestion="Check network. Retry in 30 seconds."
        ) from e
    except requests.exceptions.Timeout as e:
        raise CoinglassError(
            f"Coinglass request timed out after {timeout}s",
            code="TIMEOUT",
            suggestion="Retry with a longer timeout or simpler query."
        ) from e
    except requests.exceptions.RequestException as e:
        raise CoinglassError(
            f"Request failed: {type(e).__name__}: {e}",
            code="REQUEST_ERROR",
            suggestion="Unexpected network error. Retry."
        ) from e

    # Parse JSON
    try:
        data = response.json()
    except (json.JSONDecodeError, ValueError) as e:
        raise CoinglassError(
            f"Invalid JSON from Coinglass: {e}",
            code="PARSE_ERROR",
            suggestion="API may be returning an error page. Try again later."
        ) from e

    # Check Coinglass response code
    if isinstance(data, dict):
        code = data.get("code")
        msg = str(data.get("msg", ""))
        if code is not None and str(code) != "0":
            # Some plan-restricted endpoints return HTTP 200 with
            # code 401 and an "Upgrade plan" message in the body
            if str(code) == "401" and "upgrade" in msg.lower():
                raise _plan_error(msg)
            raise CoinglassError(
                f"Coinglass API error [{code}]: {msg}",
                code=f"API_{code}",
                suggestion="Check parameters. Some endpoints "
                           "require specific symbols or exchanges."
            )
        # Unwrap standard response envelope
        if "data" in data:
            return data["data"]

    return data
