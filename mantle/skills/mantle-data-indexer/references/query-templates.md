# Query Templates

Use these templates as starting points. Replace placeholders explicitly.

## Tool argument mapping (CLI)

- GraphQL template -> `mantle-cli indexer subgraph --json` with:
  - `--endpoint <url>` (required)
  - `--query <graphql>` (required)
  - `--variables <json>` (optional)
- SQL template -> `mantle-cli indexer sql --json` with:
  - `--endpoint <url>` (required)
  - `--query <sql>` (required, read-only SQL only)
  - `--params <json>` (optional)
- In E2E `endpoint-configured` scenarios, endpoint placeholders come from `E2E_SUBGRAPH_ENDPOINT` / `E2E_SQL_ENDPOINT`; if unset, those scenarios are skipped.

## GraphQL: wallet swap history (template)

```graphql
query WalletSwaps(
  $wallet: String!,
  $startTs: Int!,
  $endTs: Int!,
  $first: Int!,
  $skip: Int!
) {
  swaps(
    where: {
      trader: $wallet
      timestamp_gte: $startTs
      timestamp_lte: $endTs
    }
    orderBy: timestamp
    orderDirection: asc
    first: $first
    skip: $skip
  ) {
    id
    txHash
    timestamp
    tokenIn
    tokenOut
    amountIn
    amountOut
  }
}
```

## GraphQL: pool daily volume (template)

```graphql
query PoolDailyVolume(
  $poolId: String!,
  $startDay: Int!,
  $endDay: Int!,
  $first: Int!,
  $skip: Int!
) {
  poolDayDatas(
    where: {
      pool: $poolId
      date_gte: $startDay
      date_lte: $endDay
    }
    orderBy: date
    orderDirection: asc
    first: $first
    skip: $skip
  ) {
    date
    volumeUSD
    txCount
  }
}
```

## SQL: wallet activity rollup (template)

```sql
SELECT
  DATE_TRUNC('day', block_time) AS day_utc,
  COUNT(*) AS tx_count,
  SUM(amount_usd) AS volume_usd
FROM swaps
WHERE chain_id = 5000
  AND LOWER(wallet_address) = LOWER(:wallet)
  AND block_time >= :start_utc
  AND block_time < :end_utc
GROUP BY 1
ORDER BY 1 ASC;
```

## SQL: top pools by 24h volume (template)

```sql
SELECT
  pool_address,
  SUM(amount_usd) AS volume_24h_usd,
  COUNT(*) AS swap_count
FROM swaps
WHERE chain_id = 5000
  AND block_time >= :window_start_utc
  AND block_time < :window_end_utc
GROUP BY pool_address
ORDER BY volume_24h_usd DESC
LIMIT :limit_n;
```

## Template usage rules

- Always declare timestamp timezone as UTC in parameters and output.
- Use deterministic ordering plus pagination for large result sets.
- Keep SQL read-only; avoid INSERT/UPDATE/DELETE/DDL statements.
- State whether amounts are raw token units or USD-normalized.
- Include replaced parameter values in report appendix.
- Carry forward tool warnings (`hasNextPage=true`, `truncated`) in the final report.
