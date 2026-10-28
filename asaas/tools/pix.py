"""Asaas Pix — the QR code and the copy-and-paste string.

    GET /v3/payments/{id}/pixQrCode

The response is the whole artefact:

    encodedImage    base64 PNG of the QR — render or attach it
    payload         the "copia e cola" string — this is what you send in chat
    expirationDate  when the code dies

`payload` is the field that matters for a WhatsApp flow: it is a plain string a
customer can paste into their bank app. Contrast the card rail, whose artefact is
a hosted page that cannot be forwarded as text.

⚠️ Naming note: this is Asaas's own vocabulary. Angular Pay (the gateway NUMA
uses) returns the same three values renamed to `pix_qrcode`, `pix_copy_paste`
and `pix_expires_at`. Same data, one extra hop — see
`docs/integrations/asaas.md`.
"""

import os
import sys

try:  # loaded by exports.py
    from _asaas_client import call, err, ok
except ImportError:  # standalone: python3 tools/pix.py
    import importlib.util as _iu

    _spec = _iu.spec_from_file_location(
        "_asaas_client",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client.py"),
    )
    sys.modules["_asaas_client"] = _mod = _iu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    from _asaas_client import call, err, ok  # noqa: E402,F811


def pix_qr_code(payment_id):
    """The Pix QR + copy-and-paste for a charge.

    The charge must be `billingType: PIX` and must exist. A charge that is
    already paid still returns its (now useless) code, so check the status too
    if that matters.

    Returns `payload` ready to send, plus the expiry so you can tell the customer
    how long they have.
    """
    if not payment_id:
        return err(None, "pix_qr_code needs a payment id",
                   hint="create the charge first with create_charge(billing_type='PIX')")
    result = call("GET", f"/payments/{payment_id}/pixQrCode")
    if not result["ok"]:
        if result.get("status") == 400:
            result["hint"] = ("Asaas only serves a Pix QR for a charge whose "
                              "billingType is PIX. Check the charge's billing_type.")
        return result
    data = result["data"] or {}
    return ok({
        "payment_id": payment_id,
        "payload": (data or {}).get("payload"),
        "encoded_image": (data or {}).get("encodedImage"),
        "expiration_date": (data or {}).get("expirationDate"),
        "description": (data or {}).get("description"),
    })
