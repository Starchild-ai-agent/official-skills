# Trades

## Recent Trades History

| Name | Required | Description |
|------|:--------:|-------------|
| `market` | ✓ | Trading pair code to query. |
| `to` |  | End time within the query date range (UTC). |
| `count` |  | Number of trade records to retrieve. |
| `cursor` |  | Cursor for pagination. |
| `days_ago` |  | Day offset between the query date and the request date. |

```sh
upbit trades list \
  --market "KRW-BTC"
```

---
