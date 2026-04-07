"""
Birdeye skill exports — tool names match SKILL.md frontmatter.

Usage in task scripts:
    from core.skill_tools import birdeye
    data = birdeye.birdeye_token_overview(address="So11...", chain="solana")
"""
import importlib.util
import os

_base = os.path.join(os.path.dirname(__file__), "tools")


def _load_func(subpath, func_name):
    full_path = os.path.join(_base, subpath)
    spec = importlib.util.spec_from_file_location(f"_birdeye_{func_name}", full_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, func_name)


birdeye_token_security = _load_func("token/security.py", "get_token_security")
birdeye_token_overview = _load_func("token/overview.py", "get_token_overview")
birdeye_wallet_networth = _load_func("wallet/networth.py", "get_wallet_networth")
