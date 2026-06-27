"""
Across Bridge skill exports — for use in task scripts via core.skill_tools.

Usage:
    from core.skill_tools import across
    q = across.bridge_quote(from_chain="base", to_chain="arbitrum",
                            token="USDC", amount=1, wallet="0x...")
    r = across.bridge_execute(from_chain="base", to_chain="arbitrum",
                              token="USDC", amount=1, wallet="0x...")
    s = across.bridge_status(origin_chain="base", deposit_tx_hash="0x...")
"""

# Load the core module from scripts/ and re-export its public functions.
import os, importlib.util

_here = os.path.dirname(__file__)
_mod_path = os.path.join(_here, "scripts", "across.py")
_spec = importlib.util.spec_from_file_location("_across_core", _mod_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

bridge_quote = _mod.bridge_quote
bridge_execute = _mod.bridge_execute
bridge_status = _mod.bridge_status

# Convenience: expose chain/token registries for downstream scripts
CHAIN_IDS = _mod.CHAIN_IDS
TOKENS = _mod.TOKENS
