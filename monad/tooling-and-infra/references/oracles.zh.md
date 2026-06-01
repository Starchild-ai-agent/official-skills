# 预言机

在 Monad 上将链下信息带入链上的数据馈送。

| 提供商 | 主网 | 测试网 | 描述 | 文档 |
|--------|------|--------|------|------|
| Chainlink | Yes | Yes | 通过去中心化模型和链下报告聚合多个数据源 | [docs.chain.link](https://docs.chain.link/) |
| Chronicle | Yes | Yes | 最初在 MakerDAO 内构建，90+ 个数据馈送，Gas 成本降低 60-80% | [docs.chroniclelabs.org](https://docs.chroniclelabs.org/) |
| eOracle | Yes | Yes | 由以太坊安全模型支持的开放基础设施平台 | [docs.eo.app](https://docs.eo.app/docs) |
| Pyth Network | Yes | Yes | 第一方预言机网络，通过拉取机制提供 400ms 延迟的实时数据 | [docs.pyth.network](https://docs.pyth.network/) |
| Redstone | Yes | Yes | 专注于收益型抵押品（LST、LRT、BTCFi）的模块化预言机 | [docs.redstone.finance](https://docs.redstone.finance/) |
| Stork | Yes | Yes | 超低延迟拉取预言机，提供亚秒级市场数据 | [docs.stork.network](https://docs.stork.network/) |
| Supra | Yes | Yes | VRF 和去中心化价格馈送（推送/拉取），适用于 DEX、借贷、支付 | [docs.supra.com](https://docs.supra.com/) |
| Switchboard | Yes | Yes | 无许可协议，支持自定义预言机创建和超低延迟馈送 | [docs.switchboard.xyz](https://docs.switchboard.xyz/) |
| Gelato VRF | — | Yes | 可验证随机函数（仅测试网） | [docs.gelato.network](https://docs.gelato.network/web3-services/vrf/quick-start) |

## 合约地址

Monad 上的预言机合约地址可在 protocols 仓库中找到：
- Chainlink: [mainnet/chainlink.jsonc](https://github.com/monad-crypto/protocols/blob/main/mainnet/chainlink.jsonc)
- Pyth: [mainnet/pyth.jsonc](https://github.com/monad-crypto/protocols/blob/main/mainnet/pyth.jsonc)
- Redstone: [mainnet/redstone.jsonc](https://github.com/monad-crypto/protocols/blob/main/mainnet/redstone.jsonc)
- Stork: [mainnet/stork.jsonc](https://github.com/monad-crypto/protocols/blob/main/mainnet/stork.jsonc)
- Supra: [mainnet/supra_oracles.jsonc](https://github.com/monad-crypto/protocols/blob/main/mainnet/supra_oracles.jsonc)
- Switchboard: [mainnet/switchboard.jsonc](https://github.com/monad-crypto/protocols/blob/main/mainnet/switchboard.jsonc)
