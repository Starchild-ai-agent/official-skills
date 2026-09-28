"""
static-egress exports — for use in task scripts via core.skill_tools.

Usage:
    from core.skill_tools import _modules
    egress = _modules["static-egress"]
    egress.enable_egress(["db-prod.abc123.us-east-1.rds.amazonaws.com:5432"])

The CLI scripts under scripts/ are the primary interface (SKILL.md); these
functions exist so another skill can wire the egress in-process. They need the
platform's CONTAINER_JWT, so they only work inside the Starchild container.
"""
import importlib.util
import os

_here = os.path.dirname(os.path.abspath(__file__))


def _load(name: str, filename: str):
    path = os.path.join(_here, "scripts", filename)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_api = _load("_static_egress_api", "api.py")

enable_egress = _api.enable_egress
egress_status = _api.egress_status
verify_egress = _api.verify_egress
disable_egress = _api.disable_egress