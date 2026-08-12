---
name: cli-bridge
version: 0.4.0
description: |
  Manage short-code bundles that authorize the local starchild CLI to talk to this agent, including the agent-shell local-exec channel and the local MCP proxy (stdio MCP servers on the user's machine).

  Use when connecting or disconnecting the starchild CLI (e.g. mint a CLI bridge code, list my CLI bundles, revoke an old CLI session, let the agent run shell commands on the user's own machine, or drive a local app via a stdio MCP server — Blender, Figma, Godot, computer-use, etc.).
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

## Install the CLI

The rest of this skill assumes `starchild` is on the user's `$PATH` — install
it first if it isn't.

### One-liner (auto-detects OS + arch)

```bash
curl -fsSL https://workroom.iamstarchild.com/install/cli | bash
```

Picks the right binary for darwin/linux × arm64/amd64, drops it on
`$PATH` (Apple Silicon lands in `/opt/homebrew/bin`; Linux falls back to
`~/.local/bin`; `sudo` only when the dir isn't user-writable), patches the
user's shell rc if the install dir wasn't already on `$PATH`, and runs
`starchild --version` as a self-check. SHA256 etag means re-running is a
cheap "already current" no-op (HTTP 304, no download). Source for review:
[tools/install-cli.sh](https://workroom.iamstarchild.com/install/cli)
(`__SERVER_URL__` is rewritten at request time).

### Homebrew

```bash
brew tap starchild/tap https://github.com/Starchild-ai-agent/homebrew-tap
brew trust starchild/tap
brew install starchild
```

The `starchild` formula ships binaries for **macOS (arm64 / amd64) and
Linux (arm64 / amd64)** — `brew install` picks the right one for the host.
The formula has no `bottle` block, so install runs a tiny Ruby script that
downloads the prebuilt binary from the server (`workroom.iamstarchild.com`)
and drops it on `$PATH` — there's no local compile step. To upgrade later:
`brew update && brew upgrade starchild`.

**Linux caveat:** Homebrew itself works on Linux, but expects a Ruby +
build toolchain (one-time `apt install build-essential ruby` / distro
equivalent). For a Linux host, the oneliner above skips that and is
functionally identical, so prefer it unless the user is already a brew
user. **`starchild-app` (the desktop workspace) is macOS-only** — that
formula builds from source (rust + node) and only the macOS build is
meaningful.

### Verify

```bash
starchild --version
```

If you just ran the one-liner and your shell still says `command not found`,
open a new terminal — the PATH update is in your rc, not the current
session.

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
- **File-transfer policy** — the `transfer_dir` (always-allowed workspace),
  `yolo` flag, and the `read_allow` / `write_allow` globs from
  `~/.config/starchild/file-policy.toml`. Present only when the bundle
  carries the `files` capability. See "File path policy" below for the
  full rules; this bullet is just so the agent knows the laptop
  advertised file transfer at all.

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

## File transfer via `agent-shell` (CLI ≥ v0.3.0)

When the bundle is minted with `--enable-files`, the same `agent-shell`
daemon also serves **file transfer** between the user's machine and the
agent's workspace. Content streams disk→disk and never passes through the
chat, so **large/binary files (10MB+ PDFs, images, archives) work**.

Three agent-facing tools + one user command:
- `request_upload(laptop_path)` — agent pulls a file FROM the laptop into
  `workspace/uploads/` ("take my ~/big.pdf and summarize it").
- `write_local_file(src, dst)` — agent sends a workspace file TO the laptop
  ("save workspace/output/report.pdf to my ~/Downloads"). `src` is a
  workspace path, not inline content.
- `read_local_file(path)` — read a **small text** file for the agent to see
  (config/log snippet). Large/binary files go through `request_upload`.
- `starchild push <file>` — user proactively uploads a local file into the
  agent's `workspace/uploads/`; it's announced to the agent in its prompt.

```bash
python3 skills/cli-bridge/scripts/cli_login.py --label "laptop" --enable-files
# combine with shell if you want both:
python3 skills/cli-bridge/scripts/cli_login.py --label "laptop" --enable-shell --enable-files
```

`files` is an **independent capability** from `shell` — a bundle can have
either, both, or neither. Like shell, it's off by default and authoritative
on the AKM (clawd refuses transfer frames for a connection without it).

### File path policy (laptop-side, layered)

Transfers are gated on the laptop by a path policy, strictest-first:

1. **Built-in protected paths are ALWAYS refused** (even under `--yolo`):
   `~/.ssh`, `~/.aws`, shell rc (`.zshrc`/`.bashrc`/…), `.config/starchild`,
   launchd/systemd/cron, `.git/hooks`, browser cookie stores, `.env`, ssh
   keys. Writing those would be persistent RCE; reading them leaks creds.
2. **Dedicated transfer dir** (`~/starchild-transfer`, auto-created) — always
   allowed for read + write. The safe default workspace; prefer it.
3. **Outside that dir** — denied unless the path matches a `read_allow` /
   `write_allow` glob in `~/.config/starchild/file-policy.toml`, **or** the
   daemon was started with `--yolo`:

   ```bash
   starchild agent-shell --yolo   # allow ANY path (built-in deny still applies)
   ```

   ```yaml
   # ~/.config/starchild/file-policy.toml  (YAML allow-globs)
   read_allow:
     - "~/Documents/*.md"
   write_allow:
     - "~/exports/*.csv"
   ```

Other guarantees: written files get mode **0644** (never executable);
writes are atomic (temp file + rename, no half-written target); symlinks
that escape the transfer dir are refused; per-transfer cap is 100 MiB,
streamed in chunks so large files don't blow the WS frame limit.

> **Security note:** a running `agent-shell` (on a `--enable-shell` bundle)
> plus a permissive policy is effectively remote command execution on the
> user's machine, bounded by the AKM TTL, the `sc_…` code's validity, and the
> policy file. Defaults are conservative: shell is **off** unless explicitly
> granted, the policy is **deny-all** until commands are opted in, and the
> daemon's self-update verifies an **Ed25519 signature** before swapping
> binaries. Widen deliberately.

## Local MCP servers via `agent-shell` (CLI ≥ v0.5.32)

`agent-shell` **is** the MCP Host for the user's machine. The same daemon
that runs `local_shell` and file transfer also reads
`~/.config/starchild/mcp-servers.toml`, spawns each enabled stdio MCP
server as a long-lived child process, runs the MCP `initialize` →
`tools/list` handshake, and proxies `tools/call` over the existing
WebSocket to clawd. clawd then registers each remote tool as
`mcp__<server>__<tool>` and injects them into the **current** conversation
— no new session is required.

This is the path for driving a LOCAL app (Blender, Godot, a local
Figma-bridge, computer-use, browser-use, the filesystem server, …) from
the cloud agent. The agent can't reach `localhost` on the user's
machine any other way; clawd's own (direct) MCP support is for
REMOTE/HTTP/SSE servers hosted elsewhere, not for processes that must
run on the user's laptop.

### How it works (the control channel is the same WS as local_shell)

```
clawd (cloud agent)
  │  mcp_list / mcp_call frames
  │  (over the existing /ws/cli-shell WebSocket)
  ▼
agent-shell daemon (laptop) ── MCPProxy
  │  stdio JSON-RPC (newline-delimited)
  ▼
blender-mcp / figma-mcp / server-everything / … (one process per server)
```

The laptop side owns the MCP session state (initialize → initialized →
tools/list, cached). clawd only sends high-level `mcp_call`s; it never
speaks raw JSON-RPC. A `tools/list_changed` notification from a server
re-fetches and re-registers that server's tools.

### Configuring a server

Edit `~/.config/starchild/mcp-servers.toml` (YAML, despite the `.toml`
extension — same convention as exec/file-policy). Each entry:

```yaml
servers:
  - id: blender
    command: uv
    args:
      - "--directory"
      - "/Users/aladdin/Workspace/StarChild/blender_mcp/mcp"
      - "run"
      - "blender-mcp"
    env:
      - "SOME_KEY=value"
    enabled: true
```

**Absolute paths only.** `$HOME` and `~` are NOT expanded — MCP clients
spawn the command directly, not through a shell. Use
`/Users/<name>/...`, never `~/...` or `$HOME/...`.

`enabled` defaults to `true` (an entry without `enabled:` runs). The
file is hot-reloadable, but **running sessions only change when the
daemon restarts** — a reload updates the parsed config, it does not
spawn/kill server processes mid-session. The app's Settings panel writes
this file and restarts `agent-shell` for you.

### Restarting agent-shell does NOT cut the chat

The chat stream (your reply to the user) runs over clawd's HTTP/SSE
path, NOT over `agent-shell`. Restarting `agent-shell` only interrupts
`local_shell` / file-transfer / `mcp_call` for the ~2s it takes to
reconnect — the conversation itself stays alive. So you CAN tell the
user (or do it yourself via `local_shell`) to restart the daemon after a
config change; you won't kill the conversation.

After restart, the daemon sends a fresh `hello` with an `mcp_manifest`
listing the enabled servers + each one's runtime status
(`ready`/`failed`/`not_started`). clawd eagerly `mcp_list`s each ready
one and registers the tools. A per-turn `maybe_resync_local_mcp` catch-up
also covers servers that failed to fetch at hello (e.g. a slow-to-start
server) on subsequent turns.

### Dynamic injection — `local_mcp_status` + `local_mcp_reload`

You don't have to restart agent-shell to pick up a config edit. Two
agent-facing tools drive the local MCP runtime live:

- **`local_mcp_status`** — returns every configured server's runtime
  state (`ready` with tool count, `failed` with the error, or
  `not_started`). Call this when an expected `mcp__<server>__*` tool is
  missing — the server may have failed to start.
- **`local_mcp_reload`** — asks agent-shell to re-read
  `mcp-servers.toml` at runtime, start newly-added servers, stop removed
  ones. **No daemon restart, no chat interruption.** After a reload, the
  added servers' `mcp__<server>__*` tools appear in the **next turn**
  (the tool list is rebuilt per request). Use this after editing the
  config to make a new server available without asking the user to
  restart anything.

Typical flow when a server the user just configured isn't showing tools:
1. Call `local_mcp_status` → see `blender: not_started` or `failed: …`.
2. (Fix the config if `failed` — bad path, missing dep, etc.)
3. Call `local_mcp_reload` → agent-shell starts the new server.
4. Next turn, `mcp__blender__*` tools are registered.

### What the agent sees

- **Tools** appear as `mcp__<server>__<tool>` (e.g.
  `mcp__blender__get_scene`, `mcp__everything__echo`). Their
  `description` and `input_schema` come from the server's own
  `tools/list` — call them like any native tool.
- **The prompt manifest** (`build_mcp_manifest_section`, in the volatile
  tail) lists which local MCP servers are connected and a roster of
  their tool names. If a server is configured but failed to start, that
  is noted here too (config present, not loaded).
- If you don't see an `mcp__<server>__*` tool you expected, the server
  didn't come up. Diagnose in this order:
  1. Is it in `~/.config/starchild/mcp-servers.toml` with `enabled: true`?
  2. Did `agent-shell` restart AFTER the edit? (config is read at start)
  3. The daemon log (`~/.starchild/sc-chatroom[-dev]/cli-shell/agent.log`)
     has a line per server: `agent-shell: mcp: <id> ready (N tools)` on
     success, or `agent-shell: mcp: failed to start <id>: <reason>` on
     failure. Read it via `local_shell`.
  4. For servers that need a LOCAL app bridge (Blender's addon on
     `127.0.0.1:9876`, a Figma plugin, …) confirm that bridge is
     running too — the MCP server process can start but its tools will
     error until the backend app is reachable.

### Don't bypass MCP to talk to the local app

When a server like Blender's is slow to register, it's tempting to open
a raw socket to the app's own bridge (`127.0.0.1:9876`) and send Python
directly. Don't — that sidesteps the MCP tool layer (no schema, no
policy, no per-call validation) and the agent loses the structured
`mcp__blender__*` interface. Fix the MCP server's startup instead
(check the log, confirm the bridge, restart `agent-shell`). The raw
bridge is a last-resort fallback only.

### Server caveats (per-backend)

- **Blender MCP** (`blender-mcp`): two parts — the stdio MCP server
  (`uv run`) AND the Blender addon's bridge (listen on
  `127.0.0.1:9876`). Both must be running. The MCP server starts even
  if Blender is closed, but every tool call errors until the addon
  bridge is up. `which blender` often fails even when Blender.app is
  open — that's fine, the bridge is what matters.
- **Figma**: there are TWO different Figma MCPs. `figma-mcp-server`
  (REST-wrapper, read-only canvas) runs locally via `bunx`; the official
  Figma remote MCP (write canvas, SSE) is a REMOTE server — configure
  it on the clawd side (`mcp_servers:` in agent.yaml), NOT here. This
  file is only for servers that run on the laptop.
- **computer-use / browser-use**: inherently local (they drive the
  user's screen/browser). Configure them here.

### Security

A local MCP server can execute arbitrary code on the user's machine
(Blender's `execute_code`, a shell server, …). Treat adding an entry to
`mcp-servers.toml` with the same gravity as widening the exec policy:
only add servers the user asked for, prefer read-only servers, and
never put a secret (API key) in chat — use the `env:` field. The
`mcp-servers.toml` path is NOT in the file-policy allow-list by default;
add it there if the user wants the agent to write configs directly.

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
machine or touch their files. Two independent opt-in capabilities, each
granting local access — only add them when the user explicitly asks:

- `--enable-shell` → run commands ("run commands on my laptop", "use
  agent-shell", "organize my Downloads"). Remote command execution.
- `--enable-files` → read/write files ("save this to my laptop", "read my
  ~/notes.md"). Reads/writes files on their machine.

  python3 skills/cli-bridge/scripts/cli_login.py --label "<inferred>" --enable-shell
  python3 skills/cli-bridge/scripts/cli_login.py --label "<inferred>" --enable-files

Treat both as granting access to their machine — never add either by
default or "to be helpful". If they later want a capability, mint a new
bundle with the flag and have them revoke the old one.

Default the label to something like "untitled-YYYY-MM-DD" if the user
doesn't suggest one. Show them the resulting bundle and tell them how
to revoke: `cli-list` to find the code, then `cli-revoke sc_…`.

After pairing, mention they can also pipe into the CLI from their
shell — e.g. `echo "..." | starchild`, `starchild "..." | pbcopy`,
or `( echo "review:"; git diff ) | starchild`. Stdout is the reply
(pipe-safe), stderr is diagnostics. Note the gotcha: passing a
positional prompt makes stdin get ignored, so context + question
should be concatenated upstream.

## Driving a local app via MCP (agent-shell ≥ v0.5.32)

Once `--enable-shell` is granted and `agent-shell` is running, you can
also drive LOCAL apps (Blender, Godot, a local Figma-bridge,
computer-use, …) through stdio MCP servers. The agent-shell daemon IS
the MCP Host: it reads `~/.config/starchild/mcp-servers.toml`, spawns
the servers, and registers their tools as `mcp__<server>__<tool>` into
this conversation. No separate MCP client (Cursor/Claude Desktop) is
needed.

When the user asks "control Blender" / "use the local figma plugin" /
"drive my local <app> via MCP":
- Confirm `agent-shell` is connected (a `local_shell` call works).
- Add the server to `~/.config/starchild/mcp-servers.toml` (ABSOLUTE
  paths only — no `$HOME`, no `~`). The app's Settings → Local MCP
  Servers panel can do this too.
- Restart `agent-shell` (`starchild agent-shell-stop && starchild
  agent-shell`, or via the app's RestartBanner). This does NOT cut the
  chat — only `local_shell`/file-transfer pause for ~2s.
- After restart the `mcp__<server>__*` tools appear. If they don't,
  read the daemon log (`~/.starchild/sc-chatroom[-dev]/cli-shell/
  agent.log` — look for `mcp: <id> ready` or `mcp: failed to start
  <id>: <reason>`) via `local_shell`.
- For servers with a local app bridge (Blender's addon on
  127.0.0.1:9876), confirm that bridge is running too — the MCP server
  process can start but its tools error until the backend app is up.
- Prefer the `mcp__<server>__*` tools over opening a raw socket to the
  app's bridge. The MCP layer gives you schemas + validation; the raw
  bridge is a last-resort fallback.

Don't add a server the user didn't ask for — a local MCP server can
execute arbitrary code on their machine. See the "Local MCP servers via
agent-shell" section above for the full config format and per-backend
caveats (Blender two-part, Figma local-vs-remote, etc.).
```
