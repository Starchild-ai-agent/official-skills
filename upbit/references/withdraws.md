# Withdraws

## Get Available Withdrawal Information
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `currency` | ✓ | Currency code to query withdrawal availability for. |
| `net_type` | ✓ | Blockchain network identifier for digital asset withdrawal. |

```sh
upbit withdraws retrieve-chance \
  --currency "BTC" \
  --net-type "BTC"
```

---

## List Withdrawal Allowed Addresses
Auth required

```sh
upbit withdraws list-coin-addresses
```

---

## Withdraw Digital Asset
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `currency` | ✓ | Currency code of the digital asset to withdraw. |
| `net_type` | ✓ | Check the allowed withdrawal addresses API response to find the available "net_type" value for each address. |
| `amount` | ✓ | Amount of the asset to withdraw. |
| `address` | ✓ | Recipient address for digital asset withdrawal. |
| `secondary_address` |  | Secondary withdrawal address (Destination Tag, Memo, or Message). |
| `transaction_type` |  | Withdrawal transaction type. — `default`: Standard withdrawal, `internal`: Internal (instant) withdrawal |

```sh
upbit withdraws create-withdrawal \
  --currency "BTC" \
  --net-type "BTC" \
  --amount "0.01" \
  --address "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
```

---

## Cancel Withdrawal
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `uuid` | ✓ | UUID of the withdrawal to cancel. |

```sh
upbit withdraws cancel-withdrawal \
  --uuid "9f432943-54e0-40b7-825f-b6fec8b42b79"
```

---

## Withdraw KRW
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `amount` | ✓ | KRW amount to withdraw. |
| `two_factor_type` | ✓ | Two-factor authentication method for KRW transactions. — `kakao`: Kakao authentication, `naver`: Naver authentication, `hana`: Hana certificate authentication |

```sh
upbit withdraws create-krw-withdrawal \
  --amount "10000" \
  --two-factor-type "naver"
```

---

## List Withdrawals
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `currency` |  | Currency code filter. |
| `state` |  | Withdrawal state filter. — `WAITING`: Waiting, `PROCESSING`: Processing, `DONE`: Completed, `FAILED`: Failed, `CANCELLED`: Cancelled, `REJECTED`: Rejected |
| `uuids` |  | List of UUIDs to query. Maximum 100. Cannot be used together with txids. |
| `txids` |  | List of transaction IDs to query. Maximum 100. Cannot be used together with uuids. |
| `limit` |  | Number of results per request (default: 100, max: 100). |
| `page` |  | Page number for pagination. Default is 1. |
| `order_by` |  | Sort order. "desc" (newest first) or "asc" (oldest first). Default is "desc". |
| `from` |  | Cursor for pagination. |
| `to` |  | Cursor for pagination. |

```sh
upbit withdraws list \
  --currency "XRP" \
  --state "DONE"
```

---

## Get Withdrawal
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `uuid` |  | UUID of the withdrawal to query. |
| `txid` |  | Transaction ID of the withdrawal to query. |
| `currency` |  | Currency code filter. |

```sh
upbit withdraws retrieve \
  --currency "BTC"
```

---
