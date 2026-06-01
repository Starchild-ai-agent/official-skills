## 实时数据源

Monad 的高吞吐量（约 10,000 tps）使传统的 JSON-RPC 轮询变得不切实际。有三种实时数据源可用：

### 1. Geth 兼容 WebSocket 事件
- 标准的 `eth_subscribe`，支持 `newHeads` 和 `logs`。
- 数据在 **Proposed** 状态时发布。
- 通过第三方 RPC 提供商（Alchemy、QuickNode 等）提供。
- 最适合：从以太坊迁移且需要最小改动的应用。

### 2. Monad 扩展 WebSocket 事件
- `monadNewHeads` 和 `monadLogs` 订阅。
- 数据在 **Proposed** 状态时发布（比标准更早）。
- 包含共识进展追踪。
- 最适合：需要最低延迟且能处理推测性数据的应用。

### 3. 执行事件 SDK（C/C++/Rust）
- 交易级别的粒度，包含日志、调用帧和状态读写。
- 最快的选项 — 在内部驱动其他两种来源。
- 需要在与 Monad 节点相同的主机上运行自定义程序。
- 最适合：索引器、分析、MEV 和高性能基础设施。

**如何选择：**
- 大多数应用开发者应通过 RPC 提供商使用**来源 1**（Geth 兼容）。
- 如果需要更早的数据且了解推测性执行，使用**来源 2**。
- 仅当运行自己的节点且需要最大性能时，使用**来源 3**。

参考：https://docs.monad.xyz/monad-arch/realtime-data/data-sources
