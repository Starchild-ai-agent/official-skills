---
name: safe-wallet-management
description: 如何使用 Safe 交易 API 创建和使用 Safe 多签
---

本文件包含如何创建和使用 Safe 多签的说明。

## 快速导航

| 任务 | 章节 |
|------|------|
| 检查是否已存在多签 | [检查 agent 是否已创建多签](#检查-agent-是否已创建多签) |
| 获取所有者的 Safe 地址 | [获取 Safe 地址](#获取-safe-地址) |
| 创建新的 Safe 多签 | [创建多签](#创建多签) |
| 通过 Safe 部署智能合约 | [使用 Safe 多签部署智能合约](#使用-safe-多签部署智能合约) |
| 向 Safe 提交交易 | [向 Safe 交易服务提交交易](#3-向-safe-交易服务提交交易) |
| 监控并获取合约地址 | [监控并获取合约地址](#4-监控并获取合约地址) |

## 网络参考

用于各网络的 RPC URL，请确保你知道需要在哪个网络上构建，如果不确定请询问用户。

### RPC URL

| 网络 | Chain ID | RPC |
|------|----------|-----|
| Monad 测试网 | 10143 | https://testnet-rpc.monad.xyz |
| Monad 主网 | 143 | https://rpc.monad.xyz |

各网络的 Safe 交易基础 API URL，请确保你知道需要在哪个网络上构建。

### Safe 交易服务（基础 URL）

| 网络 | URL |
| --- | --- |
| Monad 测试网 | https://api.safe.global/tx-service/monad-testnet/api/v1 |
| Monad 主网 | https://api.safe.global/tx-service/monad/api/v1 |

## 获取 Safe 地址

要查找特定钱包地址拥有的 Safe 多签地址，请查询 Safe 交易服务 API。

### 从本地存储

检查 agent 是否之前存储了多签详情：

```bash
cat ~/.monskills/multisig.json
```

该文件包含 `testnet` 和 `mainnet` 属性，分别存储每个网络的 Safe 地址和所有者。

### 从 Safe 交易服务 API

查询 API 以获取指定地址拥有的所有 Safe：

**Monad 测试网：**

```bash
curl -s "https://api.safe.global/tx-service/monad-testnet/api/v1/owners/$OWNER_ADDRESS/safes/" | jq
```

**Monad 主网：**

```bash
curl -s "https://api.safe.global/tx-service/monad/api/v1/owners/$OWNER_ADDRESS/safes/" | jq
```

响应会返回一个 `safes` 数组，包含指定地址作为所有者的所有 Safe 地址。

### 在链上验证 Safe

要确认 Safe 存在并检查其所有者/阈值：

```bash
# 获取所有者
cast call $SAFE_ADDRESS "getOwners()(address[])" --rpc-url [rpc-url-respective-to-network]

# 获取阈值
cast call $SAFE_ADDRESS "getThreshold()(uint256)" --rpc-url [rpc-url-respective-to-network]
```

## 检查 agent 是否已创建多签

如果 agent 已创建多签，则 ~/.monskills/ 文件夹中应该存在 multisig.json 文件。根据网络（Monad 主网或测试网），该文件中可能包含相应信息。

如果未找到多签详情，则创建一个多签。

## 创建多签

**正确流程：**

1. 确保 agent 有钱包（检查 `~/.monskills/keystore/` 中是否存在加密密钥存储）。
2. 确保已安装 Foundry 工具包（foundryup --version）
3. 向用户索要 2 个钱包地址作为多签的签名者。
4. 使用 DeploySafeCREATE2.sol 部署 Safe（检查同一文件夹中的脚本）
   - DeploySafeCREATE2.sol 可同时用于 Monad 主网和 Monad 测试网。
5. Safe 创建后，务必将多签地址及所有者存储在 ~/.monskills/ 文件夹的 multisig.json 文件中，绝对确保 json 文件中有 "testnet" 和 "mainnet" 属性，并将多签详情存储到对应的网络属性中。

### 在 Monad 测试网上创建 Safe 的命令（仅限 Monad 测试网）

```bash
# 从水龙头为 agent 钱包充值，因为是测试网，可以从水龙头领取资金。
FAUCET_RESPONSE=$(curl -s -X POST https://agents.devnads.com/v1/faucet \
  -H "Content-Type: application/json" \
  -d "{\"chainId\": 10143, \"address\": \"$AGENT_WALLET_ADDRESS\"}")

# 等待资金到账
while [ "$(cast balance $AGENT_WALLET_ADDRESS --rpc-url https://testnet-rpc.monad.xyz)" = "0" ]; do
  sleep 2
done

# 使用 CREATE2 部署 Safe（标准 SafeProxyFactory）
# 从加密密钥存储中即时解密私钥。
# `cast wallet decrypt-keystore` 会输出 "<uuid>'s private key is: 0x..."，
# 用 awk '{print $NF}' 只保留最后的十六进制私钥。
OWNER_1=$OWNER_1 OWNER_2=$OWNER_2 OWNER_3=$CLAUDE_ADDRESS \
  forge script DeploySafeCREATE2.sol:DeploySafeCREATE2 \
    --private-key $(cast wallet decrypt-keystore --keystore-dir ~/.monskills/keystore $KEYSTORE_FILENAME --unsafe-password "" | awk '{print $NF}') \
    --rpc-url https://testnet-rpc.monad.xyz \
    --broadcast

echo "✅ Safe deployed: $SAFE_ADDRESS"
echo "🌐 https://app.safe.global/home?safe=monad-testnet:$SAFE_ADDRESS"
```

### 在 Monad 主网上创建 Safe 的命令（仅限 Monad 主网）

```bash
# 检查钱包在 Monad 主网上是否有余额，如果没有余额，请用户在 Monad 主网上为地址充值。
cast balance $AGENT_WALLET_ADDRESS --rpc-url https://rpc.monad.xyz

# 使用 CREATE2 部署 Safe（标准 SafeProxyFactory）
# 从加密密钥存储中即时解密私钥（awk 去掉 "<uuid>'s private key is:" 前缀）。
OWNER_1=$OWNER_1 OWNER_2=$OWNER_2 OWNER_3=$CLAUDE_ADDRESS \
  forge script DeploySafeCREATE2.sol:DeploySafeCREATE2 \
    --private-key $(cast wallet decrypt-keystore --keystore-dir ~/.monskills/keystore $KEYSTORE_FILENAME --unsafe-password "" | awk '{print $NF}') \
    --rpc-url https://rpc.monad.xyz \
    --broadcast

echo "✅ Safe deployed: $SAFE_ADDRESS"
echo "🌐 https://app.safe.global/home?safe=monad:$SAFE_ADDRESS"
```

Safe 创建后，将多签地址及所有者存储在 ~/.monskills/ 文件夹的 multisig.json 文件中，绝对确保 multisig.json 文件中有 "testnet" 和 "mainnet" 属性，并将多签详情存储到对应的网络属性中。

## 通过 Safe 多签提交交易

必须已经部署了 Safe 多签，才能部署智能合约或执行链上操作。

**重要提示**：此工作流程使用 Safe 多签处理所有交易 — 部署、合约调用、代币转账、提款等。不允许使用 --private-key 或 --broadcast 进行直接交易。

**关键：始终使用 `propose.mjs`** — 切勿编写新的/自定义脚本来提交 Safe 交易。utils 文件夹中的 `propose.mjs` 文件处理 EIP-712 签名、交易服务 API 和二维码生成。运行 `propose.mjs` 后，不要总结、截断或重新格式化其输出 — 脚本会打印用户需要扫描的二维码。让终端输出保持原样。它支持两种模式：

| 模式 | 环境变量 | 用途 |
|------|----------|------|
| 部署 | `DEPLOYMENT_BYTECODE` | 通过 CreateCall delegatecall 部署智能合约 |
| 调用 | `TX_TO` + `TX_DATA`（+ 可选 `TX_VALUE`） | 任何合约调用：提款、交换、转账、授权等 |

两种模式的通用环境变量：`CHAIN_ID`、`SAFE_ADDRESS`、`PRIVATE_KEY`。

流程：

✅ 准备 calldata（部署字节码或编码的函数调用）
✅ 通过 `propose.mjs` 使用 Agent 的 EIP-712 签名提交到交易服务 API
✅ 用户在 Safe UI 队列中看到交易，签名（2/2），执行
✅ 终端中打印二维码供移动端批准

---

### 部署智能合约

**关键**：Safe 钱包无法通过普通 CALL 直接 CREATE 合约。要通过 Safe 部署，需要 delegatecall Safe 的 CreateCall 辅助智能合约，这样 CREATE 操作会在 Safe 的上下文中执行（Safe 成为部署者）。

CreateCall: 0x9b35Af71d77eaf8d7e40252370304687390A1A52（Monad 主网和 Monad 测试网地址相同）

为什么需要这样做：

- Safe 通过 CALL/DELEGATECALL 执行交易（而非 CREATE）
- Delegate calling CreateCall 在 Safe 的上下文中运行 CREATE
- Safe 成为部署者（避免工厂所有权陷阱）
- 与使用 --sender <SAFE_ADDRESS> 的 Foundry 模拟匹配

```sol
interface ICreateCall {
    function performCreate(uint256 value, bytes memory deploymentData) external returns (address);
    function performCreate2(uint256 value, bytes memory deploymentData, bytes32 salt) external returns (address);
}
```

#### 1. 准备部署字节码

使用 forge script，将 --sender 设置为 Safe 地址：

```bash
forge script script/Deploy.s.sol:DeployScript \
  --rpc-url [rpc-url-respective-to-network] \
  --sender <SAFE_ADDRESS>
```

这会模拟从 Safe 钱包进行部署，而不会实际广播。

#### 2. 提取部署字节码

```bash
# 提取部署字节码
DEPLOYMENT_BYTECODE=$(jq -r '.transactions[0].transaction.input' \
  broadcast/Deploy.s.sol/[chain-id-respective-to-network]/dry-run/run-latest.json)

# 确保 Safe 地址是校验和格式
SAFE_ADDRESS=$(cast to-check-sum-address "<SAFE_ADDRESS>")
```

#### 3. 向 Safe 交易服务提交交易

使用 `utils/` 文件夹中的 `propose.sh` 包装脚本调用 `propose.mjs` — 它会在首次运行时在 `~/.monskills/propose-deps/` 中自动安装 `viem` 和 `qrcode-terminal`（一次性缓存）。请勿把 `propose.mjs` 复制到项目目录，也不要再运行 `npm install --no-save viem` — Node 无法在脚本自身目录之外解析 viem 依赖。

```bash
# 运行提交 — 将 CHAIN_ID 设置为 143（主网）或 10143（测试网）。
# SCRIPT_DIR 是 monskills 插件中本 utils/ 文件夹的绝对路径（包含 propose.sh 和 propose.mjs）。
# awk '{print $NF}' 用于去掉 cast 输出中的 "<uuid>'s private key is:" 前缀。
CHAIN_ID=$CHAIN_ID \
  SAFE_ADDRESS=$SAFE_ADDRESS \
  PRIVATE_KEY=$(cast wallet decrypt-keystore --keystore-dir ~/.monskills/keystore $KEYSTORE_FILENAME --unsafe-password "" | awk '{print $NF}') \
  DEPLOYMENT_BYTECODE=$(jq -r '.transactions[0].transaction.input' \
    broadcast/Deploy.s.sol/$CHAIN_ID/dry-run/run-latest.json) \
  bash "$SCRIPT_DIR/propose.sh"
```

---

### 调用合约（提款、交换、转账、授权等）

对于调用现有合约函数的任何交易，编码 calldata 并使用 `propose.mjs` 的调用模式。

#### 1. 使用 `cast` 编码 calldata

```bash
# 示例：withdraw(uint256 amount)
TX_DATA=$(cast calldata "withdraw(uint256)" 1000000000000000000)

# 示例：transfer(address to, uint256 amount)
TX_DATA=$(cast calldata "transfer(address,uint256)" 0xRecipient 1000000000000000000)

# 示例：approve(address spender, uint256 amount)
TX_DATA=$(cast calldata "approve(address,uint256)" 0xSpender 1000000000000000000)
```

#### 2. 向 Safe 交易服务提交合约调用

继续使用 `propose.sh` 包装脚本。`SCRIPT_DIR` 为本 `utils/` 文件夹的绝对路径。

```bash
CHAIN_ID=$CHAIN_ID \
  SAFE_ADDRESS=$SAFE_ADDRESS \
  PRIVATE_KEY=$PRIVATE_KEY \
  TX_TO=$TARGET_CONTRACT_ADDRESS \
  TX_DATA=$TX_DATA \
  TX_VALUE=0 \
  bash "$SCRIPT_DIR/propose.sh"
```

将 `TX_VALUE` 设置为随调用发送的原生代币数量（单位为 wei），或省略则默认为 0。

---

### 示例输出（两种模式）：

```
✅ Agent's address: 0x937d...
✅ Safe nonce: 0
✍️  Signing with EIP-712...
✅ Transaction hash: 0x0560...
✅ Agent signed (1/2)
📤 Posting to Transaction Service API...
✅ Transaction proposed successfully!

🎉 Transaction appears in Safe UI queue!

Scan QR code to approve on mobile:

▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄
█ ▄▄▄▄▄ █ QR  █
█ █   █ █ here █
█ ▀▀▀▀▀ █      █
▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀

User can now:
1. Open [safe url] (or scan QR code above)
2. See pending transaction (agent already signed 1/2)
3. Sign with their wallet (2/2)
4. Execute
```

请用户在多签页面上批准交易并提供交易哈希。

### 4. 监控并获取合约地址

用户在 Safe UI 中执行交易后：

```bash
# 用户在执行后提供交易哈希
cast receipt <TRANSACTION_HASH> --rpc-url https://testnet-rpc.monad.xyz
```

**不要使用 `contractAddress` 字段——对于 Safe 部署，该字段始终为 `null`。** Safe 并未直接 `CREATE`；它 delegatecall 到 CreateCall，因此回执的顶层 `contractAddress` 为空。已部署的地址在 CreateCall 发出的 `ContractCreation(address)` 日志中。

从日志中解析：

```bash
cast receipt <TRANSACTION_HASH> --rpc-url https://testnet-rpc.monad.xyz --json \
  | jq -r '.logs[] | select(.address == "0x9b35Af71d77eaf8d7e40252370304687390A1A52") | "0x" + .data[26:66]'
```

（`0x9b35Af71d77eaf8d7e40252370304687390A1A52` 是 CreateCall 在 Monad 主网和测试网上的地址——参见 `addresses/`。）

### 5. 验证智能合约

**每次智能合约部署后，你必须验证合约。** 不要跳过此步骤。有关完整说明，请参阅 `scaffold/SKILL.md` 中的 **Verification (All Explorers)** 部分。使用验证 API（`https://agents.devnads.com/v1/verify`）— 一次调用即可在所有 3 个浏览器（MonadVision、Socialscan、Monadscan）上进行验证。
