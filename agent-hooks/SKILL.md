---
name: agent-hooks
version: 1.14.0
description: "Manage shell hooks — user scripts that run at agent lifecycle points to block, rewrite, or warn on actions, via the /hooks command."
author: starchild
tags: [hooks, automation, security, lifecycle, scripts]

metadata:
  starchild:
    emoji: "🪝"
    skillKey: agent-hooks
    requires:
      bins: [bash, python3]

user-invocable: true
disable-model-invocation: false
---

# Agent Hooks

Shell hooks let a user run **their own script** at fixed points in the agent's
lifecycle — to **block** a dangerous action, **rewrite** an input or an outbound
message, **inject context** into the model, or **warn the user**. The script can
be written in any language; it talks to the agent over a simple JSON-on-stdin,
JSON-on-stdout protocol.

Tools: `read_file`, `write_file`, `bash`

## When to use

Reach for hooks when the user wants the agent to **automatically enforce a rule
or react to an event** without being asked each time. Examples:

- "Stop me from running `rm -rf` / destructive bash" → `pre_tool_call` block
- "Never let a private key get pushed to Telegram" → `on_outbound_message` block
- "Log every tool call for audit" → `post_tool_call` observe
- "Remind the agent of X at the start of every model call" → `pre_llm_call` context
- "Don't let the agent claim it published when it didn't" → `on_completion_claim` (in `/goal`) or `on_stop` (in normal chat)
- "If the answer fails my quality check, make the agent redo it" → `on_stop` block

If the user just wants a one-off check, that's not a hook — hooks are for
**recurring, automatic** lifecycle enforcement.

## How configuration works (the agent does it end-to-end)

**The agent installs and activates a hook with zero user copy-paste.** Write the
script, write the config entry, then call the loopback self-approve API — it
flips the master switch on, approves the script for every event it's wired to,
and hot-mounts it live (no restart). The user just tests it afterward.

```bash
curl -s -X POST http://localhost:8000/internal/runtime/hooks/approve \
  -H 'Content-Type: application/json' \
  -d '{"command": "/data/workspace/hooks/security_guard.py"}'
# -> {"ok": true, "events": [...], "mounted": N, "master_enabled": true}
```

> ⚠️ **ALWAYS use an absolute path under `/data/workspace`** in both the yaml
> `command:` and this call. **Never a relative path** like
> `skills/agent-hooks/templates/security_guard.py`: the bridge spawns the script
> with the *server* cwd (`/app`), so a relative path resolves to `/app/skills/…`
> — an empty dir — and every spawn fails. Because the bridge fails OPEN (a script
> it can't run = "continue"), the guard then silently protects nothing while
> `/hooks list` still shows it "mounted". To avoid this, the standard install
> **copies the template into `/data/workspace/hooks/` and points the yaml there**
> (see the workflow below). `/app/skills` is NOT the skills dir — the real one is
> `/data/workspace/skills/` (a.k.a. `/app/workspace/skills/` via symlink).

- `command` MUST be the exact `command:` string from the `shell_hooks.yaml`
  entry (the absolute script path). The hook MUST already be declared in the yaml
  — approval flips a declared hook to live, it can't conjure one out of thin air.
- The endpoint is **loopback-only** (same-uid-in-container trust boundary, same
  as `.env` reads). It auto-enables the master switch (`enable_master` defaults
  true), so the hook fires immediately.
- Approval records the script's mtime, so a later edit surfaces as drift in
  `/hooks list` / `/hooks doctor` — a swap-the-script change stays visible.

**This is the whole activation story for the user — there isn't a second step.**
After the call returns `{"ok": true}`, tell them it's live and to test it. Do not
mention `/hooks approve`, `/hooks on`, or "two gates" — those are internal.

**Fallback (older builds only):** if the curl returns `404`, this runtime
predates the self-approve API — only then fall back to asking the user to paste
`/hooks approve <command>` then `/hooks on`.

## The two gates (both handled by the self-approve API — you don't surface them)

Internally a hook fires only when BOTH hold; the self-approve call above flips
both in one shot, so the **user never sees or types either**:

1. **Master switch ON** — `shell_hooks.enabled: true` in
   `workspace/config/agent.yaml`. The API auto-enables it (`enable_master`
   defaults true).
2. **Per-hook approval** — the `(event, command)` pair is recorded in the
   allowlist with the script's mtime (so a later edit shows as "changed since
   approval" drift — a swapped script stays visible). The API approves every
   event the command is wired to.

These exist as a security boundary, not as a user step. Do NOT mention "approve"
or "two gates" when explaining hooks to a user — just say you'll set it up and
they can test it. (Manual `/hooks on` + `/hooks approve` exist only as the `404`
fallback for older runtimes.)

## The `/hooks` command

Plain text on web / Telegram / WeChat (no LLM, no cost):

| Command | What it does |
|---|---|
| `/hooks` or `/hooks list` | master switch state, config path, every hook + approval/health |
| `/hooks on` \| `/hooks off` | flip the master switch (hot mount/unmount, no restart) |
| `/hooks doctor` | run each approved hook against a synthetic payload, check JSON |
| `/hooks approve <event> <command>` | approve + activate live (no restart) |
| `/hooks revoke <command>` | revoke + detach live (no restart) |
| `/hooks help` | usage |

## Events (12) and what each can do

| Event | Fires | Capability | stdin gives the script |
|---|---|---|---|
| `on_user_message` | a user message arrives, before the model sees it | **block** / rewrite text | `message`, `channel` |
| `pre_tool_call` | before a tool runs | **block / rewrite input** | `tool_name`, `tool_input` |
| `post_tool_call` | after a tool runs | observe (log/metrics) | `tool_name`, `tool_result` |
| `transform_tool_result` | result before agent sees it | **append a note** | `tool_name`, `tool_result` |
| `pre_llm_call` | before a model call | **inject context** | `system`, `last_user_message`, `model` |
| `post_llm_call` | after a model reply | observe / swap | `model` |
| `on_response_end` | final reply assembled, once per turn | **rewrite reply** | `response`, `model`, `tokens`, `tool_names` |
| `on_stop` | turn boundary, after `on_response_end` | **block → force a redo** | `response`, `tool_names`, `stop_hook_active` |
| `on_outbound_message` | before a TG/WeChat push | **block / rewrite outbound** | `notification`, `type` |
| `on_completion_claim` | agent claims a `/goal` done | **block → force a redo** | `goal`, `summary`, `response`, `tool_names` |
| `on_session_start` | session begins | observe | `status` |
| `on_session_end` | session ends | observe / cleanup | `status` |

Every payload also includes `event`, `session_id`, `agent_id`, `cwd`.

**The `event` field is the dispatch key.** It names *which* lifecycle moment is
firing (`pre_tool_call`, `on_user_message`, …). A multi-event script (like
`security_guard.py`, one file wired to five events) reads `event` to decide which
branch to run — no `event` in the payload means no branch matches, so the script
falls through to "continue" (empty output = allow). The runtime always sets it;
**you only have to remember it when hand-crafting a test payload** (see the
dry-run step below). It is NOT something you put in `shell_hooks.yaml` — there the
`event:` key tells the *bus* when to call you; the `event` field in the payload is
the bus telling the *script* which moment it is.

### The three "make the agent fix it" levers (don't mix them up)

These three fire near the end of a turn but have **very different power** — pick
by *what you need to happen* when something's wrong:

| Event | Power | Use when |
|---|---|---|
| `on_response_end` | **rewrite only** — edit the stored/forwarded reply (footer, redaction, mask). Cannot make the agent redo. Zero loop risk. | You only need to *change the text* (mask a leaked key, add a cost footer). |
| `on_stop` | **block → redo, in normal chat** — steers your `reason` back as the next instruction and the agent keeps working. Kernel-capped (≤3 redos/turn) + `stop_hook_active` flag, so it can't trap a turn. | You need the agent to *actually fix/verify its own output* in ordinary conversation (quality gate, citation/publish check). Claude Code "Stop" hook parity. |
| `on_completion_claim` | **block → redo, in `/goal` only** — refuses a fabricated "done" and keeps the goal loop running. | Same redo power, but it only fires inside a running `/goal` supervisor loop. |

Rule of thumb: **mask → `on_response_end`; redo in chat → `on_stop`; redo in a
goal → `on_completion_claim`.** Note `on_response_end` can only rewrite the
*stored* copy — tokens already streamed to a live web client can't be unsent, so
prefer `on_stop` when you need the user to actually see a corrected answer.

## Output protocol (what the script prints on stdout)

JSON object, or empty for "continue". Fields:

```jsonc
{"decision": "block", "reason": "..."}   // deny the action / refuse completion
{"tool_input": {...}}                     // pre_tool_call: rewrite EXISTING input keys
{"notification": "..."}                   // on_outbound_message: rewrite the message
{"context": "..."}                        // pre_llm_call: inject into prompt (AGENT-facing)
{"systemMessage": "..."}                  // allow, but show the USER a note
{"add_warning": "..."}                    //   same user-facing note channel
<empty>                                   // continue, no change
```

**`context` is agent-facing** (goes into the prompt, `pre_llm_call` only).
**`systemMessage` / `add_warning` is user-facing** (shown to the human on the
tool-result / completion / outbound surfaces) — never injected into the prompt.

Safety: scripts run with `shell=False` + argv split (no shell injection) and a
per-hook timeout. A script that errors, times out, or prints non-JSON falls
through to **continue** — a broken hook can never break the agent.

### Writing a readable `reason`

The `reason` is shown to the **user** (on the blocked-action card) and to the
**model**. Keep it **short and scannable** — one clause for *why*, then the
evidence. Don't write paragraphs: a reason fires on a card the user is already
annoyed to see, and a wall of text buries the actual cause. Aim for the shape
`[tag] Blocked (<why>): <evidence>` — ~8–12 words before the colon, never two
sentences of hand-wringing.

| Avoid (verbose) | Prefer (concise) |
|---|---|
| `This command is irreversible and would cause permanent data loss, so I've blocked it: rm -rf /` | `Blocked (recursive force-delete): rm -rf /` |
| `That message contains what looks like an API key, private key, or seed phrase. I won't process it — treat it as exposed and rotate it.` | `Blocked: message contains a credential. Rotate it.` |
| `You shared a preview link whose id isn't in the registry — it looks made up. Serve the preview first and use its real id` | `Preview id not in the registry. Serve it first: /preview/x/` |

The model still gets enough to act (the *why* + the offending payload); the user
gets a card they can read at a glance. The UI splits one reason string into two
parts for you, so you don't parse anything client-side:

- **Explanation + command box** — put the human sentence first, then `: `, then
  the offending command/payload. Everything after the first `": "` is rendered
  in a separate monospace box. The split only triggers when that tail looks like
  a payload (has a space or is longer than ~12 chars), so an ordinary sentence
  that happens to contain a colon is left intact.
- **Sentence only** — a reason with no `": "` shows as a single sentence and no
  command box. That's the right shape when there's nothing to quote (e.g. a
  pasted seed phrase).
- **`[tag]` is stripped** — a leading tag like `[security]` is removed before
  display and the sentence is auto-capitalised, so you can keep a tag for your
  own `grep` without it leaking into the UI.

```jsonc
// Good — short why + a clean command box:
{"decision": "block",
 "reason": "[security] Blocked (formats the disk): mkfs.ext4 /dev/sda1"}
//  ->  "Blocked (formats the disk)"   +   [ mkfs.ext4 /dev/sda1 ]

// Avoid — a bare command (no WHY) or a verbose two-sentence lecture:
{"decision": "block", "reason": "mkfs /dev/sda1"}
{"decision": "block", "reason": "This command is irreversible and would cause permanent data loss across the entire filesystem, so I have decided to block it for your safety: mkfs /dev/sda1"}
```

A hook that doesn't follow this still works — a plain string just renders as one
sentence. The convention only unlocks the nicer "explanation + command" layout.

## Config file format

`workspace/config/shell_hooks.yaml`:

```yaml
hooks:
  - event: pre_tool_call
    matcher: "rm -rf|dd if=|mkfs"      # optional regex; script only spawns on a match (perf gate)
    command: ./extensions/shell_hooks/examples/block_secrets.py
    timeout: 10                          # seconds, default 20, max 120
```

## Two hook transports

A hook is either a local **command** (default) or an **HTTP endpoint** — same
payload in, same decision JSON out, only the transport differs.

```yaml
hooks:
  - event: pre_tool_call
    type: http                          # omit type -> "command" (default)
    url: https://my-guard.example.com/hook
    timeout: 10
```

HTTP specifics:
- **SSRF guard** — the URL must be http(s) and must NOT resolve to a loopback /
  private / link-local (incl. cloud metadata `169.254.169.254`) / reserved
  address (blocked at parse AND call time). Set
  `STARCHILD_SHELL_HOOKS_HTTP_ALLOW_LOCAL=1` only to intentionally hit a local
  service.
- **Approval keys on the URL**: `/hooks approve <event> <url>`; `/hooks list`
  shows it as `POST <url>` and skips the executable/mtime checks.

## Adding an LLM judgement (call the proxy, NOT /chat)

When a hook needs real reasoning ("does this leak a secret?", "is this
completion actually done?"), call an LLM **directly through the proxy** from your
script — never the agent's own `/chat`.

```python
from core.http_client import proxied_post
import json, sys

event = json.load(sys.stdin)
r = proxied_post(
    "https://openrouter.ai/api/v1/chat/completions",
    json={
        "model": "minimax/minimax-m3",   # cheap default (~$0.0002/call)
        "messages": [
            {"role": "system", "content":
                'You are a guard. Output ONLY JSON {"decision":"block|allow","reason":"..."}.'},
            {"role": "user", "content": json.dumps(event)},
        ],
        "temperature": 0, "max_tokens": 200,
    },
    headers={"SC-CALLER-ID": "chat:hook"},   # required for billing
    timeout=40,
)
try:
    print(json.dumps(json.loads(r.json()["choices"][0]["message"]["content"])))
except Exception:
    print("{}")   # fail-open on any parse error
```

Why proxy-direct: OpenRouter is an external stateless API, so it does **not**
re-enter the agent loop or fire `pre_llm_call` -> **no recursion**, one cheap
completion instead of a full agent turn, your own prompt + pure-JSON response.
Calling `/chat` from a hook re-emits the same event (the bridge guards against
the loop, but it's needless overhead) — and an LLM hook that calls `/chat` must
**never** sit on `pre_llm_call`. See the host docs `sc-proxy.md` section
"Calling an LLM through the proxy".

## Standard workflow (the agent's checklist)

1. **Clarify** the rule and pick the event from the table above.
2. **Write the script** — read JSON on stdin, print a decision on stdout.
   Exit non-zero / non-JSON = continue. Make it executable (`chmod +x`).
3. **Put the script at a stable ABSOLUTE path** under `/data/workspace`. For a
   shipped template, copy it out of the skill dir so a skill update can't move it:
   ```bash
   mkdir -p /data/workspace/hooks
   cp /data/workspace/skills/agent-hooks/templates/security_guard.py /data/workspace/hooks/
   chmod +x /data/workspace/hooks/security_guard.py
   ls -l /data/workspace/hooks/security_guard.py    # VERIFY it exists before going on
   ```
   Never reference the script by a relative path (see the ⚠️ box above — it
   resolves against `/app` and silently fails open).
4. **Add a config entry** in `workspace/config/shell_hooks.yaml` with the
   absolute `command:` (`/data/workspace/hooks/security_guard.py`); add a
   `matcher` regex when possible so the script only spawns when relevant.
5. **Dry-run it yourself with `bash`** — pipe a sample JSON payload into the
   script and confirm it prints valid JSON. **The payload MUST include the
   `event` field** — a multi-event script dispatches on it, so leaving it out
   makes every case fall through to "continue" and you'll wrongly conclude the
   guard doesn't fire. Test each event the script handles:
   ```bash
   # should BLOCK (note the "event" key):
   echo '{"event":"pre_tool_call","tool_name":"bash","tool_input":{"command":"rm -rf /"}}' \
     | python3 /data/workspace/hooks/security_guard.py
   # should ALLOW (empty output):
   echo '{"event":"pre_tool_call","tool_name":"bash","tool_input":{"command":"ls -la"}}' \
     | python3 /data/workspace/hooks/security_guard.py
   ```
6. **Activate it yourself** via the loopback self-approve API (no user paste);
   `command` = the exact absolute path from your yaml entry:
   ```bash
   curl -s -X POST http://localhost:8000/internal/runtime/hooks/approve \
     -H 'Content-Type: application/json' \
     -d '{"command": "/data/workspace/hooks/security_guard.py"}'
   ```
   On `{"ok": true}` the hook is live. On `404`, fall back to handing the user
   `/hooks approve <command>` + `/hooks on` (see "How configuration works").
7. **Run `/hooks doctor` to confirm it actually works** — this is the step that
   catches a wrong path / non-executable / non-JSON script. A guard that shows
   "mounted" in `/hooks list` but errors in `doctor` is a silent no-op (fails
   open). Only after `doctor` is clean tell the user it's live and ready to test.

## Ready-made scripts (each has ONE clear job)

Five **production-grade guards** ship in this skill under `templates/`
(copy + approve as-is). Four **single-purpose examples** ship with the host under
`extensions/shell_hooks/examples/` (copy + adapt). No two overlap — pick by the
job, not by trial.

### Installing from a `/hooks` number or name

`/hooks` (empty state) and `/hooks help` show a **numbered** ready-made list. The
`/hooks` command itself is static text — it never installs. When the user replies
with a number (`"1"`, `"1,3"`), a name (`"security_guard"`), or `"install all"`,
THAT reply lands on you: resolve it to the template **by the name shown next to
the number in that list** (number→`templates/<name>.py`), then run the Standard
workflow below for each — copy → yaml entry → dry-run → self-approve → `doctor`.
Map by the visible name, never a memorised number→path table (the list may be
reordered). If a self-test exists (`templates/<name>_selftest.py`), run it first.

### Production templates (in this skill, `templates/`)

> ⚠️ **Copy before you edit — for every template here.** Always `cp` a template
> into `/data/workspace/hooks/` and wire your hook at THAT path, then make any
> changes (rule tweaks, the `runtime_footer` CONFIG block, etc.) in the copy.
> Editing a file in place under `skills/agent-hooks/templates/` is pointless: the
> next skill update overwrites it and your changes vanish. The copy in `hooks/`
> is yours and is never touched by updates.

| Template | Events | Its one job |
|---|---|---|
| `security_guard.py` | `on_user_message`, `pre_tool_call`, `transform_tool_result`, `on_response_end`, `on_outbound_message` | **Secrets + destructive bash.** Block pasted/exfiltrated secrets (API keys incl. Bearer, PEM/EVM private keys, BIP-39 seeds, Solana byte-array & base58 WIF), mask leaked keys in replies/pushes, block irreversible-data-loss bash. See below. |
| `verify_publish_claims.py` | `on_stop` (chat redo) / `on_completion_claim` (`/goal` redo) / `on_response_end` (rewrite fallback) | **Anti-hallucination.** Catch fabricated "published / posted to AgentX / scheduled" claims by checking the reply against ground truth (previews registry, AgentX ledger, scheduler registry). |
| `verify_code_changes.py` | `pre_tool_call` (recorder) + `on_stop` (decider) | **Anti-"false done" for code.** When you change a source file but run no test/build/lint to check it, blocks the stop once and steers you to verify (or say plainly there's nothing to run) before finishing. Counts both `edit_file`/`write_file` AND code written via bash (heredoc, `>`/`>>` redirect, `tee`, in-place `sed -i`/`perl -i`). Docs/data edits (`.md`/`.json`/`.yaml`/…) are exempt; one nudge per edit-set, self-disarms, fails open. Wire BOTH events to the same script path. |
| `verify_commitments.py` | `on_stop` (chat redo) | **Anti-broken-promise.** When the reply makes a future notify-promise ("I'll let you know when the build finishes", "明早提醒你") but registers nothing to make it happen, blocks the stop once and steers you to actually register it — `scheduled_task(once)` for time-bound, `sessions_spawn` (bash poll + `announce=followup`) for completion-bound. Fires only when a notify verb AND a time/condition cue both appear; immediate-delivery framing ("here's", "下面就是") and cross-round registration (recent active job / recent spawn) suppress it. Capped, self-disarms, fails open. |
| `runtime_footer.py` | `on_response_end` (+ optional `pre_llm_call`) | **Model/cost footer.** On `on_response_end` (once/turn) it strips any model-typed footer at the reply end and appends the ONE true footer from the runtime's real `model` + cost. Optionally wire `pre_llm_call` too for a "don't type a footer" nudge (fires per model-request). See below. |

### Single-purpose examples (host repo, `extensions/shell_hooks/examples/`)

| Script | Event | Its one job |
|---|---|---|
| `pii_redactor.py` | `transform_tool_result`, `on_response_end` | Mask emails / phones (PII — distinct from secrets). |
| `tool_audit_log.py` | `post_tool_call` | Observe-only: append every tool call to a JSONL audit trail. |
| `budget_alert.py` | `on_response_end` | Append a soft warning when a turn's cost crosses a threshold. |
| `inject_website_reminder.sh` | `pre_llm_call` | Preventive nudge: remind the model to actually publish before claiming done (pairs with `verify_publish_claims.py`). |

### Superseded by the templates (don't ship a second, conflicting guard)

The host repo also ships some **minimal single-event examples** under
`extensions/shell_hooks/examples/` that overlap the two templates above. They're
fine as learning references, but for real use prefer the template — running both
just creates two guards with possibly different policies.

| Minimal example | Use this instead | Why |
|---|---|---|
| `block_secrets.py` | `security_guard.py` | the guard's secret detection is a strict superset (adds Bearer, Solana byte-array, base58 WIF, destructive-bash, masking) |
| `check_publish.sh` | `verify_publish_claims.py` | the template also covers AgentX posts + scheduled tasks and checks the same registry |

**Removed outright** (orphan duplicates, fully folded into `security_guard.py`):
`secret_guard.py` (vendor-key block/mask, incl. Bearer) and
`dangerous_bash_guard.py` (destructive-bash block). Want to *also* block
installers / force-push? Tune the guard's `DESTRUCTIVE` table rather than running
a second bash guard with a conflicting policy.

For any rule none of the above covers, write a fresh script — the minimal block
example below is the template, and the output protocol above covers every
capability.

### Minimal block example (`pre_tool_call`, any language)

```bash
#!/usr/bin/env bash
payload="$(cat)"
python3 - "$payload" <<'PY'
import json, sys, re
ev = json.loads(sys.argv[1])
cmd = (ev.get("tool_input") or {}).get("command", "")
if re.search(r"rm\s+-rf\s+/|dd\s+if=|mkfs", cmd):
    print(json.dumps({"decision": "block", "reason": f"This command is irreversible and would erase data, so I've blocked it: {cmd}"}))
else:
    print("{}")   # continue
PY
```

## All-in-one security guard (`templates/security_guard.py`)

A ready-to-use, self-contained script that wires **one file to five events** and
covers the common "don't leak secrets / don't nuke the box" baseline. First copy
it to a stable absolute path, then wire all five events to that same absolute
`command:` in `config/shell_hooks.yaml` (one block per event), then activate:

```bash
cp /data/workspace/skills/agent-hooks/templates/security_guard.py /data/workspace/hooks/
chmod +x /data/workspace/hooks/security_guard.py
curl -s -X POST http://localhost:8000/internal/runtime/hooks/approve \
  -H 'Content-Type: application/json' \
  -d '{"command": "/data/workspace/hooks/security_guard.py"}'
```

This approves every event that command is wired to and mounts it live — no user
paste. (On `404`, fall back to `/hooks approve <command>` + `/hooks on`.)

| Event | What it does |
|---|---|
| `on_user_message` | **block** a pasted API key (incl. Bearer token), private key (PEM / EVM hex), seed phrase, Solana byte-array secret, or base58 WIF before the model sees it |
| `pre_tool_call` (bash) | **block** only irreversible data loss (`rm -rf /`, `dd` to a block device, `mkfs`, fork bomb, `chmod -R 777`, `git reset --hard origin/*``) and credential exfiltration (`cat .env | curl`, `scp id_rsa`, `printenv | curl`) |
| `pre_tool_call` (message tools) | guard `send_to_telegram` / `send_to_wechat` args — **mask** a leaked key, **block** a seed phrase (these tools bypass the push pipeline, so this is the real outbound gate for them) |
| `transform_tool_result` | **warn** when a tool's OUTPUT contains a secret (backend can only flag, not rewrite, result text) |
| `on_response_end` | **mask** any secret that leaked into the final reply |
| `on_outbound_message` | **mask / block** secrets before they're pushed to TG / WeChat |

**Design policy:** block only what is *both* very dangerous *and* not part of
normal work. Common dev actions like `curl | bash` (installers) and
`git push --force` (rebasing your own feature branch) are intentionally
**allowed** — over-blocking trains users to disable the guard.

Tune the `SECRET_PATTERNS`, `DESTRUCTIVE`, and `MSG_TOOLS` tables at the top of
the file for your own rules. `templates/security_guard_selftest.py` is the
self-test (run it after any edit; dangerous strings live there as data only, so
the host bash guard can't trip on them).

## Anti-hallucination guard (`templates/verify_publish_claims.py`)

Catches a fabricated success: the agent writes "Published! community.iamstarchild.com/…",
"Posted to AgentX /post/…", or "Reminder scheduled" when it never ran the tool.
The script checks the reply against **ground truth** — the previews registry
(`/data/previews.json`), the AgentX post ledger, and the scheduler registry —
and either rewrites the reply or forces a redo. It is deliberately
low-false-positive: a *real* published URL or an "offer to publish" (future
tense) passes untouched; only a past-tense success claim with no backing trips it.

```bash
cp /data/workspace/skills/agent-hooks/templates/verify_publish_claims.py /data/workspace/hooks/
chmod +x /data/workspace/hooks/verify_publish_claims.py
curl -s -X POST http://localhost:8000/internal/runtime/hooks/approve \
  -H 'Content-Type: application/json' \
  -d '{"command": "/data/workspace/hooks/verify_publish_claims.py"}'
```

| Event | What it does |
|---|---|
| `on_stop` | **(preferred)** in ordinary chat, **block** a fabricated success and force the agent to actually publish/redo (loop-capped) |
| `on_completion_claim` | in a `/goal` loop, **block** a fabricated "done" and force a real publish (loop-capped) |
| `on_response_end` | rewrite-only fallback when `on_stop` isn't wired: append an honest "unverified" note (cannot make the agent redo) |

> **Wire it on `on_stop`** for normal chat — that's the only event that makes the
> agent *actually redo* a turn instead of just editing the text. The host honors
> only a `decision: block` on `on_stop` / `on_completion_claim` (a rewrite is
> ignored on those events), so the hook blocks on both and only rewrites on
> `on_response_end`. `templates/verify_publish_claims_selftest.py` is the self-test
> (covers the `on_stop` block path + the loop cap).

## Cost/model footer (`templates/runtime_footer.py`)

A model **cannot know its own per-reply cost** — and often not even its own model
id. That data lives only in the runtime. So if the model types its own footer
(e.g. `Model: GLM-5.2 | Cost: $0.038`), the numbers are invented. And once a real
footer is in the chat history, the model's autocomplete starts imitating it —
producing a *second*, fabricated footer. The footer is the runtime's job, not the
model's.

`runtime_footer.py` solves this entirely on **one event — `on_response_end`** —
which fires **once per turn** on the final assembled reply: it ① **strips** any
footer the model typed at the reply end, then ② **appends** the one true footer
from the runtime's real `model` + cost. The strip is the guarantee; nothing
per-call is needed.

> **Why on_response_end alone, not pre_llm_call.** There is no event that fires
> "just before the final response". `pre_llm_call` fires before *every* model
> request (N times/turn when tools are used) and can't know which call is the
> last — the model decides to use tools dynamically. Wiring the suppression there
> injects the directive N times/turn (visible as repeated injections in the call
> trace). It's also redundant: `on_response_end` already removes the footer
> post-hoc. So **default to on_response_end only.** The script *does* carry a
> `pre_llm_call` handler (injects a "don't type a footer" directive) if you want
> the extra nudge — wire it as a second event — but accept it runs per-call.

The strip is a **safety net** (`FOOTER_STRIP`, on by default), deliberately
narrow: it only removes a box-drawing `─ … · $N` line or a `Model: … Cost: $N`
line, and only on trailing lines — so a "Model:"/"Cost:" sentence in the body, or
a shell `$VAR`, is never touched (an earlier version used an over-broad `Model:`
regex that risked deleting legit prose; this is the tight redo). Set
`FOOTER_STRIP=0` for pure append-only.

```bash
cp /data/workspace/skills/agent-hooks/templates/runtime_footer.py /data/workspace/hooks/
chmod +x /data/workspace/hooks/runtime_footer.py
curl -s -X POST http://localhost:8000/internal/runtime/hooks/approve \
  -H 'Content-Type: application/json' \
  -d '{"command": "/data/workspace/hooks/runtime_footer.py"}'
```

Wire it in `config/shell_hooks.yaml` — no `matcher`, runs every turn:

```yaml
hooks:
  - event: on_response_end
    command: /data/workspace/hooks/runtime_footer.py
    timeout: 10
  # Optional extra nudge (fires per model-request, N times/turn):
  # - event: pre_llm_call
  #   command: /data/workspace/hooks/runtime_footer.py
  #   timeout: 10
```

**Configure by editing your copy — not env vars.** The recommended way to turn
options on is the `CONFIG` block at the top of the script. Edit it in the copy
you just made under `/data/workspace/hooks/` (NOT in `skills/…` — that gets
overwritten on the next skill update). Hooks run with the *server* process
environment, not your shell, so env vars are awkward to set and invisible in
`/hooks list`; an in-file constant is reliable, visible, and travels with the
script:

```python
# ─── CONFIG — edit your copy ───
SHOW_TOKENS = False   # True → append "· N in / N out"
SHOW_CREDIT = False   # True → append "· 💰 $bal"  (1 HTTP call/turn, fail-open)
TEMPLATE    = None    # custom format str: {model} {cost} {input} {output} {credit}
CREDIT_URL  = None    # override credit endpoint for self-hosted setups
STRIP       = True    # strip a model-typed footer at the tail
```

Each constant also has a matching env override (`FOOTER_SHOW_TOKENS`,
`FOOTER_SHOW_CREDIT`, `FOOTER_TEMPLATE`, `FOOTER_CREDIT_URL`, `FOOTER_STRIP`,
`FOOTER_SUPPRESS_TEXT`) which **wins when set** — handy for a one-off without
touching the file, but the in-file constant is the durable default.

Default footer is **model + cost only** (`─ z-ai/glm-5.2 · $0.0211`).
`SHOW_TOKENS = True` → `─ z-ai/glm-5.2 · $0.0211 · 900 in / 120 out`.

**Show remaining credit:** `SHOW_CREDIT = True` appends your balance
(`─ z-ai/glm-5.2 · $0.0211 · 💰 $271.64`). Off by default because it adds **one
internal HTTP call per turn** to the credit API — the same endpoint the `credit`
tool reads, authenticated automatically by source IPv6 (no key needed). It's
fail-open: a 2s timeout caps the wait, and if the lookup errors or times out the
balance is silently omitted (the footer still fires, no dangling separator).
Note the model can't see this number unless you wire the hook — it lives only in
the runtime, like cost.

**Don't double up:** `runtime_footer` is the shell-hook equivalent of the host
`turn_footer` extension — enable one, not both. Same for Telegram's
`tg_show_usage`.

**Safety:** never blocks. `on_response_end` appends nothing when the event
carries no cost data or the reply is empty (no `$0.0000` lie), and only ever
strips a narrowly-matched footer at the reply's tail (`STRIP = False` to
disable); the optional `pre_llm_call` injects nothing on a missing/malformed
payload; an unknown event is a no-op. Fail-open on any error. Self-test:
`templates/runtime_footer_selftest.py` (35 cases — both handlers, strip +
false-positive guards for mid-body prose and shell `$VAR`, credit balance +
fail-open, in-file CONFIG constants + env-override precedence, dispatch safety).

## Claude Code compatibility

Hook scripts written for **Claude Code** work unchanged — their output is
auto-translated into the fields above:

| Claude Code output | Translated to |
|---|---|
| `hookSpecificOutput.permissionDecision: "deny"` (+ `permissionDecisionReason`) | `decision: block` (+ `reason`) |
| `hookSpecificOutput.additionalContext` | `context` |
| `hookSpecificOutput.updatedInput` | `tool_input` (rewrite) |
| `continue: false` (+ `stopReason`) | `decision: block` (+ `reason`) |
| `systemMessage` | `add_warning` (user-facing note) |
| `suppressOutput` | no-op (our stdout never enters the transcript) |
| exit code 2 with stderr, no stdout | `decision: block`, stderr is the reason |

Only the output **payload** is translated — event NAMES stay ours
(`pre_tool_call`, not `PreToolUse`). Claude Code's **`Stop`** hook maps to our
`on_stop` (block → force a redo); its **`UserPromptSubmit`** maps to
`on_user_message`. A Stop script that returns `{"decision":"block","reason":…}`
or exits 2 works unchanged once wired to `on_stop`.

## Troubleshooting "my hook never fires"

1. Is the event one of the 12 above? (a typo is a silent no-op)
2. Is the **master switch** on? `/hooks list` shows it. The self-approve API
   enables it automatically; otherwise `/hooks on`.
3. Is the hook **approved**? `✗ NOT approved` in `/hooks list` → re-run the
   self-approve API for that command (or `/hooks approve` as fallback).
4. Does the `matcher` regex actually match? Too narrow = never spawns.
5. Run `/hooks doctor` — it flags non-executable / tampered / timed-out / non-JSON.
6. **Manual test "allows everything"?** Your test payload is probably missing the
   `event` field — a multi-event script dispatches on it and falls through to
   "continue" without it. This is a test-harness mistake, not a hook bug; the
   real runtime always sets `event`.
7. **`can't open file '/app/skills/…'` / "mounted" but nothing is blocked?** The
   `command:` is a relative or wrong path. The bridge spawns with the *server*
   cwd (`/app`), so `skills/…` resolves to the empty `/app/skills` and every
   spawn fails — and because the bridge fails OPEN, the guard silently protects
   nothing. Fix: use the ABSOLUTE path `/data/workspace/hooks/<script>.py` in both
   the yaml and the approve call, then re-approve and confirm with `/hooks
   doctor`. (`/app/skills` is not the skills dir; the real one is
   `/data/workspace/skills/`.)

## Deep reference

Full protocol, security model, and per-event payload detail live in the agent's
own docs: `config/context/references/agent-hooks.md` (read it for edge cases this
skill summarizes).
