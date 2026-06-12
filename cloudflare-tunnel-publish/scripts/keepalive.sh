#!/usr/bin/env bash
# keepalive.sh — the SINGLE recovery brain for a Cloudflare-tunnel site.
#
# One idempotent script used in BOTH places, so start-up and self-heal can
# never drift apart:
#   • boot      : called once from workspace/setup.sh (survives container restart)
#   • watchdog  : called on a schedule_task every few minutes (survives mid-life
#                 process death — cloudflared exiting on a network blip etc.)
#
# It is generic. It reads everything it needs from .cf_state.json:
#   hostname, port, tunnel_name, and (optional) app_cmd + app_dir.
# So the same file works for ANY domain published with this skill — the calling
# agent writes ZERO project-specific shell.
#
# It NEVER calls the Cloudflare API and NEVER needs CLOUDFLARE_API_TOKEN.
# Configuration (tunnel/DNS creation, run_token) is done once by setup.py and
# persisted in .cf_state.json; keepalive only reads that and (re)launches local
# processes. This is why it is safe to run on every boot and every few minutes.
#
# Reporting (so a scheduled command-task pushes signal, not spam):
#   • healthy run                    -> SILENT (log line only)
#   • newly down, auto-recovered     -> prints ONE line  (incident + resolution)
#   • newly down, still failing      -> prints ONE line  (incident needs a human)
#   • already-known down, still down -> SILENT           (no repeat spam)
# State is tracked in run/keepalive.state so only transitions speak.
set -uo pipefail

WS="/data/workspace"
STATE="$WS/.cf_state.json"
LOGDIR="$WS/logs"; PIDDIR="$WS/run"
mkdir -p "$LOGDIR" "$PIDDIR"
LASTSTATE="$PIDDIR/keepalive.state"

ts()  { date -u +'%Y-%m-%dT%H:%M:%SZ'; }
log() { echo "[$(ts)] $*" >> "$LOGDIR/keepalive.log"; }

[ -f "$STATE" ] || {
  log "no .cf_state.json — run setup.py once to configure. nothing to do."
  exit 0
}

# --- read config from state (pure local read, no API) ---
read_state() { python3 -c "import json,sys;print(json.load(open('$STATE')).get('$1',''))" 2>/dev/null; }
HOST="$(read_state hostname)"
PORT="$(read_state port)"
APP_CMD="$(read_state app_cmd)"
APP_DIR="$(read_state app_dir)"
[ -n "$HOST" ] || { log "no hostname in state — cannot guard."; exit 0; }
[ -n "$APP_DIR" ] || APP_DIR="$WS"

APP_PID="$PIDDIR/app.pid"
TUN_PID="$PIDDIR/cloudflared.pid"

# --- probes ---
public_ok() { curl -fsS --max-time 12 "https://$HOST/" >/dev/null 2>&1; }

local_ok() {
  [ -n "$PORT" ] || { echo skip; return; }   # no app to manage -> tunnel-only mode
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

# --- recovery actions (idempotent) ---
start_app() {
  [ -n "$APP_CMD" ] || { log "app down but no app_cmd in state — skipping app start"; return 1; }
  cd "$APP_DIR" 2>/dev/null || { log "ERROR app_dir not found: $APP_DIR"; return 1; }
  setsid bash -c "exec $APP_CMD" >> "$LOGDIR/app.log" 2>&1 < /dev/null &
  echo $! > "$APP_PID"
  log "started app: ($APP_CMD) in $APP_DIR pid=$(cat "$APP_PID")"
}

start_tunnel() {
  [ -f "$TUN_PID" ] && kill "$(cat "$TUN_PID" 2>/dev/null)" 2>/dev/null || true
  pkill -f "cloudflared tunnel .* run --token" 2>/dev/null || true
  rm -f "$TUN_PID"; sleep 2
  setsid bash -c "exec bash $WS/skills/cloudflare-tunnel-publish/scripts/run_tunnel.sh" \
    >> "$LOGDIR/cloudflared.log" 2>&1 < /dev/null &
  echo $! > "$TUN_PID"
  log "(re)started cloudflared pid=$(cat "$TUN_PID")"
}

heal() {
  local lo; lo="$(local_ok)"
  if [ "$lo" = "closed" ]; then
    log "WARN local app :$PORT down -> restart app + tunnel"
    start_app
    start_tunnel
  else
    log "WARN tunnel down (local :$PORT ${lo}) -> restart tunnel"
    start_tunnel
  fi
}

prev="UP"; [ -f "$LASTSTATE" ] && prev="$(cat "$LASTSTATE" 2>/dev/null || echo UP)"

# --- fast path: healthy ---
if public_ok; then
  log "ok https://$HOST"
  if [ "$prev" = "DOWN" ]; then
    echo "✅ $HOST recovered at $(ts)"
  fi
  echo "UP" > "$LASTSTATE"
  exit 0
fi

# --- down: heal, then verify with a few retries (covers cold-start tunnel warm-up) ---
heal
ok=0
for _ in 1 2 3; do
  sleep 5
  if public_ok; then ok=1; break; fi
done

if [ "$ok" = "1" ]; then
  log "recovered https://$HOST"
  echo "🔧 $HOST was down — auto-recovered at $(ts)"
  echo "UP" > "$LASTSTATE"
  exit 0
else
  log "ERROR still down https://$HOST after heal"
  if [ "$prev" != "DOWN" ]; then
    echo "🚨 $HOST is DOWN and auto-recovery failed at $(ts) — needs a manual look (check logs/cloudflared.log, logs/app.log)"
  fi
  echo "DOWN" > "$LASTSTATE"
  exit 1
fi
