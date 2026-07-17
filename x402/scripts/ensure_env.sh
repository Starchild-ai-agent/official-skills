#!/bin/bash
# x402 buyer env bootstrap — ZERO-INTERACTION, safe on machines whose global
# web3 is pinned <7 (trading bots often pin 6.x; NEVER upgrade it globally).
#
# Behavior:
#   * global web3>=7 present  -> nothing to do, use global env.
#   * otherwise               -> create/reuse an isolated .venv-x402 with
#                                web3>=7 + x402 deps, WITHOUT touching the
#                                global site-packages.
#
# Hardened against common environment interference:
#   * PIP_USER=1 in env breaks `pip install` inside venvs
#     ("User site-packages are not visible in this virtualenv")
#   * PYTHONPATH / user site-packages leak the OLD web3 6.x into the venv,
#     shadowing the venv's web3 7.
#
# Prints the python interpreter to use on the LAST line of stdout.
set -euo pipefail

VENV="${X402_VENV:-/data/workspace/.venv-x402}"
NEED="7"

ver() { "$1" - <<'PY' 2>/dev/null || echo 0
import web3, sys
print(web3.__version__.split(".")[0])
PY
}

if [ "$(ver python3)" -ge "$NEED" ]; then
  echo "global web3 OK (>=7) — using system python" >&2
  echo "python3"
  exit 0
fi

echo "global web3 <7 (or missing); using isolated venv $VENV" >&2

# Neutralize env interference BEFORE any pip/python call.
unset PYTHONPATH PIP_USER PIP_TARGET PIP_PREFIX || true
export PYTHONNOUSERSITE=1

if [ ! -x "$VENV/bin/python" ]; then
  # --without-pip then bootstrap via ensurepip: immune to PIP_* env residue.
  python3 -m venv --without-pip "$VENV"
  "$VENV/bin/python" -m ensurepip --upgrade >/dev/null
fi

if [ "$(ver "$VENV/bin/python")" -lt "$NEED" ]; then
  "$VENV/bin/python" -m pip install --quiet --upgrade pip
  "$VENV/bin/python" -m pip install --quiet \
    'x402>=2.10' 'web3>=7' httpx nest-asyncio eth-account
fi

# Verify: venv python must import web3>=7 with user-site disabled.
[ "$(ver "$VENV/bin/python")" -ge "$NEED" ] || {
  echo "FATAL: venv still resolves web3 <7 — check for sitecustomize/pth leaks" >&2
  exit 1
}

echo "venv ready: web3 $("$VENV/bin/python" -c 'import web3; print(web3.__version__)')" >&2
echo "$VENV/bin/python"
