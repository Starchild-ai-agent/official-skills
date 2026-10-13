"""
Asaas skill — public function surface.

Every function returns the same envelope:
    {"ok": True,  "status": 200, "data": ...}
    {"ok": False, "status": 400, "error": "...", "hint": "..."}

Reads are safe. Writes are gated behind `confirm=True` and say so when it is
missing, so an agent can rehearse with a dry run before touching a real account.

    from core.skill_tools import _modules
    asaas = _modules["asaas"]
    asaas.asaas_charge_by_pix(...)
"""

import importlib.util
import os
import sys

__all__ = [
    # auth / environment
    "asaas_check_credentials", "asaas_environment",
    # customers
    "asaas_find_customers", "asaas_customer", "asaas_find_or_create_customer",
    "asaas_update_customer",
    # charges
    "asaas_charges", "asaas_charge", "asaas_charge_status", "asaas_create_charge",
    "asaas_delete_charge", "asaas_confirm_payment",
    # pix
    "asaas_pix_qr_code",
    # webhooks
    "asaas_webhooks", "asaas_create_webhook", "asaas_delete_webhook",
    # finance
    "asaas_balance", "asaas_statement",
    # workflows
    "asaas_charge_by_pix", "asaas_did_they_pay",
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


# Order matters: the tool modules import the client we register first.
_client = _load("_asaas_client", "client.py")
_customers = _load("_asaas_customers", "tools", "customers.py")
_charges = _load("_asaas_charges", "tools", "charges.py")
_pix = _load("_asaas_pix", "tools", "pix.py")
_webhooks = _load("_asaas_webhooks", "tools", "webhooks.py")
_finance = _load("_asaas_finance", "tools", "finance.py")
_workflows = _load("_asaas_workflows", "tools", "workflows.py")

# ── Auth / environment ───────────────────────────────────────────────────────

asaas_environment = _client.environment


def asaas_check_credentials():
    """Confirm the key works and report which environment it points at.

    Worth calling first: sandbox and production hold entirely separate data, so
    "the customer does not exist" usually means you are on the other one.
    """
    from _asaas_client import call, credentials, err, ok
    try:
        credentials()
    except Exception as exc:
        return err(None, str(exc))
    result = call("GET", "/finance/balance")
    if not result["ok"]:
        return result
    return ok({
        "environment": _client.environment(),
        "base_url": _client.base_url(),
        "balance": (result["data"] or {}).get("balance"),
    })


# ── Customers ────────────────────────────────────────────────────────────────

asaas_find_customers = _customers.find_customers
asaas_customer = _customers.customer
asaas_find_or_create_customer = _customers.find_or_create_customer
asaas_update_customer = _customers.update_customer

# ── Charges ──────────────────────────────────────────────────────────────────

asaas_charges = _charges.charges
asaas_charge = _charges.charge
asaas_charge_status = _charges.charge_status
asaas_create_charge = _charges.create_charge
asaas_delete_charge = _charges.delete_charge
asaas_confirm_payment = _charges.confirm_payment

# ── Pix ──────────────────────────────────────────────────────────────────────

asaas_pix_qr_code = _pix.pix_qr_code

# ── Webhooks ─────────────────────────────────────────────────────────────────

asaas_webhooks = _webhooks.webhooks
asaas_create_webhook = _webhooks.create_webhook
asaas_delete_webhook = _webhooks.delete_webhook

# ── Finance ──────────────────────────────────────────────────────────────────

asaas_balance = _finance.balance
asaas_statement = _finance.statement

# ── Workflows ────────────────────────────────────────────────────────────────

asaas_charge_by_pix = _workflows.charge_by_pix
asaas_did_they_pay = _workflows.did_they_pay


if __name__ == "__main__":  # CLI for debugging: python3 exports.py <fn> [k=v ...]
    import json

    fn_name = sys.argv[1] if len(sys.argv) > 1 else "asaas_check_credentials"
    fn = globals().get(fn_name)
    if not callable(fn):
        print(f"unknown function: {fn_name}")
        raise SystemExit(2)
    kwargs = {}
    for arg in sys.argv[2:]:
        if "=" in arg:
            key, value = arg.split("=", 1)
            kwargs[key] = value
    print(json.dumps(fn(**kwargs), indent=2, ensure_ascii=False, default=str))
