"""Asaas customers — the payer record a charge points at.

Why this module exists first: an Asaas charge references a **customer id**, and
Asaas will not invent one. If the payer is not registered, the charge fails —
and on a gateway that proxies Asaas, that failure arrives as an opaque
`not-authorized` or a `404`. Creating the customer is the step that was missing.

Required to create one, and nothing else:

    name, cpfCnpj

`cpfCnpj` is the whole reason a member record must be complete before it can be
charged. There is no way around it.

Verified filters on GET /v3/customers:
    name, email, cpfCnpj, groupName, externalReference   (offset, limit)
"""

import os
import sys

try:  # loaded by exports.py
    from _asaas_client import call, digits, err, ok
except ImportError:  # standalone: python3 tools/customers.py
    import importlib.util as _iu

    _spec = _iu.spec_from_file_location(
        "_asaas_client",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client.py"),
    )
    sys.modules["_asaas_client"] = _mod = _iu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    from _asaas_client import call, digits, err, ok  # noqa: E402,F811


def _normalize(row):
    if not isinstance(row, dict):
        return row
    return {
        "id": row.get("id"),
        "name": row.get("name"),
        "email": row.get("email"),
        "cpf_cnpj": row.get("cpfCnpj"),
        "phone": row.get("phone"),
        "mobile_phone": row.get("mobilePhone"),
        "external_reference": row.get("externalReference"),
        "city": row.get("city"),
        "state": row.get("state"),
        "postal_code": row.get("postalCode"),
        "deleted": row.get("deleted"),
        "notification_disabled": row.get("notificationDisabled"),
    }


def find_customers(name=None, email=None, cpf_cnpj=None, external_reference=None,
                   take=50, skip=0):
    """Search customers. Any combination of the four filters works.

    `external_reference` is the one to prefer when the caller has its own id for
    the person — it is the only filter that is guaranteed unique and stable.
    """
    result = call("GET", "/customers", params={
        "name": name,
        "email": email,
        "cpfCnpj": digits(cpf_cnpj) or None,
        "externalReference": external_reference,
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
        "customers": [_normalize(r) for r in (rows or [])],
    })


def customer(customer_id):
    """One customer by its Asaas id."""
    result = call("GET", f"/customers/{customer_id}")
    if not result["ok"]:
        return result
    return ok(_normalize(result["data"]))


def find_or_create_customer(name, cpf_cnpj, email=None, mobile_phone=None,
                            external_reference=None, confirm=False):
    """Get the Asaas customer for this CPF/CNPJ, creating it if absent.

    This is the idempotent entry point — call it before charging and you never
    hit the "customer not found" wall. Lookup is by `cpfCnpj`, because that is
    the field Asaas enforces as unique.

    Without `confirm=True` it only reports what it found or would create.
    """
    doc = digits(cpf_cnpj)
    if not doc:
        return err(None, "find_or_create_customer needs a CPF/CNPJ",
                   hint="Asaas requires cpfCnpj on every customer. Fix the member "
                        "record first — there is no way around it.")
    if not name:
        return err(None, "find_or_create_customer needs a name")

    found = find_customers(cpf_cnpj=doc, take=5)
    if not found["ok"]:
        return found
    existing = found["data"]["customers"]
    live = [c for c in existing if not c.get("deleted")]
    if live:
        return ok({"created": False, "customer": live[0]})

    if not confirm:
        return ok({
            "created": False,
            "dry_run": True,
            "would_create": {"name": name, "cpfCnpj": doc, "email": email,
                             "mobilePhone": digits(mobile_phone) or None,
                             "externalReference": external_reference},
            "hint": "re-run with confirm=True to create it",
        })

    body = {"name": name, "cpfCnpj": doc}
    if email:
        body["email"] = email
    if mobile_phone:
        body["mobilePhone"] = digits(mobile_phone)
    if external_reference:
        body["externalReference"] = str(external_reference)

    created = call("POST", "/customers", body=body)
    if not created["ok"]:
        return created
    return ok({"created": True, "customer": _normalize(created["data"])})


def update_customer(customer_id, email=None, mobile_phone=None, external_reference=None,
                    notification_disabled=None, confirm=False):
    """Update the fields we care about. Only what you pass is sent."""
    if not confirm:
        return err(None, "update_customer is a write and requires confirm=True",
                   hint="it mutates a real payer record")
    body = {}
    if email is not None:
        body["email"] = email
    if mobile_phone is not None:
        body["mobilePhone"] = digits(mobile_phone)
    if external_reference is not None:
        body["externalReference"] = str(external_reference)
    if notification_disabled is not None:
        body["notificationDisabled"] = bool(notification_disabled)
    if not body:
        return err(None, "update_customer got nothing to change")
    result = call("PUT", f"/customers/{customer_id}", body=body)
    if not result["ok"]:
        return result
    return ok(_normalize(result["data"]))
