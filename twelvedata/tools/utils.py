"""
Shared utilities for Twelve Data tools.
"""

from typing import Optional
from .client import TwelveDataClient

# Singleton client instance
_client: Optional[TwelveDataClient] = None


def get_client() -> TwelveDataClient:
    """Get or create singleton client instance."""
    global _client
    if _client is None:
        _client = TwelveDataClient()
    return _client
