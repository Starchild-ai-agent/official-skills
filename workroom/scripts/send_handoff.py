#!/usr/bin/env python3
"""workroom send-handoff --room <room_id> --to <member_name|agent_name> --title <title> --body <text|@file>

Send a reusable handoff message into a Workroom with optional temp-files
attachments + sha256 verification.

Exit codes:
  0 success
  1 runtime/business failure (auth/permission/not-found/conflict/mismatch)
  2 usage error
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.parse
from pathlib import Path

import httpx

import _common as C

DEFAULT_TEMP_STORAGE = "http://sc-agent-backup.internal:8080"


def _json_error(err: str, message: str, detail: str = "", next_action: str = "", code: int = 1) -> None:
    payload = {
        "ok": False,
        "error": err,
        "message": message,
        "detail": detail,
        "next_action": next_action,
        "exit_code": code,
    }
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)


def _fail(args, err: str, message: str, detail: str = "", next_action: str = "", code: int = 1) -> None:
    if getattr(args, "json", False):
        _json_error(err, message, detail=detail, next_action=next_action, code=code)
    else:
        print(f"error: {message}", file=sys.stderr)
        if detail:
            print(f"detail: {detail}", file=sys.stderr)
        if next_action:
            print(f"next: {next_action}", file=sys.stderr)
    sys.exit(code)


def _ok(args, data: dict) -> None:
    if getattr(args, "json", False):
        payload = {
            "ok": True,
            "error": "",
            "message": "ok",
            "detail": "",
            "data": data,
        }
        print(json.dumps(payload, ensure_ascii=False))
        return

    C.info(f"  ✓ handoff sent to {data['target']['user_name']} ({data['target']['user_id']})")
    C.info(f"  ✓ title: {data['title']}")
    C.info(f"  ✓ status: {data['status']}  seq={data['seq']}  handoff_id={data['handoff_id']}")


def _read_body(raw: str) -> str:
    if raw.startswith("@"):
        p = Path(raw[1:]).expanduser()
        if not p.exists() or not p.is_file():
            raise ValueError(f"body file not found: {p}")
        return p.read_text(encoding="utf-8").strip()
    return raw.strip()


def _is_sha256(s: str) -> bool:
    t = s.strip().lower()
    return len(t) == 64 and all(c in "0123456789abcdef" for c in t)


def _resolve_target(args, room_id: str, target: str) -> dict:
    r = C.workroom_call("GET", f"/rooms/{room_id}/members")
    if r.status_code == 401:
        _fail(args, "unauthorized", "unauthorized (401)", r.text, "re-login / check JWT / run inside Fly machine")
    if r.status_code == 403:
        _fail(args, "forbidden", "forbidden (403)", r.text, "check room membership or owner-only restriction")
    if r.status_code == 404:
        _fail(args, "not_found", "room not found (404)", r.text, "check --room and run `workroom list`")
    if r.status_code == 409:
        _fail(args, "conflict", "room state conflict (409)", r.text, "run `workroom status <room_id>` then retry")
    if r.status_code != 200:
        _fail(args, "http_error", f"members query failed ({r.status_code})", r.text)

    members = r.json().get("members", [])
    needle = target.strip().lower()

    # priority: exact user_id, exact user_name, case-insensitive name
    for m in members:
        if str(m.get("user_id", "")).strip() == target.strip():
            return m
    for m in members:
        if str(m.get("user_name", "")).strip() == target.strip():
            return m
    for m in members:
        if str(m.get("user_name", "")).strip().lower() == needle:
            return m

    available = [f"{m.get('user_name') or '-'} ({m.get('user_id')})" for m in members]
    _fail(
        args,
        "not_found",
        "target not found in room members (404-like)",
        detail=f"target={target}; members={'; '.join(available[:10])}",
        next_action="run `python3 skills/workroom/scripts/members.py <room_id>` and pick an exact name/user_id",
    )
    return {}


def _temp_storage_url() -> str:
    return os.environ.get("TEMP_STORAGE_URL", DEFAULT_TEMP_STORAGE).rstrip("/")


def _fetch_code_sha256(args, code: str) -> str:
    token = C.get_user_jwt().strip()
    url = f"{_temp_storage_url()}/t/{urllib.parse.quote(code)}"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            with client.stream("GET", url, headers=headers) as r:
                if r.status_code != 200:
                    err_text = r.read().decode("utf-8", errors="replace")
                    if r.status_code == 401:
                        _fail(args, "unauthorized", "temp-files unauthorized (401)", err_text, "check JWT / run inside Fly machine")
                    if r.status_code == 403:
                        _fail(args, "forbidden", "temp-files forbidden (403)", err_text, "check scope and whether code is allowed")
                    if r.status_code == 404:
                        _fail(args, "not_found", "temp-files code not found (404)", err_text, "check --attach-code / regenerate via tf link")
                    if r.status_code == 409:
                        _fail(args, "conflict", "temp-files conflict (409)", err_text, "retry with a fresh tf code")
                    _fail(args, "http_error", f"temp-files fetch failed ({r.status_code})", err_text)

                sha_header = (r.headers.get("x-sha256") or r.headers.get("X-Sha256") or "").strip().lower()
                if _is_sha256(sha_header):
                    return sha_header

                h = hashlib.sha256()
                for chunk in r.iter_bytes():
                    if chunk:
                        h.update(chunk)
                return h.hexdigest()
    except httpx.HTTPError as e:
        _fail(args, "network_error", "temp-files request failed", str(e), "retry in a moment")
    return ""


def _verify_pairs(args, codes: list[str], expects: list[str]) -> list[dict]:
    if not expects:
        return []

    if len(expects) not in (1, len(codes)):
        _fail(
            args,
            "usage_error",
            "--expect-sha count must be 1 or equal to --attach-code count",
            code=2,
        )

    if len(expects) == 1 and len(codes) > 1:
        expects = expects * len(codes)

    results = []
    for code, expect in zip(codes, expects):
        exp = expect.strip().lower()
        if not _is_sha256(exp):
            _fail(args, "usage_error", "invalid --expect-sha (must be 64-char hex)", detail=f"value={expect}", code=2)
        actual = _fetch_code_sha256(args, code)
        match = (actual == exp)
        item = {
            "code": code,
            "expected_sha256": exp,
            "actual_sha256": actual,
            "match": match,
        }
        results.append(item)
        if not match:
            _fail(
                args,
                "sha256_mismatch",
                "sha256 mismatch",
                detail=f"code={code}, expected={exp}, got={actual}",
                next_action="regenerate tf code from correct artifact and retry",
                code=1,
            )
    return results


def _compose_content(target: dict, title: str, body: str, codes: list[str], verifies: list[dict]) -> str:
    lines = []
    mention = target.get("user_name")
    if mention:
        lines.append(f"@{mention} handoff")
    else:
        lines.append(f"target_user_id: {target.get('user_id')}")
        lines.append("handoff")
    lines.append(f"title: {title}")
    lines.append("body:")
    lines.append(body)

    if codes:
        lines.append("attachments:")
        verify_map = {v["code"]: v for v in verifies}
        for c in codes:
            v = verify_map.get(c)
            if v:
                lines.append(f"- code: {c}  sha256: {v['expected_sha256']}")
            else:
                lines.append(f"- code: {c}")

    lines.append("expect: fetch and reply with saved path + sha256")
    return "\n".join(lines).strip()


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="workroom send-handoff", description=__doc__)
    p.add_argument("--room", required=True, help="room id (rm_...)")
    p.add_argument("--to", required=True, help="target member name or user_id")
    p.add_argument("--title", required=True, help="handoff title")
    p.add_argument("--body", required=True, help="handoff body text, or @<file>")
    p.add_argument("--attach-code", action="append", default=[], help="temp-files code (tf_...), repeatable")
    p.add_argument("--expect-sha", action="append", default=[], help="sha256 for attach-code verification, repeatable")
    p.add_argument("--json", action="store_true", help="emit machine-readable envelope")
    args = p.parse_args(argv[1:])

    room_id = C.validate_room_id(args.room, arg_name="--room")
    C.require_env()

    title = args.title.strip()
    if not title:
        _fail(args, "usage_error", "--title is empty", code=2)

    try:
        body = _read_body(args.body)
    except ValueError as e:
        _fail(args, "usage_error", str(e), code=2)
    if not body:
        _fail(args, "usage_error", "--body is empty", code=2)

    codes = [c.strip() for c in (args.attach_code or []) if c.strip()]
    verifies = _verify_pairs(args, codes, args.expect_sha or [])

    target = _resolve_target(args, room_id, args.to)
    content = _compose_content(target, title, body, codes, verifies)

    payload = {"content": content, "reply_chain_depth": 0}
    r = C.workroom_call("POST", f"/rooms/{room_id}/messages", json=payload)

    if r.status_code == 401:
        _fail(args, "unauthorized", "unauthorized (401)", r.text, "re-login / check JWT / run inside Fly machine")
    if r.status_code == 403:
        _fail(args, "forbidden", "forbidden (403)", r.text, "check membership or owner-only boundary")
    if r.status_code == 404:
        _fail(args, "not_found", "room not found (404)", r.text, "check --room and target member")
    if r.status_code == 409:
        _fail(args, "conflict", "room conflict (409)", r.text, "run `workroom status <room_id>`; dedupe/retry after state check")
    if r.status_code != 201:
        _fail(args, "http_error", f"send failed ({r.status_code})", r.text)

    resp = r.json()
    seq = resp.get("seq")
    handoff_id = f"{room_id}:{seq}"
    out = {
        "status": "sent",
        "room_id": room_id,
        "target": {
            "input": args.to,
            "user_id": target.get("user_id"),
            "user_name": target.get("user_name") or target.get("user_id"),
            "member_kind": target.get("member_kind"),
        },
        "title": title,
        "attach_codes": codes,
        "verified": verifies,
        "seq": seq,
        "handoff_id": handoff_id,
    }
    _ok(args, out)

    prefix = C.get_key(room_id)
    if prefix:
        C.touch_key(prefix)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
