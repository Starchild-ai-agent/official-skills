"""
evo exports — W12 / ABC Evo (EVO) gym management API.

Booking, members, plans, check-ins and webhooks for EVO gyms, via EVO's public
REST API (Basic auth with the gym DNS + an EVO-issued token).

Usage from a bash block:

    python3 - <<'EOF'
    import sys, json
    sys.path.insert(0, "/data/workspace/skills/evo")
    from exports import evo_schedule, evo_book_by_name

    print(json.dumps(evo_schedule(date="today"), indent=2)[:2000])
    print(evo_book_by_name(member="Ana Silva", activity="Pilates",
                           date="tomorrow", time="19:00"))
    EOF

Or via the platform loader (hyphenated skill names need _modules):

    from core.skill_tools import _modules
    evo = _modules["evo"]
    evo.evo_spots(id_configuration=1234, date="2026-10-09")

Every function returns {"ok": True, "data": ...} or
{"ok": False, "status": ..., "error": ..., "hint": ...}.

Credentials (request_env_input, never pasted in chat):
    EVO_DNS        gym DNS used to sign into EVO
    EVO_API_TOKEN  token from Configuracoes > Integracoes > EVO > Tokens
"""

import importlib.util
import os
import sys

__all__ = [
    # read
    "evo_check_credentials", "evo_configuration", "evo_branches",
    "evo_find_members", "evo_resolve_member", "evo_member",
    "evo_member_services", "evo_membership_plans", "evo_member_memberships",
    "evo_schedule", "evo_find_session", "evo_session_detail", "evo_spots",
    "evo_my_bookings", "evo_member_sessions",
    "evo_entries", "evo_aggregator_checkins", "evo_turnstiles", "evo_api_usage",
    # write
    "evo_book", "evo_book_by_name", "evo_cancel", "evo_set_attendance",
    "evo_authorize_entry",
    "evo_webhooks", "evo_webhook_create", "evo_webhook_delete",
]

_here = os.path.dirname(os.path.abspath(__file__))


def _load(name, *parts):
    """Load a sibling module by path, registered so siblings can import it."""
    path = os.path.join(_here, *parts)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Order matters: booking.py imports the members/schedule modules we register here.
_client = _load("_evo_client", "client.py")
_config = _load("_evo_config", "tools", "config.py")
_members = _load("_evo_members", "tools", "members.py")
_schedule = _load("_evo_schedule", "tools", "schedule.py")
_booking = _load("_evo_booking", "tools", "booking.py")
_access = _load("_evo_access", "tools", "access.py")
_webhook = _load("_evo_webhook", "tools", "webhook.py")

# ── Configuration / credentials ───────────────────────────────────────────────
evo_check_credentials = _config.check_credentials
evo_configuration = _config.configuration
evo_branches = _config.branches

# ── Members, services, plans ─────────────────────────────────────────────────
evo_find_members = _members.find_members
evo_resolve_member = _members.resolve_member
evo_member = _members.member
evo_member_services = _members.member_services
evo_membership_plans = _members.membership_plans
evo_member_memberships = _members.member_memberships

# ── Schedule ─────────────────────────────────────────────────────────────────
evo_schedule = _schedule.schedule
evo_find_session = _schedule.find_session
evo_session_detail = _schedule.session_detail
evo_spots = _schedule.spots

# ── Booking ──────────────────────────────────────────────────────────────────
evo_my_bookings = _booking.my_bookings
evo_member_sessions = _booking.member_sessions
evo_book = _booking.book
evo_book_by_name = _booking.book_by_name
evo_cancel = _booking.cancel
evo_set_attendance = _booking.set_attendance

# ── Check-ins / access / usage ───────────────────────────────────────────────
evo_entries = _access.entries
evo_aggregator_checkins = _access.aggregator_checkins
evo_turnstiles = _access.turnstiles
evo_authorize_entry = _access.authorize_entry
evo_api_usage = _access.api_usage

# ── Webhooks ─────────────────────────────────────────────────────────────────
evo_webhooks = _webhook.webhooks
evo_webhook_create = _webhook.webhook_create
evo_webhook_delete = _webhook.webhook_delete


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
        elif value.isdigit():
            value = int(value)
        kwargs[key] = value

    print(json.dumps(fn(**kwargs), indent=2, ensure_ascii=False, default=str))