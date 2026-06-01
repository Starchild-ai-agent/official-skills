---
name: tooling-and-infra
description: Monad 工具和基础设施提供商支持目录。当开发者询问哪些工具、服务或基础设施提供商支持 Monad（主网或测试网），或需要查找 Monad 的 RPC 提供商、区块浏览器、预言机、跨链桥、索引器、钱包、法币入金通道、托管方案、分析工具、开发工具包或钱包基础设施提供商时，使用此技能。也适用于开发者询问"X 是否支持 Monad？"或"Monad 上有哪些 Y 类提供商？"的场景。涵盖 Monad 官方文档工具页面的所有类别。
---

# Monad 工具与基础设施

快速查询哪些工具和基础设施提供商支持 Monad 主网、测试网或两者兼有。

## 如何使用此技能

1. 如果开发者询问**特定提供商**（例如"Alchemy 支持 Monad 吗？"），请在以下参考文件中搜索该提供商名称。
2. 如果开发者询问**某个类别**（例如"哪些预言机支持 Monad 测试网？"），请阅读相关参考文件并按网络筛选。

## 类别

每个类别都有一个参考文件，包含完整的提供商列表、网络支持情况和文档链接。只需阅读与开发者问题相关的文件。

| 类别 | 参考文件 | 涵盖内容 |
|------|---------|---------|
| 分析工具 | [analytics.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/tooling-and-infra/references/analytics.zh.md) | 链上监控、投资组合追踪、DeFi 分析、仪表盘 |
| 区块浏览器 | [block-explorers.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/tooling-and-infra/references/block-explorers.zh.md) | 交易浏览器、合约验证、UserOp 浏览器 |
| 跨链 | [cross-chain.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/tooling-and-infra/references/cross-chain.zh.md) | 跨链桥、跨链桥聚合器、流动性层、AMB、链抽象 |
| 托管 | [custody.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/tooling-and-infra/references/custody.zh.md) | 机构级托管方案 |
| 索引器 | [indexers.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/tooling-and-infra/references/indexers.zh.md) | 通用数据 API 和索引框架（子图、数据管道） |
| 法币入金 | [onramps.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/tooling-and-infra/references/onramps.zh.md) | 法币转加密货币、支付网关 |
| 预言机 | [oracles.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/tooling-and-infra/references/oracles.zh.md) | 价格数据源、VRF、数据馈送 |
| RPC 提供商 | [rpc-providers.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/tooling-and-infra/references/rpc-providers.zh.md) | 与 Monad 交互的 RPC 端点 |
| 开发工具包 | [toolkits.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/tooling-and-infra/references/toolkits.zh.md) | 开发框架（Foundry、Hardhat） |
| 钱包 | [wallets.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/tooling-and-infra/references/wallets.zh.md) | 软件钱包、硬件钱包、机构钱包、多签钱包 |
| 钱包基础设施 | [wallet-infra.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/tooling-and-infra/references/wallet-infra.zh.md) | 嵌入式钱包、账户抽象、智能账户 |

## 快速查询：提供商对应类别

如果开发者提到某个提供商而你不确定它属于哪个类别，以下是常见提供商的快速对照表：

- **Alchemy** — RPC 提供商、嵌入式钱包、账户抽象
- **thirdweb** — RPC 提供商、嵌入式钱包、账户抽象、索引器（通用数据）
- **Sequence** — 嵌入式钱包、账户抽象、索引器（通用数据）
- **Quicknode** — RPC 提供商、索引器（通用数据）
- **Tenderly** — 分析工具、区块浏览器（交易分析器）
- **Goldsky** — 索引器（通用数据）、索引框架
- **Chainlink** — 预言机、跨链（CCIP）
- **Pimlico** — 账户抽象、智能账户
- **ZeroDev** — 账户抽象、智能账户
- **Biconomy** — 账户抽象、智能账户
- **Phantom** — 软件钱包、嵌入式钱包
- **MetaMask** — 软件钱包、嵌入式钱包、智能账户
- **Safepal** — 软件钱包、硬件钱包
- **Coinbase** — 法币入金、托管、嵌入式钱包

## 重要说明

- 提供商的支持状态可能会变化。如果开发者需要确认，建议他们查看提供商自己的文档或 Monad 官方文档页面。
- 某些仅标注为主网支持的提供商可能稍后会添加测试网支持（反之亦然）。
- "待定"状态（以时钟图标标记）表示提供商已宣布支持但尚未上线。
