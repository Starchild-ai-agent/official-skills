---
name: debank
version: 2.0.2
description: DeBank blockchain data API - user portfolios, token balances, transaction
  history, and DeFi protocol positions
delivery: script
metadata:
  starchild:
    emoji: 🏦
    skillKey: debank
    requires:
      env:
      - DEBANK_API_KEY
user-invocable: false
disable-model-invocation: false
---

## Script Usage

Script-mode skill — read this file, then invoke from a `bash` block:

```bash
python3 - <<'EOF'
import sys, json
sys.path.insert(0, "/data/workspace/skills/debank")
from exports import db_chain_list, db_user_total_balance, db_user_all_token_list

print(db_chain_list()[:3])
print(db_user_total_balance(user_addr="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"))
EOF
```

Read `exports.py` for the full list of `db_*` functions and exact
signatures. Common ones: `db_chain_list`, `db_chain`, `db_token`,
`db_user_total_balance`, `db_user_all_token_list`,
`db_user_all_simple_protocol_list`, `db_user_all_complex_protocol_list`,
`db_user_history_list`, `db_protocol`, `db_pre_exec_tx`, `db_explain_tx`.


# DeBank

DeBank provides comprehensive blockchain data including wallet portfolios, token balances, transaction history, DeFi protocol positions, NFTs, and transaction simulation.


## Function Reference (signatures)

All functions are in `exports.py`. `chain_id` uses DeBank's lowercase
codes: `eth`, `bsc`, `arb`, `op`, `base`, `matic`, `avax`, `sol`, `era`,
`scrl`, `linea`, `mnt`, `blast`, etc. — use `db_chain_list()` to enumerate.
`user_addr` is the wallet address (lowercase). `protocol_id` from
`db_protocol_list()`.

### Chain & Token reference
| Function | Description |
|---|---|
| `db_chain_list()` | List all supported chains. |
| `db_chain(chain_id)` | One chain's metadata. |
| `db_gas_market(chain_id)` | Gas prices for a chain. |
| `db_token(chain_id, token_id)` | Token detail. `token_id` = contract address (or `eth`, `bnb` for native). |
| `db_token_list_by_ids(chain_id, token_ids)` | Batch token lookup. |
| `db_token_history_price(chain_id, token_id, start_time, end_time=None)` | Historical prices (unix timestamps). |
| `db_token_top_holders(chain_id, token_id, start=0)` | Top holders. |

### User portfolio (single-chain)
| Function | Description |
|---|---|
| `db_user_chain_balance(user_addr, chain_id)` | USD value on one chain. |
| `db_user_token_list(user_addr, chain_id, is_all=None)` | Tokens on one chain. |
| `db_user_token(user_addr, chain_id, token_id)` | One token balance. |
| `db_user_simple_protocol_list(user_addr, chain_id)` | DeFi positions (light) on one chain. |
| `db_user_complex_protocol_list(user_addr, chain_id)` | DeFi positions (detailed) on one chain. |
| `db_user_nft_list(user_addr, chain_id, is_all=None)` | NFTs on one chain. |
| `db_user_history_list(user_addr, chain_id, start_time=None, page_count=None)` | Tx history on one chain. |
| `db_user_chain_net_curve(user_addr, chain_id)` | Net worth curve on one chain. |
| `db_user_token_authorized_list(user_addr, chain_id)` | Token approvals (security audit). |
| `db_user_nft_authorized_list(user_addr, chain_id)` | NFT approvals. |

### User portfolio (all-chain — heavier calls)
| Function | Description |
|---|---|
| `db_user_total_balance(user_addr)` | Total USD across all chains + breakdown. |
| `db_user_total_net_curve(user_addr)` | Net worth curve across all chains. |
| `db_user_used_chain_list(user_addr)` | Which chains the address has used. |
| `db_user_all_token_list(user_addr, is_all=None)` | All tokens across all chains. |
| `db_user_all_simple_protocol_list(user_addr)` | All DeFi positions (light). |
| `db_user_all_complex_protocol_list(user_addr)` | All DeFi positions (detailed). |
| `db_user_all_nft_list(user_addr, is_all=None)` | All NFTs. |
| `db_user_all_history_list(user_addr, start_time=None, page_count=None)` | All tx history. |
| `db_user_complex_app_list(user_addr)` | All app-level positions (more granular). |

### Protocol reference
| Function | Description |
|---|---|
| `db_protocol(protocol_id)` | Protocol detail. |
| `db_protocol_list(chain_id)` | Protocols on one chain. |
| `db_protocol_all_list()` | All protocols across chains. |
| `db_app_protocol_list()` | App-level protocols (groups). |
| `db_user_protocol(user_addr, protocol_id)` | User's position in one protocol. |
| `db_pool(protocol_id, chain_id, pool_id)` | One pool's detail. |

### Tx simulation
| Function | Description |
|---|---|
| `db_pre_exec_tx(user_addr, chain_id, tx)` | Simulate tx before sending. `tx` = standard tx dict. |
| `db_explain_tx(user_addr, chain_id, tx)` | Human-readable explanation of a tx. |

DeBank uses snake_case (`total_usd_value`, `chain_id`, `usd_value`).
USD values are floats. Token amounts are floats (already adjusted for
decimals — no need to divide by `10**decimals`).

## When to Use DeBank

Use DeBank for:
- **User Portfolio** - Total balance, token holdings, NFTs across all chains
- **Transaction History** - Historical transactions on single or all chains
- **DeFi Positions** - Protocol balances and complex portfolio positions
- **Token Data** - Token details, prices, and top holders
- **Transaction Simulation** - Pre-execute and explain transactions before submission
- **Authorization Tracking** - View token and NFT approvals
- **Analytics** - 24-hour net worth curves and portfolio tracking

## Common Workflows

### Get User Portfolio
```
db_user_total_balance(user_addr="0x...")  # Total balance across all chains
db_user_all_token_list(user_addr="0x...")  # All token holdings
db_user_all_nft_list(user_addr="0x...")  # All NFT collections
```

### Check Token Balances on Specific Chain
```
db_user_token_list(user_addr="0x...", chain_id="eth")  # Ethereum tokens
db_user_token_list(user_addr="0x...", chain_id="bsc")  # BSC tokens
```

### Get Transaction History
```
db_user_history_list(user_addr="0x...", chain_id="eth")  # Eth transactions
db_user_all_history_list(user_addr="0x...")  # All chain transactions
```

### Check DeFi Protocol Positions
```
db_user_simple_protocol_list(user_addr="0x...", chain_id="eth")  # Simple balances
db_user_complex_protocol_list(user_addr="0x...", chain_id="eth")  # Detailed positions
db_user_all_complex_protocol_list(user_addr="0x...")  # All chains
```

### Token Information
```
db_token(chain_id="eth", token_id="0x...")  # Token details
db_token_history_price(chain_id="eth", token_id="0x...", start_time=1234567890, end_time=1234567990)
db_token_top_holders(chain_id="eth", token_id="0x...")  # Top 100 holders
```

### Transaction Simulation
```
db_pre_exec_tx(user_addr="0x...", chain_id="eth", tx={...})  # Enhanced pre-execution
db_explain_tx(user_addr="0x...", chain_id="eth", tx={...})  # Explain transaction
```

### Protocol Data
```
db_protocol(protocol_id="uniswap")  # Protocol details
db_protocol_list(chain_id="eth")  # All protocols on chain
db_protocol_all_list()  # All protocols across chains
```

### Chain Information
```
db_chain_list()  # All supported chains
db_chain(chain_id="eth")  # Specific chain details
db_gas_market(chain_id="eth")  # Gas prices
```

## Important Notes

- **API Key**: Requires DEBANK_API_KEY environment variable (DeBank Cloud API)
- **User Address**: Most endpoints require a valid blockchain address (0x... format)
- **Chain IDs**: Use DeBank chain identifiers (eth, bsc, polygon, arbitrum, optimism, etc.)
- **Rate Limits**: Be mindful of API rate limits and unit costs
- **Unit Costs**: Different endpoints have different unit costs (see API documentation)

## Chain ID Reference

Common chain identifiers:
- eth → Ethereum Mainnet
- bsc → BNB Smart Chain
- polygon → Polygon
- arbitrum → Arbitrum One
- optimism → Optimism
- avax → Avalanche C-Chain
- ftm → Fantom
- op → Optimism
- base → Base

**Important:** Use `db_chain_list()` to get the complete list of supported chains and their identifiers.

## Address Format

All user addresses should be in Ethereum format (0x followed by 40 hexadecimal characters):
- Valid: 0x1234567890abcdef1234567890abcdef12345678
- Invalid: 1234567890abcdef1234567890abcdef12345678 (missing 0x prefix)
