#!/usr/bin/env python3
"""verify_code_changes — nudge the agent to verify code it just edited.

One script, two events (wire BOTH to this same absolute path):

  pre_tool_call   RECORDER. Classifies each tool call into a per-session
                  sidecar state file: a code-file edit marks work "pending
                  verification"; a test/build/lint/run command clears it.
                  Never blocks — always prints "{}" (pure observe).

  on_stop         DECIDER. At the turn boundary, if code was edited but
                  nothing was run to verify it, BLOCK once → the agent is
                  steered to run the relevant test/build (or say plainly
                  why there's nothing to run) before finishing.

Why this shape: on_stop only receives `tool_names` (names, no args), so it
cannot tell a code edit from a README edit, nor a test run from `ls`. Only
pre_tool_call carries `tool_input` (the path / the command). So the recorder
leg classifies the evidence; the decider leg reads it.

DESIGN POLICY — built to be lenient, never naggy (over-blocking trains users
to disable the guard):
  * Only known SOURCE-CODE extensions trigger. Docs/data (.md/.txt/.json/
    .yaml/.csv...) are exempt — editing them never demands verification.
  * "Verification" is broad: any test/build/lint/typecheck command, OR simply
    running the edited script once (a smoke run), counts. The guard only fires
    when the agent edited code and ran LITERALLY nothing executable after.
  * At most ONE nudge per set of unverified edits (a `nagged` mark), a hard
    per-session cap, `stop_hook_active` self-disarm, and a TTL so a stale edit
    from much earlier never blocks an unrelated later turn.
  * Fail-open everywhere: a bad payload / unreadable state / any error prints
    "{}" and the turn proceeds. A broken guard can never wedge a turn.

Self-test: templates/verify_code_changes_selftest.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

# ─────────────────────────── CONFIG — edit your copy ───────────────────────
# (Edit these in the copy under /data/workspace/hooks/, NOT in skills/… which
#  is overwritten on the next skill update.)

VERIFY_TTL_MIN = 30          # only nudge if the unverified edit is younger than this
MAX_NAGS_PER_SESSION = 3     # hard cap on nudges per session (anti-spam)
COUNT_SCRIPT_RUN = True      # running the edited file (python foo.py) counts as verify

# Source-code extensions that REQUIRE verification when edited.
CODE_EXTENSIONS = frozenset({
    ".py", ".pyx", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".go", ".rs", ".java", ".kt", ".kts", ".scala", ".rb", ".php",
    ".c", ".h", ".cc", ".cpp", ".hpp", ".cxx", ".cs", ".swift",
    ".sh", ".bash", ".zsh", ".lua", ".pl", ".pm", ".r", ".jl",
    ".vue", ".svelte", ".dart", ".ex", ".exs", ".clj", ".cljs",
    ".sql",
})

# Extensions that NEVER trigger (docs, prose, data, markup). Belt-and-braces:
# anything here is treated as non-code even if it sneaks into CODE_EXTENSIONS.
EXEMPT_EXTENSIONS = frozenset({
    ".md", ".markdown", ".mdx", ".rst", ".txt", ".text", ".adoc",
    ".asciidoc", ".org", ".log", ".csv", ".tsv", ".json", ".yaml",
    ".yml", ".toml", ".ini", ".cfg", ".conf", ".env", ".lock",
    ".html", ".htm", ".css", ".scss", ".less", ".xml", ".svg",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf",
})

EDIT_TOOLS = frozenset({"edit_file", "write_file"})

# Bash can write code without edit_file/write_file (heredoc, redirect, tee,
# in-place sed/perl). These patterns extract the WRITTEN target path(s) so a
# bash-authored code file is held to the same verify-before-done bar.
#   >  path / >> path / cat > path <<EOF      (redirection, incl. heredoc)
#   tee [flags] path                          (pipe-to-file)
_BASH_REDIRECT_RE = re.compile(r">>?\s*(\"[^\"]+\"|'[^']+'|[^\s|;&>()]+)")
_BASH_TEE_RE = re.compile(r"\btee\b\s+(?:-\S+\s+)*(\"[^\"]+\"|'[^']+'|[^\s|;&]+)")
# in-place editors rewrite an existing file in place; the code path is somewhere
# in the args, so when one is present we scan every token for a code extension.
_BASH_INPLACE_RE = re.compile(r"\b(?:sed\s+-i|perl\s+-\S*i\S*)\b")

# Commands that count as verification. Matched against the canonical command
# text (after splitting on && ; |). Broad on purpose.
_VERIFY_TOKEN_RE = re.compile(
    r"""(?ix)
    \b(
        pytest | unittest | nosetests | tox |
        jest | vitest | mocha | ava | jasmine |
        rspec | minitest | phpunit | bats |
        go\s+test | cargo\s+(test|check|build|run|clippy) |
        gradle | mvn | dotnet\s+(test|build|run) |
        ruff | flake8 | pylint | mypy | pyright | pyflakes | black\s+--check |
        eslint | tsc | tslint | prettier\s+--check |
        ctest | gtest |
        make | ninja | bazel | cmake |
        npm\s+(test|run\s+(test|build|lint|typecheck|check|tsc)) |
        yarn\s+(test|build|lint|typecheck|check) |
        pnpm\s+(test|run\s+(test|build|lint|typecheck|check)) |
        npx\s+(jest|vitest|tsc|eslint|playwright) |
        bun\s+test
    )\b
    """,
)
# "I ran the thing I edited" — a smoke execution. Counts only when COUNT_SCRIPT_RUN.
_SCRIPT_RUN_RE = re.compile(
    r"""(?ix)
    (^|\s|&&|;|\|)\s*(
        python[0-9.]*\s+\S+\.py |
        node\s+\S+\.(js|mjs|cjs|ts) |
        ts-node\s+\S+ |
        ruby\s+\S+\.rb |
        go\s+run\s+\S+ |
        php\s+\S+\.php |
        bash\s+\S+\.sh | sh\s+\S+\.sh |
        \./\S+
    )
    """,
)

STATE_DIR = Path("/data/workspace/.verify_guard")
_SHELL_SPLIT_RE = re.compile(r"\s*(?:&&|\|\||;)\s*")


# ─────────────────────────── helpers ───────────────────────────────────────
def _now() -> float:
    return time.time()


def _is_code_path(path: str) -> bool:
    if not path:
        return False
    ext = os.path.splitext(path.strip().rstrip("/"))[1].lower()
    if ext in EXEMPT_EXTENSIONS:
        return False
    return ext in CODE_EXTENSIONS


def _bash_code_write_targets(command: str) -> list:
    """Code-file paths a bash command WRITES (redirect / heredoc / tee / in-place
    sed-perl). Returns de-duped code paths only; empty when none. Conservative:
    a token must end in a known code extension to count, so log/data/doc
    redirections (>/dev/null, > out.json, >> app.log) are ignored."""
    if not command:
        return []
    cands = []
    for m in _BASH_REDIRECT_RE.finditer(command):
        cands.append(m.group(1))
    for m in _BASH_TEE_RE.finditer(command):
        cands.append(m.group(1))
    if _BASH_INPLACE_RE.search(command):
        # in-place editor present: any code-extension token is the target
        cands.extend(re.split(r"[\s=]+", command))
    out = []
    for c in cands:
        c = c.strip().strip("\"'")
        if c and _is_code_path(c) and c not in out:
            out.append(c)
    return out


def _looks_like_verification(command: str) -> bool:
    if not command:
        return False
    for seg in _SHELL_SPLIT_RE.split(command):
        seg = seg.strip()
        if not seg:
            continue
        if _VERIFY_TOKEN_RE.search(seg):
            return True
        if COUNT_SCRIPT_RUN and _SCRIPT_RUN_RE.search(seg):
            return True
    return False


def _state_path(session_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", session_id or "default")[:120]
    return STATE_DIR / f"{safe}.json"


def _load_state(session_id: str) -> dict:
    p = _state_path(session_id)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("pending", [])
            data.setdefault("nags", 0)
            return data
    except Exception:
        pass
    return {"pending": [], "nags": 0}


def _save_state(session_id: str, state: dict) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        p = _state_path(session_id)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, p)
    except Exception:
        pass  # fail-open: state loss just means a missed nudge, never a wedge


def _emit(obj: dict | None) -> None:
    sys.stdout.write(json.dumps(obj) if obj else "{}")


# ─────────────────────────── recorder (pre_tool_call) ──────────────────────
def _handle_pre_tool_call(payload: dict, session_id: str) -> None:
    tool = payload.get("tool_name") or ""
    ti = payload.get("tool_input")
    if not isinstance(ti, dict):
        _emit(None)
        return
    state = _load_state(session_id)

    if tool in EDIT_TOOLS:
        path = ti.get("path") or ti.get("file_path") or ti.get("filename") or ""
        if _is_code_path(str(path)):
            pending = state.get("pending") or []
            # de-dup by path; refresh ts; new edit is un-nagged so it can nudge
            pending = [e for e in pending if e.get("path") != path]
            pending.append({"path": str(path), "ts": _now(), "nagged": False})
            state["pending"] = pending
            _save_state(session_id, state)

    elif tool == "bash":
        cmd = str(ti.get("command") or "")
        if _looks_like_verification(cmd):
            # any verification clears ALL pending — proof of life on the workspace
            # (checked first: a write-then-run one-liner is already verified)
            state["pending"] = []
            _save_state(session_id, state)
        else:
            # bash that WRITES code (heredoc/redirect/tee/sed -i) but runs no
            # verification is held to the same bar as edit_file/write_file
            written = _bash_code_write_targets(cmd)
            if written:
                pending = state.get("pending") or []
                for path in written:
                    pending = [e for e in pending if e.get("path") != path]
                    pending.append({"path": path, "ts": _now(), "nagged": False})
                state["pending"] = pending
                _save_state(session_id, state)

    _emit(None)  # recorder never blocks


# ─────────────────────────── decider (on_stop) ─────────────────────────────
def _handle_on_stop(payload: dict, session_id: str) -> None:
    state = _load_state(session_id)
    pending = state.get("pending") or []
    if not pending:
        _emit(None)
        return

    ttl = VERIFY_TTL_MIN * 60
    now = _now()
    # drop stale edits — a much-earlier edit must not block an unrelated turn
    pending = [e for e in pending if (now - float(e.get("ts", 0))) < ttl]
    state["pending"] = pending

    unverified = [e for e in pending if not e.get("nagged")]
    stop_active = bool(payload.get("stop_hook_active"))
    nags = int(state.get("nags", 0))

    if unverified and not stop_active and nags < MAX_NAGS_PER_SESSION:
        for e in pending:
            e["nagged"] = True
        state["nags"] = nags + 1
        _save_state(session_id, state)
        paths = [e.get("path", "?") for e in unverified][:8]
        files = ", ".join(f"`{p}`" for p in paths)
        reason = (
            "[verify] You edited code but ran no test/build to check it: "
            + files
            + ". Run the relevant test/build/lint (or run the script once); "
            "if there is genuinely nothing to run, say so explicitly, then finish."
        )
        _emit({"decision": "block", "reason": reason})
        return

    # already nudged once, or a continuation is in flight, or cap hit:
    # stop nagging — drop the carried-over edits so a later turn starts clean.
    if not unverified:
        state["pending"] = []
    _save_state(session_id, state)
    _emit(None)


# ─────────────────────────── entry ─────────────────────────────────────────
def main() -> None:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            _emit(None)
            return
    except Exception:
        _emit(None)
        return

    event = payload.get("event") or ""
    session_id = str(payload.get("session_id") or "default")

    try:
        if event == "pre_tool_call":
            _handle_pre_tool_call(payload, session_id)
        elif event == "on_stop":
            _handle_on_stop(payload, session_id)
        else:
            _emit(None)  # dispatch safety: unknown event = no-op
    except Exception:
        _emit(None)  # fail-open on any internal error


if __name__ == "__main__":
    main()
