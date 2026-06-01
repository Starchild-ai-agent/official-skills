---
name: concepts
description: 影响开发者构建应用的 Monad 架构概念 — 异步执行、并行执行、区块状态、储备余额、EIP-7702、实时数据源和执行事件。当开发者需要了解 Monad 与以太坊不同的特定行为时，请获取此技能。
---

Monad 与以太坊兼容，但其架构引入了开发者必须了解的行为差异。请仅获取与当前任务相关的参考资料。

## 按任务获取

| 我遇到的问题... | 获取 |
|----------------------|-------|
| 新充值账户无法发送交易，资金到账延迟 | [async-execution.zh.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/concepts/references/async-execution.zh.md) |
| 现有 Solidity 合约是否需要为 Monad 做修改 | [parallel-execution.zh.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/concepts/references/parallel-execution.zh.md) |
| 选择 `latest`、`safe`、`finalized` 区块标签 | [block-states.zh.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/concepts/references/block-states.zh.md) |
| 交易因余额不足回退、10 MON 下限、清空交易 | [reserve-balance.zh.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/concepts/references/reserve-balance.zh.md) |
| 智能钱包委托、EIP-7702、会话密钥、Gas 赞助 | [eip-7702.zh.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/concepts/references/eip-7702.zh.md) |
| 订阅事件、WebSocket 数据流、高吞吐量数据接入 | [realtime-data.zh.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/concepts/references/realtime-data.zh.md) |
| 区块生命周期事件、推测性数据、BLOCK_START/QC/FINALIZED | [execution-events.zh.md](https://raw.githubusercontent.com/therealharpaljadeja/monskills/main/concepts/references/execution-events.zh.md) |

## 概要

- **异步执行：** 共识与执行解耦。状态视图有 3 个区块的延迟。新充值账户需等待约 1.2 秒才能发送交易。
- **并行执行：** 乐观并发控制 — 结果与以太坊完全一致。无需修改合约。
- **区块状态：** Proposed → Voted → Finalized → Verified。分别映射到 `latest` / `safe` / `finalized`。
- **储备余额：** 每个 EOA 有 10 MON 的余额下限。低余额账户每约 1.2 秒限发送 1 笔交易。
- **EIP-7702：** EOA 可委托给合约以获得智能钱包功能。10 MON 下限适用。在委托上下文中不可使用 CREATE/CREATE2。
- **实时数据：** 3 种来源 — Geth 兼容 WS、Monad 扩展 WS、执行事件 SDK。大多数应用使用来源 1。
- **执行事件：** 共识事件追踪区块状态转换。执行事件是推测性的 EVM 追踪数据。
