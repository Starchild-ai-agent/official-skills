---
name: deep-research
description: Evidence-grounded deep research pipeline — plan, gather with an append-only evidence ledger, synthesize citing only ledger eids, then machine-validate every claim (unknown citations and unsupported numbers are deleted, not flagged). Use for /research requests or any question needing a trustworthy sourced report.
version: 0.1.0
---

# Deep Research (P1: single-pass, evidence-grounded)

Solves three failure modes: hallucination (evidence ledger + hard validation), staleness
(dual timestamps + mandatory Timeline), peak-not-held (P3, not in this phase).

## Run layout
`output/research/<run_id>/` — run_id = `YYYYMMDD-<slug>`. Contains:
`plan.json`, `evidence.jsonl`, `draft.md`, `report.md`, `audit.json`.

## Pipeline (execute in order)

### 1. PLAN
Decompose the question into 3–6 sub-questions. Write `plan.json`:
`{"question": ..., "subqs": [...], "depth": "quick|standard|deep", "budget_usd": 0.10|0.50|2.00}`.
Depth defaults: quick=1 search round/subq, standard=2, deep=4.

### 2. GATHER
For each sub-question: `web_search` → pick top sources → `web_fetch` the promising ones.
**Every fact you may cite MUST be deposited into the ledger immediately:**

```bash
python3 skills/deep-research/scripts/ledger.py add output/research/<run_id> \
  --url "<url>" --title "<title>" \
  --quote "<verbatim excerpt ≤1000 chars containing the fact>" \
  --published-at 2026-07-28 --tool web_fetch --trust primary|secondary|social
```

Rules:
- `--quote` must be VERBATIM from the source (validation numeric-matches against it).
- `--published-at`: real publication date if visible; omit if unknown (auto-marked undated, trust capped).
- Live market numbers: use data skills (coingecko/twelvedata), deposit the tool output as quote, `--tool coingecko`.
- Twitter/X: use the twitter skill, `--trust social`.
- The script prints the assigned `eid` — record which eid holds which fact.

### 3. SYNTH — write `draft.md`
- Every factual sentence carries its citation(s): `... [E003]` or `[E003][E007]`. One claim per line/bullet.
- Cite ONLY eids returned by the ledger. Numbers must be copied exactly from quotes.
- MUST include a `## Timeline` section: all dated facts sorted by published_at, format `- 2026-07-25 — fact [E001]`.
- MUST include `## 局限` (limitations): undated sources, paywalled/unverified items, coverage gaps.
- Uncited analysis/opinion lines are allowed but must be framed as inference ("推断：..."), never as sourced fact.

### 4. VALIDATE (mandatory, never skip)
```bash
python3 skills/deep-research/scripts/ledger.py validate output/research/<run_id> \
  --draft output/research/<run_id>/draft.md [--nli]
```
- Removes claims with unknown eids or numbers absent from cited quotes; writes `report.md` + `audit.json`.
- `--nli` adds a cheap-model semantic support check (degrades gracefully if proxy unavailable).
- If claims were removed: re-gather evidence for the important ones and re-run SYNTH+VALIDATE once, or leave them in the audit appendix. Never hand the user `draft.md` — only the validated `report.md`.

### 5. DELIVER
Give the user `output/research/<run_id>/report.md` (full path), a 5-line summary,
and the kept/removed claim counts from validation.

## Model routing
PLAN/SYNTH on the strong leg, VALIDATE nli on cheap (default minimax-m3, override via `RESEARCH_NLI_MODEL`).
When spawning as a background run: `sessions_spawn` with `announce_mode=followup` and a cost note to the user.

## Gotchas
- `ledger.py validate` deletes DRAFT LINES — keep one claim per line or collateral text gets dropped.
- Quotes with reformatted numbers ("1,234" vs "1234") are normalized, but "%" vs "pp" is not — quote verbatim.
- Paywalled sources: cite but mark trust=secondary and list under 局限 as unverified-paywall.
