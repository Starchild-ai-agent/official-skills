---
name: mantle-readonly-debugger
description: Use when Mantle read-path requests fail, quotes revert, balances disagree, or RPC behavior is inconsistent and needs structured root-cause triage.
---

# Mantle Readonly Debugger

## Overview

Run deterministic troubleshooting for pre-execution failures and provide the smallest next action to restore reliable read-path behavior.

## Workflow

1. Capture failure context:
   - method/tool name
   - endpoint
   - parameters
   - timestamp (UTC)
   - full error text/code
2. Classify error with `references/error-signature-map.md`:
   - RPC transport/connectivity
   - onchain revert or call exception
   - quote/liquidity failure
   - balance/nonce inconsistency
   - other/unclassified (use when the error does not match any category above; describe the nature of the error in `issue_type`)
3. Run targeted checks from `references/troubleshooting-playbook.md`.
4. Return root-cause hypothesis with confidence and immediate next step.
5. If unresolved, return a bounded escalation checklist.

## Guardrails

- Do not claim definitive root cause without evidence.
- Preserve original error strings verbatim in the `raw_error` field — copy-paste the exact text, do not paraphrase or summarize.
- Keep remediation read-only unless user explicitly requests execution.
- Prefer smallest reversible diagnostic step first.

## Output Format

**You MUST respond using EXACTLY this template. Do not add prose before or after. Fill in every field. If a value is unknown, write "unknown".**

```text
Mantle Read-Only Debug Report
- issue_type:
- observed_at_utc:
- endpoint:
- method_or_tool:
- raw_error:

Diagnosis
- likely_causes:
- confidence: low | medium | high
- evidence:

Next Actions
- step_1:
- step_2:
- step_3:
- escalation_if_unresolved:
```

## References

- `references/error-signature-map.md`
- `references/troubleshooting-playbook.md`
