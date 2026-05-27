"""
Polymarket Skill v5.0.3 — Script-first Unified Entry

Primary interface is scripts/ via bash + wallet_sign_typed_data.
No Python tool wrappers are registered.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


def register(api) -> List[str]:
    logger.info("Polymarket loaded in script-first mode (no registered Python tools)")
    return []


EXTENSION_INFO = {
    "name": "polymarket",
    "version": "5.0.3",
    "description": "Polymarket prediction markets — script-first unified entry (search/status/auth/prepare/post/cancel/close)",
    "tools": [],
    "env_vars": [
        "POLY_API_KEY",
        "POLY_SECRET",
        "POLY_PASSPHRASE",
        "POLY_WALLET",
    ],
}
