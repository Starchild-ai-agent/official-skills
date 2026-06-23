#!/usr/bin/env bash
# One-click installer for ALL production agent-hooks.
#
# Copies every production template into /data/workspace/hooks/, writes the
# canonical config/shell_hooks.yaml wiring, runs each script's selftest, then
# self-approves + hot-mounts them via the loopback runtime API (no restart).
#
# Idempotent: safe to re-run (it overwrites the hook copies + the managed config
# block, then re-approves). Run from anywhere:
#   bash skills/agent-hooks/scripts/install_all.sh
#
# Flags:
#   --no-footer      skip the footer policy (footer_guard.py, pre_llm_call + on_response_end)
#   --footer-tokens  set FOOTER_SHOW_TOKENS=1 in the footer hook (show token counts)
#   --dry-run        show what would happen, change nothing
set -euo pipefail

WS="/data/workspace"
TPL="$WS/skills/agent-hooks/templates"
HOOKS="$WS/hooks"
CFG="$WS/config/shell_hooks.yaml"
API="http://localhost:8000/internal/runtime/hooks/approve"

WANT_FOOTER=1
FOOTER_TOKENS=0
DRY=0
for a in "${@:-}"; do
  case "$a" in
    "") ;;
    --no-footer) WANT_FOOTER=0 ;;
    --footer-tokens) FOOTER_TOKENS=1 ;;
    --dry-run) DRY=1 ;;
    *) echo "unknown flag: $a" >&2; exit 2 ;;
  esac
done

say() { printf '%s\n' "$*"; }
run() { if [ "$DRY" = 1 ]; then say "  [dry-run] $*"; else eval "$*"; fi; }

# Production scripts to install (each has a matching *_selftest.py)
SCRIPTS=(security_guard verify_publish_claims)
if [ "$WANT_FOOTER" = 1 ]; then
  SCRIPTS+=(footer_guard)
fi

say "== agent-hooks one-click install =="
say "templates : $TPL"
say "target    : $HOOKS"
say "footer    : $([ "$WANT_FOOTER" = 1 ] && echo on || echo off)  tokens=$FOOTER_TOKENS"
say ""

# 1) selftest each (fail fast before touching anything live)
say "-- running selftests --"
for s in "${SCRIPTS[@]}"; do
  st="$TPL/${s}_selftest.py"
  if [ -f "$st" ]; then
    if [ "$DRY" = 1 ]; then
      say "  [dry-run] python3 $st"
    else
      if python3 "$st" >/tmp/hook_selftest.log 2>&1; then
        say "  ok  $s ($(tail -1 /tmp/hook_selftest.log))"
      else
        say "  FAIL $s — aborting:"; cat /tmp/hook_selftest.log; exit 1
      fi
    fi
  else
    say "  --  $s (no selftest)"
  fi
done
say ""

# 2) copy templates -> hooks/ (+x)
say "-- copying hooks --"
run "mkdir -p '$HOOKS'"
for s in "${SCRIPTS[@]}"; do
  run "cp '$TPL/${s}.py' '$HOOKS/${s}.py'"
  run "chmod +x '$HOOKS/${s}.py'"
  say "  $s.py"
done
say ""

# 3) write canonical config
say "-- writing $CFG --"
if [ "$DRY" = 1 ]; then
  say "  [dry-run] would write managed shell_hooks.yaml"
else
  mkdir -p "$(dirname "$CFG")"
  [ -f "$CFG" ] && cp "$CFG" "$CFG.bak.$(date +%s)" && say "  backed up existing -> $CFG.bak.*"
  {
    cat <<'YAML'
# Shell hooks — managed by agent-hooks/scripts/install_all.sh
# Re-run that installer to regenerate. Manual edits below the marker are kept
# only until the next install; put custom hooks ABOVE the marker if you add any.
hooks:
  # ── Security guard (secrets + destructive bash) ───────────────────
  - event: on_user_message
    command: /data/workspace/hooks/security_guard.py
    timeout: 15
  - event: pre_tool_call
    command: /data/workspace/hooks/security_guard.py
    timeout: 15
  - event: transform_tool_result
    command: /data/workspace/hooks/security_guard.py
    timeout: 15
  - event: on_response_end
    command: /data/workspace/hooks/security_guard.py
    timeout: 15
  - event: on_outbound_message
    command: /data/workspace/hooks/security_guard.py
    timeout: 15

  # ── Anti-hallucination (verify_publish_claims) ────────────────────
  - event: on_stop
    matcher: "publish|posted|preview|/post/|community\\.iamstarchild|已发布|已上线|已更新|发布成功"
    command: /data/workspace/hooks/verify_publish_claims.py
    timeout: 10
  - event: on_completion_claim
    matcher: "publish|posted|preview|/post/|community\\.iamstarchild|已发布|已上线|已更新|发布成功"
    command: /data/workspace/hooks/verify_publish_claims.py
    timeout: 10
  - event: on_response_end
    matcher: "publish|posted|preview|/post/|community\\.iamstarchild|已发布|已上线|已更新|发布成功"
    command: /data/workspace/hooks/verify_publish_claims.py
    timeout: 10
YAML
    if [ "$WANT_FOOTER" = 1 ]; then
      cat <<'YAML'

  # ── Footer policy (ONE script, two events) ────────────────────────
  - event: pre_llm_call
    command: /data/workspace/hooks/footer_guard.py
    timeout: 10
  - event: on_response_end
    command: /data/workspace/hooks/footer_guard.py
    timeout: 10
YAML
    fi
  } > "$CFG"
  say "  written ($(grep -c 'command:' "$CFG") hook entries)"
fi
say ""

# 4) self-approve + hot-mount each unique script
say "-- approving + mounting --"
for s in "${SCRIPTS[@]}"; do
  cmd="$HOOKS/${s}.py"
  if [ "$DRY" = 1 ]; then
    say "  [dry-run] approve $cmd"
  else
    resp=$(curl -s -X POST "$API" -H 'Content-Type: application/json' \
      -d "{\"command\": \"$cmd\"}")
    say "  $s -> $resp"
  fi
done
say ""
say "== done =="
[ "$WANT_FOOTER" = 1 ] && [ "$FOOTER_TOKENS" = 1 ] && \
  say "note: set FOOTER_SHOW_TOKENS=1 in the agent env to show token counts."
say "verify with: /hooks list   (or)   /hooks status"
