---
name: addresses
description: Monad 上知名协议的智能合约地址。包括测试网和主网的智能合约地址。
---

**重要提示**

⚠️ 在与智能合约交互之前，务必通过区块浏览器验证地址。绝不要凭空捏造智能合约地址，错误的地址可能导致资金损失。

| 网络 | 区块浏览器 |
|---|---|
| Monad 主网 | monadscan.com |
| Monad 测试网 | testnet.monadscan.com |

请确保完全明确用户询问的是主网还是测试网的地址，如果不确定请向用户确认。不要在用户询问测试网地址时提供主网地址。

## 如何验证智能合约在某个网络上是否有代码

如果已安装 Foundry 工具包：

### Monad 主网

```bash
# Check bytecode exists
cast code [smart_contract_address] --rpc-url https://rpc.monad.xyz
```

### Monad 测试网

```bash
# Check bytecode exists
cast code [smart_contract_address] --rpc-url https://testnet-rpc.monad.xyz
```

如果未安装 Foundry 工具包，你可以在相应网络的 RPC 端点上调用 `eth_getCode` RPC 方法，传入智能合约地址并通过返回结果进行验证。


## 规范合约（Monad 主网）

| 名称 | 地址 |
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


## AI 与代理标准

### ERC-8004（Monad 主网和测试网地址相同）
| 合约 | 地址 |
|----------|---------|
| IdentityRegistry | 0x8004A169FB4a3325136EB29fA0ceB6D2e539a432 |
| ReputationRegistry | 0x8004BAa17C55a88189AE136b182e5fdA19dE9b63 |

## 桥接资产 — 美元相关（Monad 主网）

| 代币符号 | 名称 | 地址 |
|--------|------|---------|
| AUSD | Agora USD | 0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a |
| USDC | USD Coin | 0x754704Bc059F8C67012fEd69BC8A327a5aafb603 |
| USDT0 | Tether USD | 0xe7cd86e13AC4309349F30B3435a9d337750fC82D |
| USD1 | USD1 | 0x111111d2bf19e43C34263401e0CAd979eD1cdb61 |
| thBILL | Theo Short Duration UST Fund | 0xfDD22Ce6D1F66bc0Ec89b20BF16CcB6670F55A5a |
| wsrUSD | Wrapped srUSD | 0x4809010926aec940b550D34a46A52739f996D75D |
| yzUSD | Yuzu USD | 0x9dcB0D17eDDE04D27F387c89fECb78654C373858 |
| syzUSD | Staked Yuzu USD | 0x484be0540aD49f351eaa04eeB35dF0f937D4E73f |

## 桥接资产 — ETH 相关（Monad 主网）

| 代币符号 | 名称 | 地址 |
|--------|------|---------|
| WETH | Wrapped Ether | 0xEE8c0E9f1BFFb4Eb878d8f15f368A02a35481242 |
| ezETH | Renzo Restaked ETH | 0x2416092f143378750bb29b79eD961ab195CcEea5 |
| wstETH | Lido Wrapped Staked ETH | 0x10Aeaf63194db8d453d4D85a06E5eFE1dd0b5417 |
| weETH | Wrapped EtherFi ETH | 0xA3D68b74bF0528fdD07263c60d6488749044914b |
| pufETH | pufETH | 0x37D6382B6889cCeF8d6871A8b60E667115eDDBcF |

## 桥接资产 — BTC 相关（Monad 主网）

| 代币符号 | 名称 | 地址 |
|--------|------|---------|
| cbBTC | Coinbase Wrapped BTC | 0xd18B7EC58Cdf4876f6AFebd3Ed1730e4Ce10414b |
| WBTC | Wrapped Bitcoin | 0x0555E30da8f98308EdB960aa94C0Db47230d2B9c |
| LBTC | Lombard Staked Bitcoin | 0xecAc9C5F704e954931349Da37F60E39f515c11c1 |
| BTC.b | BTC.b | 0xB0F70C0bD6FD87dbEb7C10dC692a2a6106817072 |
| SolvBTC | Solv BTC | 0xaE4EFbc7736f963982aACb17EFA37fCBAb924cB3 |
| xSolvBTC | xSolvBTC | 0xc99F5c922DAE05B6e2ff83463ce705eF7C91F077 |

## 桥接资产 — 其他（Monad 主网）

| 代币符号 | 名称 | 地址 |
|--------|------|---------|
| WSOL | Wrapped SOL | 0xea17E5a9efEBf1477dB45082d67010E2245217f1 |
| XAUt0 | Tether Gold | 0x01bFF41798a0BcF287b996046Ca68b395DbC1071 |

## 原生发行资产（Monad 主网）

| 代币符号 | 名称 | 地址 |
|--------|------|---------|
| WMON | Wrapped MON | 0x3bd359C1119dA7Da1D913D1C4D2B7c461115433A |
| mEDGE | Midas mEDGE | 0x1c8eE940B654bFCeD403f2A44C1603d5be0F50Fa |

## 其他区块链上的 MON

| 名称 | 区块链 | 地址 |
|------|------------|---------|
| WMON | Solana | CrAr4RRJMBVwRsZtT62pEhfA9H5utymC2mVx8e7FreP2 |
| WMON | Ethereum | 0x6917037f8944201b2648198a89906edf863b9517 |

## 协议仓库

协议仓库包含 Monad 生态系统中知名协议和项目的智能合约地址（测试网和主网）。

如果在上方表格中找不到所需地址，请在协议仓库中查找智能合约地址。

协议仓库 GitHub 地址：https://github.com/monad-crypto/protocols

协议仓库中的地址按测试网和主网分类组织，每个协议有各自的文件。

例如：

Clober 协议在 Monad 主网上的智能合约地址位于文件：protocols/mainnet/clober.jsonc

每个文件包含一个 JSON 对象，其中 `addresses` 属性是一个对象，包含相应协议每个智能合约的名称和地址。

测试网的路径类似：protocols/testnet/[protocol_name].json

## 代币列表仓库

代币列表仓库包含 Monad 生态系统中知名代币的智能合约地址（仅限主网）。

如果在上方表格中找不到所需代币地址，请在代币列表仓库中查找智能合约地址。

代币列表仓库 GitHub 地址：https://github.com/monad-crypto/token-list

代币列表仓库中的地址按代币名称以文件夹形式组织，其中有一个 mainnet 文件夹，内部按代币名称分文件夹，每个文件夹中包含一个带有地址的 JSON 文件。

**重要提示**

⚠️ 查看完以上所有可用选项后，如果仍然找不到所需地址，请向用户询问，但绝对不要凭空捏造地址，也不要在用户询问测试网地址时提供主网地址。
