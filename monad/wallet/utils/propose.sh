#!/usr/bin/env bash
# Self-bootstrapping wrapper for propose.mjs.
#
# Why this exists: Node resolves ES-module imports against the script's own
# directory, not the cwd. If we asked users to `npm install viem` in their
# project and then `node /plugin/path/propose.mjs`, Node would look for viem
# in the plugin directory's node_modules (which is empty) and fail with
# ERR_MODULE_NOT_FOUND. This wrapper copies propose.mjs + package.json into
# a stable cache dir (~/.monskills/propose-deps/), installs deps there once,
# and runs propose.mjs from that cache — so imports resolve cleanly no matter
# where the user invokes it from.
#
# Usage (from SAFE_WALLET_MANAGEMENT.md):
#   CHAIN_ID=... SAFE_ADDRESS=... PRIVATE_KEY=... DEPLOYMENT_BYTECODE=... \
#     bash <plugin-root>/wallet/utils/propose.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPS_DIR="${HOME}/.monskills/propose-deps"

mkdir -p "$DEPS_DIR"
cp "$SCRIPT_DIR/propose.mjs" "$DEPS_DIR/propose.mjs"
cp "$SCRIPT_DIR/package.json" "$DEPS_DIR/package.json"

if [ ! -d "$DEPS_DIR/node_modules" ]; then
  echo "📦 Installing propose.mjs dependencies (one-time, cached in $DEPS_DIR)..."
  (cd "$DEPS_DIR" && npm install --silent --no-audit --no-fund --loglevel=error)
fi

exec node "$DEPS_DIR/propose.mjs" "$@"
