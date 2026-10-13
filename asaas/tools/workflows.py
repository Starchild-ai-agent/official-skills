"""Asaas workflows — the multi-step flows the agent actually needs.

`charge_by_pix` is the whole Pix sale in one call:

    ensure the payer exists -> create the charge -> read the QR

That middle step is the one that silently breaks. An Asaas charge points at a
**customer id**, and if the payer was never registered the charge cannot be
created. Behind a gateway that failure surfaces as a bare `not-authorized`; here
it surfaces as the field Asaas names.
"""

import os
import sys

try:  # loaded by exports.py
    from _asaas_client import _money, err, ok
    from _asaas_charges import charge_status as _charge_status, create_charge as _create
    from _asaas_customers import find_or_create_customer as _ensure_customer
    from _asaas_pix import pix_qr_code as _pix_qr
except ImportError:  # standalone: python3 tools/workflows.py
    import importlib.util as _iu

    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _load(name, *parts):
        spec = _iu.spec_from_file_location(name, os.path.join(_root, *parts))
        module = _iu.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    _load("_asaas_client", "client.py")
    _load("_asaas_customers", "tools", "customers.py")
    _load("_asaas_charges", "tools", "charges.py")
    _load("_asaas_pix", "tools", "pix.py")

    from _asaas_client import _money, err, ok  # noqa: E402,F811
    from _asaas_charges import charge_status as _charge_status, create_charge as _create  # noqa: E402,F811
    from _asaas_customers import find_or_create_customer as _ensure_customer  # noqa: E402,F811
    from _asaas_pix import pix_qr_code as _pix_qr  # noqa: E402,F811


def charge_by_pix(name, cpf_cnpj, value, email=None, mobile_phone=None,
                  external_reference=None, description=None, due_date=None,
                  confirm=False):
    """Charge a person by Pix and hand back the copy-and-paste string.

    Steps, each of which can fail on its own and reports why:

      1. `find_or_create_customer` — idempotent, keyed on CPF/CNPJ
      2. `create_charge` with `billingType: PIX`
      3. `pix_qr_code` — the artefact you send the customer

    `external_reference` is worth setting to your own member id: it is how you
    find the customer again next month without depending on Asaas's ids.

    Without `confirm=True` nothing is written and you get the plan instead.
    """
    if not confirm:
        return ok({
            "dry_run": True,
            "would_do": {
                "ensure_customer": {"name": name, "cpfCnpj": cpf_cnpj,
                                    "email": email,
                                    "externalReference": external_reference},
                "create_charge": {"value": _money(value), "billingType": "PIX",
                                  "dueDate": due_date or "today",
                                  "description": description},
                "read_pix_qr": True,
            },
            "hint": "re-run with confirm=True to execute",
        })

    who = _ensure_customer(name, cpf_cnpj, email=email, mobile_phone=mobile_phone,
                           external_reference=external_reference, confirm=True)
    if not who["ok"]:
        return who
    customer_id = (who["data"].get("customer") or {}).get("id")
    if not customer_id:
        return err(None, "Asaas returned a customer without an id",
                   detail=who.get("data"))

    made = _create(customer_id, value, due_date=due_date, billing_type="PIX",
                   description=description, external_reference=external_reference,
                   confirm=True)
    if not made["ok"]:
        return made
    created = made["data"]["charge"]
    payment_id = created.get("id")

    qr = _pix_qr(payment_id)
    if not qr["ok"]:
        return err(qr.get("status"),
                   "the charge exists but the Pix QR could not be read",
                   hint="the charge id is valid — retry pix_qr_code(payment_id) "
                        "rather than charging again",
                   payment_id=payment_id, customer_id=customer_id)

    return ok({
        "payment_id": payment_id,
        "customer_id": customer_id,
        "customer_created": who["data"].get("created"),
        "value": created.get("value"),
        "due_date": created.get("due_date"),
        "status": created.get("status"),
        "pix_payload": qr["data"].get("payload"),
        "pix_encoded_image": qr["data"].get("encoded_image"),
        "pix_expiration_date": qr["data"].get("expiration_date"),
        "invoice_url": created.get("invoice_url"),
        "next": ("Send `pix_payload` to the payer. Then poll "
                 f"charge_status('{payment_id}') for status in {('CONFIRMED', 'RECEIVED')}."),
    })


def did_they_pay(payment_id):
    """One-line answer to the only question that matters, plus what to do next."""
    result = _charge_status(payment_id)
    if not result["ok"]:
        return result
    data = result["data"]
    status = data.get("status")
    if data.get("settled"):
        nxt = "settled — book the sale"
    elif status in ("PENDING", "AWAITING_RISK_ANALYSIS"):
        nxt = "still open — keep waiting, do not re-charge"
    elif status == "OVERDUE":
        nxt = "expired — send a fresh charge if the customer still wants it"
    elif status in ("REFUNDED", "REFUND_REQUESTED", "REFUND_IN_PROGRESS"):
        nxt = "reversed — the money is not ours"
    elif status and status.startswith("CHARGEBACK"):
        nxt = "disputed — needs a human"
    else:
        nxt = "unrecognised status — read the raw charge for detail"
    return ok({"payment_id": payment_id, "status": status,
               "status_label": data.get("status_label"),
               "settled": data.get("settled"), "next": nxt})
