"""Unified image skill — generate, edit, remove_background, inspect.

Design rules (see SKILL.md for the agent-facing version):
  * The AGENT writes the prompt. There are no prompt templates here. `prompt`
    is forwarded verbatim; the only thing the skill adds is an explicit
    "keep" clause when the caller provides one — and it is visible in the
    result so nothing is hidden.
  * Fail-closed. Unknown model, unsupported parameter, too many references,
    mask on a model without mask support → ValueError BEFORE any paid call.
    Nothing is silently dropped or downgraded.
  * Every job has its own directory + persisted request_id (client.py).
  * Optional edit transaction (transaction.py) keeps asset roles, approved
    revision and the auto-fix budget out of the chat context.
"""
from __future__ import annotations

import base64
import json
import os
import sys
from typing import Any, Dict, List, Optional

import requests

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import catalog  # noqa: E402
import client  # noqa: E402
import transaction as tx  # noqa: E402
from _cost_track import caller_headers, record_response  # noqa: E402

TOOL = "image"


# ── helpers ──────────────────────────────────────────────────────────────────

def _compose(prompt: str, keep: Optional[str]) -> str:
    p = (prompt or "").strip()
    if not p:
        raise ValueError("prompt is required and must describe the change in your own words")
    if keep and keep.strip():
        p += f"\nKeep unchanged: {keep.strip()}"
    return p


def _resolve_many(paths: Optional[List[str]], urls: Optional[List[str]]) -> List[str]:
    out: List[str] = []
    for p in paths or []:
        v, err = client.resolve_input(path=p)
        if err:
            raise ValueError(err)
        out.append(v)
    for u in urls or []:
        v, err = client.resolve_input(url=u)
        if err:
            raise ValueError(err)
        out.append(v)
    return out


def _fmt(params: Dict[str, Any]) -> str:
    return params.get("output_format", "png")


# ── public API ───────────────────────────────────────────────────────────────

def list_models() -> Dict[str, Any]:
    """Capability catalog: which model can edit / mask / how many refs / which params."""
    return catalog.describe()


def generate(prompt: str, model: Optional[str] = None, **params: Any) -> Dict[str, Any]:
    """Text → image. `params` are validated against the model's catalog entry.

    Common params: aspect_ratio (nano2/nanopro), resolution 1K|2K|4K (nanopro),
    image_size + quality + background (gpt), num_images, output_format, seed.
    """
    cat = catalog.load()
    alias = model or cat["default_generate"]
    m = catalog.get_model(alias, cat)
    if not m.get("id"):
        raise ValueError(f"'{alias}' has no text-to-image endpoint; use edit() with a reference or pick another model")
    if not model and m.get("status") != "default":
        raise ValueError(f"default model '{alias}' is not status=default; fix the catalog")
    clean = catalog.validate_params(alias, params, cat)
    body = {"prompt": _compose(prompt, None), **clean}
    res = client.run_job(m["id"], body, tool=TOOL, label=f"gen_{alias}",
                         timeout_s=m["timeout_s"], poll_s=m["poll_s"], fmt=_fmt(clean))
    res.update({"model": alias, "prompt": body["prompt"], "params": clean})
    return res


def edit(prompt: str, image_paths: Optional[List[str]] = None, image_urls: Optional[List[str]] = None,
         *, model: Optional[str] = None, keep: Optional[str] = None,
         mask_path: Optional[str] = None, tx_id: Optional[str] = None,
         auto_fix: bool = False, **params: Any) -> Dict[str, Any]:
    """Image(s) + instruction → edited image.

    image_paths[0] (or image_urls[0]) is the BASE that gets edited; the rest are
    references (logo, style, second subject…). Say what each reference is in the
    prompt ("image 2 is the logo to place…").
    keep      — what must not change; appended verbatim and returned.
    mask_path — white = editable, black = locked. Only models with mask=True.
    tx_id     — record this edit into an open transaction (see start_transaction).
                When given and image_paths is omitted, the transaction's current
                approved base is used automatically.
    auto_fix  — mark this call as an automatic retry; consumes the transaction's
                auto-fix budget and is refused once it is spent.
    """
    cat = catalog.load()
    alias = model or cat["default_edit"]
    m = catalog.get_model(alias, cat)
    if not m.get("edit_id"):
        raise ValueError(f"'{alias}' cannot edit images; models with edit: "
                         f"{', '.join(a for a, e in cat['models'].items() if e.get('edit_id'))}")

    t = None
    if tx_id:
        t = tx.load(tx_id)
        if auto_fix:
            if not tx.can_auto_fix(t):
                return {"success": False, "tx_id": tx_id,
                        "error": (f"auto-fix budget exhausted ({t['auto_fix']}/{tx.MAX_AUTO_FIX}). "
                                  "Show the candidates to the user and let them choose or give new instructions.")}
        if not image_paths and not image_urls:
            image_paths = [tx.current_base(t)]
        keep = keep or t.get("keep")

    refs = _resolve_many(image_paths, image_urls)
    if not refs:
        raise ValueError("edit() needs at least one image (image_paths or image_urls)")
    if len(refs) > m["refs_max"]:
        raise ValueError(f"'{alias}' accepts at most {m['refs_max']} images, got {len(refs)}")

    if m.get("no_prompt"):
        raise ValueError(f"'{alias}' is a fixed-function model; call remove_background() instead")

    clean = catalog.validate_params(alias, params, cat)
    body: Dict[str, Any] = {"prompt": _compose(prompt, keep), "image_urls": refs, **clean}

    if mask_path:
        if not m.get("mask"):
            raise ValueError(f"'{alias}' has no mask support. Models with mask: "
                             f"{', '.join(a for a, e in cat['models'].items() if e.get('mask')) or 'none'}")
        mv, err = client.resolve_input(path=mask_path)
        if err:
            raise ValueError(f"mask: {err}")
        body["mask_url"] = mv

    if t is not None and auto_fix:
        tx.consume_auto_fix(t)

    res = client.run_job(m["edit_id"], body, tool=TOOL, label=f"edit_{alias}",
                         timeout_s=m["timeout_s"], poll_s=m["poll_s"], fmt=_fmt(clean))
    res.update({"model": alias, "prompt": body["prompt"], "params": clean,
                "inputs": len(refs), "mask": bool(mask_path)})
    if image_paths:
        res["source_dims"] = client.image_dims(image_paths[0])
    if t is not None:
        rev = tx.record(t, model=alias, endpoint=m["edit_id"], prompt=body["prompt"], params=clean, result=res)
        res["tx_id"], res["rev"] = t["tx_id"], rev["rev"]
        res["auto_fix_left"] = tx.MAX_AUTO_FIX - t["auto_fix"]
    return res


def remove_background(image_path: Optional[str] = None, image_url: Optional[str] = None,
                      model: str = "bria-rmbg") -> Dict[str, Any]:
    """Dedicated cut-out → transparent PNG."""
    cat = catalog.load()
    m = catalog.get_model(model, cat)
    if not m.get("no_prompt"):
        raise ValueError(f"'{model}' is not a background-removal model")
    v, err = client.resolve_input(path=image_path, url=image_url)
    if err:
        raise ValueError(err)
    res = client.run_job(m["edit_id"], {"image_url": v}, tool=TOOL, label="rmbg",
                         timeout_s=m["timeout_s"], poll_s=m["poll_s"], fmt="png")
    res["model"] = model
    return res


def recover(job_id: str) -> Dict[str, Any]:
    """Fetch the output of an already-submitted job (after a timeout/network drop). No new charge."""
    return client.recover(job_id)


# ── transactions (thin wrappers) ─────────────────────────────────────────────

def start_transaction(goal: str, base_path: str, keep: str = "", **assets: str) -> Dict[str, Any]:
    """Open an edit transaction. Extra kwargs are asset roles: logo=..., mask=..., end_frame=..."""
    t = tx.start(goal=goal, keep=keep, assets={"base": base_path, **assets})
    return tx.summary(t)


def approve(tx_id: str, rev: int) -> Dict[str, Any]:
    return tx.summary(tx.approve(tx_id, rev))


def reject(tx_id: str, rev: int, reason: str = "") -> Dict[str, Any]:
    return tx.summary(tx.reject(tx_id, rev, reason))


def transaction(tx_id: str) -> Dict[str, Any]:
    return tx.summary(tx.load(tx_id))


# ── inspect (observe, don't judge) ───────────────────────────────────────────

_OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"

_MODE_HINTS = {
    "inspect": ("Answer the question about the image(s) directly and concretely. If asked about "
                "text, transcribe it exactly. If asked where something is, give approximate "
                "bounding boxes as fractions of width/height (x0,y0,x1,y1). Say 'not visible' "
                "rather than guessing. Do not evaluate quality unless asked."),
    "compare": ("You are shown several images in order. Describe what differs between them, "
                "focusing on the region/element the question names. Report what was preserved "
                "and what changed. Be specific; no quality verdicts unless asked."),
    "qa": ("Evaluate ONLY against the stated goal and constraints. Return JSON: "
           "{\"pass\": bool, \"issues\": [{\"what\": str, \"where\": str, \"severity\": \"major|minor\"}], "
           "\"confidence\": 0-1}. An intermediate step is judged by its own stated goal, not by "
           "final-deliverable standards."),
}


def _vision_chain(cat: Dict[str, Any]) -> List[str]:
    env = os.environ.get("IMAGE_VISION_MODELS", "").strip()
    if env:
        return [m.strip() for m in env.split(",") if m.strip()]
    return list(cat.get("vision", {}).get("chain", []))


def _img_part(path_or_url: str) -> Dict[str, Any]:
    if path_or_url.startswith(("http://", "https://")):
        return {"type": "image_url", "image_url": {"url": path_or_url}}
    v, err = client.resolve_input(path=path_or_url)
    if err:
        raise ValueError(err)
    return {"type": "image_url", "image_url": {"url": v}}


def inspect(images: List[str] | str, question: str, mode: str = "inspect",
            goal: Optional[str] = None, keep: Optional[str] = None,
            model: Optional[str] = None) -> Dict[str, Any]:
    """Ask a vision model a free-form question about one or more images.

    mode: inspect (OCR / where is X / what is this) | compare (image1 vs image2…) |
          qa (pass/fail against `goal` + `keep`; returns parsed JSON when possible)
    Unlike a fixed QA tool, this answers the question you asked.
    """
    if mode not in _MODE_HINTS:
        raise ValueError(f"mode must be one of {list(_MODE_HINTS)}")
    imgs = [images] if isinstance(images, str) else list(images)
    if not imgs:
        raise ValueError("at least one image is required")
    cat = catalog.load()
    chain = [model] if model else _vision_chain(cat)
    if not chain:
        raise ValueError("no vision model configured")

    text = _MODE_HINTS[mode]
    if mode == "qa":
        text += f"\nGoal: {goal or question}\nMust stay unchanged: {keep or 'not specified'}"
    content: List[Dict[str, Any]] = [{"type": "text", "text": f"{text}\n\nQuestion: {question}"}]
    for i, im in enumerate(imgs, 1):
        if len(imgs) > 1:
            content.append({"type": "text", "text": f"Image {i}:"})
        content.append(_img_part(im))

    headers = caller_headers({"Authorization": "Bearer fake-openrouter-key",
                              "Content-Type": "application/json"}, tool_default=TOOL)
    attempts = []
    for cand in chain:
        body = {"model": cand, "messages": [{"role": "user", "content": content}],
                "max_tokens": cat.get("vision", {}).get("max_tokens", 1200), "temperature": 0}
        try:
            r = requests.post(_OPENROUTER, headers=headers, json=body,
                              proxies=client.PROXIES, verify=False, timeout=90)
            record_response(r, request_url=_OPENROUTER, request_payload={"model": cand})
            if r.status_code != 200:
                attempts.append(f"{cand}: HTTP {r.status_code}")
                continue
            answer = r.json()["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001
            attempts.append(f"{cand}: {e}")
            continue
        out: Dict[str, Any] = {"success": True, "mode": mode, "model": cand, "answer": answer,
                               "cost_usd": float(r.headers.get("X-Credits-Used", 0) or 0)}
        if mode == "qa":
            try:
                s = answer[answer.index("{"): answer.rindex("}") + 1]
                out["verdict"] = json.loads(s)
            except (ValueError, json.JSONDecodeError):
                out["verdict"] = None
        return out
    return {"success": False, "error": "all vision models failed: " + "; ".join(attempts)}


if __name__ == "__main__":
    print(json.dumps(list_models(), indent=1, ensure_ascii=False))
