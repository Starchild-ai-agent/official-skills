"""Lare skill exports."""
from __future__ import annotations

import importlib.util
import os
import sys
from datetime import date

__all__ = [
    "lare_sessions",
    "lare_session_detail",
    "lare_find_members",
    "lare_member_detail",
    "lare_book",
    "lare_waitlist",
    "lare_cancel_booking",
    "lare_check_in",
    "lare_no_show",
    "lare_products",
    "lare_orders",
    "lare_create_payment_link",
    "lare_reports_sales",
]

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("_lare_client", os.path.join(_here, "client.py"))
_client = importlib.util.module_from_spec(_spec)
sys.modules["_lare_client"] = _client
_spec.loader.exec_module(_client)
call = _client.call


def lare_sessions(date_value: str | None = None):
    return call("GET", "/api/v1/sessions", query={"date_value": date_value or date.today().isoformat()})


def lare_session_detail(session_token: str):
    return call("GET", f"/api/v1/sessions/{session_token}")


def lare_find_members(search: str = "", page: int = 1):
    return call("GET", "/api/v1/members", query={"search": search, "page": page, "is_staff": "false"})


def lare_member_detail(member_id: int):
    return call("GET", f"/api/v1/members/{int(member_id)}")


def lare_book(session_token: str, user_id: int, spot: str | None = None):
    body = {"user_id": int(user_id)}
    if spot:
        body["spot"] = spot
    return call("POST", f"/api/v1/sessions/{session_token}/bookings", body=body)


def lare_waitlist(session_token: str, user_id: int):
    return call("POST", f"/api/v1/sessions/{session_token}/waitlist", body={"user_id": int(user_id)})


def lare_cancel_booking(booking_token: str):
    return call("POST", f"/api/v1/bookings/{booking_token}/cancel", body={})


def lare_check_in(booking_token: str):
    return call("POST", f"/api/v1/bookings/{booking_token}/check-in", body={})


def lare_no_show(booking_token: str):
    return call("POST", f"/api/v1/bookings/{booking_token}/no-show", body={})


def lare_products():
    return call("GET", "/api/v1/products")


def lare_orders(status: str | None = None, page: int = 1):
    return call("GET", "/api/v1/console/orders", query={"status": status, "page": page})


def lare_create_payment_link(member_id: int, product_id: int, mode: str = "pix"):
    added = call(
        "POST",
        f"/api/v1/members/{int(member_id)}/cart/items",
        body={"product_id": int(product_id), "quantity": 1},
    )
    if not added.get("ok"):
        return added
    return call("POST", f"/api/v1/members/{int(member_id)}/checkout", body={"mode": mode})


def lare_reports_sales(date_from: str | None = None, date_to: str | None = None):
    return call("GET", "/api/v1/console/reports/sales", query={"date_from": date_from, "date_to": date_to})
