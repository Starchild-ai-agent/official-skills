---
name: addresses
description: Smart contract address for well known protocols on Monad. The addresses include testnet and mainnet smart contract addresses.
---

**CRITICAL**

⚠️ Always verify addresses using the explorer before interacting with smart contracts. Never hallucinate a smart contract address, wrong addresses can lead to loss of funds. 

| Network | Explorer |
|---|---|
| Monad Mainnet | monadscan.com |
| Monad Testnet | testnet.monadscan.com |

Make sure you have zero doubts about which network the user is asking the address for whether mainnet or testnet, if you are unsure then ask the user. Do not provide mainnet address when a testnet address was asked for.

## How to verify if a smart contract has code on a network.

If Foundry toolkit is installed.

### Monad Mainnet

```bash
# Check bytecode exists
cast code [smart_contract_address] --rpc-url https://rpc.monad.xyz
```

### Monad Testnet

```bash
# Check bytecode exists
cast code [smart_contract_address] --rpc-url https://testnet-rpc.monad.xyz
```

If Foundry toolkit is not installed you can call "eth_getCode" RPC method on the respective RPC endpoint for the network with the smart contract address and verify using the response.


## Canonical contracts (on Monad mainnet)

| Name | Address |
|------|---------|
| Wrapped MON | 0x3bd359C1119dA7Da1D913D1C4D2B7c461115433A |
| Create2Deployer | 0x13b0D85CcB8bf860b6b79AF3029fCA081AE9beF2 |
| CreateX | 0xba5Ed099633D3B313e4D5F7bdc1305d3c28ba5Ed |
| ERC-2470 Singleton Factory | 0xce0042b868300000d44a59004da54a005ffdcf9f |
| ERC-4337 EntryPoint v0.6 | 0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789 |
| ERC-4337 SenderCreator v0.6 | 0x7fc98430eAEdbb6070B35B39D798725049088348 |
| ERC-4337 EntryPoint v0.7 | 0x0000000071727De22E5E9d8BAf0edAc6f37da032 |
| ERC-4337 SenderCreator v0.7 | 0xEFC2c1444eBCC4Db75e7613d20C6a62fF67A167C |
| ERC-6492 UniversalSigValidator | 0xdAcD51A54883eb67D95FAEb2BBfdC4a9a6BD2a3B |
| Foundry Deterministic Deployer | 0x4e59b44847b379578588920ca78fbf26c0b4956c |
| Multicall3 | 0xcA11bde05977b3631167028862bE2a173976CA11 |
| MultiSend | 0x998739BFdAAdde7C933B942a68053933098f9EDa |
| MultiSendCallOnly | 0xA1dabEF33b3B82c7814B6D82A79e50F4AC44102B |
| Permit2 | 0x000000000022d473030f116ddee9f6b43ac78ba3 |
| Safe | 0x69f4D1788e39c87893C980c06EdF4b7f686e2938 |
| SafeL2 | 0xfb1bffC9d739B8D520DaF37dF666da4C687191EA |
| SafeSingletonFactory | 0x914d7Fec6aaC8cd542e72Bca78B30650d45643d7 |
| SimpleAccount | 0x68641DE71cfEa5a5d0D29712449Ee254bb1400C2 |
| Simple7702Account | 0xe6Cae83BdE06E4c305530e199D7217f42808555B |
| Sub Zero VanityMarket | 0x000000000000b361194cfe6312EE3210d53C15AA |
| Zoltu Deterministic Deployment Proxy | 0x7A0D94F55792C434d74a40883C6ed8545E406D12 |


## AI & Agent Standards

### ERC-8004 (same addresses for Monad mainnet and testnet)
| Contract | Address |
|----------|---------|
| IdentityRegistry | 0x8004A169FB4a3325136EB29fA0ceB6D2e539a432 |
| ReputationRegistry | 0x8004BAa17C55a88189AE136b182e5fdA19dE9b63 |

## Bridged Assets Dollar-related (on Monad mainnet) 

| Symbol | Name | Address |
|--------|------|---------|
| AUSD | Agora USD | 0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a |
| USDC | USD Coin | 0x754704Bc059F8C67012fEd69BC8A327a5aafb603 |
| USDT0 | Tether USD | 0xe7cd86e13AC4309349F30B3435a9d337750fC82D |
| USD1 | USD1 | 0x111111d2bf19e43C34263401e0CAd979eD1cdb61 |
| thBILL | Theo Short Duration UST Fund | 0xfDD22Ce6D1F66bc0Ec89b20BF16CcB6670F55A5a |
| wsrUSD | Wrapped srUSD | 0x4809010926aec940b550D34a46A52739f996D75D |
| yzUSD | Yuzu USD | 0x9dcB0D17eDDE04D27F387c89fECb78654C373858 |
| syzUSD | Staked Yuzu USD | 0x484be0540aD49f351eaa04eeB35dF0f937D4E73f |

## Bridged Assets ETH-related (on Monad mainnet)

| Symbol | Name | Address |
|--------|------|---------|
| WETH | Wrapped Ether | 0xEE8c0E9f1BFFb4Eb878d8f15f368A02a35481242 |
| ezETH | Renzo Restaked ETH | 0x2416092f143378750bb29b79eD961ab195CcEea5 |
| wstETH | Lido Wrapped Staked ETH | 0x10Aeaf63194db8d453d4D85a06E5eFE1dd0b5417 |
| weETH | Wrapped EtherFi ETH | 0xA3D68b74bF0528fdD07263c60d6488749044914b |
| pufETH | pufETH | 0x37D6382B6889cCeF8d6871A8b60E667115eDDBcF |

## Bridged Assets BTC-related (on Monad mainnet)

| Symbol | Name | Address |
|--------|------|---------|
| cbBTC | Coinbase Wrapped BTC | 0xd18B7EC58Cdf4876f6AFebd3Ed1730e4Ce10414b |
| WBTC | Wrapped Bitcoin | 0x0555E30da8f98308EdB960aa94C0Db47230d2B9c |
| LBTC | Lombard Staked Bitcoin | 0xecAc9C5F704e954931349Da37F60E39f515c11c1 |
| BTC.b | BTC.b | 0xB0F70C0bD6FD87dbEb7C10dC692a2a6106817072 |
| SolvBTC | Solv BTC | 0xaE4EFbc7736f963982aACb17EFA37fCBAb924cB3 |
| xSolvBTC | xSolvBTC | 0xc99F5c922DAE05B6e2ff83463ce705eF7C91F077 |

## Bridged Assets - Others (on Monad mainnet)

| Symbol | Name | Address |
|--------|------|---------|
| WSOL | Wrapped SOL | 0xea17E5a9efEBf1477dB45082d67010E2245217f1 |
| XAUt0 | Tether Gold | 0x01bFF41798a0BcF287b996046Ca68b395DbC1071 |

## Natively-Issued Assets (on Monad mainnet)

| Symbol | Name | Address |
|--------|------|---------|
| WMON | Wrapped MON | 0x3bd359C1119dA7Da1D913D1C4D2B7c461115433A |
| mEDGE | Midas mEDGE | 0x1c8eE940B654bFCeD403f2A44C1603d5be0F50Fa |

## MON on other blockchains

| Name | Blockchain | Address |
|------|------------|---------|
| WMON | Solana | CrAr4RRJMBVwRsZtT62pEhfA9H5utymC2mVx8e7FreP2 |
| WMON | Ethereum | 0x6917037f8944201b2648198a89906edf863b9517 |

## Protocols repo

The protocols repo contains smart contract address (testnet and mainnet) for well known protocols and projects in the monad ecosystem.

If you need an address that is not found from the tables above check the protocols repo for the smart contract address.

Protocol repo GitHub URL: https://github.com/monad-crypto/protocols

Addresses in protocols repo are organized by testnet and mainnet and each protocol has it's own file.

For example:

Smart contract addresses for Clober protocol on Monad mainnet is in file: protocols/mainnet/clober.jsonc

Each file has a JSON object with property "addresses" which is object with items as "name" and address of each smart contract associated with the respected protocol.

Similarly for testnet, the route is protocols/testnet/[protocol_name].json

## Token list repo

The token list repo contains smart contract address (mainnet only) for well known tokens in the monad ecosystem.

If you need an address for a token that is not found from the tables above check the token list repo for smart contract address.

Token list repo GitHub URL: https://github.com/monad-crypto/token-list

Addresses in token list repo are organized by token names in folders, there is a mainnet folder inside which there are folders with token names inside each folder is a json with the address.

**CRITICAL**

⚠️ After looking at all the available options above, if you are still not able to find the address ask the user for it but do not at all hallucinate an address and do not provide mainnet address when a testnet address was asked for.
