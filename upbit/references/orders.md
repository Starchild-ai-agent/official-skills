# Orders

## Get Available Order Info
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `market` | ✓ | Trading pair to query. |

```sh
upbit orders retrieve-chance \
  --market "KRW-BTC"
```

---

## Create Order
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `market` | ✓ | Target trading pair for the order. |
| `side` | ✓ | Order direction (ask=sell, bid=buy). |
| `volume` |  | Order volume. |
| `price` |  | Order price or total amount. |
| `ord_type` | ✓ | Order type. — `limit`: Limit order, `price`: Market buy order (by total price), `market`: Market sell order (by volume), `best`: Best available price order |
| `identifier` |  | Client-assigned order identifier. |
| `time_in_force` |  | Time in force condition. — `fok`: Fill or Kill, `ioc`: Immediate or Cancel, `post_only`: Post only (maker only) |
| `smp_type` |  | Self-Match Prevention (SMP) mode. — `cancel_maker`: Cancel maker order, `cancel_taker`: Cancel taker order, `reduce`: Reduce order quantity |

```sh
upbit orders create \
  --market "KRW-BTC" \
  --side "bid" \
  --volume "1" \
  --price "14000000" \
  --ord-type "limit"
```

---

## Test Order Creation
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `market` | ✓ | Target trading pair for the order. |
| `side` | ✓ | Order direction (ask=sell, bid=buy). |
| `volume` |  | Order volume. |
| `price` |  | Order price or total amount. |
| `ord_type` | ✓ | Order type. — `limit`: Limit order, `price`: Market buy order (by total price), `market`: Market sell order (by volume), `best`: Best available price order |
| `identifier` |  | Client-assigned order identifier. |
| `time_in_force` |  | Time in force condition. — `fok`: Fill or Kill, `ioc`: Immediate or Cancel, `post_only`: Post only (maker only) |
| `smp_type` |  | Self-Match Prevention (SMP) mode. — `cancel_maker`: Cancel maker order, `cancel_taker`: Cancel taker order, `reduce`: Reduce order quantity |

```sh
upbit orders test-create \
  --market "KRW-BTC" \
  --side "bid" \
  --volume "1" \
  --price "14000000" \
  --ord-type "limit"
```

---

## List Closed Orders
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `market` |  | Trading pair to filter by. |
| `state` |  | Order state filter. Market buy orders can result in either `cancel` or `done`. |
| `states` |  | Order state filter (array form). "done" or "cancel". Default returns all states. |
| `start_time` |  | Start time of the query range. Max range is 7 days. |
| `end_time` |  | End time of the query range. Max range is 7 days. |
| `limit` |  | Number of results per request (default: 100, max: 1,000). |
| `order_by` |  | Sort order. "desc" (newest first) or "asc" (oldest first). Default is "desc". |

```sh
upbit orders list-closed \
  --market "KRW-BTC" \
  --state "done" \
  --state "cancel"
```

---

## Cancel and New Order
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `prev_order_uuid` |  | UUID of the order to cancel. |
| `prev_order_identifier` |  | Client-assigned identifier of the order to cancel. |
| `new_ord_type` | ✓ | Order type for the new order. — `limit`: Limit order, `price`: Market buy order (by total price), `market`: Market sell order (by volume), `best`: Best available price order |
| `new_volume` |  | Volume for the new order. |
| `new_price` |  | Price or total amount for the new order. |
| `new_identifier` |  | Client-assigned identifier for the new order. |
| `new_time_in_force` |  | Time in force condition for the new order. — `fok`: Fill or Kill, `ioc`: Immediate or Cancel, `post_only`: Post only (maker only) |
| `new_smp_type` |  | SMP mode for the new order. — `cancel_maker`: Cancel maker order, `cancel_taker`: Cancel taker order, `reduce`: Reduce order quantity |

```sh
upbit orders cancel-and-new \
  --prev-order-uuid "ad217e24-ed02-469c-9b30-c08dbbda6908" \
  --new-ord-type "limit" \
  --new-price "100000000"
```

---

## Get Order
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `uuid` |  | UUID of the order to query. |
| `identifier` |  | Client-assigned identifier of the order to query. |

```sh
upbit orders retrieve \
  --uuid "9ca023a5-851b-4fec-9f0a-48cd83c2eaae"
```

---

## Cancel Order
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `uuid` |  | UUID of the order to cancel. |
| `identifier` |  | Client-assigned identifier of the order to cancel. |

```sh
upbit orders cancel \
  --uuid "cdd92199-2897-4e14-9448-f923320408ad"
```

---

## List Orders by IDs
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `market` |  | Trading pair to filter by. |
| `uuids` |  | List of UUIDs of orders to query. Maximum 100 orders. |
| `identifiers` |  | List of client-assigned identifiers of orders to query. Maximum 100 orders. |
| `order_by` |  | Sort order. "desc" (newest first) or "asc" (oldest first). Default is "desc". |

```sh
upbit orders list-by-uuids \
  --uuid "5d303952-8be9-41e6-915b-121a90026248" \
  --uuid "3944c2c1-bd8c-441a-aa25-2370d08217a9" \
  --uuid "5b95451b-971e-4e76-8f61-5ff441f078d5" \
  --uuid "3b67e543-8ad3-48d0-8451-0dad315cae73"
```

---

## Cancel Orders by IDs
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `uuids` |  | List of UUIDs of orders to cancel. Maximum 20 orders. |
| `identifiers` |  | List of client-assigned identifiers of orders to cancel. Maximum 20 orders. |

```sh
upbit orders cancel-by-uuids \
  --uuid "bbbb8e07-1689-4769-af3e-a117016623f8" \
  --uuid "4312ba49-5f1a-4a01-9f3b-2d2bce17267e" \
  --uuid "bdb49a54-de36-4eb4-a963-9c8d4337a9da"
```

---

## List Open Orders
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `market` |  | Trading pair to filter by. |
| `state` |  | Order state filter. "wait" (pending) or "watch" (reservation). Default is "wait". |
| `states` |  | Order state filter (array form). "wait" or "watch". Default is ["wait"]. |
| `page` |  | Page number for pagination. Default is 1. |
| `limit` |  | Number of results per request (default: 100, max: 100). |
| `order_by` |  | Sort order. "desc" (newest first) or "asc" (oldest first). Default is "desc". |

```sh
upbit orders list-open \
  --market "KRW-BTC" \
  --state "wait" \
  --state "watch"
```

---

## Batch Cancel Orders
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `quote_currencies` |  | Quote currency filter (KRW, BTC, USDT). Cancels all open orders in markets with the specified quote currency. |
| `cancel_side` |  | Side filter. "all" (both), "ask" (sell only), "bid" (buy only). |
| `count` |  | Maximum number of orders to cancel. Max 300, default 20. |
| `order_by` |  | Sort order for determining which orders to cancel. "desc" (newest first) or "asc" (oldest first). Default is "desc". |
| `pairs` |  | Trading pair filter. Cancels open orders only for the specified pairs. Up to 20 pairs, comma-separated. |
| `excluded_pairs` |  | Trading pair exclusion filter. Cancels all open orders except those for the specified pairs. Up to 20 pairs, comma-separated. |

```sh
upbit orders cancel-open \
  --quote-currencies "KRW,BTC" \
  --cancel-side "all" \
  --excluded-pairs "KRW-ETH,BTC-XRP"
```

---
