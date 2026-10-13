"""Asaas finance — balance and statement.

    GET /v3/finance/balance            the account balance
    GET /v3/financialTransactions      the statement (offset/limit, startDate/finishDate)

This is the reconciliation side: a scheduler reads the statement and matches
settled charges against whatever booked them. Asaas charges no webhook for
"money moved", so a periodic pull is the only way to catch adjustments,
transfers and fees that no payment event describes.
"""

import os
import sys

try:  # loaded by exports.py
    from _asaas_client import _date_str, _money, call, err, ok
except ImportError:  # standalone: python3 tools/finance.py
    import importlib.util as _iu

    _spec = _iu.spec_from_file_location(
        "_asaas_client",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client.py"),
    )
    sys.modules["_asaas_client"] = _mod = _iu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    from _asaas_client import _date_str, _money, call, err, ok  # noqa: E402,F811


def balance():
    """Account balance, per bucket.

    Asaas splits it: `balance` is available now, the rest is money that exists
    but is not withdrawable yet (blocked, awaiting settlement, scheduled).
    """
    result = call("GET", "/finance/balance")
    if not result["ok"]:
        return result
    data = result["data"] or {}
    return ok({k: _money(v) if isinstance(v, (int, float)) else v
               for k, v in (data or {}).items()})


def statement(start_date=None, finish_date=None, take=100, skip=0):
    """Financial transactions in a window — the reconciliation feed.

    Defaults to the last 30 days when no window is given, because asking for
    "everything" on a busy account is how you get rate-limited.
    """
    if not start_date:
        start_date = "-30"
    result = call("GET", "/financialTransactions", params={
        "startDate": _date_str(start_date),
        "finishDate": _date_str(finish_date) if finish_date else None,
        "limit": min(int(take or 100), 100),
        "offset": int(skip or 0),
    })
    if not result["ok"]:
        return result
    data = result["data"] or {}
    rows = data.get("data") if isinstance(data, dict) else None
    out = []
    for row in (rows or []):
        if not isinstance(row, dict):
            out.append(row)
            continue
        out.append({
            "id": row.get("id"),
            "type": row.get("type"),
            "date": row.get("date"),
            "value": _money(row.get("value")),
            "balance": _money(row.get("balance")),
            "description": row.get("description"),
            "payment_id": row.get("paymentId"),
            "transfer_id": row.get("transferId"),
        })
    return ok({
        "total": (data or {}).get("totalCount"),
        "has_more": (data or {}).get("hasMore"),
        "transactions": out,
    })
