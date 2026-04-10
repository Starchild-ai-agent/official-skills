---
name: mantle
version: 1.0.0
description: Mantle Network skills suite - 9 specialized skills for onboarding, registry safety, analytics, DeFi planning, and smart contract lifecycle on Mantle
metadata:
  starchild:
    emoji: "🔷"
    skillKey: mantle
    requires:
      bins:
        - npx
        - node
user-invocable: true
disable-model-invocation: false
---

# Skills

`skills/` contains one directory per Mantle-focused agent skill. Each skill combines a primary workflow in `SKILL.md` with local references or assets so the runtime can ground answers in repository data instead of relying only on model memory.

## Directory Convention

- `skills/<skill-name>/SKILL.md`: trigger conditions, workflow, guardrails, and output format
- `skills/<skill-name>/agents/openai.yaml`: runtime-facing metadata
- `skills/<skill-name>/references/`: playbooks, policies, templates, and supporting notes
- `skills/<skill-name>/assets/`: machine-readable local data used by the skill

## Skill Catalog

### Onboarding and Reference

| Skill | Role |
| --- | --- |
| [`mantle-network-primer`](./mantle-network-primer/SKILL.md) | Clarifies Mantle fundamentals such as MNT gas, chain IDs, official endpoints, and inclusion vs settlement |

### Registry and Safety Gates

| Skill | Role |
| --- | --- |
| [`mantle-address-registry-navigator`](./mantle-address-registry-navigator/SKILL.md) | Resolves verified Mantle addresses and blocks unsafe address guessing |
| [`mantle-risk-evaluator`](./mantle-risk-evaluator/SKILL.md) | Returns `pass`, `warn`, or `block` verdicts for state-changing intents |
| [`mantle-portfolio-analyst`](./mantle-portfolio-analyst/SKILL.md) | Inspects balances, allowances, and spender exposure with read-only data |

### Analytics and Diagnostics

| Skill | Role |
| --- | --- |
| [`mantle-data-indexer`](./mantle-data-indexer/SKILL.md) | Retrieves historical wallet activity and time-windowed Mantle analytics |
| [`mantle-readonly-debugger`](./mantle-readonly-debugger/SKILL.md) | Triages RPC failures, quote reverts, and ambiguous read-path behavior |
| [`mantle-tx-simulator`](./mantle-tx-simulator/SKILL.md) | Prepares external simulation handoffs and WYSIWYS summaries |

### DeFi Planning

| Skill | Role |
| --- | --- |
| [`mantle-defi-operator`](./mantle-defi-operator/SKILL.md) | Orchestrates venue discovery, comparison, and execution-ready DeFi planning |

### Smart Contract Lifecycle

| Skill | Role |
| --- | --- |
| [`mantle-smart-contract-developer`](./mantle-smart-contract-developer/SKILL.md) | Frames Mantle-specific contract design and deployment-readiness decisions |
| [`mantle-smart-contract-deployer`](./mantle-smart-contract-deployer/SKILL.md) | Prepares deployment, verification, and external signer handoff steps |

## How to Pick a Skill

- Start with the narrowest skill that matches the task.
- Use `mantle-network-primer` when Mantle-specific assumptions need to be checked before execution work.
- Use `mantle-defi-operator` only when the request genuinely spans discovery, address verification, risk evidence, and execution planning.
- Split contract work between `mantle-smart-contract-developer` and `mantle-smart-contract-deployer` rather than treating deployment as part of design.
