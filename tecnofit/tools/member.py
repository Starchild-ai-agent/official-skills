"""Tecnofit member lookup and entitlement verdict.

The `ticket-gate` endpoint returns a `CustomerSummary`: the student, their
status, and their contracts. That is the whole public surface — Tecnofit
publishes no schedule, booking or check-in endpoints, so this module answers
"who is this and are they allowed in?", not "what is on the timetable?".
"""

import os
import sys

try:  # loaded by exports.py
    from _tecnofit_client import (CONTRACT_ENTITLED, CONTRACT_STATUS, STUDENT_STATUS,
                                  _label, auth, err, ok, ticket_gate)
except ImportError:  # standalone
    import importlib.util as _iu

    _spec = _iu.spec_from_file_location(
        "_tecnofit_client",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client.py"),
    )
    sys.modules["_tecnofit_client"] = _mod = _iu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    from _tecnofit_client import (CONTRACT_ENTITLED, CONTRACT_STATUS, STUDENT_STATUS,  # noqa: E402,F811
                                  _label, auth, err, ok, ticket_gate)


def _normalize(row):
    if not isinstance(row, dict):
        return row
    plans = []
    for plan in (row.get("plans") or []):
        if not isinstance(plan, dict):
            continue
        plans.append({
            "contract_id": plan.get("id"),
            "name": plan.get("name"),
            "start_date": plan.get("startDate"),
            "end_date": plan.get("endDate"),
            "status_code": plan.get("status"),
            "status": _label(CONTRACT_STATUS, plan.get("status")),
        })
    status_code = row.get("status")
    return {
        "name": row.get("name"),
        "phones": row.get("phones") or [],
        "gender": row.get("gender"),
        "birth_date": row.get("birthDate"),
        "height_cm": row.get("customerHeight"),
        "status_code": status_code,
        "status": _label(STUDENT_STATUS, status_code),
        "plans": plans,
    }


def member(gate_token, member_id, auth_token=None):
    """Look up one student through the ticket gate, normalised."""
    result = ticket_gate(gate_token, member_id, auth_token=auth_token)
    if not result["ok"]:
        return result
    return ok(_normalize(result["data"] or {}))


def entitlement(gate_token, member_id, auth_token=None):
    """Should this student be let in?

    Combines the student status with the contract statuses and returns a
    one-word verdict plus the reasons. `allowed` is true only when the student
    is `active` and holds at least one `active` contract — anything else
    (blocked, canceled, restricted, on leave, no contract, pending payment)
    is surfaced explicitly rather than silently allowed.
    """
    found = member(gate_token, member_id, auth_token=auth_token)
    if not found["ok"]:
        return found

    data = found["data"]
    active_contracts = [p for p in data["plans"] if p["status_code"] in CONTRACT_ENTITLED]
    reasons = []
    if data["status"] != "active":
        reasons.append(f"student status is {data['status'] or data['status_code']}")
    if not data["plans"]:
        reasons.append("no contract on record")
    elif not active_contracts:
        reasons.append("no active contract (" + ", ".join(
            sorted({p["status"] or str(p["status_code"]) for p in data["plans"]})) + ")")

    return ok({
        "member": data,
        "allowed": not reasons,
        "verdict": "allowed" if not reasons else "denied",
        "reasons": reasons or ["student active with an active contract"],
        "active_contracts": len(active_contracts),
        "contracts": len(data["plans"]),
    })


def check_credentials():
    """Prove TECNOFIT_USER / TECNOFIT_PASS work, and report the token's life."""
    minted = auth(force=True)
    if not minted["ok"]:
        return minted
    return ok({
        "credentials": "ok",
        "token_expires_in": minted["data"].get("expires_in"),
        "token_expires_at": minted["data"].get("expires_at"),
        "note": ("a token is only valid for 1 hour; this client re-mints it "
                 "automatically, so callers never handle the token."),
        "endpoints_available": [
            "POST /2024-09-01/auth",
            "GET /2024-09-01/ticket-gate/{token}/{id}",
        ],
        "not_available": ("no schedule, booking, check-in or payment endpoints are "
                          "documented — this API is entitlement/access-control only"),
    })
