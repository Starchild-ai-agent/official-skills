#!/usr/bin/env bash
# init.sh — scaffold a creator-paywall instance into a target directory.
#
# Usage:
#   bash skills/creator-paywall/scripts/init.sh <target_dir> <creator_wallet> [jwt_secret] [siwe_domain]
#
# Example:
#   bash skills/creator-paywall/scripts/init.sh output/projects/my-paywall 0xABC...123
#
# Copies the template, writes a .env, and installs dependencies.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="$SKILL_DIR/template"

TARGET="${1:?target_dir required}"
WALLET="${2:?creator_wallet (0x...) required}"
JWT="${3:-$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')}"
DOMAIN="${4:-localhost}"

if [ -e "$TARGET" ] && [ -n "$(ls -A "$TARGET" 2>/dev/null)" ]; then
  echo "⚠️  $TARGET already exists and is non-empty. Aborting to avoid overwrite." >&2
  exit 1
fi

mkdir -p "$TARGET"
cp -r "$TEMPLATE/." "$TARGET/"

cat > "$TARGET/.env" <<EOF
CREATOR_WALLET=$WALLET
JWT_SECRET=$JWT
SIWE_DOMAIN=$DOMAIN
PORT=${PORT:-3007}
EOF

echo "✓ Template copied to $TARGET"
echo "✓ Wrote .env (wallet=$WALLET, domain=$DOMAIN)"
echo "→ Installing dependencies (npm install)…"
( cd "$TARGET" && npm install --no-audit --no-fund 2>&1 | tail -3 )
echo ""
echo "Done. Start it with:  cd $TARGET && npm start"
echo "Then edit config.js to set your PLANS (chains / tokens / prices)."
