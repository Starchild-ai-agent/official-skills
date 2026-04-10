---
name: mantle-data-indexer
description: Use when a Mantle task needs historical wallet activity, time-windowed metrics, event backfills, or protocol analytics that raw RPC cannot answer efficiently.
---

# Mantle Data Indexer

## Overview

Use GraphQL or SQL indexers to answer historical questions on Mantle with reproducible queries, clear time boundaries, and source attribution.

## Workflow

1. Normalize request:
   - objective (for example volume, swaps, user history)
   - entities (wallet, pool, token, protocol)
   - time range (absolute UTC start/end). If the user provides relative times like "past 7 days" or "last month", convert them to absolute UTC timestamps (e.g., "2026-03-18T00:00:00Z to 2026-03-25T00:00:00Z") and state the conversion explicitly.
2. Resolve endpoint availability:
   - `mantle-cli indexer subgraph --endpoint <url> --query <graphql> --json` requires an endpoint URL + query.
   - `mantle-cli indexer sql --endpoint <url> --query <sql> --json` requires an endpoint URL + query.
   - If endpoint config is missing, STOP and use the Blocked Output Format below. Do NOT proceed to step 3.
   - WRONG: making up a URL like `https://api.thegraph.com/subgraphs/name/mantle-...` or `https://indexer.mantle.xyz/...`.
   - RIGHT: responding with the Blocked Output Format and asking the user to provide the endpoint.
   - In E2E `endpoint-configured` scenarios, skip when `E2E_SUBGRAPH_ENDPOINT` or `E2E_SQL_ENDPOINT` is unset.
3. Select source by availability and latency target:
   - GraphQL indexer -> `mantle-cli indexer subgraph --endpoint <url> --query <graphql> --json`
   - SQL indexer -> `mantle-cli indexer sql --endpoint <url> --query <sql> --json`
4. Build query from `references/query-templates.md`.
5. Execute with pagination and deterministic ordering.
6. Normalize units and decimals before aggregation.
7. Produce output with query provenance, tool warnings, and caveats.

## Guardrails

- Confirm chain scope is Mantle before querying.
- Use absolute timestamps and include timezone (`UTC`).
- Do not invent endpoint URLs. If missing, report blocked input and request an endpoint.
- Keep SQL read-only; avoid mutation statements.
- Do not merge datasets with mismatched granularity without labeling.
- Distinguish `no data` from `query failure`.
- Propagate tool warnings (for example `hasNextPage=true` or SQL truncation).
- If indexer lag is known or suspected, disclose it.

## Output Format

```text
Mantle Historical Data Report
- objective:
- source_type: graphql | sql
- source_endpoint:
- queried_at_utc:
- time_range_utc:
- entity_scope:

Query Summary
- dataset_or_subgraph:
- filters_applied:
- pagination_strategy:
- records_scanned:

Results
- metric_1:
- metric_2:
- sample_rows:

Quality Notes
- indexer_lag_status:
- tool_warnings:
- assumptions:
- caveats:
- confidence:
```

## Blocked Output Format

When the workflow cannot proceed (for example, no endpoint URL was provided), you MUST still use a structured output. NEVER fabricate an endpoint URL. Instead, use this format:

```text
Mantle Historical Data Report -- BLOCKED
- objective:
- status: blocked
- blocked_reason: [explain exactly what is missing, e.g. "No GraphQL or SQL endpoint was provided"]
- action_required: [what the user must supply, e.g. "Provide a subgraph endpoint URL or SQL indexer endpoint URL"]
- time_range_utc: [convert any relative time to absolute UTC, e.g. "2026-02-23T00:00:00Z to 2026-03-25T00:00:00Z"]
- entity_scope:

Quality Notes
- tool_warnings: Endpoint missing -- cannot execute query. This is NOT a "no data" result; it is a configuration gap.
- assumptions: none
- caveats: No query was executed. Results will be available once an endpoint is provided.
- confidence: n/a
```

CRITICAL: If the user does not provide an endpoint URL and you do not have one configured, you MUST use the blocked format above. Do not guess, fabricate, or assume any endpoint URL.

## References

- `references/indexer-selection-and-quality.md`
- `references/query-templates.md`
