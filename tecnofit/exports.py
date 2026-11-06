"""
tecnofit exports — Tecnofit member lookup and entitlement checks.

Tecnofit's public API has exactly two endpoints (OpenAPI 3.0.0 on ReadMe.io):
a credential exchange and a ticket-gate member lookup. There is no schedule,
booking, check-in or payment endpoint — do not promise one.

Usage from a bash block:

    python3 - <<'EOF'
    import sys, json
    sys.path.insert(0, "/data/workspace/skills/tecnofit")
    from exports import tecnofit_check_credentials, tecnofit_entitlement

    print(json.dumps(tecnofit_check_credentials(), indent=2, ensure_ascii=False))
    print(json.dumps(tecnofit_entitlement(gate_token="…", member_id="…"), indent=2))
    EOF

Or via the platform loader:

    from core.skill_tools import _modules
    tecnofit = _modules["tecnofit"]
    tecnofit.tecnofit_member(gate_token="…", member_id="…")

Every function returns {"ok": True, "data": ...} or
{"ok": False, "status": ..., "error": ..., "hint": ...}.

Credentials (request_env_input, never pasted in chat):
    TECNOFIT_USER   tenant user
    TECNOFIT_PASS   tenant password
"""

import importlib.util
import os
import sys

__all__ = [
    "tecnofit_check_credentials",
    "tecnofit_auth",
    "tecnofit_member",
    "tecnofit_entitlement",
]

_here = os.path.dirname(os.path.abspath(__file__))


def _load(name, *parts):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_here, *parts))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_client = _load("_tecnofit_client", "client.py")
_member = _load("_tecnofit_member", "tools", "member.py")

tecnofit_auth = _client.auth
tecnofit_member = _member.member
tecnofit_entitlement = _member.entitlement
tecnofit_check_credentials = _member.check_credentials


if __name__ == "__main__":  # CLI for debugging: python3 exports.py <fn> [k=v ...]
    import json

    argv = sys.argv[1:]
    if not argv:
        print("usage: python3 exports.py <function> [key=value ...]")
        print("functions: " + ", ".join(__all__))
        raise SystemExit(1)

    fn = globals().get(argv[0])
    if fn is None or argv[0] not in __all__:
        raise SystemExit(f"unknown function {argv[0]!r}")

    kwargs = {}
    for pair in argv[1:]:
        key, _, value = pair.partition("=")
        if value.lower() in ("true", "false"):
            value = value.lower() == "true"
        kwargs[key] = value

    print(json.dumps(fn(**kwargs), indent=2, ensure_ascii=False, default=str))
