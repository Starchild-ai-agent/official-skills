---
name: wallet-integration
description: 如何使用 Para 为已存在的 Monad 前端添加钱包连接与身份认证 —— 通过邮箱 / 手机号 / Passkey / 社交登录（Google、Apple、Twitter、Discord、Facebook、Farcaster）获得嵌入式 MPC 钱包，同时支持外部钱包连接（MetaMask、Coinbase、WalletConnect、Rainbow 等）。由 `para` CLI（`@getpara/cli`）驱动。当用户希望在已有的 Next.js 或 Vite 前端中集成 Para，或希望从终端管理 Para 项目、API Key 与 Webhook 时，加载此 skill。这是 monskills 的官方钱包集成 skill —— 没有单独的 “social login” 或 “embedded wallets” skill，全部内容都在这里。
---

# 钱包集成（Para）

本 skill 介绍如何使用 **Para** 与 `para` CLI（`@getpara/cli`）为 Monad 项目的前端添加钱包与身份认证。

Para 为用户提供嵌入式 MPC 钱包 —— 用户使用邮箱、手机号、Passkey 或社交服务商（Google、Apple、Twitter、Discord、Facebook、Farcaster）登录后立即获得一个钱包，不需要任何浏览器扩展。同时支持已有钱包用户连接外部钱包（MetaMask、Coinbase、WalletConnect、Rainbow、Zerion、Rabby）。同一个 `ParaProvider` 同时处理两种流程。

本 skill 假设前端已经存在（通常由 `scaffold/` skill 生成在 `web/` 目录中）。它**不**负责脚手架新应用 —— Para 的 `para create` 模板在此 skill 中是有意排除的，因为项目脚手架由其他 skill 处理。

## 何时加载此 skill

- 用户希望在 Monad 主网或测试网的前端上做任何钱包连接 / 登录流程。
- 用户希望使用嵌入式钱包、社交登录、邮箱 / 短信登录或 Passkey 登录。
- 用户已有 Next.js 或 Vite 前端，希望集成 Para（`para init` + `ParaProvider` + `para doctor`）。
- 用户希望从 CLI 管理 Para API Key、环境、Webhook、品牌或认证方式。
- 用户希望调试一个无法工作的钱包集成（`para doctor`）。

## Monad 在 Para 中的支持

Para 的 `--networks` flag 支持 `evm`。Monad 主网与 Monad 测试网都是 EVM 链，因此可使用 EVM 模板 —— 但 Para 并未把 Monad 作为内置 chain 对象发布。在 `para init` 之后，你需要从 `wagmi/chains` 导入 `monad` 与 `monadTestnet`，并通过 `ParaProvider` 上的 `externalWalletConfig.evmConnector.config.{chains,transports}` 传入（v2 把链列表放在这里 —— 不再有独立的 `wagmi.ts` `createConfig`，也没有 `defaultChain` prop）。详见 `references/para-monad-wiring.zh.md` 中的精确代码改动。

## v2 SDK 形态 —— 改动 provider 前必读

如果你在修改一个已存在的 Para 集成，`ParaProvider` 的 props **不是**扁平的 `apiKey={...}`。v2 把它们拆成了四个 config 对象：

- `paraClientConfig={{ apiKey, env: Environment.BETA }}` —— 凭证与环境（`BETA` / `PRODUCTION`）。
- `config={{ appName }}` —— 应用元数据。
- `paraModalConfig={{ oAuthMethods, disablePhoneLogin, recoverySecretStepEnabled, ... }}` —— **客户端**弹窗控制项（要渲染哪些 IDP 按钮、手机号开关、恢复步骤）。`oAuthMethods: []` 为空数组会隐藏所有社交登录。
- `externalWalletConfig={{ evmConnector: { config: { chains, transports } }, wallets: ['METAMASK', ...] }}` —— 链列表、RPC transports，以及要显示哪些外部钱包入口。

默认链 = `externalWalletConfig.evmConnector.config.chains` 中的第一项。没有顶层 `defaultChain` prop。完整示例见 `references/para-workflows.zh.md` → 步骤 7。

## 前置条件

任何 `para` 命令能跑通之前，用户必须满足以下全部条件：

1. 全局安装 `@getpara/cli`：`npm install -g @getpara/cli`（或 `pnpm add -g @getpara/cli`，或通过 `npx @getpara/cli@latest` 运行）。
2. 已登录 `para`：`para login`（浏览器 OAuth 流程 —— 只有用户本人可以完成）。
3. 选定一个 Para 组织与项目作为当前上下文。`para login` 之后，CLI 会自动选择第一个组织与项目；需要切换则使用 `para orgs switch` / `para projects switch`。

monskills 的 hook 会在 install + login 这两件事完成之前拦截 `para` 命令。如果缺少前置条件，hook 会以缺失项作为原因拒绝工具调用 —— 把这条消息原文转达给用户并等待。

### 不要做的事

- **不要替用户安装 CLI。** 如果 `@getpara/cli` 缺失，告诉他们准确的命令并等待。
- **不要替用户运行 `para login`。** 该命令会打开浏览器标签页，只有用户本人能完成 OAuth 流程。（虽然 `--no-browser` 存在于无头环境，但 monskills 是给交互式使用的 —— 让用户自己选择。）
- **不要通过 Web 后台替用户创建 Para 账号或 API Key。** CLI 可以创建项目与 Key —— 引导用户使用 CLI。
- **不要运行 `para create`。** 项目脚手架由 `scaffold/` skill 负责；本 skill 只负责把 Para 集成进已存在的前端。

## 把 Para 集成到已存在的前端中

```bash
cd web   # 或前端实际所在的目录
para init
```

`para init` 会写入 `.pararc`（组织 + 项目 + 环境上下文），然后你安装 SDK 包、把应用包在 `ParaProvider` 中、导入 Para 的 CSS。接线完成后运行 `para doctor` 验证有无遗漏。

在沙盒或无头终端（没有真正的 TTY）下，`para init` 会以 `TTY initialization failed: uv_tty_init returned EINVAL` 退出 —— 改用 `para init --no-input` 重新执行，它会读取全局配置中的当前组织 / 项目 / 环境而不进行交互提问。

详见 `references/para-workflows.zh.md` → “把 Para 集成到已存在的前端中” 中的精确代码改动、依赖包清单与 `para doctor` 调试循环。

## 接下来去哪里查

参考文件 —— 按需加载：

- [工作流配方](./references/para-workflows.zh.md) —— 针对以下场景的固定步骤：把 Para 集成进已存在前端、轮换 API Key、通过 `para keys config` 配置认证方式 / 品牌 / Webhook、用 `para doctor` 调试。
- [CLI 参考](./references/para-cli.zh.md) —— 按主题（认证、配置、组织/项目、Key、诊断）分组的全部 `para` 命令，附带 flag 与坑点说明。
- [Monad 接线](./references/para-monad-wiring.zh.md) —— 在 `para init` 之后把 Monad 主网 + 测试网加入 Para provider 所消费的 wagmi 配置的精确编辑步骤。每次集成 Para 后都应应用此补丁。

按用户目标对应的工作流配方开始操作。只有在工作流文档里没覆盖到某个 flag 或子命令时才回到 CLI 参考。

## 退出码契约

所有 `para` 命令都遵循同一约定 —— 检查退出码，而不仅是 stdout：

| 退出码 | 含义 | 应对方式 |
|---|---|---|
| `0` | 成功 | 继续 |
| `1` | 用户错误（参数错误、未登录、未知项目，或 `para doctor --json` 发现错误） | 阅读 stderr，修正输入后重试 |
| `2` | API / 服务端错误 | 不是用户的问题。重试一次；仍失败则告知用户并停止。 |

`para doctor --json` 在发现错误时退出 1 —— 这是预期行为，不是 CLI bug。把它作为 “集成存在问题” 的信号。

## 密钥卫生

- `para keys get --show-secret` 与 `para keys get --copy-secret` 会打印 / 复制**密钥** API Key。永远不要在回复中回显该值，也不要把它粘贴到会被提交的文件里。公钥（不加 flag）则可以写入 `.env.local`，前缀使用 `NEXT_PUBLIC_PARA_API_KEY`（或对应框架的等价前缀）。
- 写入 Key 前总是确认环境变量前缀与框架匹配：Next.js 用 `NEXT_PUBLIC_`，Vite 用 `VITE_`。`para doctor` 会指出前缀不匹配。
- `.pararc` 可以放心提交（只保存组织 / 项目 ID 与环境，不含密钥）。`.env` / `.env.local` 应放入 `.gitignore`。

## 官方文档

- CLI 概览：https://docs.getpara.com/v2/cli/overview
- 安装：https://docs.getpara.com/v2/cli/installation
- 命令参考：https://docs.getpara.com/v2/cli/commands
