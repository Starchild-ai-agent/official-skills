"""Asaas webhooks — subscribe a URL to payment events.

Creating one requires **all seven** of:

    name, url, email, interrupted, enabled, events, sendType

`email` is where Asaas writes when the endpoint starts failing, and `interrupted`
is its own circuit breaker — Asaas disables a webhook that keeps erroring and
tells that address. Registering a webhook without a monitored mailbox is how you
silently stop receiving payment confirmations.

`sendType`:
    SEQUENTIALLY      in order — safer when order matters, slower
    NON_SEQUENTIALLY  parallel — faster, events can arrive out of order

Asaas exposes **112 events**. `WEBHOOK_EVENTS_CORE` in the client is the small
set that actually moves a sale; pass `events` explicitly for anything else.
"""

import os
import sys

try:  # loaded by exports.py
    from _asaas_client import (WEBHOOK_EVENTS_CORE, WEBHOOK_SEND_TYPES, call, err, ok)
except ImportError:  # standalone: python3 tools/webhooks.py
    import importlib.util as _iu

    _spec = _iu.spec_from_file_location(
        "_asaas_client",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client.py"),
    )
    sys.modules["_asaas_client"] = _mod = _iu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    from _asaas_client import (  # noqa: E402,F811
        WEBHOOK_EVENTS_CORE, WEBHOOK_SEND_TYPES, call, err, ok,
    )


def _normalize(row):
    if not isinstance(row, dict):
        return row
    return {
        "id": row.get("id"),
        "name": row.get("name"),
        "url": row.get("url"),
        "email": row.get("email"),
        "enabled": row.get("enabled"),
        "interrupted": row.get("interrupted"),
        "send_type": row.get("sendType"),
        "events": row.get("events") or [],
        "has_auth_token": bool(row.get("authToken")),
    }


def webhooks():
    """List the webhooks registered on this account."""
    result = call("GET", "/webhooks", params={"limit": 100})
    if not result["ok"]:
        return result
    data = result["data"] or {}
    rows = data.get("data") if isinstance(data, dict) else None
    return ok({
        "total": (data or {}).get("totalCount"),
        "webhooks": [_normalize(r) for r in (rows or [])],
    })


def create_webhook(name, url, email, events=None, send_type="SEQUENTIALLY",
                   auth_token=None, enabled=True, interrupted=False, confirm=False):
    """Register a webhook.

    `events` defaults to `WEBHOOK_EVENTS_CORE` — created/confirmed/received plus
    the failure paths. Pass the full list when you need more.
    """
    chosen = list(events) if events else list(WEBHOOK_EVENTS_CORE)
    kind = (send_type or "SEQUENTIALLY").upper()
    if kind not in WEBHOOK_SEND_TYPES:
        return err(None, f"unknown send_type {send_type!r}",
                   hint="one of: " + ", ".join(WEBHOOK_SEND_TYPES))
    for field, value in (("name", name), ("url", url), ("email", email)):
        if not value:
            return err(None, f"create_webhook needs {field}",
                       hint="Asaas requires name, url and email — the address is where "
                            "it reports a failing endpoint.")

    body = {
        "name": name,
        "url": url,
        "email": email,
        "interrupted": bool(interrupted),
        "enabled": bool(enabled),
        "events": chosen,
        "sendType": kind,
    }
    if auth_token:
        body["authToken"] = auth_token

    if not confirm:
        return ok({"dry_run": True, "would_create": body,
                   "hint": "re-run with confirm=True to register it"})

    result = call("POST", "/webhooks", body=body)
    if not result["ok"]:
        return result
    return ok({"created": True, "webhook": _normalize(result["data"])})


def delete_webhook(webhook_id, confirm=False):
    """Remove a webhook. Payment confirmations stop arriving immediately."""
    if not confirm:
        return err(None, "delete_webhook is a write and requires confirm=True",
                   hint="once removed, Asaas stops notifying that URL")
    result = call("DELETE", f"/webhooks/{webhook_id}")
    if not result["ok"]:
        return result
    data = result["data"] or {}
    return ok({"deleted": (data or {}).get("deleted", True),
               "webhook_id": webhook_id})
