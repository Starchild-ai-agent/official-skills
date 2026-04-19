#!/usr/bin/env python3
"""
LunarCrush API Utilities

Shared utilities for LunarCrush API tools including:
- API request handling with authentication
- Rate limiting and error handling
- Response parsing
"""

import os
import time
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from core.http_client import proxied_get

# Load environment variables
load_dotenv()

# LunarCrush API base URL
LUNARCRUSH_API_BASE = "https://lunarcrush.com/api4"


def get_api_key() -> str:
    """Get LunarCrush API key from environment."""
    api_key = os.getenv("LUNARCRUSH_API_KEY")
    if not api_key:
        raise ValueError(
            "LUNARCRUSH_API_KEY environment variable is required. "
            "Get your API key from https://lunarcrush.com/developers"
        )
    return api_key


def make_request(
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    retries: int = 2,
    backoff_seconds: float = 1.2,
) -> Dict[str, Any]:
    """
    Make authenticated request to LunarCrush API.

    Args:
        endpoint: API endpoint path (e.g., "/public/coins/list/v2")
        params: Optional query parameters
        timeout: Request timeout in seconds

    Returns:
        Parsed JSON response

    Raises:
        ValueError: If API key is missing
        requests.RequestException: If request fails
    """
    api_key = get_api_key()

    url = f"{LUNARCRUSH_API_BASE}{endpoint}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }

    for attempt in range(retries + 1):
        try:
            response = proxied_get(
                url,
                headers=headers,
                params=params,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            if attempt < retries:
                time.sleep(backoff_seconds * (attempt + 1))
                continue
            raise requests.RequestException("Request timeout - LunarCrush API may be slow")
        except requests.exceptions.ConnectionError:
            if attempt < retries:
                time.sleep(backoff_seconds * (attempt + 1))
                continue
            raise requests.RequestException("Connection error - check internet connection")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise ValueError("Invalid LUNARCRUSH_API_KEY - check your API key")
            elif e.response.status_code == 429:
                if attempt < retries:
                    time.sleep(backoff_seconds * (attempt + 1))
                    continue
                raise requests.RequestException("Rate limit exceeded - please wait before retrying")
            raise requests.RequestException(f"API request failed: {e}")

    raise requests.RequestException("API request failed after retries")


def format_galaxy_score(score: Optional[float]) -> str:
    """
    Format Galaxy Score with interpretation.

    Galaxy Score (0-100):
    - 80-100: Exceptional momentum
    - 60-79: Strong engagement
    - 40-59: Moderate activity
    - 0-39: Low presence
    """
    if score is None:
        return "N/A"

    if score >= 80:
        return f"{score:.1f} (Exceptional)"
    elif score >= 60:
        return f"{score:.1f} (Strong)"
    elif score >= 40:
        return f"{score:.1f} (Moderate)"
    else:
        return f"{score:.1f} (Low)"


def format_alt_rank(rank: Optional[int], total: Optional[int] = None) -> str:
    """
    Format AltRank with interpretation.

    AltRank measures relative social performance vs other alts.
    Lower = better relative performance.
    """
    if rank is None:
        return "N/A"

    if total:
        return f"#{rank} of {total}"
    return f"#{rank}"


def normalize_symbol(symbol: str) -> str:
    """Normalize coin symbol for API requests."""
    return symbol.upper().strip()


def parse_time_series_bucket(bucket: str) -> str:
    """
    Validate and normalize time series bucket parameter.

    Valid buckets: hour, day, week
    """
    valid_buckets = ["hour", "day", "week"]
    bucket = bucket.lower().strip()

    if bucket not in valid_buckets:
        raise ValueError(f"Invalid bucket: {bucket}. Must be one of: {valid_buckets}")

    return bucket
