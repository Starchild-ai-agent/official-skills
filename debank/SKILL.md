---
name: debank
version: 1.0.0
description: DeBank blockchain data API - user portfolios, token balances, transaction history, DeFi protocol positions, NFTs, and tx simulation
tools:
  - db_chain_list
  - db_chain
  - db_token
  - db_token_history_price
  - db_token_list_by_ids
  - db_gas_market
  - db_user_total_balance
  - db_user_token_list
  - db_user_all_token_list
  - db_user_history_list
  - db_user_all_history_list
  - db_user_simple_protocol_list
  - db_user_all_simple_protocol_list
  - db_user_complex_protocol_list
  - db_user_all_complex_protocol_list
  - db_user_complex_app_list
  - db_user_nft_list
  - db_user_all_nft_list
  - db_user_chain_balance
  - db_user_token
  - db_user_protocol
  - db_user_used_chain_list
  - db_user_token_authorized_list
  - db_user_nft_authorized_list
  - db_user_chain_net_curve
  - db_user_total_net_curve
  - db_protocol
  - db_protocol_list
  - db_protocol_all_list
  - db_app_protocol_list
  - db_pool
  - db_token_top_holders
  - db_pre_exec_tx
  - db_explain_tx

metadata:
  starchild:
    emoji: "🏦"
    skillKey: debank
    requires:
      env: [DEBANK_API_KEY]

user-invocable: false
disable-model-invocation: false
---

# DeBank

33 tools for wallet portfolios, token data, DeFi positions, NFTs, tx simulation across all EVM chains.

## Tool Categories

### User Portfolio
| Tool | Purpose |
|------|---------|
| `db_user_total_balance(user_addr)` | Total balance across all chains |
| `db_user_all_token_list(user_addr)` | All token holdings |
| `db_user_token_list(user_addr, chain_id)` | Tokens on specific chain |
| `db_user_all_nft_list(user_addr)` | All NFTs |
| `db_user_chain_balance(user_addr, chain_id)` | Balance on one chain |
| `db_user_used_chain_list(user_addr)` | Which chains has this wallet used |

### Transaction History
| Tool | Purpose |
|------|---------|
| `db_user_history_list(user_addr, chain_id)` | Tx history on one chain |
| `db_user_all_history_list(user_addr)` | Tx history across all chains |

### DeFi Positions
| Tool | Purpose |
|------|---------|
| `db_user_simple_protocol_list(user_addr, chain_id)` | Simple protocol balances |
| `db_user_complex_protocol_list(user_addr, chain_id)` | Detailed DeFi positions |
| `db_user_all_simple_protocol_list(user_addr)` | All chains simple |
| `db_user_all_complex_protocol_list(user_addr)` | All chains detailed |

### Token & Protocol Data
| Tool | Purpose |
|------|---------|
| `db_token(chain_id, token_id)` | Token details |
| `db_token_history_price(chain_id, token_id, start_time, end_time)` | Historical price |
| `db_token_top_holders(chain_id, token_id)` | Top 100 holders |
| `db_protocol(protocol_id)` | Protocol details |
| `db_protocol_list(chain_id)` | Protocols on a chain |

### Tx Simulation
| Tool | Purpose |
|------|---------|
| `db_pre_exec_tx(user_addr, chain_id, tx)` | Pre-execute transaction |
| `db_explain_tx(user_addr, chain_id, tx)` | Explain transaction |

### Chain & Gas
`db_chain_list()` | `db_chain(chain_id)` | `db_gas_market(chain_id)`

### Authorizations
`db_user_token_authorized_list(user_addr, chain_id)` | `db_user_nft_authorized_list(user_addr, chain_id)`

### Analytics
`db_user_chain_net_curve(user_addr, chain_id)` | `db_user_total_net_curve(user_addr)`

## Chain IDs
`eth` Ethereum | `bsc` BSC | `polygon` Polygon | `arbitrum` Arbitrum | `optimism` Optimism | `avax` Avalanche | `base` Base | `ftm` Fantom — use `db_chain_list()` for full list.

## Notes
- Addresses: `0x...` format (40 hex chars with prefix)
- Different endpoints have different unit costs
- `_all_` variants scan all chains (more expensive but comprehensive)
