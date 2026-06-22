# Travel Rule

## List Travel Rule Supporting VASPs
Auth required

```sh
upbit travel-rule list-vasps
```

---

## Verify Travel Rule by Deposit UUID
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `deposit_uuid` | ✓ | Unique identifier (UUID) for the deposit to verify. |
| `vasp_uuid` | ✓ | Unique identifier (UUID) of the counterparty exchange from which the asset was withdrawn. |

```sh
upbit travel-rule verify-deposit-by-uuid \
  --deposit-uuid "5b871d34-fe38-4025-8f5c-9b22028f85d3" \
  --vasp-uuid "8d4fe968-82b2-42e5-822f-3840a245f802"
```

---

## Verify Travel Rule by Deposit TxID
Auth required

| Name | Required | Description |
|------|:--------:|-------------|
| `vasp_uuid` | ✓ | Unique identifier (UUID) of the counterparty exchange from which the asset was withdrawn. |
| `txid` | ✓ | Transaction ID of the deposit to be verified. |
| `currency` | ✓ | Currency code to be queried. |
| `net_type` | ✓ | Blockchain network identifier for deposit/withdrawal of digital assets. |

```sh
upbit travel-rule verify-deposit-by-txid \
  --vasp-uuid "8d4fe968-82b2-42e5-822f-3840a245f802" \
  --txid "5b871d34-fe38-4025-8f5c-9b22028f85d3" \
  --currency "ETH" \
  --net-type "ETH"
```

---
