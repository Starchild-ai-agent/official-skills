# Indexer Selection and Quality

Use this guide to choose index sources and communicate confidence.

## Tool mapping and endpoint availability

- GraphQL path: use `mantle-cli indexer subgraph --endpoint <url> --query <graphql> --json`.
- SQL path: use `mantle-cli indexer sql --endpoint <url> --query <sql> --json`.
- Endpoints are runtime inputs; do not fabricate URLs when missing.
- For E2E `endpoint-configured` scenarios, `E2E_SUBGRAPH_ENDPOINT` / `E2E_SQL_ENDPOINT` may be unset and those scenarios should be skipped.

## Source choice

- Choose `GraphQL` when:
  - A maintained subgraph exists.
  - You need flexible entity filtering and nested fields.
- Choose `SQL` when:
  - A warehouse/indexer table exists for the target protocol.
  - You need heavy aggregations or window functions.

## Required metadata in every answer

- `source_type` (`graphql` or `sql`)
- Endpoint or dataset name
- Time range in absolute UTC timestamps
- Query execution time (`queried_at_utc`)
- Known lag status (if available)

## Data quality checks

1. Confirm chain scope is Mantle.
2. Confirm timestamp units (`seconds` vs `milliseconds`).
3. Confirm decimal normalization assumptions.
4. Confirm pagination did not truncate data (`hasNextPage=true` warning requires follow-up pages).
5. Confirm SQL result truncation (`truncated=true`) did not hide required rows.
6. Confirm sorting/order key is deterministic.

## Lag and completeness policy

- If lag is unknown, say `lag status unknown`.
- If lag is known and non-trivial, include impact statement.
- If query fails partway, report partial result with clear boundary.
- If tool warnings are present, copy them into output and explain impact.

## Common failure modes

- Query returns zero rows because wrong network or wrong entity ID.
- Endpoint missing and agent guesses an URL instead of requesting one.
- Aggregation mismatch due to unnormalized token decimals.
- Double-counting due to overlapping pagination windows.
- Misleading totals due to mixed time granularities.
