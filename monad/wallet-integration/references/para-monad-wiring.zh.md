# Para —— 把 Monad 接入 ParaProvider

`para init` 会把 Para 的 React SDK 配置进你已有的前端，但 Para 自带的 EVM 链集是通用的（Ethereum mainnet、Sepolia 等）。Monad **不**在内置列表里 —— 主网（chain id 143）和测试网（chain id 10143）都不在。本文件是你在集成之后应用的补丁，用来把 Monad 设为默认链。

请在 `references/para-workflows.zh.md` → “把 Para 集成到已存在的前端中” 完成 `ParaProvider` 接线**之后**再应用本补丁。v2 中链列表在 `ParaProvider` 的 `externalWalletConfig.evmConnector.config` **内部** —— 不再有独立的 `wagmi.ts` `createConfig`，也没有顶层 `defaultChain` prop。

## 前置：把 tsconfig target 升到 ES2020

`create-next-app` 默认生成 `"target": "ES2017"`。viem 与 wagmi 在 chain id、gas、金额等地方使用 BigInt 字面量（`0n`、`1n`）—— 没有 ES2020，一旦你碰到 chain id 或 `useReadContract`，就会撞上 `TS2737: BigInt literals are not available when targeting lower than ES2020`。

```bash
cd web
jq '.compilerOptions.target = "ES2020"' tsconfig.json > tsconfig.tmp && mv tsconfig.tmp tsconfig.json
```

如果未安装 `jq`，打开 `tsconfig.json` 把 `"target": "ES2017"` 手动改成 `"target": "ES2020"`。

## 把 Monad 加入 `externalWalletConfig.evmConnector.config`

找到渲染 `<ParaProvider>` 的那个文件（Next.js App Router 通常是 `web/app/providers.tsx`；Vite 有时是 `web/src/main.tsx`）。从 `wagmi/chains` 导入 Monad 链对象，并通过 `externalWalletConfig.evmConnector.config` 传入：

```tsx
import { Environment, ParaProvider } from '@getpara/react-sdk'
import { http } from 'wagmi'
import { monad, monadTestnet } from 'wagmi/chains'

<ParaProvider
  paraClientConfig={{
    apiKey: process.env.NEXT_PUBLIC_PARA_API_KEY!,
    env: Environment.BETA,
  }}
  config={{ appName: 'My Monad App' }}
  externalWalletConfig={{
    evmConnector: {
      config: {
        // 数组第一项即用户可见的默认链。
        chains: [monadTestnet, monad /* , ...保留脚手架加进来的其他链 */],
        transports: {
          [monadTestnet.id]: http('https://testnet-rpc.monad.xyz'),
          [monad.id]: http('https://rpc.monad.xyz'),
          // ...其他 transports
        },
      },
    },
    wallets: ['METAMASK', 'COINBASE', 'WALLETCONNECT', 'RAINBOW', 'ZERION', 'RABBY'],
  }}
>
  {children}
</ParaProvider>
```

说明：
- `monad` 与 `monadTestnet` 直接由 `wagmi/chains` 导出 —— 不需要自己定义。如果 import 报错，把 `wagmi` 升到较新的 `2.x` 小版本（这两条链是 2.x 线里较晚加入的）。
- 不要在用户没明确要求 “只保留 Monad” 的情况下移除脚手架加入的其他链。例如移除 Ethereum 主网后，某些外部钱包在连接时做的链上余额查询可能会失败。
- 除非用户使用了付费 RPC（Alchemy / QuickNode / Ankr），否则用上面的公开 RPC URL —— 如果有付费 RPC，则改成从环境变量读取的 URL。

## 把 Monad 设为默认链

v2 的 `ParaProvider` 上**没有 `defaultChain` prop**。默认链是 `externalWalletConfig.evmConnector.config` 中 `chains` 数组**第 0 位**的那条链。要把 `monadTestnet`（或 `monad`）设为默认，就把它放第一：

```ts
chains: [monadTestnet, monad, mainnet]   // 测试网为默认
chains: [monad, monadTestnet, mainnet]   // 主网为默认
```

根据合约部署到哪个网络选择 `monad`（主网）或 `monadTestnet`。如果两边都部署了，而用户希望链切换器默认落在主网，就把 `monad` 放前。

## 验证

改完之后：

```bash
cd web
para doctor                    # 应仍然通过
npm run dev                    # 启动开发服务器
```

打开应用、点击连接、走完一次 Para 认证流程，然后打开链切换器 —— Monad 主网与 Monad 测试网都应该出现，第一项被选中。如果没出现，最常见的原因是改到了旧脚手架残留的 `wagmi.ts`，而新版 v2 `ParaProvider` 已经不消费它。grep `ParaProvider` 确认现在到底接的是哪个文件，再去改*那个*文件。

## 不要做的事

- **不要往 `ParaProvider` 传 `defaultChain` prop** —— 在 v2 里没有效果。改 `chains` 数组的顺序。
- **不要保留一个已停止使用的 wagmi `createConfig`。** Para 的 `externalWalletConfig.evmConnector.config` 接收同样的 `{ chains, transports }` 形状并在内部构建 wagmi 配置；残留的 `wagmiConfig` 导出会逐渐与真实配置漂移，让后来的读者困惑。
- **不要手写 Monad 的 chain 对象**（`{ id: 143, name: 'Monad', ... }`）。`wagmi/chains` 已经导出了它们 —— 用导出的版本能保证 chain id、默认 RPC、浏览器 URL、原生代币等如果上游有变化时也能保持同步。
- **不要把 chain id 写成字符串。** `[monad.id]: http(...)` 之所以能工作是因为 `monad.id` 已经是 number；`["143"]: http(...)` 会悄无声息地匹配不上。
