"""Angulare attendance — who actually showed up, and when.

This is the module behind the "message the member 2 hours after their first
class" scenario.

Endpoint: GET /api/v1/events/reports/event-books/
Verified working filters (and ONLY these): `status`, `user_id`, `event_token`,
`page`, `page_size`. Everything else — including `is_first_activity_checkin`,
`checkedin_at__isnull`, `event_time__gte`, `ordering`, `search` — is **silently
ignored**: the request succeeds and returns the full set. Never trust a filter
here without checking that the returned `count` changed.

Aggregator check-ins (TotalPass / Wellhub) live on a different endpoint and only
accept `date`.
"""

import os
import sys
from datetime import datetime, timedelta, timezone

try:  # loaded by exports.py
    from _angulare_client import (ATTENDANCE_STATUS, _parse_dt, call, class_end,
                                  date_str, err, ok, page)
except ImportError:  # standalone
    import importlib.util as _iu

    _spec = _iu.spec_from_file_location(
        "_angulare_client",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client.py"),
    )
    sys.modules["_angulare_client"] = _mod = _iu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    from _angulare_client import (ATTENDANCE_STATUS, _parse_dt, call, class_end,  # noqa: E402,F811
                                  date_str, err, ok, page)

REPORT = "/api/v1/events/reports/event-books/"


def _person(row):
    info = row.get("user_info") if isinstance(row.get("user_info"), dict) else {}
    name = " ".join(x for x in (info.get("first_name"), info.get("last_name")) if x).strip()
    return {"id": row.get("user_id") or info.get("id"),
            "name": name or None,
            "email": info.get("email"),
            "tags": info.get("tags")}


def _normalize(row):
    if not isinstance(row, dict):
        return row
    event = row.get("event_info") if isinstance(row.get("event_info"), dict) else {}
    activity = row.get("activity_info") if isinstance(row.get("activity_info"), dict) else {}
    instructor = row.get("instructor_info") if isinstance(row.get("instructor_info"), dict) else {}
    end = class_end(row)
    return {
        "id": row.get("id"),
        "status": row.get("status"),
        "member": _person(row),
        "event_id": row.get("event_id"),
        "event_token": event.get("token"),
        "event_name": event.get("name"),
        "activity": activity.get("name"),
        "instructor": " ".join(x for x in (instructor.get("first_name"),
                                           instructor.get("last_name")) if x) or None,
        "class_start": row.get("event_time"),
        "class_end": end.isoformat() if end else None,
        "checkedin_at": row.get("checkedin_at"),
        "checkedout_at": row.get("checkedout_at"),
        "noshow_at": row.get("noshow_at"),
        "booked_at": row.get("booked_at") or row.get("created_at"),
        "is_first_activity_checkin": row.get("is_first_activity_checkin"),
        "checkin_number": row.get("checkin_number"),
        "checkin_activity_number": row.get("checkin_activity_number"),
        "booking_source": row.get("booking_source"),
        "consumption_status": row.get("consumption_status"),
        "credits_spent": row.get("credits_spended"),
        "is_unpaid": row.get("is_unpaid"),
        "crm_case_stage": row.get("crm_case_stage"),
        "crm_case_token": row.get("crm_case_token"),
    }


def _fetch(status=None, user_id=None, event_token=None, take=200,
           max_pages=10, all_pages=False):
    collected, page_no, pages = [], 1, 0
    while True:
        result = call("GET", REPORT, params={
            "status": status,
            "user_id": user_id,
            "event_token": event_token,
            "page_size": take,
            "page": page_no,
        })
        if not result["ok"]:
            return result
        p = page(result)
        collected += p["results"]
        pages += 1
        if not all_pages or not p["next"] or pages >= max_pages:
            return ok({"count": p["count"], "returned": len(collected), "rows": collected})
        page_no += 1


def attendance(status=None, user_id=None, event_token=None, take=200, skip=0,
               all_pages=False, max_pages=10):
    """Attendance / booking rows.

    `status` — one of: checked-in, booked, waiting-list, canceled, no-show,
    late-canceled. `user_id` — one member's whole history. `event_token` — one
    class's full roster (the most precise query).
    """
    if isinstance(status, str) and status not in ATTENDANCE_STATUS:
        return err(None, f"unknown status {status!r}",
                   hint="use one of: " + ", ".join(ATTENDANCE_STATUS))
    fetched = _fetch(status=status, user_id=user_id, event_token=event_token,
                     take=take, max_pages=max_pages, all_pages=all_pages)
    if not fetched["ok"]:
        return fetched
    rows = fetched["data"]["rows"]
    return ok({"count": fetched["data"]["count"], "returned": len(rows),
               "rows": [_normalize(r) for r in rows]})


def first_experience_checkins(event_token=None, take=200, max_pages=10):
    """Checked-in rows flagged `is_first_activity_checkin` (their first class).

    ⚠️ The API cannot filter on that flag, so this scans `status=checked-in`
    pages and filters client-side. Raise `max_pages` if you need deeper history;
    narrow with `event_token` when you already know the class.
    """
    fetched = _fetch(status="checked-in", event_token=event_token, take=take,
                     max_pages=max_pages, all_pages=True)
    if not fetched["ok"]:
        return fetched
    rows = [r for r in fetched["data"]["rows"] if r.get("is_first_activity_checkin")]
    normalized = [_normalize(r) for r in rows]
    normalized.sort(key=lambda r: r.get("class_end") or "", reverse=True)
    return ok({"scanned": fetched["data"]["returned"],
               "first_experience": len(normalized), "rows": normalized})


def followup_candidates(hours_after=2, window_minutes=90, first_experience_only=False,
                        event_token=None, take=200, max_pages=10, now=None):
    """Members whose class ended ~`hours_after` ago and who actually showed up.

    This is the 2-hour post-class follow-up feed. A row qualifies when
    `class_end + hours_after` has passed but is no older than `window_minutes`
    (so a poller does not re-send yesterday's cohort).

    `now` defaults to the current UTC time; pass a datetime for reproducible runs.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    fetched = _fetch(status="checked-in", event_token=event_token, take=take,
                     max_pages=max_pages, all_pages=True)
    if not fetched["ok"]:
        return fetched

    due, considered = [], 0
    for raw in fetched["data"]["rows"]:
        if first_experience_only and not raw.get("is_first_activity_checkin"):
            continue
        end = class_end(raw)
        if not end:
            continue
        considered += 1
        fire_at = end + timedelta(hours=hours_after)
        if fire_at > now:
            continue
        if now - fire_at > timedelta(minutes=window_minutes):
            continue
        row = _normalize(raw)
        row["followup_due_at"] = fire_at.isoformat()
        due.append(row)

    due.sort(key=lambda r: r.get("class_end") or "")
    return ok({"scanned": fetched["data"]["returned"], "considered": considered,
               "due": len(due), "hours_after": hours_after,
               "window_minutes": window_minutes, "rows": due})


def member_attendance(user_id, take=200, max_pages=5):
    """One member's attendance history (newest class first)."""
    fetched = _fetch(user_id=user_id, take=take, max_pages=max_pages, all_pages=True)
    if not fetched["ok"]:
        return fetched
    rows = [_normalize(r) for r in fetched["data"]["rows"]]
    rows.sort(key=lambda r: r.get("class_start") or "", reverse=True)
    return ok({"count": fetched["data"]["count"], "returned": len(rows), "rows": rows})


def aggregator_checkins(date=None, take=200, all_pages=False, max_pages=5):
    """TotalPass / Wellhub check-ins for a day.

    `date` is the ONLY filter this endpoint honours. `checkin_type`, `status`
    and `unit` are ignored — filter those client-side.
    """
    collected, page_no, pages = [], 1, 0
    while True:
        result = call("GET", "/api/v1/events/external-checkins/", params={
            "date": date_str(date), "page_size": take, "page": page_no})
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
        "name": r.get("name"),
        "aggregator": r.get("checkin_type"),
        "status": r.get("status"),
        "pass_type": r.get("pass_type_name"),
        "user_token": r.get("user_token"),
        "transaction_token": r.get("transaction_token"),
        "created_at": r.get("created_at"),
        "last_error": r.get("last_error"),
    } for r in collected]
    return ok({"count": p["count"], "returned": len(rows), "checkins": rows})


def instructor_stats(take=50):
    """Aggregate per-instructor attendance: books, checkins, no-shows, cancels."""
    result = call("GET", "/api/v1/events/event-books/book-stats-by-instructor/",
                  params={"page_size": take})
    if not result["ok"]:
        return result
    p = page(result)
    return ok({"count": p["count"], "stats": [{
        "instructor_id": r.get("instructor"),
        "instructor": r.get("instructor_name"),
        "books": r.get("books"),
        "checkins": r.get("checkins"),
        "no_shows": r.get("no_shows"),
        "cancels": r.get("cancels"),
        "late_cancels": r.get("late_cancels"),
    } for r in p["results"]]})
