# Deposits

## Get Available Deposit Information
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `currency` | ✓ | Currency code to query deposit availability for. |
| `net_type` | ✓ | Blockchain network identifier for digital asset deposit. |

```sh
upbit deposits retrieve-chance \
  --currency "BTC" \
  --net-type "BTC"
```

---

## Create Deposit Address
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `currency` | ✓ | Currency code for which to create a deposit address. |
| `net_type` | ✓ | Network type. |

```sh
upbit deposits create-coin-address \
  --currency "BTC" \
  --net-type "BTC"
```

---

## Get Deposit Address
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `currency` | ✓ | Currency code to query. |
| `net_type` | ✓ | Blockchain network identifier. |

```sh
upbit deposits retrieve-coin-address \
  --currency "BTC" \
  --net-type "BTC"
```

---

## List Deposit Addresses
Auth required

```sh
upbit deposits list-coin-addresses
```

---

## Deposit KRW
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `amount` | ✓ | KRW amount to deposit. |
| `two_factor_type` | ✓ | Two-factor authentication method for KRW transactions. — `kakao`: Kakao authentication, `naver`: Naver authentication, `hana`: Hana certificate authentication |

```sh
upbit deposits deposit-krw \
  --amount "10000" \
  --two-factor-type "naver"
```

---

## List Deposits
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `currency` |  | Currency code filter. |
| `state` |  | Deposit state filter. — `PROCESSING`: Processing, `ACCEPTED`: Completed, `CANCELLED`: Cancelled, `REJECTED`: Rejected, `TRAVEL_RULE_SUSPECTED`: Pending Travel Rule verification, `REFUNDING`: Refund in progress, `REFUNDED`: Refunded |
| `uuids` |  | List of UUIDs to query. |
| `txids` |  | List of transaction IDs to query. |
| `limit` |  | Number of results per request (default: 100, max: 100). |
| `page` |  | Page number for pagination. Default is 1. |
| `order_by` |  | Sort order. "desc" (newest first) or "asc" (oldest first). Default is "desc". |
| `from` |  | Cursor for pagination. |
| `to` |  | Cursor for pagination. |

```sh
upbit deposits list \
  --currency "KRW"
```

---

## Get Deposit
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `currency` |  | Currency code filter. |
| `uuid` |  | UUID of the deposit to query. |
| `txid` |  | Transaction ID of the deposit to query. |

```sh
upbit deposits retrieve \
  --uuid "94332e99-3a87-4a35-ad98-28b0c969f830"
```

---
