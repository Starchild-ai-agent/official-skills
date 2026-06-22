# Tickers

## List Tickers by Pairs

| Name | Required | Description |
|------|:--------:|-------------|
| `markets` | ✓ | List of trading pairs to query. |

```sh
upbit tickers list-by-trading-pairs \
  --markets "KRW-BTC,KRW-ETH"
```

---

## List Tickers by Market

| Name | Required | Description |
|------|:--------:|-------------|
| `quote_currencies` | ✓ | List of quote currencies to query. |

```sh
upbit tickers list-by-quote-currencies \
  --quote-currencies "KRW,BTC,USDT"
```

---
