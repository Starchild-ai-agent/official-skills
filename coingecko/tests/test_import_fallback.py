"""Regression tests for the no-package-context import fallback.

Covers the P1/P2 review findings on the private-package fallback:
  1. Fallback must survive another skill having already claimed a generic
     top-level module name (LunarCrush ships coins.py, Polymarket ships
     search.py) — the original sys.path-based fallback broke here.
  2. Fallback must not mutate sys.path (no cross-skill pollution).
  3. Fallback must only trigger for the missing-package-context failure
     mode; a genuine dependency ImportError stays visible as-is.

Run: python -m pytest coingecko/tests/test_import_fallback.py -q
(from the repo root; requires only stdlib — core.* deps are stubbed)
"""
import importlib.util
import os
import sys
import types

import pytest

SKILL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
COINGECKO_PY = os.path.join(SKILL_DIR, "coingecko.py")


def _stub_core_modules():
    """Stub clawd-only deps so coingecko.py imports outside the agent."""
    core = types.ModuleType("core")
    core.__path__ = []
    tool = types.ModuleType("core.tool")

    class _Stub:
        pass

    tool.BaseTool = tool.ToolContext = tool.ToolResult = _Stub
    http_client = types.ModuleType("core.http_client")
    http_client.proxied_get = http_client.proxied_post = lambda *a, **k: None
    core.tool = tool
    core.http_client = http_client
    sys.modules.update({
        "core": core,
        "core.tool": tool,
        "core.http_client": http_client,
    })


def _load_without_package_context(mod_name="_cg_under_test"):
    """Load coingecko.py the way the platform does: file path, no parent
    package — the exact context where relative imports fail."""
    spec = importlib.util.spec_from_file_location(mod_name, COINGECKO_PY)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _clean_modules():
    """Isolate each test's sys.modules / sys.path mutations."""
    saved_modules = sys.modules.copy()
    saved_path = list(sys.path)
    _stub_core_modules()
    yield
    sys.modules.clear()
    sys.modules.update(saved_modules)
    sys.path[:] = saved_path


def test_fallback_loads_without_package_context():
    mod = _load_without_package_context()
    assert mod.COINGECKO_AVAILABLE is True
    assert callable(mod.get_coins_list)
    assert callable(mod.search)


def test_fallback_survives_conflicting_toplevel_module():
    """P1 repro: another skill already registered a top-level `coins` /
    `search` module. The private-package fallback must neither use nor
    clobber them."""
    fake_coins = types.ModuleType("coins")  # e.g. LunarCrush's coins.py
    fake_coins.MARKER = "lunarcrush"
    fake_search = types.ModuleType("search")  # e.g. Polymarket's search.py
    sys.modules["coins"] = fake_coins
    sys.modules["search"] = fake_search

    mod = _load_without_package_context()

    assert mod.COINGECKO_AVAILABLE is True
    # CoinGecko functions resolve despite the name collision
    assert callable(mod.get_coins_list)
    assert callable(mod.search)
    # The foreign modules are untouched
    assert sys.modules["coins"] is fake_coins
    assert sys.modules["search"] is fake_search
    assert not hasattr(fake_coins, "get_coins_list")


def test_fallback_does_not_pollute_sys_path():
    before = list(sys.path)
    mod = _load_without_package_context()
    assert mod.COINGECKO_AVAILABLE is True
    assert sys.path == before


def test_fallback_uses_private_namespace():
    mod = _load_without_package_context()
    assert mod.COINGECKO_AVAILABLE is True
    pkg_mods = [m for m in sys.modules
                if m.startswith("starchild_coingecko_tools")]
    assert "starchild_coingecko_tools" in pkg_mods
    assert "starchild_coingecko_tools.coins" in sys.modules


def test_genuine_dependency_error_is_not_masked():
    """P2: an ImportError that is NOT the missing-package-context case
    must skip the fallback and surface the original failure."""
    # Break a real dependency of the tool modules
    sys.modules.pop("core.http_client", None)
    sys.modules["core"].http_client = None

    class _Blocker:
        def find_module(self, name, path=None):
            return self if name == "core.http_client" else None

        def load_module(self, name):
            raise ImportError("No module named 'core.http_client'")

        def find_spec(self, name, path=None, target=None):
            if name == "core.http_client":
                raise ImportError("No module named 'core.http_client'")
            return None

    blocker = _Blocker()
    sys.meta_path.insert(0, blocker)
    try:
        mod = _load_without_package_context("_cg_dep_err")
        assert mod.COINGECKO_AVAILABLE is False
        # fallback namespace must NOT have been fully populated
        assert not hasattr(mod, "get_coins_list")
    finally:
        sys.meta_path.remove(blocker)
