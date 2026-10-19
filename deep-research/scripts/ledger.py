#!/usr/bin/env python3
"""Deep Research P1: evidence ledger + grounding validator.

Usage:
  python ledger.py add <run_dir> --url U --title T --quote Q [--published-at D] [--tool web_fetch] [--trust secondary]
  python ledger.py list <run_dir>
  python ledger.py validate <run_dir> --draft draft.md [--nli] [--out report.md]

Ledger: <run_dir>/evidence.jsonl (append-only).
Validate: every claim line containing [E###] refs is checked:
  - eid must exist in ledger
  - numbers in claim must appear in the cited quotes (numeric exact-match)
  - optional --nli: cheap-model semantic support check via sc-proxy
Failed claims are REMOVED from the output report and logged to <run_dir>/audit.json.
"""
import argparse, hashlib, json, os, re, sys, datetime

def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def ledger_path(run_dir):
    return os.path.join(run_dir, "evidence.jsonl")

def load_ledger(run_dir):
    entries = {}
    p = ledger_path(run_dir)
    if os.path.exists(p):
        with open(p) as f:
            for line in f:
                line = line.strip()
                if line:
                    e = json.loads(line)
                    entries[e["eid"]] = e
    return entries

def cmd_add(a):
    os.makedirs(a.run_dir, exist_ok=True)
    entries = load_ledger(a.run_dir)
    eid = "E%03d" % (len(entries) + 1)
    quote = a.quote.strip()[:1000]
    e = {
        "eid": eid, "url": a.url, "title": a.title,
        "published_at": a.published_at or "undated",
        "fetched_at": now_utc(),
        "quote": quote,
        "hash": hashlib.sha256(quote.encode()).hexdigest()[:16],
        "tool": a.tool, "trust": a.trust if a.published_at else "secondary",
    }
    if not a.published_at:
        e["trust_note"] = "undated -> trust capped at secondary"
    with open(ledger_path(a.run_dir), "a") as f:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(eid)

def cmd_list(a):
    for e in load_ledger(a.run_dir).values():
        print(f'{e["eid"]}  [{e.get("published_at","?")}] {e["title"][:60]}  ({e["trust"]})')

NUM_RE = re.compile(r"\d[\d,]*\.?\d*%?")

def norm_num(s):
    return s.replace(",", "").rstrip("%").rstrip(".")

def extract_claims(text):
    """Split markdown into lines; a claim = line containing >=1 [E###] ref."""
    claims = []
    for i, line in enumerate(text.splitlines()):
        eids = re.findall(r"\[(E\d{3})\]", line)
        if eids:
            claims.append({"line_no": i, "text": line, "eids": eids})
    return claims

def nli_check(claim_text, quotes):
    """Cheap-model support check via sc-proxy. Returns (supported: bool|None, note)."""
    try:
        sys.path.insert(0, "/app")
        from core.http_client import proxied_post  # platform helper
    except Exception:
        return None, "nli-unavailable: core.http_client not importable"
    body = {
        "model": os.environ.get("RESEARCH_NLI_MODEL", "minimax/minimax-m3"),
        "messages": [{"role": "user", "content":
            "Evidence quotes:\n" + "\n---\n".join(quotes[:5]) +
            "\n\nClaim:\n" + re.sub(r"\[E\d{3}\]", "", claim_text).strip() +
            "\n\nIs the claim directly supported by the quotes? Answer exactly YES or NO."}],
        "max_tokens": 5, "temperature": 0,
    }
    try:
        r = proxied_post("https://openrouter.ai/api/v1/chat/completions", json=body,
                         headers={"SC-CALLER-ID": "chat:research-validate"}, timeout=60)
        ans = r.json()["choices"][0]["message"]["content"].strip().upper()
        return ans.startswith("YES"), f"nli={ans}"
    except Exception as ex:
        return None, f"nli-error: {ex}"

def cmd_validate(a):
    entries = load_ledger(a.run_dir)
    with open(a.draft) as f:
        text = f.read()
    claims = extract_claims(text)
    removed, kept, audit = [], [], []
    for c in claims:
        problems = []
        quotes = []
        for eid in c["eids"]:
            if eid not in entries:
                problems.append(f"unknown eid {eid}")
            else:
                quotes.append(entries[eid]["quote"])
        # numeric exact-match: every number in claim must appear in some cited quote
        if quotes and not problems:
            qnums = set()
            for q in quotes:
                qnums |= {norm_num(n) for n in NUM_RE.findall(q)}
            for n in NUM_RE.findall(re.sub(r"\[E\d{3}\]", "", c["text"])):
                if norm_num(n) not in qnums:
                    problems.append(f"number '{n}' not found in cited quotes")
        # optional semantic check
        if quotes and not problems and a.nli:
            ok, note = nli_check(c["text"], quotes)
            if ok is False:
                problems.append(f"semantic: quotes do not support claim ({note})")
        rec = {"line_no": c["line_no"], "claim": c["text"].strip(),
               "eids": c["eids"], "problems": problems}
        audit.append(rec)
        (removed if problems else kept).append(rec)

    # produce cleaned report: drop failed claim lines
    bad_lines = {r["line_no"] for r in removed}
    out_lines = [l for i, l in enumerate(text.splitlines()) if i not in bad_lines]
    if removed:
        out_lines += ["", "## 已删除的未落地论断（审计）", ""]
        out_lines += [f"- ~~{r['claim']}~~ — {'; '.join(r['problems'])}" for r in removed]
    out_path = a.out or os.path.join(a.run_dir, "report.md")
    with open(out_path, "w") as f:
        f.write("\n".join(out_lines) + "\n")
    with open(os.path.join(a.run_dir, "audit.json"), "w") as f:
        json.dump({"validated_at": now_utc(), "total_claims": len(claims),
                   "kept": len(kept), "removed": len(removed), "details": audit},
                  f, ensure_ascii=False, indent=2)
    print(json.dumps({"total_claims": len(claims), "kept": len(kept),
                      "removed": len(removed), "report": out_path}))
    if removed:
        for r in removed:
            print(f"REMOVED: {r['claim'][:80]} :: {'; '.join(r['problems'])}", file=sys.stderr)

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    pa = sub.add_parser("add"); pa.add_argument("run_dir")
    pa.add_argument("--url", required=True); pa.add_argument("--title", required=True)
    pa.add_argument("--quote", required=True); pa.add_argument("--published-at", default=None)
    pa.add_argument("--tool", default="web_fetch"); pa.add_argument("--trust", default="secondary")
    pl = sub.add_parser("list"); pl.add_argument("run_dir")
    pv = sub.add_parser("validate"); pv.add_argument("run_dir")
    pv.add_argument("--draft", required=True); pv.add_argument("--nli", action="store_true")
    pv.add_argument("--out", default=None)
    a = p.parse_args()
    {"add": cmd_add, "list": cmd_list, "validate": cmd_validate}[a.cmd](a)

if __name__ == "__main__":
    main()
