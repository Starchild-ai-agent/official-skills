---
name: mantle-smart-contract-deployer
description: Use when a finalized Mantle contract build needs deployment-readiness checks, external signer handoff, receipt capture, or explorer verification.
---

# Mantle Smart Contract Deployer

## Overview

Run a safe deployment planning pipeline from finalized build inputs to explorer verification readiness. This skill starts after contract architecture and implementation are already decided; for Mantle contract design or authoring guidance, use `$mantle-smart-contract-developer`.

## Workflow

1. **Confirm environment and chain ID first — before anything else.**
   - Ask the user to confirm the target environment (`mainnet` or `testnet`).
   - Explicitly state the chain ID: Mantle mainnet = `5000`, Mantle Sepolia testnet = `5003`.
   - Do NOT proceed to any other step until the user has confirmed or you have explicitly stated and confirmed the chain ID in your response.
   - This applies to ALL workflows including verification-only requests. Even if the user only provides a contract address, you must confirm which network (mainnet chain ID 5000 or testnet chain ID 5003) before proceeding with verification.
2. Collect deployment inputs:
   - source path and contract name
   - compiler version and optimizer settings
   - constructor args (every constructor parameter must have an explicit, confirmed value — see Guardrails)
   - finalized artifacts or development brief from `$mantle-smart-contract-developer`
3. Run pre-deploy checks from `references/deployment-checklist.md`.
4. Build artifacts and bytecode fingerprint.
5. Estimate gas and deployment cost; confirm limits.
6. Produce an external execution handoff package (unsigned deployment payload, gas bounds, and signer instructions).
7. After the user/external executor submits, capture receipt metadata and persist deployment evidence.
8. Verify source on explorer using `references/verification-playbook.md`, then record verification evidence.

## Guardrails

- **Read-only agent.** This skill is read-only. You CANNOT sign, broadcast, deploy, execute, submit, or send any transaction. Use `mantle-cli` commands for on-chain reads; do NOT enable or connect to the MCP server. Never use phrases like "I deployed," "I verified," "I submitted," or "I broadcast." Instead say "the deployment must be executed externally" or "verification should be submitted by the user/signer." All on-chain actions happen outside this agent.
- **No contract authoring.** This skill does not design or write contracts. If the user asks you to write, create, design, or author Solidity code, immediately redirect them to `$mantle-smart-contract-developer` and OpenZeppelin MCP. Do NOT write any contract code, not even a skeleton or example.
- If the user asks for execution, provide a wallet/signer handoff checklist and state execution must happen externally.
- Never deploy with unresolved constructor argument ambiguity. If any constructor parameter is missing, unknown, or the user expresses uncertainty, STOP and ask for explicit values before proceeding.
- Never skip chain ID or environment confirmation.
- Never claim verification success without explorer response evidence.
- If compile hash changes after quote/approval, restart pre-deploy checks.

## Output Format

**Always produce the Deployment Report below**, even for partial workflows. Fill in known fields; mark unknown fields as `pending` or `not yet available`. If the workflow is blocked (e.g., missing constructor args, awaiting environment confirmation), still emit the report skeleton with a `BLOCKED:` note explaining what is needed before proceeding.

For verification-only requests, fill in the Verification section and mark Deployment fields as `previously completed externally`.

Example when blocked: if constructor args are missing, emit the report with `BLOCKED: awaiting constructor argument values for [param1, param2]` in the Deployment section and ask the user to provide the missing values.

```text
Mantle Deployment Report
- contract_name:
- environment:
- chain_id:
- compiler_profile:
- bytecode_hash:

Deployment
- execution_mode: external_wallet_or_signer
- tx_hash: (from external execution evidence)
- deployed_address: (from external execution evidence)
- block_number: (from external execution evidence)
- gas_used: (from external execution evidence)
- deployment_fee_native: (from external execution evidence)

Verification
- explorer:
- status: verified | pending | failed
- verification_id_or_link:
- failure_reason:

Artifacts
- constructor_args_encoded:
- abi_path:
- metadata_path:
```

## References

- `references/deployment-checklist.md`
- `references/verification-playbook.md`
