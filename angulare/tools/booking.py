"""Angulare bookings — create, cancel, waitlist, and verify.

This is the capability the product documents call "what converts a chatbot into
an operational employee": the AI must make the change in the booking system, not
redirect the customer to the app.

Endpoints, and where each one came from:

    GET  /events/event-books/?user={uid}                 member's bookings
    GET  /events/events/{event_token}/bookings/          a session's roster
    POST /events/events/{event_token}/book/              create
    POST /events/event-books/{booking_token}/cancel/     cancel
    POST /events/events/{event_token}/add-to-waiting-list/
    POST /events/event-books/{booking_token}/reschedule/

**The booking id is the row's `token`, not its `id`.** The list serializer
returns `id: null` on every row, which is why an earlier pass through this API
concluded cancellation was impossible — it was looking for `id`. `token` is
present and is what `.../cancel/` wants. Do not mix it up with the *event* token
(`events/{event_token}/…`), which identifies the class, not the booking.

Statuses on a booking row:
    booked · waiting-list · allocated
A row with `canceled_at` set is cancelled.

The booking endpoints and the guard order below were taken from NUMA's
production bot (`bot_booking.py`), which has run them against real members:
**check credits -> check for a duplicate -> book -> read back and verify.**
"""

import os
import sys
from datetime import datetime, timedelta

try:  # loaded by exports.py
    from _angulare_client import call, date_str, err, ok
except ImportError:  # standalone: python3 tools/booking.py
    import importlib.util as _iu

    _spec = _iu.spec_from_file_location(
        "_angulare_client",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client.py"),
    )
    sys.modules["_angulare_client"] = _mod = _iu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    from _angulare_client import call, date_str, err, ok  # noqa: E402,F811


ACTIVE_STATUSES = ("booked", "waiting-list", "allocated")


def _fail(status, message, hint=None, **extra):
    """`err()` takes only (status, message, hint); this carries extra context."""
    out = err(status, message, hint)
    out.update(extra)
    return out


def _normalize_booking(row):
    if not isinstance(row, dict):
        return row
    event = row.get("event_info") if isinstance(row.get("event_info"), dict) else {}
    instructor = event.get("instructor_detail") if isinstance(event.get("instructor_detail"), dict) else {}
    return {
        #: feed this to cancel_booking() / reschedule_booking()
        "booking_token": row.get("token"),
        "user_id": row.get("user"),
        "status": row.get("status"),
        "spot": row.get("map_spot_code"),
        "canceled": bool(row.get("canceled_at")),
        "canceled_at": row.get("canceled_at"),
        #: server-computed deadline — use this instead of re-deriving the policy
        "can_cancel_until": row.get("can_cancel_until"),
        "checked_in_at": row.get("checkin_at") or row.get("check_in_at"),
        "event_token": event.get("token"),
        "class_name": event.get("name"),
        "date": event.get("event_date"),
        "hour": (event.get("event_hour") or "")[:5] or None,
        "starts_at": event.get("start_time"),
        "instructor": instructor.get("nickname") or instructor.get("first_name"),
    }


def my_bookings(user_id, days_ahead=7, include_past=False, take=50):
    """A member's bookings, upcoming by default.

    This is the only place the **booking token** comes from — you need it for
    both cancelling and rescheduling, so start here.
    """
    result = call("GET", "/api/v1/events/event-books/",
                  params={"user": user_id, "limit": min(int(take or 50), 100)})
    if not result["ok"]:
        return result
    data = result["data"] or {}
    rows = data.get("results") if isinstance(data, dict) else None

    now = datetime.now()
    horizon = now + timedelta(days=days_ahead) if days_ahead else None
    out = []
    for row in (rows or []):
        b = _normalize_booking(row)
        if b.get("canceled"):
            continue
        if b.get("status") not in ACTIVE_STATUSES:
            continue
        starts = b.get("starts_at")
        if starts and not include_past:
            try:
                when = datetime.fromisoformat(str(starts).replace("Z", "+00:00")).replace(tzinfo=None)
                if when < now:
                    continue
                if horizon and when > horizon:
                    continue
            except ValueError:
                pass
        out.append(b)
    out.sort(key=lambda b: str(b.get("starts_at") or ""))
    return ok({"count": len(out), "bookings": out})


def session_bookings(event_token, take=100):
    """Who is booked into one session, with their booking tokens.

    Use this to answer "is this member already in the class", and to read a
    booking back after a write.
    """
    result = call("GET", f"/api/v1/events/events/{event_token}/bookings/",
                  params={"limit": min(int(take or 100), 100)})
    if not result["ok"]:
        return result
    data = result["data"] or {}
    rows = data.get("results") if isinstance(data, dict) else (data if isinstance(data, list) else None)
    return ok({"count": len(rows or []),
               "bookings": [_normalize_booking(r) for r in (rows or [])]})


def _booking_for(result_payload, user_id):
    for row in (result_payload or []):
        if str(row.get("user_id")) == str(user_id) and not row.get("canceled"):
            return row
    return None


def _find_booking(event_token, user_id):
    found = session_bookings(event_token)
    if not found["ok"]:
        return found, None
    return found, _booking_for(found["data"]["bookings"], user_id)


def book(event_token, user_id, spot_code=None, check_credits=True, confirm=False):
    """Book a member into a session. The change happens in Angulare.

    Runs the same guards NUMA's bot runs, in the same order, because each one
    prevents a failure that actually happened:

      1. **already booked?** — the API will happily accept a duplicate
      2. **has credits?** — a booking without credits succeeds and then fails
         at check-in, which is worse than refusing
      3. book, then **read back** — a 200 is not proof the member is in class

    `spot_code` is the mat/bike position (`map_spot_code`). Omit it and the
    provider assigns one. Pass `check_credits=False` for aggregator members
    (Wellhub/TotalPass), whose entitlement does not live in the credit balance.
    """
    if not confirm:
        return _fail(None, "book is a write and requires confirm=True",
                   hint="it creates a real reservation in the member's name")

    existing, already = _find_booking(event_token, user_id)
    if not existing["ok"]:
        return existing
    if already:
        return _fail(None, "this member already has a booking for that session",
                   status_already=already.get("status"),
                   spot=already.get("spot"),
                   booking_token=already.get("booking_token"),
                   hint="do not create a duplicate — reuse the existing booking")

    if check_credits:
        member = call("GET", f"/api/v1/users/users/{user_id}/")
        if not member["ok"]:
            return member
        stats = (member["data"] or {}).get("user_stats")
        credits = (stats or {}).get("credits_available_all_packages") if isinstance(stats, dict) else None
        if credits is not None and int(credits) <= 0:
            return _fail(None, "this member has no credits",
                       credits=int(credits),
                       hint="booking without credits succeeds here and then fails at "
                            "check-in. Sell a package first, or pass check_credits=False "
                            "for an aggregator member.")

    body = {"user": int(user_id)}
    if spot_code is not None:
        body["map_spot_code"] = str(spot_code)
    created = call("POST", f"/api/v1/events/events/{event_token}/book/", body=body)
    if not created["ok"]:
        return created

    after, booking = _find_booking(event_token, user_id)
    if not after["ok"]:
        return _fail(created.get("status"),
                   "the booking call returned OK but the read-back failed",
                   hint="re-check with my_bookings() before retrying — the booking "
                        "may well exist",
                   raw=created.get("data"))
    if not booking:
        return _fail(None, "the booking call returned OK but the member is not in the session",
                   raw=created.get("data"),
                   hint="do NOT report success to the customer. Re-read with "
                        "session_bookings() and escalate if it stays missing.")
    if spot_code is not None and str(booking.get("spot")) != str(spot_code):
        return ok({"booked": True, "spot_matches": False,
                   "booking": booking,
                   "note": "booked, but not in the requested spot — the provider may have "
                           "assigned another. Do not confirm the spot to the customer."})
    return ok({"booked": True, "spot_matches": True, "booking": booking})


def cancel_booking(booking_token, confirm=False):
    """Cancel a booking. `booking_token` comes from `my_bookings()`.

    Read `can_cancel_until` (on the same row) before calling: it is the
    server-computed deadline for a credit-refunding cancellation. Past it, the
    cancellation still works but the credit is forfeit — so say so first rather
    than reporting the outcome afterwards.
    """
    if not confirm:
        return _fail(None, "cancel_booking is a write and requires confirm=True",
                   hint="it cancels a real reservation and can forfeit a credit")
    result = call("POST", f"/api/v1/events/event-books/{booking_token}/cancel/", body={})
    if not result["ok"]:
        return result
    return ok({"canceled": True, "booking_token": booking_token,
               "raw": result.get("data")})


def join_waitlist(event_token, user_id, confirm=False):
    """Put a member on a session's waiting list.

    The provider promotes people on its own rules — this does not reserve
    anything, so never tell the customer they have a spot.
    """
    if not confirm:
        return _fail(None, "join_waitlist is a write and requires confirm=True",
                   hint="it registers the member on a real waiting list")
    existing, already = _find_booking(event_token, user_id)
    if not existing["ok"]:
        return existing
    if already:
        return _fail(None, "this member is already on this session",
                   status_already=already.get("status"),
                   booking_token=already.get("booking_token"))
    result = call("POST", f"/api/v1/events/events/{event_token}/add-to-waiting-list/",
                  body={"user": int(user_id)})
    if not result["ok"]:
        return result
    _, booking = _find_booking(event_token, user_id)
    if not booking:
        return _fail(None, "the waitlist call returned OK but the member is not on the list",
                   raw=result.get("data"),
                   hint="do not tell the customer they are on the waitlist until this reads back")
    return ok({"waitlisted": True, "status": booking.get("status"), "booking": booking})


def reschedule_booking(booking_token, to_event_token, spot_code=None, confirm=False):
    """Move a booking to another session.

    ⚠️ **The request body is not verified.** The endpoint exists
    (`POST /events/event-books/{token}/reschedule/`) but NUMA's bot never uses
    it, so unlike `book`/`cancel`/`join_waitlist` this has not been exercised
    against production. Try it on a throwaway booking before relying on it.

    If it fails, the safe fallback is cancel-then-book, with the caveat the
    product doc raises: if the cancel succeeds and the new booking fails, the
    member has lost the spot and possibly a credit. Check the target session has
    capacity **before** cancelling anything.
    """
    if not confirm:
        return _fail(None, "reschedule_booking is a write and requires confirm=True",
                   hint="it moves a real reservation between sessions")
    body = {"event": to_event_token}
    if spot_code is not None:
        body["map_spot_code"] = str(spot_code)
    result = call("POST", f"/api/v1/events/event-books/{booking_token}/reschedule/", body=body)
    if not result["ok"]:
        result.setdefault("hint", "if this endpoint rejects the body, fall back to "
                                  "cancel-then-book after confirming the target has capacity")
        return result
    return ok({"rescheduled": True, "booking_token": booking_token,
               "to_event_token": to_event_token, "raw": result.get("data"),
               "note": "body unverified — confirm with my_bookings() that the date moved"})
