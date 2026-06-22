# Candles

## List Second Candles

| Name | Required | Description |
|------|:--------:|-------------|
| `market` | ✓ | Trading pair code to query. |
| `to` |  | End time of the query range. |
| `count` |  | Number of candles to retrieve. |

```sh
upbit candles list-seconds \
  --market "KRW-BTC"
```

---

## List Minute Candles

| Name | Required | Description |
|------|:--------:|-------------|
| `unit` | ✓ | Candle unit in minutes. — `1`, `3`, `5`, `10`, `15`, `30`, `60`, `240` |
| `market` | ✓ | Trading pair code to query. |
| `to` |  | End time of the query range. |
| `count` |  | Number of candles to retrieve. |

```sh
upbit candles list-minutes \
  --unit 15 \
  --market "KRW-BTC"
```

---

## List Day Candles

| Name | Required | Description |
|------|:--------:|-------------|
| `market` | ✓ | Trading pair code to query. |
| `to` |  | End time of the query range. |
| `count` |  | Number of candles to retrieve. |
| `converting_price_unit` |  | Currency to convert the closing price into. |

```sh
upbit candles list-days \
  --market "KRW-BTC"
```

---

## List Week Candles

| Name | Required | Description |
|------|:--------:|-------------|
| `market` | ✓ | Trading pair code to query. |
| `to` |  | End time of the query range. |
| `count` |  | Number of candles to retrieve. Up to 200, default: 1. |

```sh
upbit candles list-weeks \
  --market "KRW-BTC"
```

---

## List Month Candles

| Name | Required | Description |
|------|:--------:|-------------|
| `market` | ✓ | Trading pair code to query. |
| `to` |  | End time of the query range. If not specified, the most recent candles are returned. |
| `count` |  | Number of candles to retrieve. Up to 200, default: 1. |

```sh
upbit candles list-months \
  --market "KRW-BTC"
```

---

## List Year Candles

| Name | Required | Description |
|------|:--------:|-------------|
| `market` | ✓ | Trading pair code to query. |
| `to` |  | End time of the query range. ISO 8601 format. |
| `count` |  | Number of candles to retrieve. Up to 200, default: 1. |

```sh
upbit candles list-years \
  --market "KRW-BTC"
```

---
