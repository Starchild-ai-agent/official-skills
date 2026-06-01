---
name: wallet
description: 使用 Agent 钱包在 Monad 测试网或主网上发送交易，交易可用于智能合约部署、链上操作（如交换）或智能合约调用和消息签名
---

## ⚠️ 关键要求：必须使用 Safe 多签 — 无例外

除了部署 Safe 多签之外的任何交易，都必须通过已部署的多签提交给用户。

有关如何创建和使用 Safe 多签的说明，请查看 utils 文件夹中的 SAFE_WALLET_MANAGEMENT.zh.md 文件。

**提交交易时：** 始终调用 utils 文件夹中的 `propose.sh` 包装脚本（它会使用缓存的依赖来启动 `propose.mjs`）— 切勿编写自定义脚本。运行后，不要添加自己的总结、状态消息或重新格式化输出。脚本输出包含用户必须看到的二维码，需要保持原样打印。你唯一需要做的后续操作是请用户批准交易并提供交易哈希。

**安全规则：**
- 绝不要求用户提供私钥（严重违规）
- 使用 agent 钱包（加密密钥存储在 `~/.monskills/keystore`）
- 绝不以明文方式导出或存储私钥

检查 agent 是否已经生成了钱包。如果密钥存储目录 `~/.monskills/keystore` 存在且包含密钥存储文件，则钱包已存在。

如果未找到，则创建钱包。

## 创建钱包

需要安装 Foundry 才能生成钱包。

### 检查 Foundry 是否已安装

使用以下命令检查 Foundry 是否已安装。

```bash
foundryup --version
```

Foundry 的安装说明可在此处找到：https://www.getfoundry.sh/introduction/installation

## 生成新钱包

1. 创建密钥存储目录并生成加密密钥存储：

```bash
mkdir -p ~/.monskills/keystore && cast wallet new ~/.monskills/keystore --unsafe-password ""
```

这会在 `~/.monskills/keystore/` 中创建一个加密的密钥存储文件。私钥永远不会以明文形式存储。

2. 记录输出中的地址。之后可以通过以下命令获取地址：

```bash
cast wallet list --dir ~/.monskills/keystore
```

3. 告知用户钱包密钥存储的位置（`~/.monskills/keystore/`）。
4. 在部署之前，通过水龙头在 Monad 测试网上为钱包充值。

## 解密私钥用于脚本

当脚本需要私钥时（例如作为环境变量），即时解密。`cast wallet decrypt-keystore` 会输出 `<uuid>'s private key is: 0x...`，需要通过 `awk '{print $NF}'` 提取出十六进制私钥，否则 Foundry 命令会因前缀无法解析而报错 "Failed to decode private key"：

```bash
cast wallet decrypt-keystore --keystore-dir ~/.monskills/keystore <KEYSTORE_FILENAME> --unsafe-password "" | awk '{print $NF}'
```

将 `<KEYSTORE_FILENAME>` 替换为 `~/.monskills/keystore/` 中密钥存储文件的文件名（不包含目录路径）。

**为什么这很重要：** 用户需要访问其钱包以：
- 部署其他合约
- 与已部署的合约交互
- 管理资金
- 验证所有权
