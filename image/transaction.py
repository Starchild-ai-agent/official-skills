"""Edit transaction sidecar — the memory the chat should not have to carry.

One JSON file per edit transaction under output/images/.tx/<tx_id>.json:
  assets      {role: path}   roles: base | logo | style_reference | mask | ...
  goal / keep what the user wants / what must NOT change (verbatim)
  revisions   [{rev, parent, model, endpoint, prompt, params, job_id,
                images, cost_usd, status: candidate|approved|rejected|failed}]
  approved    rev number the user accepted (next edit builds on THIS one)
  auto_fix    automatic retries consumed (hard cap MAX_AUTO_FIX)

Concurrency model: every mutation is read-modify-write under a per-transaction
file lock (fcntl) and NOTHING holds a snapshot across a paid call. A long edit
does reserve() (lock → check/consume budget → capture parent → unlock), runs the
model for minutes, then record() (lock → re-read LATEST state → append one
revision with the submit-time parent → unlock). A user approve/reject in the
meantime is never overwritten; two edits in flight append independently.
"""
from __future__ import annotations

import fcntl
import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Iterator, Optional

TX_DIR = os.path.join(os.environ.get("IMAGE_OUTPUT_DIR", "output/images"), ".tx")
MAX_AUTO_FIX = 1
_VALID_BASE = ("approved",)   # only these statuses may serve as the next base


def _path(tx_id: str) -> str:
    return os.path.join(TX_DIR, f"{tx_id}.json")


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


@contextmanager
def _locked(tx_id: str) -> Iterator[None]:
    """Cross-process exclusive lock for one transaction (blocking)."""
    os.makedirs(TX_DIR, exist_ok=True)
    fd = os.open(_path(tx_id) + ".lock", os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _read(tx_id: str) -> Dict[str, Any]:
    p = _path(tx_id)
    if not os.path.exists(p):
        raise ValueError(f"unknown transaction '{tx_id}'")
    with open(p) as f:
        return json.load(f)


def _write(tx: Dict[str, Any]) -> None:
    os.makedirs(TX_DIR, exist_ok=True)
    tmp = _path(tx["tx_id"]) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(tx, f, indent=1, default=str)
    os.replace(tmp, _path(tx["tx_id"]))


def start(goal: str, keep: str = "", assets: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    assets = dict(assets or {})
    if "base" not in assets:
        raise ValueError("assets must include a 'base' image role")
    for role, p in assets.items():
        if not os.path.isfile(p):
            raise ValueError(f"asset '{role}' not found: {p}")
    tx = {"tx_id": uuid.uuid4().hex[:10], "created_at": _now(), "goal": goal, "keep": keep,
          "assets": assets, "revisions": [], "approved": 0, "auto_fix": 0}
    with _locked(tx["tx_id"]):
        _write(tx)
    return tx


def load(tx_id: str) -> Dict[str, Any]:
    """Read-only snapshot. Never pass a snapshot back into a mutator."""
    with _locked(tx_id):
        return _read(tx_id)


def _rev(tx: Dict[str, Any], n: int) -> Optional[Dict[str, Any]]:
    return next((r for r in tx["revisions"] if r["rev"] == n), None)


def _valid_base_rev(tx: Dict[str, Any], n: int) -> bool:
    r = _rev(tx, n) if n else None
    return bool(r and r["status"] in _VALID_BASE and r.get("images"))


def current_base(tx: Dict[str, Any]) -> str:
    """Approved revision if it is STILL approved, else the original base.
    A rejected/failed pointer is never used."""
    if _valid_base_rev(tx, tx["approved"]):
        return _rev(tx, tx["approved"])["images"][0]["local_path"]
    return tx["assets"]["base"]


def _fallback_approved(tx: Dict[str, Any], from_rev: int) -> int:
    """Nearest still-approved ancestor of from_rev along the parent chain, else 0."""
    seen, n = set(), from_rev
    while n and n not in seen:
        seen.add(n)
        r = _rev(tx, n)
        if r is None:
            return 0
        n = r.get("parent", 0)
        if _valid_base_rev(tx, n):
            return n
    return 0


# ── mutations: all locked, all read-modify-write on the latest state ─────────

def reserve(tx_id: str, auto_fix: bool = False) -> Dict[str, Any]:
    """Call BEFORE the paid request. Atomically checks/consumes the auto-fix budget
    and returns submit-time context {parent, base, keep, auto_fix_left}.
    Raises ValueError when the budget is exhausted (nothing is charged)."""
    with _locked(tx_id):
        tx = _read(tx_id)
        if auto_fix:
            if tx["auto_fix"] >= MAX_AUTO_FIX:
                raise ValueError(
                    f"auto-fix budget exhausted ({tx['auto_fix']}/{MAX_AUTO_FIX}). "
                    "Show the candidates to the user and let them choose or give new instructions.")
            tx["auto_fix"] += 1
            _write(tx)
        parent = tx["approved"] if _valid_base_rev(tx, tx["approved"]) else 0
        return {"tx_id": tx_id, "parent": parent, "base": current_base(tx),
                "keep": tx.get("keep", ""), "auto_fix_left": MAX_AUTO_FIX - tx["auto_fix"]}


def record(tx_id: str, *, parent: int, model: str, endpoint: str, prompt: str,
           params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    """Call AFTER the paid request. Re-reads the latest state under lock and appends
    ONE revision; never touches approved / auto_fix / other revisions."""
    with _locked(tx_id):
        tx = _read(tx_id)
        rev = {"rev": len(tx["revisions"]) + 1, "parent": parent, "model": model,
               "endpoint": endpoint, "prompt": prompt, "params": params,
               "job_id": result.get("job_id"), "request_id": result.get("request_id"),
               "images": result.get("images") or [], "cost_usd": result.get("cost_usd", 0),
               "status": "candidate" if result.get("success") else "failed",
               "error": result.get("error"), "at": _now()}
        tx["revisions"].append(rev)
        _write(tx)
        return rev


def approve(tx_id: str, rev: int) -> Dict[str, Any]:
    with _locked(tx_id):
        tx = _read(tx_id)
        r = _rev(tx, rev)
        if r is None or r["status"] == "failed" or not r.get("images"):
            raise ValueError(f"revision {rev} does not exist, failed, or has no image")
        for o in tx["revisions"]:
            if o["status"] == "candidate" and o["rev"] != rev:
                o["status"] = "rejected"
        r["status"] = "approved"
        tx["approved"] = rev
        tx["auto_fix"] = 0          # a human decision resets the automatic budget
        _write(tx)
        return tx


def reject(tx_id: str, rev: int, reason: str = "") -> Dict[str, Any]:
    """Reject a revision. If it was the approved base, roll the pointer back to the
    nearest still-approved ancestor (or the original image)."""
    with _locked(tx_id):
        tx = _read(tx_id)
        r = _rev(tx, rev)
        if r is None:
            raise ValueError(f"revision {rev} does not exist")
        r["status"], r["reject_reason"] = "rejected", reason
        if tx["approved"] == rev:
            tx["approved"] = _fallback_approved(tx, rev)
        _write(tx)
        return tx


def summary(tx: Dict[str, Any]) -> Dict[str, Any]:
    return {"tx_id": tx["tx_id"], "goal": tx["goal"], "keep": tx["keep"],
            "assets": tx["assets"], "approved_rev": tx["approved"],
            "current_base": current_base(tx),
            "auto_fix_used": f"{tx['auto_fix']}/{MAX_AUTO_FIX}",
            "revisions": [{k: r.get(k) for k in ("rev", "parent", "model", "status", "cost_usd", "error")}
                          | {"images": [i["local_path"] for i in r.get("images", [])]}
                          for r in tx["revisions"]]}
