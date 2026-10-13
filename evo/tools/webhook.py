"""EVO webhooks (POST /api/v1/webhook, GET /api/v2/webhook, DELETE ...).

Webhooks need a public HTTPS callback. `eventType` strings are EVO-defined and
only partially published (e.g. NewSale, CreateMember, AlterMember, NewInvoice);
"Webhook PRO" (CRM-driven events such as crm.automation.contract_due_date) is
gated to API Pro and configured in EVO's UI, not here.
"""

import os
import sys

try:  # loaded by exports.py
    from _evo_client import _call, err, ok
except ImportError:  # standalone: python3 tools/webhook.py
    import importlib.util as _iu

    _spec = _iu.spec_from_file_location(
        "_evo_client",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client.py"),
    )
    sys.modules["_evo_client"] = _mod = _iu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    from _evo_client import _call, err, ok  # noqa: E402,F811


def _headers_payload(headers):
    """Accept {"Authorization": "Bearer x"} or [{"name","value"}]; EVO wants nome/valor."""
    if not headers:
        return None
    if isinstance(headers, dict):
        return [{"nome": str(k), "valor": str(v)} for k, v in headers.items()]
    out = []
    for item in headers:
        if isinstance(item, dict):
            name = item.get("nome") or item.get("name")
            value = item.get("valor") or item.get("value")
            if name is not None:
                out.append({"nome": str(name), "valor": str(value if value is not None else "")})
    return out or None


def _filters_payload(filters):
    """Accept [{"filterType": .., "value": ..}] or [(type, value), ...]."""
    if not filters:
        return None
    out = []
    for item in filters:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            out.append({"filterType": item[0], "value": item[1]})
        elif isinstance(item, dict):
            out.append({"filterType": item.get("filterType") or item.get("type"),
                        "value": item.get("value")})
    return out or None


def webhooks():
    """List every webhook registered on this key (GET /api/v2/webhook)."""
    result = _call("GET", "/api/v2/webhook")
    if not result["ok"]:
        return result
    return ok(result["data"])


def webhook_create(event_type, url_callback, id_branch=None, headers=None, filters=None):
    """Register a webhook. `url_callback` must be HTTPS.

    Example: webhook_create("NewSale", "https://my.app/evo/hook",
                            headers={"Authorization": "Bearer s3cr3t"},
                            filters=[("SaleItemDescription", "Produto A")])
    """
    if not event_type or not url_callback:
        return err(None, "webhook_create needs event_type and url_callback")
    if not str(url_callback).lower().startswith("https://"):
        return err(None, "url_callback must be an https:// URL")
    body = {
        "idBranch": id_branch,
        "eventType": event_type,
        "urlCallback": url_callback,
        "headers": _headers_payload(headers),
        "filters": _filters_payload(filters),
    }
    result = _call("POST", "/api/v1/webhook", body=body)
    if not result["ok"]:
        return result
    return ok({"event_type": event_type, "url_callback": url_callback,
               "evo_result": result["data"]})


def webhook_delete(id_webhook):
    """Remove one webhook by its id (from webhooks())."""
    result = _call("DELETE", "/api/v1/webhook", params={"IdWebhook": id_webhook})
    if not result["ok"]:
        return result
    return ok({"id_webhook": id_webhook, "evo_result": result["data"]})