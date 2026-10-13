"""Asaas charges (`cobranças`) — create, read, and read the real status.

A charge is created against a **customer id**, never a raw CPF, and needs:

    customer, billingType, value, dueDate

`billingType` decides the rail: PIX, BOLETO, CREDIT_CARD, or UNDEFINED to let the
payer choose on the checkout page. For Pix you then read the QR from
`pix_qr_code()` — that is where the copy-and-paste string lives.

The status is a genuine state machine, unlike the single `not-authorized` a
payment gateway tends to collapse everything into. Use `charge_status()` when you
need to know *why* something did not settle.

Verified filters on GET /v3/payments:
    customer, billingType, status, subscription, installment, externalReference,
    paymentDate, dateCreated[ge|le], dueDate[ge|le], paymentDate[ge|le]
    (offset, limit)
"""

import os
import sys

try:  # loaded by exports.py
    from _asaas_client import (BILLING_TYPES, SETTLED_STATUS, _date_str, _money,
                               _status_label, call, digits, err, ok)
except ImportError:  # standalone: python3 tools/charges.py
    import importlib.util as _iu

    _spec = _iu.spec_from_file_location(
        "_asaas_client",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client.py"),
    )
    sys.modules["_asaas_client"] = _mod = _iu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    from _asaas_client import (  # noqa: E402,F811
        BILLING_TYPES, SETTLED_STATUS, _date_str, _money, _status_label,
        call, digits, err, ok,
    )


def _normalize(row):
    if not isinstance(row, dict):
        return row
    return {
        "id": row.get("id"),
        "customer": row.get("customer"),
        "status": row.get("status"),
        "status_label": _status_label(row.get("status")),
        "settled": row.get("status") in SETTLED_STATUS,
        "billing_type": row.get("billingType"),
        "value": _money(row.get("value")),
        "net_value": _money(row.get("netValue")),
        "due_date": row.get("dueDate"),
        "payment_date": row.get("paymentDate"),
        "client_payment_date": row.get("clientPaymentDate"),
        "invoice_url": row.get("invoiceUrl"),
        "bank_slip_url": row.get("bankSlipUrl"),
        "description": row.get("description"),
        "external_reference": row.get("externalReference"),
        "installment_count": row.get("installmentCount"),
        "deleted": row.get("deleted"),
    }


def charges(customer=None, status=None, billing_type=None, external_reference=None,
            due_date_from=None, due_date_to=None, take=50, skip=0):
    """List charges. `customer` is the Asaas customer id, not a CPF."""
    if billing_type and billing_type.upper() not in BILLING_TYPES + ("DEBIT_CARD", "TRANSFER", "DEPOSIT"):
        return err(None, f"unknown billing_type {billing_type!r}",
                   hint="one of: " + ", ".join(BILLING_TYPES))
    result = call("GET", "/payments", params={
        "customer": customer,
        "status": status.upper() if status else None,
        "billingType": billing_type.upper() if billing_type else None,
        "externalReference": external_reference,
        "dueDate[ge]": _date_str(due_date_from),
        "dueDate[le]": _date_str(due_date_to),
        "limit": min(int(take or 50), 100),
        "offset": int(skip or 0),
    })
    if not result["ok"]:
        return result
    data = result["data"] or {}
    rows = data.get("data") if isinstance(data, dict) else None
    return ok({
        "total": (data or {}).get("totalCount"),
        "has_more": (data or {}).get("hasMore"),
        "charges": [_normalize(r) for r in (rows or [])],
    })


def charge(payment_id):
    """One charge in full."""
    result = call("GET", f"/payments/{payment_id}")
    if not result["ok"]:
        return result
    return ok(_normalize(result["data"]))


def charge_status(payment_id):
    """Just the status — cheap, and it is the question you actually have.

    `settled` is the machine-readable answer; `status_label` is for a human.
    """
    result = call("GET", f"/payments/{payment_id}/status")
    if not result["ok"]:
        return result
    data = result["data"] or {}
    status = data.get("status") if isinstance(data, dict) else data
    return ok({
        "payment_id": payment_id,
        "status": status,
        "status_label": _status_label(status),
        "settled": status in SETTLED_STATUS,
    })


def create_charge(customer, value, due_date=None, billing_type="PIX",
                  description=None, external_reference=None, confirm=False):
    """Create a charge. `customer` is the Asaas customer id.

    `due_date` defaults to today, which is what a Pix charge almost always wants
    — Pix settles immediately, so the due date is bookkeeping, not a deadline.
    For BOLETO it matters: Asaas rejects a due date in the past.

    Returns the charge; for Pix, follow with `pix_qr_code(charge["id"])`.
    """
    if not customer:
        return err(None, "create_charge needs a customer id",
                   hint="Asaas charges reference a customer id. Create one with "
                        "find_or_create_customer() first.")
    kind = (billing_type or "PIX").upper()
    if kind not in BILLING_TYPES:
        return err(None, f"unknown billing_type {billing_type!r}",
                   hint="one of: " + ", ".join(BILLING_TYPES))
    amount = _money(value)
    if amount is None or amount <= 0:
        return err(None, "create_charge needs a positive value")

    when = _date_str(due_date) or _date_str("today")
    body = {"customer": customer, "billingType": kind, "value": amount,
            "dueDate": when}
    if description:
        body["description"] = description
    if external_reference:
        body["externalReference"] = str(external_reference)

    if not confirm:
        return ok({"dry_run": True, "would_create": body,
                   "hint": "re-run with confirm=True to create the charge"})

    result = call("POST", "/payments", body=body)
    if not result["ok"]:
        return result
    return ok({"created": True, "charge": _normalize(result["data"])})


def delete_charge(payment_id, confirm=False):
    """Delete a charge. Asaas keeps it restorable for a while."""
    if not confirm:
        return err(None, "delete_charge is a write and requires confirm=True")
    result = call("DELETE", f"/payments/{payment_id}")
    if not result["ok"]:
        return result
    data = result["data"] or {}
    return ok({"deleted": (data or {}).get("deleted", True),
               "payment_id": payment_id})
