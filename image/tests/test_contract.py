"""Offline contract tests for the unified image skill (no network, no charge)."""
import os, sys, importlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import pytest

@pytest.fixture(autouse=True)
def _tmp_out(tmp_path, monkeypatch):
    monkeypatch.setenv("IMAGE_OUTPUT_DIR", str(tmp_path))
    import transaction, client
    importlib.reload(transaction); importlib.reload(client)
    yield

def _png(tmp_path, name="a.png"):
    from PIL import Image
    p = tmp_path / name; Image.new("RGB", (64, 48)).save(p); return str(p)

def test_catalog_rejects_unknown_model_and_params():
    import catalog
    with pytest.raises(ValueError, match="Unknown model"): catalog.get_model("nope")
    with pytest.raises(ValueError, match="does not support parameter 'mask_url'"):
        catalog.validate_params("nanopro", {"mask_url": "x"})
    with pytest.raises(ValueError, match="resolution"): catalog.validate_params("nanopro", {"resolution": "8K"})
    with pytest.raises(ValueError, match="within"): catalog.validate_params("gpt", {"num_images": 9})
    assert catalog.validate_params("nanopro", {"resolution": "2K", "num_images": "2", "seed": None}) == {"resolution": "2K", "num_images": 2}

def test_catalog_describe_has_mask_flag_only_on_gpt():
    import catalog
    d = catalog.describe()["models"]
    assert [a for a, m in d.items() if m["mask"]] == ["gpt"]
    assert d["seedream"]["status"] == "candidate"

def test_edit_fails_closed_before_paid_call(tmp_path, monkeypatch):
    import image_skill as s, client
    calls = []
    monkeypatch.setattr(client, "run_job", lambda *a, **k: calls.append(1) or {"success": True})
    p = _png(tmp_path)
    with pytest.raises(ValueError, match="no mask support"): s.edit("x", [p], model="nanopro", mask_path=p)
    with pytest.raises(ValueError, match="at most 6"): s.edit("x", [p] * 7, model="nanopro")
    with pytest.raises(ValueError, match="does not support parameter"): s.edit("x", [p], model="nanopro", quality="high")
    with pytest.raises(ValueError, match="prompt is required"): s.edit("", [p])
    with pytest.raises(ValueError, match="no text-to-image"): s.generate("x", model="seedream")
    with pytest.raises(ValueError, match="remove_background"): s.edit("x", [p], model="bria-rmbg")
    assert calls == []  # nothing was submitted

def test_edit_forwards_keep_and_validated_params(tmp_path, monkeypatch):
    import image_skill as s, client
    seen = {}
    def fake(endpoint, body, **kw):
        seen.update(endpoint=endpoint, body=body); return {"success": True, "images": [], "job_id": "j"}
    monkeypatch.setattr(client, "run_job", fake)
    p = _png(tmp_path)
    r = s.edit("swap W", [p, p], model="nanopro", keep="ALL ST", resolution="2K")
    assert seen["endpoint"] == "fal-ai/gemini-3-pro-image-preview/edit"
    assert seen["body"]["resolution"] == "2K" and len(seen["body"]["image_urls"]) == 2
    assert seen["body"]["prompt"].endswith("Keep unchanged: ALL ST")
    assert r["prompt"] == seen["body"]["prompt"] and r["inputs"] == 2
    r = s.edit("fill", [p], model="gpt", mask_path=p)
    assert "mask_url" in seen["body"] and seen["endpoint"] == "openai/gpt-image-2/edit"

def test_transaction_budget_and_base_tracking(tmp_path, monkeypatch):
    import image_skill as s, client, transaction as tx
    monkeypatch.setattr(client, "run_job", lambda e, b, **k: {"success": True, "job_id": "j",
                        "images": [{"local_path": _png(tmp_path, "out.png")}], "cost_usd": 0.1})
    base = _png(tmp_path, "base.png"); logo = _png(tmp_path, "logo.png")
    t = s.start_transaction("swap W", base, keep="ALL ST", logo=logo)
    tid = t["tx_id"]
    r1 = s.edit("try 1", tx_id=tid)                 # base auto-picked from tx
    assert r1["rev"] == 1 and r1["prompt"].endswith("Keep unchanged: ALL ST")
    r2 = s.edit("try 2", tx_id=tid, auto_fix=True)  # consumes the single auto-fix
    assert r2["auto_fix_left"] == 0
    r3 = s.edit("try 3", tx_id=tid, auto_fix=True)  # refused
    assert r3["success"] is False and "budget exhausted" in r3["error"]
    assert s.transaction(tid)["current_base"] == base   # candidates never become base
    s.approve(tid, 2)
    st = s.transaction(tid)
    assert st["current_base"].endswith("out.png") and st["auto_fix_used"] == "0/1"
    assert [r["status"] for r in st["revisions"]] == ["rejected", "approved"]

def test_job_dirs_unique_and_request_persisted(tmp_path, monkeypatch):
    import client
    class R:  # fake requests.post response
        status_code = 200; headers = {"X-Credits-Used": "0.15"}; text = ""
        def json(self): return {"request_id": "req1", "status_url": "s", "response_url": "r"}
    monkeypatch.setattr(client.requests, "post", lambda *a, **k: R())
    j1, d1 = client.new_job_dir("edit_x"); j2, d2 = client.new_job_dir("edit_x")
    assert d1 != d2
    data, err = client.submit("fal-ai/x/edit", {"prompt": "p", "image_urls": ["data:..."]}, "image", j1)
    assert err is None and client.load_job(j1)["request_id"] == "req1"
    assert client.load_job(j1)["body"]["image_urls"] == "<1 inputs>"  # no data URIs on disk

def test_inspect_mode_validation(tmp_path):
    import image_skill as s
    with pytest.raises(ValueError, match="mode"): s.inspect(_png(tmp_path), "q", mode="judge")
    with pytest.raises(ValueError, match="at least one"): s.inspect([], "q")


def test_approve_during_inflight_edit_is_not_overwritten(tmp_path, monkeypatch):
    """P1: user approves rev 1 while rev 2 is rendering → approval must survive."""
    import image_skill as s, client
    base = _png(tmp_path, "base.png")
    tid = s.start_transaction("g", base)["tx_id"]
    monkeypatch.setattr(client, "run_job", lambda e, b, **k: {"success": True, "job_id": "j",
                        "images": [{"local_path": _png(tmp_path, "r1.png")}], "cost_usd": 0.1})
    s.edit("rev1", tx_id=tid)
    def slow_job(e, b, **k):
        s.approve(tid, 1)   # user acts while the model is running
        return {"success": True, "job_id": "j2", "images": [{"local_path": _png(tmp_path, "r2.png")}], "cost_usd": 0.1}
    monkeypatch.setattr(client, "run_job", slow_job)
    r2 = s.edit("rev2", tx_id=tid)
    st = s.transaction(tid)
    assert st["approved_rev"] == 1 and st["current_base"].endswith("r1.png")
    assert r2["parent"] == 0   # parent = approved at submit time
    assert [r["status"] for r in st["revisions"]] == ["approved", "candidate"]


def test_reject_approved_rev_rolls_base_back(tmp_path, monkeypatch):
    """P1: rejecting the approved revision must never leave it as the next base."""
    import image_skill as s, client
    base = _png(tmp_path, "base.png")
    tid = s.start_transaction("g", base)["tx_id"]
    for n in (1, 2):
        monkeypatch.setattr(client, "run_job", lambda e, b, n=n, **k: {"success": True, "job_id": "j",
                            "images": [{"local_path": _png(tmp_path, f"r{n}.png")}], "cost_usd": 0.1})
        s.edit(f"rev{n}", tx_id=tid)
        s.approve(tid, n)   # rev2.parent == 1
    assert s.transaction(tid)["current_base"].endswith("r2.png")
    s.reject(tid, 2, "worse")
    st = s.transaction(tid)
    assert st["approved_rev"] == 1 and st["current_base"].endswith("r1.png")
    s.reject(tid, 1)
    st = s.transaction(tid)
    assert st["approved_rev"] == 0 and st["current_base"] == base
    r3 = s.edit("rev3", tx_id=tid)   # next edit starts from original, not a rejected image
    assert r3["parent"] == 0


def test_budget_reserved_before_paid_call_and_released_never(tmp_path, monkeypatch):
    import image_skill as s, client
    base = _png(tmp_path, "base.png")
    tid = s.start_transaction("g", base)["tx_id"]
    calls = []
    monkeypatch.setattr(client, "run_job", lambda e, b, **k: calls.append(1) or {"success": False, "job_id": "j", "error": "boom"})
    r = s.edit("x", tx_id=tid, auto_fix=True)
    assert r["success"] is False and r["auto_fix_left"] == 0 and len(calls) == 1
    r = s.edit("x", tx_id=tid, auto_fix=True)
    assert "budget exhausted" in r["error"] and len(calls) == 1   # refused before charge
    assert s.transaction(tid)["revisions"][0]["status"] == "failed"


def test_qa_verdict_is_strict():
    import image_skill as s
    ok, err = s._parse_verdict('{"pass": true, "issues": [], "confidence": 0.9}')
    assert ok["pass"] is True and err is None
    for bad in ['{"pass": "false", "issues": []}',
                '{"pass": true, "issues": [{"what":"x","where":"y","severity":"major"}]}',
                '{"pass": false, "issues": []}',
                '{"pass": true, "issues": [{"what":"x"}]}',
                '{"pass": true, "issues": [], "confidence": 3}',
                'looks fine to me']:
        v, e = s._parse_verdict(bad)
        assert v is None and e, bad


def test_validation_failure_does_not_consume_auto_fix(tmp_path, monkeypatch):
    """P2: bad params must fail BEFORE the budget is reserved."""
    import image_skill as s, client
    calls = []
    monkeypatch.setattr(client, "run_job", lambda e, b, **k: calls.append(1) or {"success": True, "job_id": "j",
                        "images": [{"local_path": _png(tmp_path, "o.png")}], "cost_usd": 0.1})
    tid = s.start_transaction("g", _png(tmp_path, "base.png"))["tx_id"]
    for bad in (dict(quality="high"), dict(mask_path=_png(tmp_path, "m.png")), dict(resolution="8K")):
        with pytest.raises(ValueError):
            s.edit("x", tx_id=tid, auto_fix=True, model="nanopro", **bad)
    assert s.transaction(tid)["auto_fix_used"] == "0/1" and calls == []
    r = s.edit("x", tx_id=tid, auto_fix=True, model="nanopro", resolution="2K")   # corrected call still allowed
    assert r["success"] and r["auto_fix_left"] == 0 and len(calls) == 1
