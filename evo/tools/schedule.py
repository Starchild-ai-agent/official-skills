"""EVO class/activity schedule: weekly agenda, session detail, free spots.

EVO's schedule is driven by a composite key:
    idConfiguration (the recurring activity slot) + activityDate (yyyy-MM-dd)
or by idActivitySession (one concrete occurrence). Booking uses the composite
key; per-slot booking additionally needs a slotNumber.
"""

import os
import re
import sys

try:  # loaded by exports.py
    from _evo_client import _call, _date_str, _norm, err, ok
except ImportError:  # standalone: python3 tools/schedule.py
    import importlib.util as _iu

    _spec = _iu.spec_from_file_location(
        "_evo_client",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client.py"),
    )
    sys.modules["_evo_client"] = _mod = _iu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    from _evo_client import _call, _date_str, _norm, err, ok  # noqa: E402,F811


def _hhmm(value):
    """'19:00:00' / '19:00' / '19' -> '19:00' (None-safe)."""
    if value is None:
        return None
    text = str(value).strip()
    match = re.match(r"^(\d{1,2})(?::(\d{2}))?", text)
    if not match:
        return text
    return f"{int(match.group(1)):02d}:{match.group(2) or '00'}"


def _available(capacity, occupancy):
    try:
        return int(capacity) - int(occupancy)
    except (TypeError, ValueError):
        return None


def _normalize_session(row):
    if not isinstance(row, dict):
        return row
    capacity = row.get("capacity")
    occupancy = row.get("ocupation")  # EVO's spelling
    spots = [{
        "number": s.get("number"),
        "available": s.get("available"),
        "name": (s.get("nameSpot") or "").strip() or None,
    } for s in (row.get("spots") or [])]
    return {
        "id_configuration": row.get("idConfiguration"),
        "id_activity": row.get("idActivity"),
        "id_activity_session": row.get("idAtividadeSessao") or row.get("idActivitySession"),
        "id_group_activity": row.get("idGroupActivity"),
        "name": row.get("name") or row.get("title"),
        "date": _date_str(row.get("activityDate") or row.get("date")),
        "start": _hhmm(row.get("startTime")),
        "end": _hhmm(row.get("endTime")),
        "capacity": capacity,
        "occupancy": occupancy,
        "available": _available(capacity, occupancy),
        "allow_spot_choice": row.get("allowChoosingSpot"),
        "spots": spots,
        "instructor": row.get("instructor"),
        "area": row.get("area"),
        "audience": row.get("audience"),
        "branch_name": row.get("branchName"),
        "code": row.get("code"),
        "status_code": row.get("status"),
        "status": row.get("statusName"),
        "member_status": row.get("memberStatus"),
        "booking_window": {
            "start": _hhmm(row.get("bookingStartTime")),
            "end": _hhmm(row.get("bookingEndTime")),
        },
        "allows_experimental_class": row.get("allowExperimentalClass"),
        "experimental_slots": row.get("experimentalClassSlots"),
    }


def schedule(date=None, id_branch=None, only_available=False, id_member=None,
             show_full_week=False, experimental_class=False, activity_ids=None,
             audience_ids=None, origin=None, take=None):
    """Weekly (or single-day) class agenda.

    `date` is the anchor day; pass show_full_week=True for Sunday..Saturday.
    `only_available=True` hides sessions with no free spot. Passing `id_member`
    annotates each session with that member's booking status.
    """
    result = _call("GET", "/api/v1/activities/schedule", params={
        "date": _date_str(date),
        "idBranch": id_branch,
        "onlyAvailables": only_available,
        "idMember": id_member,
        "showFullWeek": show_full_week,
        "experimentalClass": experimental_class,
        "idActivities": activity_ids,
        "idAudiences": audience_ids,
        "origin": origin,
        "take": take,
    })
    if not result["ok"]:
        return result
    rows = result["data"] if isinstance(result["data"], list) else []
    sessions = [_normalize_session(r) for r in rows]
    return ok({"count": len(sessions), "sessions": sessions})


def session_detail(id_configuration=None, activity_date=None, id_activity_session=None):
    """One session in full, including who is enrolled and every spot state.

    Pass either (id_configuration + activity_date) or id_activity_session.
    """
    if id_activity_session is None and (id_configuration is None or activity_date is None):
        return err(None, "session_detail needs id_activity_session, or both "
                         "id_configuration and activity_date")
    result = _call("GET", "/api/v1/activities/schedule/detail", params={
        "idConfiguration": id_configuration,
        "activityDate": _date_str(activity_date),
        "idActivitySession": id_activity_session,
    })
    if not result["ok"]:
        return result
    row = result["data"] or {}
    detail = _normalize_session(row)
    detail["enrollments"] = [{
        "id_member": e.get("idMember"),
        "id_prospect": e.get("idProspect"),
        "id_employee": e.get("idEmployee"),
        "name": e.get("name"),
        "status_code": e.get("status"),
        "slot_number": e.get("slotNumber"),
        "absent": e.get("justifiedAbsence"),
        "suspended": e.get("suspended"),
        "removed": e.get("removed"),
    } for e in (row.get("enrollments") or [])]
    return ok(detail)


def spots(id_configuration, date):
    """Which spot numbers are free in one session, plus the free count."""
    taken = _call("GET", "/api/v1/activities/list-unavailable-spots",
                  params={"idConfiguration": id_configuration, "date": _date_str(date)})
    if not taken["ok"]:
        return taken
    unavailable = (taken["data"] or {}).get("unavailableSpots") or []
    detail = session_detail(id_configuration=id_configuration, activity_date=date)
    capacity = free = None
    if detail["ok"]:
        capacity = detail["data"].get("capacity")
        free = detail["data"].get("available")
    return ok({
        "id_configuration": id_configuration,
        "date": _date_str(date),
        "capacity": capacity,
        "occupied": len(unavailable),
        "free": free,
        "unavailable_spots": unavailable,
        "allows_spot_choice": detail["data"].get("allow_spot_choice") if detail["ok"] else None,
    })


def find_session(activity=None, date=None, time=None, id_branch=None,
                 only_available=True, id_member=None):
    """Resolve a human query ("Pilates", "19:00", "tomorrow") to one session.

    Returns {session, candidates, matched_by}. `session` is None when nothing
    matched or the query was ambiguous — inspect `candidates` and ask the user.
    """
    agenda = schedule(date=date, id_branch=id_branch, only_available=only_available,
                      id_member=id_member)
    if not agenda["ok"]:
        return agenda

    sessions = agenda["data"]["sessions"]
    matched_by = []
    if activity:
        needle = _norm(activity)
        sessions = [s for s in sessions if needle in _norm(s.get("name"))]
        matched_by.append("activity")
    if time:
        wanted = _hhmm(time)
        sessions = [s for s in sessions if (s.get("start") or "").startswith(wanted[:2])]
        matched_by.append("time")
    if not sessions:
        return ok({"session": None, "candidates": [], "matched_by": matched_by,
                   "reason": "no session matched; widen the date or check the activity name"})

    session = sessions[0] if len(sessions) == 1 else None
    return ok({
        "session": session,
        "candidates": sessions[:15],
        "count": len(sessions),
        "matched_by": matched_by,
        "reason": None if session else "more than one session matched; pick one from candidates",
    })