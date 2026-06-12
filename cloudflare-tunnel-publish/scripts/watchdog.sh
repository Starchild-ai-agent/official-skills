#!/usr/bin/env bash
# Runtime self-heal for a Cloudflare tunnel published by this skill.
#
# Designed to be run periodically (e.g. a scheduled `command` task every 1-2 min).
# Idempotent. Prints to stdout ONLY when it had to take recovery action, so a
# scheduled task stays SILENT (zero push cost) during normal operation and
# pushes a one-line alert only on an actual incident.
#
# Covers the failure mode a one-shot boot script (setup.sh / start_services.sh)
# CANNOT catch: cloudflared dies mid-life while the container keeps running
# (network blip -> "context deadline exceeded" -> process exits -> 530/1033).
#
# Reads hostname/port from .cf_state.json — no per-domain editing needed.
set -uo pipefail

WS="/data/workspace"
STATE="$WS/.cf_state.json"
LOGDIR="$WS/logs"; PIDDIR="$WS/run"
mkdir -p "$LOGDIR" "$PIDDIR"

[ -f "$STATE" ] || { echo "watchdog: no .cf_state.json — nothing to guard"; exit 0; }

HOST=$(python3 -c "import json;print(json.load(open('$STATE')).get('hostname',''))" 2>/dev/null || true)
PORT=$(python3 -c "import json;print(json.load(open('$STATE')).get('port',''))" 2>/dev/null || true)
[ -n "$HOST" ] || { echo "watchdog: no hostname in state"; exit 0; }

NAME="cloudflared-$(echo "$HOST" | cut -d. -f1)"
PIDFILE="$PIDDIR/$NAME.pid"

ts()  { date -u +'%Y-%m-%dT%H:%M:%SZ'; }
log() { echo "[$(ts)] $*" >> "$LOGDIR/watchdog.log"; }

public_ok() { curl -fsS --max-time 12 "https://$HOST/" >/dev/null 2>&1; }

local_ok() {
  [ -n "$PORT" ] || { echo closed; return; }
  python3 - "$PORT" <<'PY'
import socket, sys
s = socket.socket(); s.settimeout(1.0)
try:
    s.connect(("127.0.0.1", int(sys.argv[1]))); print("open")
except Exception:
    print("closed")
finally:
    s.close()
PY
}

restart_tunnel() {
  [ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE" 2>/dev/null)" 2>/dev/null || true
  pkill -f "cloudflared tunnel .* run --token" 2>/dev/null || true
  rm -f "$PIDFILE"
  sleep 2
  setsid bash -c "exec bash $WS/skills/cloudflare-tunnel-publish/scripts/run_tunnel.sh" \
    >> "$LOGDIR/$NAME.log" 2>&1 < /dev/null &
  echo $! > "$PIDFILE"
}

# ---- fast path: already healthy ----
if public_ok; then
  log "ok https://$HOST"
  exit 0
fi

# ---- public is down: figure out the culprit, then heal ----
LOCAL=$(local_ok)
if [ "$LOCAL" != "open" ]; then
  log "WARN local app on :$PORT down -> start_services.sh (app + tunnel)"
  pkill -f "cloudflared tunnel .* run --token" 2>/dev/null || true
  rm -f "$PIDFILE"
  bash "$WS/scripts/start_services.sh" >/dev/null 2>&1 || true
else
  log "WARN tunnel down (local :$PORT ok) -> restart tunnel"
  restart_tunnel
fi

# ---- verify recovery, report only now ----
sleep 8
if public_ok; then
  log "recovered https://$HOST"
  echo "🔧 $HOST tunnel was down — auto-recovered at $(ts)"
  exit 0
else
  log "ERROR still down https://$HOST after auto-restart"
  echo "🚨 $HOST STILL DOWN after auto-restart at $(ts) — needs a manual look"
  exit 1
fi
