"""EVO configuration: branch settings and branch groups.

`configuration()` doubles as the credential smoke test — it is the cheapest
endpoint that proves EVO_DNS + EVO_API_TOKEN work.
"""

import os
import sys

try:  # loaded by exports.py
    from _evo_client import _call, err, ok
except ImportError:  # standalone: python3 tools/config.py
    import importlib.util as _iu

    _spec = _iu.spec_from_file_location(
        "_evo_client",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client.py"),
    )
    sys.modules["_evo_client"] = _mod = _iu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    from _evo_client import _call, err, ok  # noqa: E402,F811


def configuration():
    """Branch configuration for the key's branch (GET /api/v1/configuration)."""
    result = _call("GET", "/api/v1/configuration")
    if not result["ok"]:
        return result
    return ok(result["data"])


def branches():
    """Branch groups visible to this key (GET /api/v1/configuration/group-branches).

    Multi-branch (ADM) keys use these ids as `id_branch` elsewhere.
    """
    result = _call("GET", "/api/v1/configuration/group-branches")
    if not result["ok"]:
        return result
    return ok(result["data"])


def check_credentials():
    """Verify EVO_DNS + EVO_API_TOKEN and report what the key can reach."""
    config = configuration()
    if not config["ok"]:
        return config
    branch = config["data"] if isinstance(config["data"], dict) else {}
    groups = branches()
    return ok({
        "credentials": "ok",
        "branch_id": branch.get("idBranch") or branch.get("id"),
        "branch_name": branch.get("name") or branch.get("nome"),
        "branch_groups": groups["data"] if groups["ok"] else None,
        "raw": config["data"],
    })