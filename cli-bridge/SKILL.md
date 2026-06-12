---
name: cli-bridge
version: 0.2.2
description: >-
  Authorize the local starchild CLI / agent-shell — mint, list, revoke CLI bridge codes for local shell access.
delivery: script
metadata:
  starchild:
    emoji: "🔗"
    skillKey: cli-bridge
    requires:
      bins: [python3]
user-invocable: false
author: starchild
tags: [cli, akm, bridge, sc-chatroom, short-code]

---

# cli-bridge — issue CLI bundles for the user's own `starchild` binary

This skill mints a fresh AKM key (`scope=chat:bridge:cli`) on the local
clawd, then registers it with sc-chatroom in exchange for a short opaque
code (``sc_xxxxxxxx``). The bundle handed to the user contains only that
short code — never the AKM secret, never the Fly machine id.

```
+----------------+   POST /agent/chat/stream   +-----------------+
| starchild CLI  |   Bearer sc_xxxxxxxx        | sc-chatroom     |
| (user laptop)  | --------------------------> | (gateway)       |
+----------------+                             +--------+--------+
                                                        |
                            resolves sc_… → AKM + container_id
                                                        |
                                                        v
                                          POST /chat/stream (Bearer sk_…
                                          + fly-force-instance-id)
                                          +----------------------+
                                          | user's own clawd     |
                                          | (Fly internal)       |
                                          +----------------------+
```

## When to use

Manage short-code bundles that authorize the local starchild CLI to talk to this agent, including the agent-shell local-exec channel.

Use when connecting or disconnecting the starchild CLI (e.g. mint a CLI bridge code, list my CLI bundles, revoke an old CLI session, or let the agent run shell commands on the user's own machine).

## Why a short code instead of the raw AKM?

Earlier versions baked the AKM secret + Fly machine id into the bundle
directly. That worked but had two downsides — the bundle leaked routing
metadata when decoded, and any party that ever held the bundle held a
permanent AKM secret. The short-code form fixes both:

- Bundle base64 decodes to ``{d, c:"", k:"sc_…", s, exp, l}`` — no
  secret, no Fly machine id.
- ``cli-revoke <sc_…>`` kills just the short code; the underlying AKM
  stays alive (use ``cli-revoke --akm <prefix>`` to nuke that too).
- sc-chatroom now holds the AKM secret in its DB. That's a deliberate
  trust shift — the AKM stays inside Fly's internal network instead of
  riding around on user laptops.

## Scope boundary — read this first

`cli-bridge` covers **exactly one path**: the user's local CLI talking 1:1
to that user's own clawd. It is **not** a chatroom membership credential.

| Use case | Right credential | Wrong |
|---|---|---|
| Personal CLI ↔ own clawd (this skill) | `chat:bridge:cli` AKM, fronted by `sc_…` code | — |
| Join an sc-chatroom room | `chat:thread:chatroom-{room_id}` AKM via `chatroom join` | `chat:bridge:cli` AKM |
| Browse a public room as a guest | no credential needed | any AKM |

## Prerequisites

Same as `chatroom`:

- AKM is installed in this clawd (`POST /api/keys` works on loopback)
- AKM accepts `scope="chat:bridge:cli"` and the `/chat/stream` middleware
  allows arbitrary `thread_id` for that scope (already shipped in clawd
  branch `aladdin/feat/akm-chatroom`)
- sc-chatroom is on a build that includes `POST /cli-keys` (migration 007+)
- `FLY_MACHINE_ID` (or `CONTAINER_ID`) env is set
- `CHATROOM_PUBLIC_URL` env points at the sc-chatroom gateway (defaults
  to `https://workroom.iamstarchild.com`)
- `CHATROOM_SERVER_URL` env points at the Fly-internal sc-chatroom
  (defaults to `http://sc-chatroom.internal:8080`)

## Commands

### `cli-login` — mint a new bundle

```bash
python3 skills/cli-bridge/scripts/cli_login.py --label "my laptop"
python3 skills/cli-bridge/scripts/cli_login.py --label "codex-vm" --ttl-days 14
```

Default TTL is 90 days; max is 365 days. Output is a one-liner the user
copies into `starchild login`. The bundle is opaque — sc-chatroom
resolves it on each call.

### `cli-list` — show active bundles

```bash
python3 skills/cli-bridge/scripts/cli_list.py
python3 skills/cli-bridge/scripts/cli_list.py --include-revoked
```

Lists every CLI short code minted by this user on sc-chatroom. Columns:
code, issued, expires, uses, label.

### `cli-revoke` — kill a bundle

```bash
python3 skills/cli-bridge/scripts/cli_revoke.py sc_xxxxxxxx
python3 skills/cli-bridge/scripts/cli_revoke.py --akm sk_yyyyyy
```

Default: kills the short code in sc-chatroom; underlying AKM stays alive.
With `--akm`: also revokes the AKM on local clawd, taking out every
bundle backed by it.

## Local shell via `agent-shell` (CLI ≥ v0.2.0)

A `cli-login` bundle **minted with `--enable-shell`** also authorizes the
agent to run shell commands on the **user's own machine** — for "is nginx
running on my laptop", "organize ~/Downloads", and the like. A plain bundle
is a chat bridge only and grants no shell access (see "Shell is off by
default" below). The user starts a small daemon:

```bash
starchild agent-shell            # daemonizes; holds a WS open to your clawd
starchild agent-shell --foreground   # attach to the terminal for debugging
starchild agent-shell-stop       # stop the daemon
```

`agent-shell` refuses to start if the logged-in bundle wasn't granted shell
— it tells the user to get a `--enable-shell` bundle rather than connecting
a channel clawd would reject.

The daemon is single-instance (pidfile + flock) and macOS/Linux only. It
self-updates at startup and periodically; downloaded binaries are verified
against an embedded Ed25519 release key before swapping, so a hostile or
MITM'd update server can't push arbitrary code to the user's machine.

How it works: the daemon dials `wss://<chatroom>/ws/cli-shell` with the
bundle's `sc_…` code. sc-chatroom resolves the code and **reverse-proxies**
the WebSocket to the user's clawd machine — it accepts the laptop's
upgrade, opens its own upstream WS to clawd pinned with
`fly-force-instance-id`, and pumps bytes between the two (this is *not*
`fly-replay`: chatroom and clawd are different Fly apps, and cross-app
replay is rejected with 403). The AKM is injected server-side on the
upstream hop — it never reaches the laptop. clawd holds the connection in
its `ShellHubService`; the `local_shell` tool is then exposed to the LLM
**only while a shell-capable laptop is connected**, and pushes commands
down the socket.

### Shell is off by default (capability gate)

`cli-login` does **not** grant shell unless `--enable-shell` is passed. The
AKM is the authoritative capability source: clawd reads it on the
`/ws/cli-shell` handshake and refuses every exec for a connection that
doesn't carry `shell` (#264). So a leaked plain bundle is a chat credential,
never local RCE.

- Grant shell: `cli_login.py --label … --enable-shell` → AKM
  `capabilities: ["shell"]`, bundle carries `x: ["shell"]`.
- Upgrade an existing no-shell bundle: you can't flip it in place — mint a
  new `--enable-shell` bundle, `starchild login` it, and `cli-revoke` the
  old one. Privilege escalation always goes through a fresh issuance.

### What the agent knows up front (capability manifest)

On connect, the daemon sends a `hello` frame advertising:

- **Platform** — `os` (darwin/linux), `arch` (arm64/amd64), and the active
  `shell`. So the agent knows whether it's talking to BSD or GNU userland,
  which package manager to assume, etc. — no more guessing `ps` flags or
  hitting `ps: illegal option`.
- **Policy summary** — `mode` (`default-deny` when no allow rules exist, else
  `allowlist`), the user's `allowed` rules, explicit `denied_extra` rules,
  and the always-on `builtin_denied` list.

clawd renders this into the agent's system prompt (only while connected),
so the agent picks a permitted command — or tells the user plainly that the
local policy forbids it — instead of probing blindly.

### Session behavior

- **Connection-level cwd.** Each command's resulting working directory is
  echoed back (via a trailing-`pwd` sentinel stripped from stdout) and
  persisted for the next command, so `cd` has real meaning across calls
  within a session — without the cost/fragility of a full PTY. An explicit
  per-call cwd overrides it.
- **Output truncation.** stdout/stderr are each capped at 200 lines (plus a
  byte cap) so a `find /` or log dump can't flood the LLM context. The full
  pre-truncation line count is reported (`stdout_lines` / `stderr_lines`),
  and `truncated: true` is set — the agent can say "showing first 200 of N
  lines" rather than truncating silently.
- **Heartbeat.** The daemon pings every 45s to keep the idle WebSocket
  alive (Fly's edge cuts idle sockets at ~2.5min). Exec runs in a goroutine
  so a long command doesn't block heartbeats.

### Local execution policy (the only auto-run guard)

The daemon runs headless (no TTY to prompt on), so every command is
gated by `~/.config/starchild/exec-policy.toml` (parsed as a tiny
YAML `allow:`/`deny:` line format — no TOML dependency, despite the name).
Rules are **substring** matches by default; wrap a rule in `/ /` for a
regex:

```yaml
allow:
  - "ls"
  - "cat "
  - "/^git (status|log|diff)/"
  - "ps"
deny:
  - "git push"
```

Decision order: **built-in deny (always wins) → file `deny` → file
`allow` → default-deny.** Two hard rules apply regardless of the file:

- A built-in deny list of interactive/TTY-blocking and destructive
  commands is **always** refused: `vim`/`vi`/`nano`/`emacs`,
  `less`/`more`/`man`, `top`/`htop`/`btop`, `ssh`/`telnet`, `sudo`/`su`/
  `doas`, `tmux`/`screen`, `reboot`/`shutdown`/`halt`, plus the shapes
  `rm -rf`, `mkfs`, `dd if=`, `… | sh`, `… | bash`, `> /dev/sd*`.
- **Default-deny:** anything not matched by an `allow` rule is denied. So
  with no policy file the policy `mode` is `default-deny` and nothing runs
  until the user opts commands in.

### Limitations

- **Unattended policy only.** There is no interactive approval prompt; the
  policy file is the sole guard. A future version adds a web-approval popup.
- **Synchronous commands only.** No background jobs / progress polling yet.
- **macOS/Linux only.** The daemon refuses to run on Windows.
- **Revocation:** `cli-revoke <sc_…>` kills the short code; the daemon's
  next reconnect then fails auth and the channel closes.

> **Security note:** a running `agent-shell` (on a `--enable-shell` bundle)
> plus a permissive policy is effectively remote command execution on the
> user's machine, bounded by the AKM TTL, the `sc_…` code's validity, and the
> policy file. Defaults are conservative: shell is **off** unless explicitly
> granted, the policy is **deny-all** until commands are opted in, and the
> daemon's self-update verifies an **Ed25519 signature** before swapping
> binaries. Widen deliberately.

## End-to-end smoke test

```bash
# 1. Inside agent chat:
@agent give me a cli key for my laptop
# → outputs `starchild login starchild_<base64>` (bundle has sc_… code)

# 2. On laptop:
starchild login starchild_xxx
starchild whoami
starchild "hello, who are you?"
# → starchild sends Bearer sc_… to sc-chatroom; sc-chatroom resolves
# → it to AKM + container_id and forwards to user's clawd

# 3. Revoke the short code from chat:
@agent revoke cli code sc_xxxxxxxx

# 4. Next CLI call should fail at the gateway:
starchild "hello?"
# → "gateway rejected (401) — code may be revoked; ask your agent for a fresh CLI bundle"
```

## Pipe / shell composition (CLI ≥ v0.1.0)

Once paired, `starchild` is pipe-friendly. It reads stdin when no
positional prompt is given, writes the assistant reply to stdout, and
sends diagnostics to stderr — so it composes with any Unix tool.

```bash
# stdin → reply
echo "explain monads in 3 lines" | starchild

# reply → downstream
starchild "what is the OWASP top 10?" | pbcopy

# full three-stage pipe with streaming output
( echo "summarize this README:"; cat README.md ) | starchild --stream | tee summary.md

# code review pattern — concatenate context + question upstream
( echo "review this diff, flag risky changes:"; git diff ) | starchild
```

**Gotcha:** when you pass a positional prompt, stdin is **ignored**.
To send both context and an instruction, concatenate them upstream
with `( echo "<question>"; cat <file> )` rather than relying on
`cat <file> | starchild "<question>"` (which would silently drop the
file contents).

## SOUL.md hint (recommended)

Add to your agent's SOUL.md so the LLM picks the right tool when the
user asks for a CLI key:

```markdown
## Issuing CLI bundles for the user's own bots/scripts

When the user asks "give me a cli key" / "create a starchild bundle" /
"let me talk to you from my terminal", run:

  python3 skills/cli-bridge/scripts/cli_login.py --label "<inferred>"

This is a chat bridge only — it does NOT let you run commands on their
machine. ONLY add `--enable-shell` when the user explicitly asks for local
shell access ("run commands on my laptop", "use agent-shell", "organize my
Downloads"):

  python3 skills/cli-bridge/scripts/cli_login.py --label "<inferred>" --enable-shell

Treat `--enable-shell` as granting remote command execution on their
machine — never add it by default or "to be helpful". If they later want
shell, mint a new `--enable-shell` bundle and have them revoke the old one.

Default the label to something like "untitled-YYYY-MM-DD" if the user
doesn't suggest one. Show them the resulting bundle and tell them how
to revoke: `cli-list` to find the code, then `cli-revoke sc_…`.

After pairing, mention they can also pipe into the CLI from their
shell — e.g. `echo "..." | starchild`, `starchild "..." | pbcopy`,
or `( echo "review:"; git diff ) | starchild`. Stdout is the reply
(pipe-safe), stderr is diagnostics. Note the gotcha: passing a
positional prompt makes stdin get ignored, so context + question
should be concatenated upstream.
```
