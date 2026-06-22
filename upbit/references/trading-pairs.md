# Trading Pairs

## Market Pair Format

Upbit uses `{QUOTE}-{BASE}` order — quote currency first, base asset second.

| Market | Quote | Base | Other exchanges equivalent |
|---|---|---|---|
| `KRW-BTC` | KRW | BTC | `BTC/KRW` |
| `KRW-ETH` | KRW | ETH | `ETH/KRW` |
| `BTC-ETH` | BTC | ETH | `ETH/BTC` |
| `USDT-XRP` | USDT | XRP | `XRP/USDT` |

Quote currencies: `KRW`, `BTC`, `USDT`. Always uppercase, hyphen-delimited.

## List Trading Pairs

| Name | Required | Description |
|------|:--------:|-------------|
| `is_details` |  | Whether to include detailed information in the query. |

```sh
upbit trading-pairs list
```

---
