"""
angulare exports — Angular e-Commerce (Angulare) gym/studio management API.

Class schedule, member attendance and check-ins, first-experience detection,
sales orders / payment status, and the credit-card payment link.

Angulare publishes no developer documentation; every endpoint here was
reverse-engineered from their dashboard SPA and verified against production.
Read `references/api-reference.md` before trusting a filter — unsupported query
params are silently ignored.

Usage from a bash block:

    python3 - <<'EOF'
    import sys, json
    sys.path.insert(0, "/data/workspace/skills/angulare")
    from exports import angulare_check_credentials, angulare_followup_candidates

    print(json.dumps(angulare_check_credentials(), indent=2, ensure_ascii=False))
    print(json.dumps(angulare_followup_candidates(hours_after=2), indent=2)[:1500])
    EOF

Or via the platform loader:

    from core.skill_tools import _modules
    angulare = _modules["angulare"]
    angulare.angulare_payment_status(user_id=2200)

Every function returns {"ok": True, "data": ...} or
{"ok": False, "status": ..., "error": ..., "hint": ...}.

Credentials (request_env_input, never pasted in chat):
    ANGULARE_EMAIL     manager login e-mail
    ANGULARE_PASSWORD  manager password
    ANGULARE_TENANT    tenant code (find it with angulare_discover_tenants)
"""

import importlib.util
import os
import sys

__all__ = [
    # auth / tenant
    "angulare_check_credentials", "angulare_discover_tenants", "angulare_tenant_settings",
    # members
    "angulare_find_members", "angulare_resolve_member", "angulare_member",
    "angulare_quick_register_member",
    # schedule
    "angulare_sessions", "angulare_session", "angulare_session_roster", "angulare_find_session",
    # attendance / check-ins
    "angulare_attendance", "angulare_first_experience_checkins", "angulare_followup_candidates",
    "angulare_member_attendance", "angulare_aggregator_checkins", "angulare_instructor_stats",
    # catalog
    "angulare_products", "angulare_categories", "angulare_payment_methods", "angulare_reference_data",
    # payments
    "angulare_orders", "angulare_payment_status", "angulare_checkouts", "angulare_checkout",
    "angulare_current_checkout",
    # writes
    "angulare_checkout_add_product", "angulare_checkout_remove_line",
    "angulare_checkout_set_payment_method", "angulare_checkout_create_payment",
    "angulare_checkout_share",
    "angulare_send_payment_link",
    "angulare_pix_charge",
]

_here = os.path.dirname(os.path.abspath(__file__))


def _load(name, *parts):
    """Load a sibling module by path, registered so siblings can import it."""
    spec = importlib.util.spec_from_file_location(name, os.path.join(_here, *parts))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Order matters: the tool modules import the client we register first.
_client = _load("_angulare_client", "client.py")
_auth = _load("_angulare_auth", "tools", "auth.py")
_members = _load("_angulare_members", "tools", "members.py")
_schedule = _load("_angulare_schedule", "tools", "schedule.py")
_attendance = _load("_angulare_attendance", "tools", "attendance.py")
_catalog = _load("_angulare_catalog", "tools", "catalog.py")
_payments = _load("_angulare_payments", "tools", "payments.py")
_workflows = _load("_angulare_workflows", "tools", "workflows.py")

# ── Auth / tenant ────────────────────────────────────────────────────────────
angulare_check_credentials = _auth.check_credentials
angulare_discover_tenants = _members.discover_tenants
angulare_tenant_settings = _members.tenant_settings

# ── Members ──────────────────────────────────────────────────────────────────
angulare_find_members = _members.find_members
angulare_resolve_member = _members.resolve_member
angulare_member = _members.member
angulare_quick_register_member = _members.quick_register_member

# ── Schedule ─────────────────────────────────────────────────────────────────
angulare_sessions = _schedule.sessions
angulare_session = _schedule.session
angulare_session_roster = _schedule.session_roster
angulare_find_session = _schedule.find_session

# ── Attendance / check-ins ───────────────────────────────────────────────────
angulare_attendance = _attendance.attendance
angulare_first_experience_checkins = _attendance.first_experience_checkins
angulare_followup_candidates = _attendance.followup_candidates
angulare_member_attendance = _attendance.member_attendance
angulare_aggregator_checkins = _attendance.aggregator_checkins
angulare_instructor_stats = _attendance.instructor_stats

# ── Catalog ──────────────────────────────────────────────────────────────────
angulare_products = _catalog.products
angulare_categories = _catalog.categories
angulare_payment_methods = _catalog.payment_methods
angulare_reference_data = _catalog.reference_data

# ── Payments ─────────────────────────────────────────────────────────────────
angulare_orders = _payments.orders
angulare_payment_status = _payments.payment_status
angulare_checkouts = _payments.checkouts
angulare_checkout = _payments.checkout
angulare_current_checkout = _payments.current_checkout

# ── Writes (gated) ───────────────────────────────────────────────────────────
angulare_checkout_add_product = _payments.checkout_add_product
angulare_checkout_remove_line = _payments.checkout_remove_line
angulare_checkout_set_payment_method = _payments.checkout_set_payment_method
angulare_checkout_create_payment = _payments.checkout_create_payment
angulare_checkout_share = _payments.checkout_share
angulare_pix_charge = _payments.pix_charge

# ── Workflows (composed flows) ───────────────────────────────────────────────
angulare_send_payment_link = _workflows.send_payment_link


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
        elif value.lstrip("-").isdigit():
            value = int(value)
        kwargs[key] = value

    print(json.dumps(fn(**kwargs), indent=2, ensure_ascii=False, default=str))
