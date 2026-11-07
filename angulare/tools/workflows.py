"""Angulare workflows — the multi-step flows the agent actually needs.

Everything here is a *composition* of the primitives in the other modules. The
point is that the agent should not have to know that "sell a plan over WhatsApp"
is six API calls with three guards in between.

`send_payment_link` is the sales flow in one call:

    resolve the member -> put the product in their cart -> send the payment
    link -> report whether it went out

Verified against production; see references/api-reference.md for the raw
evidence behind every guard below.
"""

import os
import sys

try:  # loaded by exports.py
    from _angulare_client import err, ok
    from _angulare_catalog import products as _products
    from _angulare_members import member as _member, resolve_member as _resolve
    from _angulare_payments import (
        checkout_add_product as _add_product,
        checkout_remove_line as _remove_line,
        checkout_set_payment_method as _set_method,
        checkout_share as _share,
        current_checkout as _current_checkout,
    )
except ImportError:  # standalone: python3 tools/workflows.py
    import importlib.util as _iu

    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _load(name, *parts):
        path = os.path.join(_root, *parts)
        spec = _iu.spec_from_file_location(name, path)
        module = _iu.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    _load("_angulare_client", "client.py")
    _load("_angulare_members", "tools", "members.py")
    _load("_angulare_catalog", "tools", "catalog.py")
    _load("_angulare_payments", "tools", "payments.py")

    from _angulare_client import err, ok  # noqa: E402,F811
    from _angulare_catalog import products as _products  # noqa: E402,F811
    from _angulare_members import member as _member, resolve_member as _resolve  # noqa: E402,F811
    from _angulare_payments import (  # noqa: E402,F811
        checkout_add_product as _add_product,
        checkout_remove_line as _remove_line,
        checkout_set_payment_method as _set_method,
        checkout_share as _share,
        current_checkout as _current_checkout,
    )


def _fail(status, message, hint=None, **extra):
    """`err()` takes only (status, message, hint); this carries extra context."""
    out = err(status, message, hint)
    out.update(extra)
    return out


def _product_brief(product_id):
    """Name/price for the plan display. Best-effort — never fatal."""
    found = _products(take=200)
    if not found["ok"]:
        return {"id": product_id}
    for row in found["data"]["products"]:
        if row.get("id") == product_id:
            return {"id": row.get("id"), "name": row.get("name"),
                    "price": row.get("price")}
    return {"id": product_id}


def send_payment_link(user_id=None, query=None, product_id=None, quantity=1,
                      replace_cart=True, channels=None, expiration=None,
                      set_payment_method=None, confirm=False):
    """Sell one product to one member by sending Angulare's payment link.

    This is the WhatsApp sales flow end to end:

      1. resolve the member (`user_id`, or `query` = id / CPF / e-mail / name)
      2. find their current cart (Angulare keeps exactly one per member)
      3. optionally clear it, then add `product_id`
      4. `share` the cart, which makes Angulare e-mail the customer a link to pay
      5. read the cart back and confirm `shared_to_customer`

    Without `confirm=True` it does **nothing** and returns the plan it would
    execute — run it that way first when you are unsure which cart you are about
    to overwrite.

    Returns `{ok, sent, checkout_id, user_id, total, expiration,
    shared_to_customer, steps, next}`. `sent` is the answer to "did the e-mail go
    out": Angulare accepts it (200) and the cart's flag flips.

    Three guards, each of which turns a confusing API error into a plain one:

    - **staff members are refused up front.** Sharing a payment link for a staff
      account's cart is a `403 Você não tem permissão…`, which reads like a
      missing permission but is a design rule. There is no permission to grant.
    - **a member without an e-mail is refused** when `channels` includes "email",
      because that channel needs an address.
    - **an empty cart after adding is refused** — there would be nothing to pay.

    Not included on purpose: telling the customer. That is your messaging layer's
    job — this function's contract is that the link has been sent and verified.
    """
    chans = [c.lower() for c in (["email"] if channels is None else channels)]

    # ── 1. member ────────────────────────────────────────────────────────────
    if user_id is None:
        if not query:
            return _fail(None, "send_payment_link needs user_id or query",
                       hint="query accepts an id, a CPF, an e-mail or a name")
        found = _resolve(query)
        if not found["ok"]:
            return found
        hit = found["data"]
        if not hit.get("member"):
            return _fail(None, "no single member matched %r" % (query,),
                       candidates=hit.get("candidates", [])[:5],
                       hint="narrow the query, or pass user_id directly")
        user_id = hit["member"]["id"]

    who = _member(user_id)
    if not who["ok"]:
        return who
    person = who["data"] or {}
    name = person.get("name")

    if person.get("is_staff"):
        return err(None, "%s is a staff account" % (name or user_id),
                   hint="Angulare refuses to share a payment link for a staff "
                        "member's cart (403). Send the link for a customer's cart.")
    if "email" in chans and not person.get("email"):
        return err(None, "%s has no e-mail address" % (name or user_id),
                   hint="channels=['email'] needs one — add the address to the "
                        "member, or ask for a phone number and use 'whatsapp'.")

    # ── 2. cart ──────────────────────────────────────────────────────────────
    cart = _current_checkout(user_id=user_id)
    if not cart["ok"]:
        return cart
    ck = cart["data"]["id"]
    existing = [line["line_id"] for line in (cart["data"].get("lines") or [])]

    # ── 3. plan ──────────────────────────────────────────────────────────────
    plan = {
        "member": {"id": user_id, "name": name, "email": person.get("email")},
        "checkout_id": ck,
        "cart_total_before": cart["data"].get("total"),
        "remove_line_ids": existing if replace_cart else [],
        "add_product": _product_brief(product_id) if product_id is not None else None,
        "quantity": quantity,
        "set_payment_method": set_payment_method,
        "channels": chans,
        "expiration": expiration,
    }

    if not confirm:
        return ok({"dry_run": True, "plan": plan,
                   "hint": "nothing was written — re-run with confirm=True to execute"})

    # ── 4. execute ───────────────────────────────────────────────────────────
    steps = []

    if replace_cart:
        for line_id in existing:
            gone = _remove_line(line_id, confirm=True)
            steps.append({"step": "remove_line", "line_id": line_id,
                          "ok": gone["ok"], "status": gone.get("status")})
            if not gone["ok"]:
                return _fail(gone.get("status"), "could not clear the cart",
                           steps=steps, detail=gone.get("error"),
                           hint="the cart may already be gone; re-read it with "
                                "angulare_current_checkout and retry")

    if product_id is not None:
        added = _add_product(product_id, checkout_id=ck, quantity=quantity, confirm=True)
        steps.append({"step": "add_product", "product_id": product_id,
                      "ok": added["ok"], "status": added.get("status")})
        if not added["ok"]:
            return _fail(added.get("status"), "could not add the product",
                       steps=steps, detail=added.get("error"))

    if set_payment_method is not None:
        seted = _set_method(ck, set_payment_method, confirm=True)
        steps.append({"step": "set_payment_method", "payment_method": set_payment_method,
                      "ok": seted["ok"], "status": seted.get("status")})
        if not seted["ok"]:
            return _fail(seted.get("status"), "could not set the payment method",
                       steps=steps, detail=seted.get("error"))

    after = _current_checkout(user_id=user_id)
    total = after["data"].get("total") if after["ok"] else None
    if not total:
        return _fail(None, "the cart is empty — nothing to charge",
                   steps=steps, checkout_id=ck,
                   hint="pass a product_id that can be sold to this member")

    # ── 5. send ──────────────────────────────────────────────────────────────
    sent = _share(ck, channels=chans, expiration=expiration, confirm=True)
    steps.append({"step": "share", "ok": sent["ok"], "status": sent.get("status")})
    if not sent["ok"]:
        status = sent.get("status")
        hint = None
        if status == 403:
            hint = ("Angulare refuses to share a payment link for a staff member's "
                    "cart. This is a design rule, not a missing permission.")
        elif status == 404:
            hint = "the cart expired and was purged — build a fresh one and retry"
        return _fail(status, "the payment link was NOT sent",
                   steps=steps, checkout_id=ck, user_id=user_id, detail=sent.get("error"),
                   hint=hint)

    return ok({
        "sent": True,
        "user_id": user_id,
        "checkout_id": ck,
        "total": total,
        "channels": chans,
        "expiration": ((sent["data"] or {}).get("evo_result") or {}).get("expiration"),
        "expiration_capped": ((sent["data"] or {}).get("evo_result") or {}).get("expiration_capped"),
        "shared_to_customer": (sent["data"] or {}).get("shared_to_customer"),
        "steps": steps,
        "next": ("Angulare e-mailed the customer a 'Link para pagamento do seu pedido'. "
                 "Tell them in your own channel to open it. Then poll "
                 "angulare_payment_status(user_id=%d) for status 'paid'." % user_id),
    })


if __name__ == "__main__":  # CLI for debugging: python3 tools/workflows.py
    import json
    print(json.dumps(send_payment_link(user_id=2246, product_id=2), indent=2,
                     ensure_ascii=False, default=str))
