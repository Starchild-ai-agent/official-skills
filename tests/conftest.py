"""
Shared test configuration for coinglass skill tests.

Stubs out core.http_client before any coinglass modules are imported,
ensuring consistent mock behavior across all test files.
"""
import sys
from types import ModuleType
from unittest.mock import MagicMock

# Only stub if not already stubbed
if "core" not in sys.modules:
    core_mod = ModuleType("core")
    sys.modules["core"] = core_mod

if "core.http_client" not in sys.modules:
    http_mod = ModuleType("core.http_client")
    http_mod.proxied_get = MagicMock()
    sys.modules["core.http_client"] = http_mod

if "core.tool" not in sys.modules:
    sys.modules["core.tool"] = ModuleType("core.tool")

# Ensure the project root and patches dir are on the path
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

PATCHES_DIR = os.path.join(PROJECT_ROOT, "patches")
if PATCHES_DIR not in sys.path:
    sys.path.insert(0, PATCHES_DIR)
