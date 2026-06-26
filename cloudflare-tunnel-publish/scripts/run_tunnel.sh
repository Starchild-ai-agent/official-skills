#!/usr/bin/env bash
# Download cloudflared if missing, then start the tunnel.
# Run with bash(background=true) — this script blocks while cloudflared runs.
set -euo pipefail

WORKSPACE="/data/workspace"
BIN_DIR="$WORKSPACE/bin"
BIN="$BIN_DIR/cloudflared"
STATE="$WORKSPACE/.cf_state.json"

mkdir -p "$BIN_DIR"

if [[ ! -x "$BIN" ]]; then
    echo "→ Downloading cloudflared..."
    arch=$(uname -m)
    case "$arch" in
        x86_64) suffix="amd64" ;;
        aarch64|arm64) suffix="arm64" ;;
        *) echo "Unsupported arch: $arch"; exit 2 ;;
    esac
    url="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${suffix}"
    curl -fsSL -o "$BIN" "$url"
    chmod +x "$BIN"
    echo "✅ cloudflared installed at $BIN"
fi

if [[ ! -f "$STATE" ]]; then
    echo "❌ Missing $STATE — run setup.py first."
    exit 2
fi

# Allow the caller to pass a run token explicitly (used by keepalive.sh when
# guarding multiple sites, each with its own token). Fall back to the state file.
TOKEN="${1:-}"
if [[ -z "$TOKEN" ]]; then
    TOKEN=$(python3 -c "import json; print(json.load(open('$STATE'))['run_token'])")
fi

if [[ -z "$TOKEN" ]]; then
    echo "❌ run_token missing from state."
    exit 2
fi

echo "→ Starting cloudflared tunnel..."
exec "$BIN" tunnel --no-autoupdate run --token "$TOKEN"
