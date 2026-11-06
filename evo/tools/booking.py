"""EVO booking: enroll a member in a class, cancel, read their bookings.

The write path is verify-by-default: after EVO accepts the call we re-read the
session and confirm the member actually appears (or disappeared, for cancels)
before reporting success. EVO returns `{"result": "..."}` for both outcomes of
a booking, so the write response alone is not proof.
"""

import os
import sys

try:  # loaded by exports.py
    from _evo_client import ATTENDANCE_STATUS, _call, _date_str, err, ok
    import _evo_members as _members
    import _evo_schedule as _schedule
except ImportError:  # standalone: python3 tools/booking.py
    import importlib.util as _iu

    _here = os.path.dirname(os.path.abspath(__file__))
    _root = os.path.dirname(_here)
    for _name, _path in (("_evo_client", os.path.join(_root, "client.py")),
                         ("_evo_members", os.path.join(_here, "members.py")),
                         ("_evo_schedule", os.path.join(_here, "schedule.py"))):
        _spec = _iu.spec_from_file_location(_name, _path)
        sys.modules[_name] = _mod = _iu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
    from _evo_client import ATTENDANCE_STATUS, _call, _date_str, err, ok  # noqa: E402,F811
    import _evo_members as _members  # noqa: E402,F811
    import _evo_schedule as _schedule  # noqa: E402,F811


def _is_enrolled(id_member, id_configuration, activity_date):
    """Read the session back and look for the member in its enrollment list."""
    detail = _schedule.session_detail(id_configuration=id_configuration,
                                      activity_date=activity_date)
    if not detail["ok"]:
        return None, detail
    for enrollment in detail["data"].get("enrollments", []):
        if str(enrollment.get("id_member")) == str(id_member) and not enrollment.get("removed"):
            return enrollment, None
    return None, None


def book(id_member, id_configuration, activity_date, slot_number=None, origin=None,
         verify=True):
    """Enroll a member in one class occurrence.

    `slot_number` is required only for activities with spot booking
    (allow_spot_choice / "mapa de posicoes") — call spots() first.
    """
    result = _call("POST", "/api/v1/activities/schedule/enroll", params={
        "idMember": id_member,
        "idConfiguration": id_configuration,
        "activityDate": _date_str(activity_date),
        "slotNumber": slot_number,
        "origin": origin,
    })
    if not result["ok"]:
        return result

    payload = {
        "id_member": id_member,
        "id_configuration": id_configuration,
        "date": _date_str(activity_date),
        "slot_number": slot_number,
        "evo_result": result["data"],
        "confirmed": None,
    }
    if verify:
        enrollment, failure = _is_enrolled(id_member, id_configuration, activity_date)
        if failure:
            payload["verification_error"] = failure["error"]
        payload["confirmed"] = enrollment is not None
        payload["enrollment"] = enrollment
        if enrollment is None:
            return {"ok": False, "status": result["status"], "data": payload,
                    "error": "EVO accepted the enrollment call but the member does not "
                             "appear in the session afterwards — most likely the class "
                             "was full, outside the booking window, or the member has no "
                             "entitlement for it.",
                    "hint": "check spots() and member_services() for this member"}
    return ok(payload)


def book_by_name(member, activity, date=None, time=None, slot_number=None,
                 id_branch=None, origin=None):
    """End-to-end: "book Ana into Pilates tomorrow at 19:00".

    Resolves the member (id/CPF/e-mail/phone/name) and the session, then books
    and verifies. Fails loudly with candidates when either lookup is ambiguous.
    """
    who = _members.resolve_member(member)
    if not who["ok"]:
        return who
    if not who["data"]["member"]:
        return err(None, f"no unique member matched {member!r}",
                   hint="pick one from candidates and pass its id_member")

    found = _schedule.find_session(activity=activity, date=date, time=time,
                                   id_branch=id_branch)
    if not found["ok"]:
        return found
    if not found["data"]["session"]:
        return err(None, f"no unique session matched {activity!r} on {date!r}"
                   + (f" at {time!r}" if time else ""),
                   hint=found["data"].get("reason") or "pass explicit ids")

    session = found["data"]["session"]
    member_row = who["data"]["member"]
    result = book(
        id_member=member_row["id_member"],
        id_configuration=session["id_configuration"],
        activity_date=session["date"],
        slot_number=slot_number,
        origin=origin,
    )
    if not result["ok"]:
        return result
    result["data"]["member"] = member_row
    result["data"]["session"] = session
    return result


def my_bookings(id_member, status=None):
    """A member's enrollments (GET /api/v2/activities/enroll/member)."""
    result = _call("GET", "/api/v2/activities/enroll/member",
                   params={"idMember": id_member, "status": status})
    if not result["ok"]:
        return result
    rows = result["data"] if isinstance(result["data"], list) else []
    return ok({"count": len(rows), "bookings": [{
        "id_configuration_enroll": r.get("idConfigurationEnroll"),
        "id_configuration": r.get("idConfiguration"),
        "activity": r.get("activityName"),
        "activity_group": r.get("activityGroup"),
        "status": r.get("status"),
        "enrolled_at": _date_str(r.get("enrollDate")),
        "start": _date_str(r.get("startDate")),
        "end": _date_str(r.get("endDate")),
        "weekday": r.get("weekDay"),
        "time": f"{r.get('startTime')}-{r.get('endTime')}",
        "spot_number": r.get("spotNumber"),
        "instructor": r.get("teacherName"),
    } for r in rows]})


def member_sessions(id_member, date_start=None, date_end=None, take=50, skip=0,
                    id_branch=None, activity_ids=None):
    """A member's past/future class sessions (GET /api/v2/activities/member/sessions).

    Rows carry presenca/falta/faltaJustificada, i.e. the attendance outcome.
    """
    result = _call("GET", "/api/v2/activities/member/sessions", params={
        "idMember": id_member,
        "dateStart": _date_str(date_start),
        "dateEnd": _date_str(date_end),
        "take": take,
        "skip": skip,
        "idBranch": id_branch,
        "idActivities": activity_ids,
    })
    if not result["ok"]:
        return result
    rows = result["data"] if isinstance(result["data"], list) else []
    return ok({"count": len(rows), "sessions": [{
        "id_configuration": r.get("idConfiguration"),
        "id_activity_session": r.get("idActivitieSession"),
        "activity": r.get("activitieName"),
        "date": _date_str(r.get("date")),
        "start": r.get("startTime"),
        "end": r.get("endTime"),
        "instructor": r.get("instructor"),
        "status": r.get("statusName"),
        "attended": r.get("presenca"),
        "absent": r.get("falta"),
        "justified_absence": r.get("faltaJustificada"),
        "spot_number": r.get("spotNumber"),
        "replacement": r.get("isReplacement"),
    } for r in rows]})


def _enrollment_id(id_member, id_configuration):
    """Find the idConfigurationEnroll for a member+activity, for cancellation."""
    listed = my_bookings(id_member)
    if not listed["ok"]:
        return None, listed
    matches = [b for b in listed["data"]["bookings"]
               if str(b.get("id_configuration")) == str(id_configuration)]
    if len(matches) == 1:
        return matches[0]["id_configuration_enroll"], None
    if not matches:
        return None, err(None, f"member {id_member} has no enrollment in activity "
                               f"{id_configuration}")
    return None, err(None, "several enrollments match that activity",
                     hint="pass id_configuration_enroll explicitly, from my_bookings()")


def cancel(id_member, id_configuration=None, id_configuration_enroll=None,
           id_configuration_participation=None, id_branch=None, verify=True):
    """Cancel an enrollment. Prefers the v2 endpoint (DELETE /api/v2/activities/enroll).

    Pass id_configuration_enroll, or just id_configuration and the enrollment id
    is resolved from my_bookings().
    """
    if id_configuration_enroll is None and id_configuration_participation is None:
        if id_configuration is None:
            return err(None, "cancel needs id_configuration_enroll "
                             "(or id_configuration to resolve it)")
        resolved, failure = _enrollment_id(id_member, id_configuration)
        if failure:
            return failure
        id_configuration_enroll = resolved

    if id_configuration_participation is not None:
        result = _call("DELETE", "/api/v1/activities/enrollment", params={
            "idMember": id_member,
            "idConfigurationParticipation": id_configuration_participation,
            "idBranch": id_branch,
        })
    else:
        result = _call("DELETE", "/api/v2/activities/enroll", params={
            "idMember": id_member,
            "idConfigurationEnroll": id_configuration_enroll,
            "idBranch": id_branch,
        })
    if not result["ok"]:
        return result

    payload = {
        "id_member": id_member,
        "id_configuration_enroll": id_configuration_enroll,
        "id_configuration_participation": id_configuration_participation,
        "evo_result": result["data"],
        "confirmed": None,
    }
    if verify and id_configuration is not None:
        listed = my_bookings(id_member)
        if listed["ok"]:
            still = [b for b in listed["data"]["bookings"]
                     if str(b.get("id_configuration")) == str(id_configuration)]
            payload["confirmed"] = not still
            payload["remaining"] = still
    return ok(payload)


def set_attendance(status, id_member=None, id_prospect=None, id_configuration=None,
                   activity_date=None, id_activity_session=None, id_branch=None):
    """Mark a member as attending / absent / justified-absent in a session.

    `status` accepts 0/1/2 or "attending"/"absent"/"justified_absence".
    """
    code = status
    if isinstance(status, str) and not status.isdigit():
        lookup = {v: k for k, v in ATTENDANCE_STATUS.items()}
        code = lookup.get(status.strip().lower())
    if code is None:
        return err(None, f"unknown attendance status {status!r}",
                   hint="use 0/1/2 or attending/absent/justified_absence")
    result = _call("POST", "/api/v1/activities/schedule/enroll/change-status", params={
        "status": code,
        "idMember": id_member,
        "idProspect": id_prospect,
        "idConfiguration": id_configuration,
        "activityDate": _date_str(activity_date),
        "idActivitySession": id_activity_session,
        "idBranch": id_branch,
    })
    if not result["ok"]:
        return result
    return ok({"status_code": code, "status": ATTENDANCE_STATUS.get(code),
               "evo_result": result["data"]})