"""
TaAPI Extension - Technical Analysis Indicators

Provides technical analysis indicators including:
- RSI, MACD, Bollinger Bands
- Support/Resistance levels
- 200+ pre-calculated indicators

Environment Variables Required:
- TAAPI_API_KEY: TaAPI.io API key

Usage:
    This extension is auto-loaded by the ExtensionLoader.
    Tools are available to agents configured with these tools in agents.yaml.
"""
import os
import sys
import logging
from typing import List

try:
    from core.tool import ToolRegistry
except Exception:
    ToolRegistry = None  # Standalone script usage

logger = logging.getLogger(__name__)

# Add local tools directory to path for imports
TOOLS_DIR = os.path.join(os.path.dirname(__file__), 'tools')
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)


def register(api) -> List[str]:
    """
    Extension entry point - register all TaAPI tools.

    Args:
        api: ExtensionApi instance with registry and config

    Returns:
        List of registered tool names
    """
    registered = []

    try:
        from .taapi import IndicatorTool, SupportResistanceTool
        api.register_tool(IndicatorTool())
        api.register_tool(SupportResistanceTool())
        registered.extend(["indicator", "support_resistance"])
        logger.info("Registered TaAPI tools (2 tools)")
    except Exception as e:
        logger.warning(f"Failed to load TaAPI tools: {e}")

    return registered


# Extension metadata
EXTENSION_INFO = {
    "name": "taapi",
    "version": "1.0.0",
    "description": "TaAPI technical analysis indicators",
    "tools": [
        "indicator",
        "support_resistance",
    ],
    "env_vars": [
        "TAAPI_API_KEY",
    ],
}
