"""Shared utilities for Coinglass tools."""
import os
from typing import Optional


def get_api_key() -> Optional[str]:
    """Get Coinglass API key from environment."""
    return os.getenv("COINGLASS_API_KEY")
