#!/usr/bin/env bash
# keepalive.sh — the SINGLE recovery brain for Cloudflare-tunnel sites.
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
# MULTIPLE SITES: .cf_state.json can hold one site (flat) OR many (under a
# "sites" array). When "sites" exists, this script guards EVERY site in the
# list — one process, one watchdog, all hostnames. This is the fix for the
# "each site got its own tunnel + its own keepalive, and only one was watched"
# bug. See SKILL.md § "Multiple sites" for the state format.
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

ts()  { date -u +'%Y-%m-%dT%H:%M:%SZ'; }
log() { echo "[$(ts)] $*" >> "$LOGDIR/keepalive.log"; }

[ -f "$STATE" ] || {
  log "no .cf_state.json — run setup.py once to configure. nothing to do."
  exit 0
}

# --- enumerate sites to guard ---
# Each site is a flat dict: hostname, port, app_cmd, app_dir, run_token,
# tunnel_id, tunnel_name. When .cf_state.json has a top-level "sites" array,
# guard every entry. Otherwise (legacy single-site state), wrap the flat state
# into a one-element list.
mapfile -t SITES < <(python3 -c "
import json, sys
s = json.load(open('$STATE'))
sites = s.get('sites') if isinstance(s, dict) else None
if not sites and isinstance(s, dict) and s.get('hostname'):
    sites = [s]
if not sites:
    sys.exit(0)
for s in sites:
    h = s.get('hostname','')
    if not h: continue
    # Escape for tab-separated output (newlines/tabs in values are unlikely
    # but we strip them defensively).
    vals = [str(s.get(k,'')).replace('\t',' ').replace('\n',' ') for k in
            ('hostname','port','app_cmd','app_dir','run_token','tunnel_id','tunnel_name')]
    print('\t'.join(vals))
")

[ "${#SITES[@]}" -gt 0 ] || {
  log "no sites in .cf_state.json — run setup.py once to configure. nothing to do."
  exit 0
}

# --- per-site helpers ---
guard_site() {
  local HOST PORT APP_CMD APP_DIR RUN_TOKEN TUNNEL_ID TUNNEL_NAME
  IFS=$'\t' read -r HOST PORT APP_CMD APP_DIR RUN_TOKEN TUNNEL_ID TUNNEL_NAME <<<"$1"
  [ -n "$HOST" ] || return 0
  [ -n "$APP_DIR" ] || APP_DIR="$WS"

  # PID files are per-tunnel (one cloudflared process serves all hostnames
  # on that tunnel, but we track it under the first hostname for simplicity).
  local SAFE_HOST; SAFE_HOST="${HOST//[^a-zA-Z0-9]/_}"
  local APP_PID="$PIDDIR/app-${SAFE_HOST}.pid"
  local TUN_PID="$PIDDIR/cloudflared-${SAFE_HOST}.pid"
  local LASTSTATE="$PIDDIR/keepalive-${SAFE_HOST}.state"

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

  public_ok() { curl -fsS --max-time 12 "https://$HOST/" >/dev/null 2>&1; }

  start_app() {
    [ -n "$APP_CMD" ] || { log "$HOST: app down but no app_cmd — skipping app start"; return 1; }
    cd "$APP_DIR" 2>/dev/null || { log "$HOST: ERROR app_dir not found: $APP_DIR"; return 1; }
    setsid bash -c "exec $APP_CMD" >> "$LOGDIR/app-${SAFE_HOST}.log" 2>&1 < /dev/null &
    echo $! > "$APP_PID"
    local apid; apid=$(cat "$APP_PID" 2>/dev/null)
    log "$HOST: started app ($APP_CMD) in $APP_DIR pid=$apid"
  }

  start_tunnel() {
    # Kill the tunnel process for THIS site only (match by PID file, then by
    # run token so we don't clobber a different site's cloudflared).
    if [ -f "$TUN_PID" ]; then
      local old; old=$(cat "$TUN_PID" 2>/dev/null)
      [ -n "$old" ] && kill "$old" 2>/dev/null || true
    fi
    # Also kill any stale cloudflared holding this exact token
    if [ -n "$RUN_TOKEN" ]; then
      pkill -f "cloudflared tunnel .* --token .*${RUN_TOKEN:0:32}" 2>/dev/null || true
    fi
    rm -f "$TUN_PID"; sleep 2
    if [ -z "$RUN_TOKEN" ]; then
      log "$HOST: ERROR no run_token in state — cannot start tunnel"
      return 1
    fi
    setsid bash -c "exec bash $WS/skills/cloudflare-tunnel-publish/scripts/run_tunnel.sh '$RUN_TOKEN'" \
      >> "$LOGDIR/cloudflared-${SAFE_HOST}.log" 2>&1 < /dev/null &
    echo $! > "$TUN_PID"
    local pid; pid=$(cat "$TUN_PID" 2>/dev/null)
    log "$HOST: (re)started cloudflared pid=$pid"
  }

  heal() {
    local lo; lo="$(local_ok)"
    if [ "$lo" = "closed" ]; then
      log "$HOST: WARN local app :$PORT down -> restart app + tunnel"
      start_app
      start_tunnel
    else
      log "$HOST: WARN tunnel down (local :$PORT ${lo}) -> restart tunnel"
      start_tunnel
    fi
  }

  prev="UP"; [ -f "$LASTSTATE" ] && prev="$(cat "$LASTSTATE" 2>/dev/null || echo UP)"

  # fast path: healthy
  if public_ok; then
    log "ok https://$HOST"
    if [ "$prev" = "DOWN" ]; then
      echo "✅ $HOST recovered at $(ts)"
    fi
    echo "UP" > "$LASTSTATE"
    return 0
  fi

  # down: heal, then verify with a few retries
  heal
  local ok=0
  for _ in 1 2 3; do
    sleep 5
    if public_ok; then ok=1; break; fi
  done

  if [ "$ok" = "1" ]; then
    log "$HOST: recovered"
    echo "🔧 $HOST was down — auto-recovered at $(ts)"
    echo "UP" > "$LASTSTATE"
    return 0
  else
    log "$HOST: ERROR still down after heal"
    if [ "$prev" != "DOWN" ]; then
      echo "🚨 $HOST is DOWN and auto-recovery failed at $(ts) — check logs/cloudflared-${SAFE_HOST}.log, logs/app-${SAFE_HOST}.log"
    fi
    echo "DOWN" > "$LASTSTATE"
    return 1
  fi
}

# --- guard every site ---
overall=0
for site in "${SITES[@]}"; do
  guard_site "$site" || overall=1
done
exit $overall
