#!/bin/bash
# x402 skill dependencies (idempotent). Referenced by SKILL.md; a fresh
# machine must run this once before client.py / gateway / facilitator work.
pip install --quiet 'x402>=2.10' httpx nest-asyncio eth-account web3 2>/dev/null || \
  pip install 'x402>=2.10' httpx nest-asyncio eth-account web3
