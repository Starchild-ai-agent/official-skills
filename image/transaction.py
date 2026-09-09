"""Edit transaction sidecar — the memory the chat should not have to carry.

One JSON file per edit transaction under output/images/.tx/<tx_id>.json:
  assets      {role: path}   roles: base | logo | style_reference | mask |
                             start_frame | end_frame | <any string>
  goal        what the user wants (verbatim, one sentence)
  keep        what must NOT change (verbatim)
  revisions   [{rev, parent, model, endpoint, prompt, params, job_id,
                images, cost_usd, status: candidate|approved|rejected}]
  approved    rev number the user accepted (later edits build on THIS one)
  auto_fix    count of automatic retries consumed (hard cap, see MAX_AUTO_FIX)

Why: on the audited machine the agent re-derived "which image is the base"
from chat text after every compaction, silently promoted rejected outputs to
the next base, and re-ran review loops that reset when a file was renamed or
cropped. The transaction makes those states explicit and the budget sticky.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

TX_DIR = os.path.join(os.environ.get("IMAGE_OUTPUT_DIR", "output/images"), ".tx")
MAX_AUTO_FIX = 1   # automatic retries per transaction; beyond this, hand candidates to the user


def _path(tx_id: str) -> str:
    return os.path.join(TX_DIR, f"{tx_id}.json")


def _save(tx: Dict[str, Any]) -> None:
    os.makedirs(TX_DIR, exist_ok=True)
    tmp = _path(tx["tx_id"]) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(tx, f, indent=1, default=str)
    os.replace(tmp, _path(tx["tx_id"]))


def start(goal: str, keep: str = "", assets: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Open a transaction. `assets` maps role → local path (base is required)."""
    assets = dict(assets or {})
    if "base" not in assets:
        raise ValueError("assets must include a 'base' image role")
    for role, p in assets.items():
        if not os.path.isfile(p):
            raise ValueError(f"asset '{role}' not found: {p}")
    tx = {"tx_id": uuid.uuid4().hex[:10], "created_at": datetime.utcnow().isoformat() + "Z",
          "goal": goal, "keep": keep, "assets": assets, "revisions": [],
          "approved": 0, "auto_fix": 0}
    _save(tx)
    return tx


def load(tx_id: str) -> Dict[str, Any]:
    p = _path(tx_id)
    if not os.path.exists(p):
        raise ValueError(f"unknown transaction '{tx_id}'")
    with open(p) as f:
        return json.load(f)


def current_base(tx: Dict[str, Any]) -> str:
    """Path the next edit must start from: the approved revision, else the original base."""
    if tx["approved"] == 0:
        return tx["assets"]["base"]
    for r in tx["revisions"]:
        if r["rev"] == tx["approved"] and r["images"]:
            return r["images"][0]["local_path"]
    return tx["assets"]["base"]


def record(tx: Dict[str, Any], *, model: str, endpoint: str, prompt: str,
           params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    rev = {"rev": len(tx["revisions"]) + 1, "parent": tx["approved"], "model": model,
           "endpoint": endpoint, "prompt": prompt, "params": params,
           "job_id": result.get("job_id"), "request_id": result.get("request_id"),
           "images": result.get("images") or [], "cost_usd": result.get("cost_usd", 0),
           "status": "candidate" if result.get("success") else "failed",
           "error": result.get("error"), "at": datetime.utcnow().isoformat() + "Z"}
    tx["revisions"].append(rev)
    _save(tx)
    return rev


def approve(tx_id: str, rev: int) -> Dict[str, Any]:
    tx = load(tx_id)
    revs = {r["rev"]: r for r in tx["revisions"]}
    if rev not in revs or revs[rev]["status"] == "failed":
        raise ValueError(f"revision {rev} does not exist or failed")
    for r in tx["revisions"]:
        if r["status"] == "candidate" and r["rev"] != rev:
            r["status"] = "rejected"
    revs[rev]["status"] = "approved"
    tx["approved"] = rev
    tx["auto_fix"] = 0          # a human decision resets the automatic budget
    _save(tx)
    return tx


def reject(tx_id: str, rev: int, reason: str = "") -> Dict[str, Any]:
    tx = load(tx_id)
    for r in tx["revisions"]:
        if r["rev"] == rev:
            r["status"], r["reject_reason"] = "rejected", reason
    _save(tx)
    return tx


def can_auto_fix(tx: Dict[str, Any]) -> bool:
    return tx["auto_fix"] < MAX_AUTO_FIX


def consume_auto_fix(tx: Dict[str, Any]) -> None:
    tx["auto_fix"] += 1
    _save(tx)


def summary(tx: Dict[str, Any]) -> Dict[str, Any]:
    return {"tx_id": tx["tx_id"], "goal": tx["goal"], "keep": tx["keep"],
            "assets": tx["assets"], "approved_rev": tx["approved"],
            "current_base": current_base(tx),
            "auto_fix_used": f"{tx['auto_fix']}/{MAX_AUTO_FIX}",
            "revisions": [{k: r.get(k) for k in ("rev", "parent", "model", "status", "cost_usd", "error")}
                          | {"images": [i["local_path"] for i in r.get("images", [])]}
                          for r in tx["revisions"]]}
