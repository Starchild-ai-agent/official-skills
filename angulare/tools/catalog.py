"""Angulare catalog — products/plans, categories, payment methods, reference data.

These are the "what can be sold and in which room" endpoints. Useful for
resolving human names to the ids that other calls need.
"""

import os
import sys

try:  # loaded by exports.py
    from _angulare_client import call, err, ok, page
except ImportError:  # standalone
    import importlib.util as _iu

    _spec = _iu.spec_from_file_location(
        "_angulare_client",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client.py"),
    )
    sys.modules["_angulare_client"] = _mod = _iu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    from _angulare_client import call, err, ok, page  # noqa: E402,F811


def _list(path, take=200, params=None, timeout=60):
    result = call("GET", path, params={**(params or {}), "page_size": take}, timeout=timeout)
    if not result["ok"]:
        return result
    p = page(result)
    return ok({"count": p["count"], "results": p["results"]})


def products(active_only=True, can_sell=None, take=200, max_pages=5):
    """Sellable plans/packages.

    ⚠️ Filter with the **server** `active=true`, never the `active` field.
    The field is a manual switch and ignores the availability window: one
    product here is `active: true` with `active_to` already in the past. The
    `active=true` filter is the one that honours `active_from`/`active_to`, so it
    is what "currently sellable" actually means (26 products -> 19).

    Verified filters: `active` (true|false), `can_sell` (true), `can_sell_mobile`.
    Not filters (silently ignored): `can_sell=false`, `approval_required`,
    `category`, `main_category`.

    Price is `current_price` — it is the sellable price and can differ from
    `price_sales_base` (promotions). `event_credit_quantity` is how many class
    credits the product grants.
    """
    collected, page_no, pages = [], 1, 0
    while True:
        result = call("GET", "/api/v1/products/products/", params={
            "active": "true" if active_only else None,
            "can_sell": "true" if can_sell else None,
            "page_size": take,
            "page": page_no,
        })
        if not result["ok"]:
            return result
        p = page(result)
        collected += p["results"]
        pages += 1
        if not p["next"] or pages >= max_pages:
            break
        page_no += 1

    def _num(value):
        try:
            return round(float(value), 2)
        except (TypeError, ValueError):
            return None

    def _on_promotion(row):
        current, base = _num(row.get("current_price")), _num(row.get("price_sales_base"))
        return None if current is None or base is None else current != base

    return ok({"count": len(collected), "products": [{
        "id": r.get("id"),
        "name": r.get("name"),
        "price": r.get("current_price"),
        "base_price": r.get("price_sales_base"),
        "on_promotion": _on_promotion(r),
        "credits": r.get("current_event_credit_quantity") or r.get("event_credit_quantity"),
        "credit_validity_days": r.get("current_event_credit_validity"),
        "auto_renew": r.get("auto_renew"),
        "category": (r.get("category_info") or {}).get("name")
                    if isinstance(r.get("category_info"), dict) else None,
        "active": r.get("active"),
        "can_sell": r.get("can_sell"),
        "available_from": r.get("active_from"),
        "available_to": r.get("active_to"),
        "approval_required": r.get("approval_required"),
    } for r in collected]})


def categories(take=50):
    """Product categories as they appear in the PDV."""
    listed = _list("/api/v1/products/categories/", take=take)
    if not listed["ok"]:
        return listed
    return ok({"count": listed["data"]["count"], "categories": [{
        "id": r.get("id"), "name": r.get("name"), "slug": r.get("slug"),
    } for r in listed["data"]["results"]]})


def payment_methods(take=50):
    """Payment method codes — the vocabulary for checkouts and orders.

    Observed: creditcard, creditcard-pos, debitcard-pos, cash, other, pix,
    pix-presencial. Note "Link de pagamento" is NOT here: it is a PDV action
    (`send-cart`), not a payment method.
    """
    listed = _list("/api/v1/payments/payment-methods/", take=take)
    if not listed["ok"]:
        return listed
    return ok({"count": listed["data"]["count"], "payment_methods": [{
        "id": r.get("id"), "code": r.get("code"), "name": r.get("name"),
        "enabled": r.get("enabled"),
    } for r in listed["data"]["results"]]})


def reference_data(take=1000):
    """Units, activities, rooms, locations and instructors in one call.

    Handy for mapping human names -> ids before booking or reporting.
    """
    out, errors = {}, {}
    for key, path in (("units", "/api/v1/events/units/"),
                      ("activities", "/api/v1/events/activities/"),
                      ("rooms", "/api/v1/events/rooms/"),
                      ("locations", "/api/v1/events/locations/"),
                      ("instructors", "/api/v1/events/instructors/")):
        listed = _list(path, take=take)
        if listed["ok"]:
            out[key] = [{"id": r.get("id"), "name": r.get("name"),
                         "active": r.get("active") or r.get("enabled")}
                        for r in listed["data"]["results"]]
        else:
            errors[key] = listed.get("error")
    return ok({"data": out, "errors": errors or None})
