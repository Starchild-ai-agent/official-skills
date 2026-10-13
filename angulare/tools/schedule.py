"""Angulare class sessions — the agenda, one session, and its roster.

A "session" here is one concrete occurrence of a class (`evento`). Its
identifier is a UUID called `token` — that same token is what the attendance
report and the nested roster endpoint key on.

Verified: GET /api/v1/events/events/?date=YYYY-MM-DD narrows the list
(465 total -> 2 for a given day). `ordering`, `unit`, `activity` and `token`
are NOT filters (silently ignored).
"""

import os
import sys

try:  # loaded by exports.py
    from _angulare_client import _parse_dt, call, class_end, date_str, err, ok, page
except ImportError:  # standalone
    import importlib.util as _iu

    _spec = _iu.spec_from_file_location(
        "_angulare_client",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client.py"),
    )
    sys.modules["_angulare_client"] = _mod = _iu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    from _angulare_client import _parse_dt, call, class_end, date_str, err, ok, page  # noqa: E402,F811


def _activity_name(row):
    detail = row.get("activity_detail")
    if isinstance(detail, dict):
        return detail.get("name") or detail.get("title")
    return row.get("activity_name") or row.get("name")


def _normalize(row):
    if not isinstance(row, dict):
        return row
    return {
        "id": row.get("id"),
        "token": row.get("token"),
        "activity": _activity_name(row),
        "activity_id": row.get("activity"),
        "start": row.get("start_time"),
        "end": row.get("end_time"),
        "date": date_str(row.get("event_date") or row.get("start_time")),
        "duration_minutes": row.get("duration_time"),
        "attendees_booked": row.get("attendees_booked"),
        "max_attendees": row.get("max_attendees"),
        "bookable_until": row.get("bookable_until"),
        "booking_strategy": row.get("booking_strategy"),
        "closed_at": row.get("closed_at"),
        "canceled_at": row.get("canceled_at"),
        "event_type": row.get("event_type"),
        "instructor": row.get("instructor_name") or row.get("instructor"),
        "room": row.get("room_name") or row.get("room"),
        "unit": row.get("unit"),
    }


def sessions(date=None, take=100, skip=0, all_pages=False, max_pages=10):
    """Class sessions, optionally for one day (`date` accepts "today", "+1", …).

    With `all_pages=True` it walks pagination up to `max_pages` (the API is
    not date-sorted, so a single page is a poor sample).
    """
    collected, next_page, pages = [], 1, 0
    while True:
        result = call("GET", "/api/v1/events/events/", params={
            "date": date_str(date),
            "page_size": take,
            "page": next_page,
        })
        if not result["ok"]:
            return result
        p = page(result)
        collected += p["results"]
        pages += 1
        if not all_pages or not p["next"] or pages >= max_pages:
            return ok({"count": p["count"], "returned": len(collected),
                       "sessions": [_normalize(r) for r in collected]})
        next_page += 1


def session(event_token):
    """One session by its token, including the activity and instructor detail."""
    result = call("GET", f"/api/v1/events/events/{event_token}/")
    if not result["ok"]:
        return result
    return ok(_normalize(result["data"] or {}))


def session_roster(event_token):
    """Everyone booked into one session, with their attendance status.

    This is the endpoint behind the "who attended class X?" question. The same
    data is also available flat via the attendance report (see attendance.py),
    which additionally exposes check-in timestamps.
    """
    result = call("GET", f"/api/v1/events/events/{event_token}/bookings/",
                  params={"page_size": 200})
    if not result["ok"]:
        return result
    p = page(result)
    rows = p["results"]
    return ok({
        "event_token": event_token,
        "count": p["count"],
        "bookings": [{
            "id": r.get("id"),
            "status": r.get("status"),
            "user_id": r.get("user") if not isinstance(r.get("user"), dict) else r["user"].get("id"),
            "user_name": (r.get("user_detail") or {}).get("first_name")
                         if isinstance(r.get("user_detail"), dict) else r.get("user_name"),
            "checkedin_at": r.get("checkedin_at"),
            "noshow_at": r.get("noshow_at"),
            "booked_at": r.get("booked_at") or r.get("created_at"),
            "is_first_activity_checkin": r.get("is_first_activity_checkin"),
        } for r in rows],
    })


def find_session(activity=None, date=None, time=None, take=100):
    """Resolve a human query ("Pilates", "19:00", "tomorrow") to one session.

    Returns {session, candidates, count}. `session` is None when nothing matched
    or the query was ambiguous — inspect `candidates` and ask the user.
    """
    import re
    import unicodedata

    def norm(value):
        text = unicodedata.normalize("NFKD", str(value or ""))
        return re.sub(r"\s+", " ", "".join(c for c in text if not unicodedata.combining(c))).strip().lower()

    listed = sessions(date=date, take=take, all_pages=True, max_pages=4)
    if not listed["ok"]:
        return listed
    rows = listed["data"]["sessions"]

    if activity:
        needle = norm(activity)
        rows = [r for r in rows if needle in norm(r.get("activity"))]
    if time:
        want = str(time).strip()[:2]
        rows = [r for r in rows if str(r.get("start") or "").startswith(want)]

    if not rows:
        return ok({"session": None, "candidates": [], "count": 0,
                   "reason": "no session matched; widen the date or check the activity name"})
    chosen = rows[0] if len(rows) == 1 else None
    return ok({"session": chosen, "candidates": rows[:15], "count": len(rows),
               "reason": None if chosen else "more than one session matched; pick from candidates"})
