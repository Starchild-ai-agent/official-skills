"""Angulare payments — orders, checkouts, and the credit-card payment link.

The important structural fact (verified in production):

    a checkout is the CART; an order is the SALE that cart produces.

`shared_to_customer` on the checkout stays `True`/`False`; it does **not** flip
to "paid". Payment status lives on the **order**:

    paid             Pago                        settled
    waiting_payment  Aguardando pagamento        link/cart issued, not settled
    not_authorized   Pagamento não autorizado    refused by the card issuer
    canceled         Cancelado                   canceled

So "did the customer pay?" is answered by `orders()`, never by the checkout.

Verified filters:
    /api/v1/sales/orders/            user_id, status        (page, page_size)
    /api/v1/checkouts/checkouts/     user_id                (page, page_size)
Unsupported params are silently ignored.
"""

import os
import sys

try:  # loaded by exports.py
    from _angulare_client import ORDER_STATUS, _digits, call, credentials, err, ok, page
except ImportError:  # standalone
    import importlib.util as _iu

    _spec = _iu.spec_from_file_location(
        "_angulare_client",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client.py"),
    )
    sys.modules["_angulare_client"] = _mod = _iu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    from _angulare_client import ORDER_STATUS, _digits, call, credentials, err, ok, page  # noqa: E402,F811


def _method(row):
    info = row.get("payment_method_info")
    if isinstance(info, dict):
        return info.get("code")
    return row.get("payment_method")


def orders(user_id=None, status=None, take=100, max_pages=5, all_pages=False):
    """Sales orders — this is where payment status lives.

    `status`: paid | waiting_payment | not_authorized | canceled.
    `user_id`: one member's orders.
    """
    if isinstance(status, str) and status not in ORDER_STATUS:
        return err(None, f"unknown order status {status!r}",
                   hint="use one of: " + ", ".join(ORDER_STATUS))
    collected, page_no, pages = [], 1, 0
    while True:
        result = call("GET", "/api/v1/sales/orders/", params={
            "user_id": user_id, "status": status,
            "page_size": take, "page": page_no})
        if not result["ok"]:
            return result
        p = page(result)
        collected += p["results"]
        pages += 1
        if not all_pages or not p["next"] or pages >= max_pages:
            break
        page_no += 1
    rows = [{
        "id": r.get("id"),
        "status": r.get("status"),
        "status_display": r.get("status_display"),
        "status_reason": r.get("status_reason"),
        "user_id": r.get("customer_id"),
        "user_name": " ".join(x for x in ((r.get("customer_detail") or {}).get("first_name"),
                                          (r.get("customer_detail") or {}).get("last_name"))
                              if x) if isinstance(r.get("customer_detail"), dict) else None,
        "checkout_id": r.get("checkout"),
        "payment_method": _method(r),
        "card": r.get("creditcard_masked_number"),
        "installments": r.get("installments"),
        "total": r.get("total_with_discounts"),
        "is_subscription": r.get("is_subscription"),
        "has_packages": r.get("has_packages"),
        "created_at": r.get("created_at"),
        "submitted_at": r.get("date_submitted"),
    } for r in collected]
    return ok({"count": p["count"], "returned": len(rows), "orders": rows})


def payment_status(user_id, take=50):
    """Did this member pay? A compact answer for one customer.

    Returns their orders split by state plus a one-line verdict. Remember an
    order can exist as `waiting_payment` before any money moves.
    """
    found = orders(user_id=user_id, take=take, all_pages=True, max_pages=3)
    if not found["ok"]:
        return found
    rows = found["data"]["orders"]
    paid = [r for r in rows if r["status"] == "paid"]
    pending = [r for r in rows if r["status"] == "waiting_payment"]
    latest = sorted(rows, key=lambda r: r.get("created_at") or "", reverse=True)[:1]
    return ok({
        "user_id": user_id,
        "orders": len(rows),
        "paid": len(paid),
        "awaiting_payment": len(pending),
        "latest": latest[0] if latest else None,
        "verdict": ("paid" if paid and not pending else
                    "awaiting_payment" if pending else
                    "no orders" if not rows else "other"),
    })


def checkouts(user_id=None, take=100, max_pages=5, all_pages=False):
    """Carts / checkout records. `shared_to_customer=True` means a link went out.

    Note the status stays `Submitted` even after payment — check `orders()` for
    whether it was actually paid.
    """
    collected, page_no, pages = [], 1, 0
    while True:
        result = call("GET", "/api/v1/checkouts/checkouts/", params={
            "user_id": user_id, "page_size": take, "page": page_no})
        if not result["ok"]:
            return result
        p = page(result)
        collected += p["results"]
        pages += 1
        if not all_pages or not p["next"] or pages >= max_pages:
            break
        page_no += 1
    return ok({"count": p["count"], "returned": len(collected), "checkouts": [{
        "id": r.get("id"),
        "status": r.get("status"),
        "shared_to_customer": r.get("shared_to_customer"),
        "payment_method": _method(r),
        "user_id": r.get("owner"),
        "total": r.get("total_with_discounts"),
        "channel": r.get("channel"),
        "is_subscription": r.get("is_subscription"),
        "should_deliver": r.get("should_deliver"),
    } for r in collected]})


def checkout(checkout_id):
    """One checkout in full (lines, installments, totals, sharing state).

    ⚠️ Cart ids rotate: once an `Open` cart expires it is gone for good, so this
    legitimately 404s on an old id. Use `current_checkout()` to find the live one.
    """
    result = call("GET", f"/api/v1/checkouts/checkouts/{checkout_id}/")
    if not result["ok"]:
        return result
    return ok(result["data"])


def current_checkout(user_id=None):
    """Find the cart worth sharing — Angulare keeps exactly one "current" cart.

    `user_id` given -> that member's current cart
    (`/checkouts/checkouts/user-{id}/`); omitted -> the caller's own working cart
    (`/checkouts/checkouts/current/`).

    There is **no create-cart endpoint**: carts are session-scoped working objects
    that Angulare maintains, and the id rotates when the old one expires. So this
    is the only correct way to obtain a `ck` — never store one.
    """
    path = (f"/api/v1/checkouts/checkouts/user-{user_id}/" if user_id
            else "/api/v1/checkouts/checkouts/current/")
    result = call("GET", path)
    if not result["ok"]:
        return result
    data = result["data"] or {}
    if not isinstance(data, dict):
        return ok(data)
    lines = []
    for line in (data.get("lines_info") or []):
        product = line.get("product") if isinstance(line.get("product"), dict) else {}
        lines.append({"line_id": line.get("id"),
                      "product_id": product.get("id"),
                      "product": product.get("name"),
                      "quantity": line.get("quantity"),
                      "unit_price": line.get("unit_price")})
    return ok({
        "id": data.get("id"),
        "status": data.get("status"),
        "user_id": data.get("owner"),
        "shared_to_customer": data.get("shared_to_customer"),
        "total": data.get("total_with_discounts"),
        "channel": data.get("channel"),
        "pos_id": data.get("pos_id"),
        "is_subscription": data.get("is_subscription"),
        "lines": lines,
        "is_empty": not lines,
        "sharable": bool(lines) and not data.get("is_expired"),
    })


def checkout_set_payment_method(checkout_id, payment_method, installments=None,
                                 confirm=False):
    """⚠️ WRITE — choose the payment method on a cart.

    The PDV does `checkout.patch(id, {payment_method, installments})`, where
    `payment_method` is an **id** from `angulare_payment_methods()` (1 = credit
    card, 9 = pix). `installments` is only meaningful for cards.

    UNVERIFIED ENDPOINT — reverse-engineered from the dashboard, never executed
    here. Requires `confirm=True`; verifies by re-reading the cart.
    """
    if not confirm:
        return err(None, "checkout_set_payment_method is a write and requires confirm=True",
                   hint="it mutates a real cart. Use a throwaway member and cart.")
    if payment_method is None:
        return err(None, "checkout_set_payment_method needs a payment_method id",
                   hint="see angulare_payment_methods()")
    body = {"payment_method": payment_method}
    if installments is not None:
        body["installments"] = int(installments)
    result = call("PATCH", f"/api/v1/checkouts/checkouts/{checkout_id}/", body=body)
    if not result["ok"]:
        return result
    after = checkout(checkout_id)
    applied = None
    if after["ok"] and isinstance(after["data"], dict):
        applied = after["data"].get("payment_method")
    return ok({"checkout_id": checkout_id, "requested": payment_method,
               "applied": applied, "installments": installments,
               "evo_result": result["data"]})


def checkout_create_payment(checkout_id="current", confirm=False):
    """⚠️ WRITE — ask the gateway to create the payment for a cart.

    **This is where the Pix artifact comes from.** The app does
    `checkout.createPayment(id)` and, when the response carries
    `payment_method: "pix"` with `status: "pending-payment"`, renders that
    payload to the shopper — i.e. the Pix code/QR lives inside this response.
    (The exact field holding the copy-and-paste code is not verified here; the
    whole payload is returned so the caller can inspect it.)

    Credit card is different: its artifact is a **hosted page**, not a value, so
    there is nothing to hand over — which is exactly why the PDV falls back to
    e-mailing a payment link.

    UNVERIFIED ENDPOINT — reverse-engineered, never executed here. Requires
    `confirm=True`.
    """
    if not confirm:
        return err(None, "checkout_create_payment is a write and requires confirm=True",
                   hint="it creates a real gateway transaction on a real cart.")
    result = call("POST", f"/api/v1/checkouts/checkouts/{checkout_id}/create-payment/")
    if not result["ok"]:
        return result
    data = result["data"] if isinstance(result["data"], dict) else {}
    return ok({
        "checkout_id": checkout_id,
        "payment_method": data.get("payment_method"),
        "status": data.get("status"),
        "is_pix": data.get("payment_method") == "pix",
        "payload": data,
        "note": ("for Pix the code/QR is inside `payload` — send it over WhatsApp; "
                 "for cards there is no value to send, only a hosted page."),
    })


def checkout_add_product(product_id, checkout_id="current", quantity=1, pos_id=None,
                         product_rules_accepted=None, confirm=False):
    """⚠️ WRITE — put a product into a cart.

    Body shape taken from the app store (`web.js`), which calls
    `checkout.addProduct("current", {product, quantity, pos_id,
    product_rules_accepted})`. `pos_id` is resolved from the POS list by the app;
    here it defaults to the cart's own `pos_id`.

    `product_rules_accepted` is **a string of HTML, not a boolean** — the store
    builds it from the product's rules message (`outerHTML` of the
    `#product_rules_accepted` element) and sends `""` when there are none. Sending
    a bool is rejected with `Not a valid string.` Leave it as `None` to omit the
    field entirely, which is what works for products without rules.

    VERIFIED — executed against production. Requires `confirm=True`; verifies by
    re-reading the cart.
    """
    if not confirm:
        return err(None, "checkout_add_product is a write and requires confirm=True",
                   hint="it mutates a real cart. Use a throwaway member and cart.")
    if not product_id:
        return err(None, "checkout_add_product needs a product_id")

    if pos_id is None:
        existing = (current_checkout() if checkout_id == "current"
                    else checkout(checkout_id))
        if existing["ok"] and isinstance(existing["data"], dict):
            pos_id = existing["data"].get("pos_id")

    body = {"product": product_id, "quantity": int(quantity or 1)}
    if pos_id is not None:
        body["pos_id"] = pos_id
    if product_rules_accepted is not None:
        body["product_rules_accepted"] = str(product_rules_accepted)

    result = call("POST", f"/api/v1/checkouts/checkouts/{checkout_id}/add-product/",
                  body=body)
    if not result["ok"]:
        return result

    after = (current_checkout() if checkout_id == "current" else checkout(checkout_id))
    payload = {"checkout_id": checkout_id, "product_id": product_id,
               "quantity": body["quantity"], "pos_id": pos_id,
               "evo_result": result["data"], "added": None, "lines": None}
    if after["ok"] and isinstance(after["data"], dict):
        # `checkout()` returns the raw row (line list is `lines_info`), while
        # `current_checkout()` normalises it to `lines`. Handle both.
        rows = after["data"].get("lines")
        if rows is None:
            rows = [{"line_id": l.get("id"),
                     "product_id": (l.get("product") or {}).get("id")}
                    for l in (after["data"].get("lines_info") or [])]
        payload["lines"] = rows
        payload["added"] = any(str(l.get("product_id")) == str(product_id)
                               for l in rows)
    return ok(payload)


def checkout_remove_line(line_id, confirm=False):
    """⚠️ WRITE — remove one line from a cart.

    The app store does `checkoutLines.delete(lineId)` →
    `DELETE /api/v1/checkouts/checkout-lines/{line_id}/` (a real delete, not a
    soft flag). Line ids come from `angulare_current_checkout()["lines"][].line_id`.

    UNVERIFIED ENDPOINT — reverse-engineered, never executed by this skill's
    authors. Requires `confirm=True`.
    """
    if not confirm:
        return err(None, "checkout_remove_line is a write and requires confirm=True",
                   hint="it mutates a real cart. Use a throwaway member and cart.")
    if not line_id:
        return err(None, "checkout_remove_line needs a line_id")
    result = call("DELETE", f"/api/v1/checkouts/checkout-lines/{line_id}/")
    if not result["ok"]:
        return result
    return ok({"line_id": line_id, "evo_result": result["data"]})


def checkout_share(checkout_id, channels=None, expiration=None, revalidate=False,
                   ask_password=False, ask_card=False, show_checkout=True,
                   confirm=False):
    """⚠️ WRITE — send the "Link de Pagamento" for a cart to the customer.

    Angulare e-mails and/or SMSes the payment link **to the customer** (the
    member on the cart). The API does NOT return the URL: the dashboard throws
    the response away, which is why this skill cannot hand you a link to
    forward over WhatsApp.

    All six API fields are required; this function fills them, so in practice you
    only pass `checkout_id`.

    `channels` — subset of ["email", "whatsapp"]. Defaults to `["email"]`, which
    matters: omitting the field makes the API assume a phone channel and reject
    with `Necessário cadastrar telefone celular do usuário`. `whatsapp` is not
    enabled on every tenant and answers `non_field_errors`.

    `expiration` — the link's validity, a datetime. A bare `YYYY-MM-DD` is
    normalised to the **start** of that day, so it expires earlier than you
    expect. Defaults here to the end of tomorrow at UTC-3 (24-48h), rather than
    the dashboard's end-of-today, which can be minutes away.

    `ask_password` / `ask_card` make the link ask the customer to re-register a
    password / a new card; `show_checkout` shows the checkout as the last step.

    VERIFIED — executed successfully against production. It sends a real message
    to a real person, so it requires `confirm=True`. The reply is a usable
    success signal: `200 {"ok":…, "expiration":…, "expiration_capped":…}` means
    queued, `404` means the cart is gone, `400` means a bad expiry.

    After sending, re-read the checkout and `orders(user_id=…)` to see the
    `shared_to_customer` flag and any new `waiting_payment` order.
    """
    if not confirm:
        return err(None, "checkout_share is a write and requires confirm=True",
                   hint="it e-mails/SMSes a real payment link to the customer and may "
                        "create a real order. Test on a throwaway member first.")
    if not expiration:
        # The endpoint rejects a null expiry with `Este campo não pode ser nulo.`
        # and requires a datetime.
        #
        # Two traps here. Angulare runs on Brazil time (UTC-3), so "today" has to
        # be computed there, not on the caller's clock. And a bare date is
        # normalised to the *start* of that day (`"2026-10-17"` ->
        # `2026-10-17T00:00:00-03:00`), so passing tomorrow's date expires the
        # link at midnight, not at the end of tomorrow.
        #
        # The dashboard defaults to the end of today, which can be minutes away
        # if the UTC-3 day is nearly over — useless for a link a customer has to
        # open later. Default to the end of tomorrow instead: always 24-48h.
        from datetime import datetime, timedelta, timezone
        expiration = (datetime.now(timezone(timedelta(hours=-3)))
                      + timedelta(days=1)).strftime("%Y-%m-%dT23:59:59-03:00")
    body = {
        # `channels=[]` must stay an empty list (it is the candidate switch for
        # "mint the link without delivering it") — hence `is None`, not `or`.
        "channels_to_send": [c.lower() for c in (["email"] if channels is None else channels)],
        "expiration": expiration,
        "revalidate": bool(revalidate),
        "ask_password": bool(ask_password),
        "ask_card": bool(ask_card),
        "show_checkout": bool(show_checkout),
    }
    result = call("POST", f"/api/v1/checkouts/checkouts/{checkout_id}/share/", body=body)
    if not result["ok"]:
        if result.get("status") == 404:
            result["hint"] = ("No such checkout — open (unsubmitted) carts expire and are "
                              "purged, so an old cart id 404s. This is not a permission "
                              "problem. Build a fresh cart instead of re-sharing an old one.")
        return result

    after = checkout(checkout_id)
    payload = {"checkout_id": checkout_id, "sent": True, "channels": body["channels_to_send"],
               "evo_result": result["data"], "shared_to_customer": None, "url": None}
    if after["ok"] and isinstance(after["data"], dict):
        payload["shared_to_customer"] = after["data"].get("shared_to_customer")
        payload["user_id"] = after["data"].get("owner")
    payload["note"] = ("Angulare delivered the link itself; the URL is not returned by the "
                       "API. Ask the customer to forward the e-mail, or ask Angulare for "
                       "the link template (see references/api-reference.md).")
    return ok(payload)


def pix_charge(user_id, product_id=None, quantity=1, replace_cart=True,
               pos_id=None, installments=1, confirm=False):
    """⚠️ WRITE — charge a member by Pix and hand back the copy-paste code.

    This is the flow the NUMA bot already runs in production, lifted into the
    skill so it stops being re-implemented per service. It ends with a real
    order, so it requires `confirm=True`.

        cart (clear) -> add product -> payment_method = 9 (Pix)
        -> create-payment -> gateway transaction -> place-order

    Returns `{pix_copy_paste, pix_expires_at, order_id, checkout_id, total}`.
    `pix_copy_paste` is what you send to the customer over WhatsApp — unlike the
    card link, Pix is a string you can deliver yourself.

    Three things the gateway taught us, all encoded here:

    - the gateway wants the **`payment_id`** from `create-payment`, not an
      amount, which is why this must run after `create-payment`;
    - it is called **before** `place-order` (that is the order the dashboard
      uses, and the order that works);
    - `payment_method` is the string `"pix"`, and `card_data` must still be sent
      as `{}`.

    A member with no CPF is refused up front: the gateway answers
    `CPF é obrigatório para pagamento via Pix`, and a hand-made test member never
    has one.
    """
    if not confirm:
        return err(None, "pix_charge is a write and requires confirm=True",
                   hint="it creates a real order and a real Pix charge.")

    who = call("GET", "/api/v1/users/users/%s/" % user_id)
    if not who["ok"]:
        return who
    person = who["data"] or {}
    cpf = _digits(person.get("cpf"))
    if not cpf:
        return err(None, "member %s has no CPF" % user_id,
                   hint="the gateway requires a CPF for Pix (CPF é obrigatório para "
                        "pagamento via Pix). Fill it in before charging.")

    cart = current_checkout(user_id=user_id)
    if not cart["ok"]:
        return cart
    ck = cart["data"]["id"]

    steps = []
    if replace_cart:
        for line in (cart["data"].get("lines") or []):
            gone = checkout_remove_line(line["line_id"], confirm=True)
            steps.append({"step": "remove_line", "line_id": line["line_id"],
                          "status": gone.get("status")})
            if not gone["ok"]:
                return err(gone.get("status"), "could not clear the cart", steps=steps)

    if product_id is not None:
        added = checkout_add_product(product_id, checkout_id=ck, quantity=quantity,
                                     confirm=True)
        steps.append({"step": "add_product", "product_id": product_id,
                      "status": added.get("status")})
        if not added["ok"]:
            return err(added.get("status"), "could not add the product", steps=steps)

    body = {"payment_method": 9}
    if pos_id is not None:
        body["pos_id"] = pos_id
    if installments:
        body["installments"] = installments
    seted = checkout_set_payment_method(ck, 9, installments=installments, confirm=True)
    steps.append({"step": "set_payment_method", "payment_method": 9,
                  "status": seted.get("status")})
    if not seted["ok"]:
        return err(seted.get("status"), "could not set the payment method", steps=steps)

    paid = checkout_create_payment(ck, confirm=True)
    steps.append({"step": "create_payment", "status": paid.get("status")})
    if not paid["ok"]:
        return err(paid.get("status"), "could not create the payment", steps=steps)

    after = current_checkout(user_id=user_id)
    total = after["data"].get("total") if after["ok"] else None
    if not total:
        return err(None, "the cart is empty — nothing to charge", steps=steps)

    cfg = call("GET", "/api/v1/core/settings/")
    if not cfg["ok"]:
        return err(cfg.get("status"), "could not read the payment settings", steps=steps)
    pay_url = ((cfg["data"] or {}).get("payments") or {}).get("angular_pay_url")
    if not pay_url:
        return err(None, "the tenant has no angular_pay_url configured", steps=steps)

    _, _, tenant = credentials()
    tx = call("POST", pay_url.rstrip("/") + "/api/v3/transaction/transaction/", body={
        "reference": ck,
        "payment_id": (paid["data"] or {}).get("payment_id") or (after["data"] or {}).get("payment_id"),
        "public_key": (paid["data"] or {}).get("pay_key_public") or (after["data"] or {}).get("pay_key_public"),
        "tenant": tenant,
        "payment_method": "pix",
        "channel": "pdv",
        "pos": (paid["data"] or {}).get("pos_unit_id") or (after["data"] or {}).get("pos_unit_id"),
        "installments": int(installments or 1),
        "card_data": {},
        "customer": {
            "name": ("%s %s" % (person.get("first_name") or "",
                                person.get("last_name") or "")).strip(),
            "email": person.get("email"),
            "cpf": cpf,
            "phone": _digits(person.get("mobile_phone") or person.get("phone")),
        },
    }, timeout=45)
    steps.append({"step": "gateway_transaction", "status": tx.get("status")})
    if not tx["ok"]:
        return err(tx.get("status"), "the gateway refused the Pix charge",
                   steps=steps, detail=tx.get("error"), gateway=tx.get("data"))

    pix_code = (tx["data"] or {}).get("pix_copy_paste")
    if not pix_code:
        return err(None, "the gateway returned no Pix code", steps=steps,
                   gateway=tx["data"],
                   hint="check the gateway status/reason fields above — a common cause "
                        "is a member record that Asaas cannot resolve.")

    placed = call("POST", "/api/v1/checkouts/checkouts/%s/place-order/" % ck,
                  body={"point_of_sale": pos_id or 1, "channel": "web"})
    steps.append({"step": "place_order", "status": placed.get("status")})

    return ok({
        "pix_copy_paste": pix_code,
        "pix_expires_at": (tx["data"] or {}).get("pix_expires_at"),
        "pix_qrcode": (tx["data"] or {}).get("pix_qrcode"),
        "gateway_status": (tx["data"] or {}).get("status"),
        "checkout_id": ck,
        "order_id": (placed["data"] or {}).get("id") if placed["ok"] else None,
        "order_status": (placed["data"] or {}).get("status") if placed["ok"] else None,
        "total": total,
        "user_id": user_id,
        "steps": steps,
        "next": ("Send `pix_copy_paste` to the customer. Then poll "
                 "angulare_payment_status(user_id=%s) for status 'paid'." % user_id),
    })
