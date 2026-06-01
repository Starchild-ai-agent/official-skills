# Para —— 工作流配方

针对常见 Para 任务的固定步骤序列。每个配方都假定用户已登录（`para auth status` 退出 0）。如果未登录，把安装 + 登录的命令呈现给用户并等待 —— 见 `para-cli.zh.md` → “安装与认证”。

本 skill 永远不会脚手架一个全新的应用 —— 项目脚手架由 `scaffold/` skill 负责。下面所有配方都假定仓库里已经存在一个 Next.js 或 Vite 前端（通常在 `web/`）。

## 把 Para 集成到已存在的前端中

使用场景：前端已经存在，用户希望把 Para 接进去（例如 `scaffold/` skill 生成的 Next.js 应用，或已有的 Vite 应用）。

1. **`cd` 到前端目录**（有 `package.json` 的那个）。如果前端在子目录里，不要在仓库根目录运行 `para init` —— `.pararc` 应该和前端的 `package.json` 同级。
2. **Pin 住 Para 项目上下文：**
   ```bash
   para init
   ```
   这会写入 `.pararc`（组织 + 项目 + 环境）。提交它 —— 队友能无须手动切换就拿到同一个上下文。文件中没有密钥。

   **如果 `para init` 报错 `TTY initialization failed: uv_tty_init returned EINVAL`**，说明 shell 没有挂到真正的 TTY（沙盒 agent、Codespaces 以及大多数 CI 形状的环境很常见）。改用 `--no-input` 重新执行 —— 它会跳过交互提问并使用全局配置里的当前组织 / 项目 / 环境：
   ```bash
   para init --no-input
   ```
   如果用户还没运行过 `para projects switch` / `para config set defaultEnvironment`，先做这件事，再 `para init --no-input`。
3. **安装 Para SDK 依赖包。** 具体列表取决于框架与目标网络。Next.js + EVM：
   ```bash
   npm install @getpara/react-sdk @getpara/evm-wallet-connectors viem wagmi @tanstack/react-query
   ```
   Para 的 React hooks 依赖 React Query —— 如果项目里还没有，要装上。
4. **把 `tsconfig.json` 的 target 升到 ES2020。** viem / wagmi 用 BigInt 字面量（`0n`），需要 ES2020+。`create-next-app` 默认是 ES2017。在写任何链上代码之前先打补丁：
   ```bash
   jq '.compilerOptions.target = "ES2020"' tsconfig.json > tsconfig.tmp && mv tsconfig.tmp tsconfig.json
   ```
5. **创建或选择一个 API Key：**
   ```bash
   para keys list
   # 如果该环境下没有，或想要一个全新的：
   para keys create -n monad-app-dev --display-name "Monad App (dev)"
   ```
   不要把密钥回显给用户。前端使用的是公钥。
6. **写入环境变量。** 把公钥写入框架的 env 文件，使用正确的前缀：
   - Next.js → `web/.env.local`，写 `NEXT_PUBLIC_PARA_API_KEY=<public-key>`
   - Vite → `web/.env`，写 `VITE_PARA_API_KEY=<public-key>`

   追加（不要重复）—— 先删掉任何已存在的 `*_PARA_API_KEY=` 行。
7. **把应用包在 `ParaProvider` 中并导入 Para 的 CSS。** 这是 `para doctor` 在跳过时会报错的部分。Next.js App Router：

   `web/app/providers.tsx`：
   ```tsx
   'use client'

   import '@getpara/react-sdk/styles.css'
   import { Environment, ParaProvider } from '@getpara/react-sdk'
   import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
   import { http } from 'wagmi'
   import { monad, monadTestnet } from 'wagmi/chains'
   import type { ReactNode } from 'react'

   const queryClient = new QueryClient()

   export default function Providers({ children }: { children: ReactNode }) {
     return (
       <QueryClientProvider client={queryClient}>
         <ParaProvider
           paraClientConfig={{
             apiKey: process.env.NEXT_PUBLIC_PARA_API_KEY!,
             env: Environment.BETA, // 生产构建切到 Environment.PRODUCTION
           }}
           config={{ appName: 'My Monad App' }}
           paraModalConfig={{
             // 空数组会隐藏所有社交登录按钮。省略该键（或只列子集）
             // 来启用它们。客户端 vs Key 端的拆分见下文
             // “配置认证方式……”。
             oAuthMethods: ['GOOGLE', 'APPLE', 'DISCORD', 'TWITTER', 'FACEBOOK', 'FARCASTER'],
             disablePhoneLogin: false,
             recoverySecretStepEnabled: true,
           }}
           externalWalletConfig={{
             evmConnector: {
               config: {
                 // 数组第一项是连接时用户落到的默认链。
                 chains: [monadTestnet, monad],
                 transports: {
                   [monadTestnet.id]: http('https://testnet-rpc.monad.xyz'),
                   [monad.id]: http('https://rpc.monad.xyz'),
                 },
               },
             },
             wallets: ['METAMASK', 'COINBASE', 'WALLETCONNECT', 'RAINBOW', 'ZERION', 'RABBY'],
           }}
         >
           {children}
         </ParaProvider>
       </QueryClientProvider>
     )
   }
   ```

   `web/app/layout.tsx`：
   ```tsx
   import Providers from './providers'

   export default function RootLayout({ children }: { children: React.ReactNode }) {
     return (
       <html lang="en">
         <body>
           <Providers>{children}</Providers>
         </body>
       </html>
     )
   }
   ```

   `providers.tsx` 顶部的 `'use client'` 指令是必需的 —— Para 的 hooks 只在客户端可用。少了它 `para doctor` 会报错。

   **v2 prop 形状 —— 常见坑：**
   - v2 没有扁平的 `apiKey` prop，也没有 `defaultChain` prop。所有配置都在 `paraClientConfig`、`config`、`paraModalConfig` 或 `externalWalletConfig` 之内。
   - 默认链 = `externalWalletConfig.evmConnector.config.chains` 中第一项。
   - `oAuthMethods` 是字符串联合类型的数组：`'APPLE' | 'DISCORD' | 'FACEBOOK' | 'FARCASTER' | 'GOOGLE' | 'TWITTER' | 'TELEGRAM'`。
   - `wallets` 接受 `'METAMASK' | 'COINBASE' | 'WALLETCONNECT' | 'RAINBOW' | 'ZERION' | 'RABBY'`。
8. **应用 Monad 接线改动。** 加载 `references/para-monad-wiring.zh.md` 获取 `externalWalletConfig.evmConnector.config` 的精确形状（chains + transports）与 tsconfig 升级。
9. **运行 `para doctor`** 验证全部接线：
   ```bash
   para doctor
   ```
   声明集成完成前，把每一条报告出来的错误都修掉。Warning 可以晚点处理，但 error 会在运行时变成真正的失败。
10. **启动开发服务器**，打开连接流程，确认 Para 弹窗按配置渲染出认证方式，并且链列表中能看到 Monad。

## 轮换 API Key

使用场景：Key 泄漏，或用户按计划轮换。

1. **识别 Key：**
   ```bash
   para keys list
   ```
2. **轮换**（这会立即禁用旧 Key）：
   ```bash
   para keys rotate            # 轮换公钥（最常见）
   # 或
   para keys rotate --secret   # 轮换密钥
   ```
3. **在同一改动中更新前端 env 文件**，应用才能继续工作。删掉旧的 `*_PARA_API_KEY=` 行并追加新值。不要把值回显给用户 —— 用一句中文确认（“已轮换并更新 `web/.env.local`”）。
4. **重新部署前端**，让新 Key 在生产环境生效。
5. **如果被轮换的 Key 也被后端 / Webhook 处理器使用**，单独轮换密钥并把那些 env vars 也更新。

## 通过 CLI 配置认证方式、品牌或 Webhook

使用场景：用户希望不离开终端就修改 Para 弹窗里出现的登录方式、更新颜色 / 字体、给后端接一个 Webhook。

### 客户端 vs Key 端 —— 各自控制什么

这一点很容易绊倒人。“认证方式” 配置有两个独立面，而 `para doctor` 抓不到配错位置的情况：

| 在哪 | 控制什么 | 例子 |
|---|---|---|
| **客户端** —— `ParaProvider` 上的 `paraModalConfig`（见上文步骤 7） | 弹窗里出现哪些 **IDP 按钮**、手机登录可见性、恢复步骤开关、弹窗主题 / 布局 | 隐藏社交登录：`oAuthMethods: []`。隐藏手机：`disablePhoneLogin: true`。只隐藏 Twitter：从数组里删除 `'TWITTER'`。 |
| **Key 端** —— `para keys config security` | 用户可以注册哪些**二次验证方式**（PASSKEY / PASSWORD / PIN）、允许的 origin、会话时长、IP 白名单、交易弹窗 | 强制仅 Passkey：选中 `PASSKEY`，取消其他。给 IP 白名单加一段 CIDR。 |

如果用户说 “隐藏社交登录” 或 “我只要邮箱登录” —— 这是**客户端**，改 `paraModalConfig`。CLI 关不掉 IDP 按钮。反之，如果用户想禁止 PIN 作为二次验证 —— 这是 **Key 端**，通过 `para keys config security` 改。

1. **查看当前配置：**
   ```bash
   para keys config show              # 所有分类
   para keys config show security     # 单一分类
   para keys config show --json       # 脚本可解析
   ```
2. **以交互或 flag 方式编辑。** 五个分类是 `security`、`branding`、`setup`、`ramps`、`webhooks` —— 各自控制什么见 `para-cli.zh.md` → “`para keys config`”。
3. **专门针对 Webhook：** 在设置好端点 URL 与订阅事件之后，正式依赖它之前先发送一次测试事件：
   ```bash
   para keys config webhooks test
   ```
   确认后端收到了事件并能验证签名。
4. **针对 IP 白名单（security 分类）：** *先*把用户当前的 IP 加进去，再开启强制。否则你会把他们锁在自己的项目外面。问用户拿 IP —— 不要猜。（详见 `para-cli.zh.md` → “IP 白名单坑点”。）

## 调试一个坏掉的 Para 集成

使用场景：开发服务器能跑，但 Para 弹窗打不开；env vars 看起来没问题但 `useAccount()` 返回空；或者认证完成了但钱包不出现。

1. **先跑 `para doctor`。** 大多数集成 bug 都是这五个之一：缺 `ParaProvider`、缺 CSS 导入、缺 `'use client'`、env-var 前缀和框架不匹配、`@getpara/*` 包之间版本漂移。`para doctor` 五个都能抓。
   ```bash
   para doctor
   ```
   把它报出的每条错误原文转达给用户 —— 不要自行总结掉。
2. **如果 `para doctor` 干净但弹窗仍然打不开**，看浏览器控制台是不是 `Invalid API key` 或 origin 错误：
   - 环境错位：生产构建里用了 beta Key（或反之）。检查 `para config get defaultEnvironment` 与 env-var 的来源。
   - origin 未在白名单：如果在 `para keys config` 的 security 里设置了 `allowed origins`，本地开发 URL（`http://localhost:3000`）也需要加进去。
3. **如果认证完成但没有钱包出现**，通常是网络配置出问题。确认 wagmi 配置里包含了 Monad（或目标链），并且 chain id 与合约期望一致（Monad 测试网是 10143，主网是 143 —— 以 `wagmi/chains` 为准核对，这些虽然很少变但确实会变）。
4. **如果怀疑是 Para 侧故障**（少见），检查 `para auth status` 的退出码 —— 退出 2 表示 API / 服务端错误。重试一次；仍失败则告知用户。

## 切换环境（beta ↔ prod）

使用场景：从本地开发迁到正式发布。

1. **以 local 方式设置环境**，把它 pin 到当前项目：
   ```bash
   para config set --local defaultEnvironment prod
   ```
   这会写入 `.pararc`。提交它。
2. **拿一个 prod API Key：**
   ```bash
   para keys create -n monad-app-prod --display-name "Monad App (prod)"
   ```
3. **把 prod Key 写进 prod 前端的 env**（Vercel 项目设置等）—— 绝不要粘贴到会被提交的 `.env`。不同部署环境用不同的 env vars。
4. **用 `PARA_ENVIRONMENT=prod` 在本地跑一次 `para doctor`** 验证 prod 构建没接错：
   ```bash
   PARA_ENVIRONMENT=prod para doctor
   ```
5. **除非用户明确要求，否则不要把全局默认切到 prod** —— 用 `.pararc` 把 `prod` 锁在这个项目内，同机器上的其他 Para 项目继续保持在 `beta`。

## 归档 / 删除一个 Para 项目

使用场景：用户明确表示要删除一个 Para 项目。

1. **按名字确认**。把项目名与组织名复述给用户，等待明确的 yes。
2. **归档**（可逆）：
   ```bash
   para projects archive
   ```
3. **反归档**（用户改主意时）：
   ```bash
   para projects restore
   ```

CLI 没有对项目的硬删除 —— 归档就是终止动作。对于 Key，`para keys archive` 是等价操作，且从 CLI 端**不可**反归档。
