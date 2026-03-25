---
name: debank
version: 1.0.0
description: DeBank blockchain data API - user portfolios, token balances, transaction history, and DeFi protocol positions
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
      env:
        - DEBANK_API_KEY

user-invocable: false
disable-model-invocation: false
---

# DeBank

DeBank provides comprehensive blockchain data including wallet portfolios, token balances, transaction history, DeFi protocol positions, NFTs, and transaction simulation.

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
