# Para — wiring Monad into the ParaProvider

`para init` sets up Para's React SDK in your existing frontend, but the EVM chain set Para's connectors ship with is generic (Ethereum mainnet, Sepolia, etc.). Monad isn't included — neither mainnet (chain id 143) nor testnet (chain id 10143). This file is the post-integration patch you apply to make Monad the default chain.

Apply this **after** the `ParaProvider` wiring in `references/para-workflows.md` → "Integrate Para into the existing frontend." The chain list lives **inside** `ParaProvider`'s `externalWalletConfig.evmConnector.config` in v2 — there is no separate `wagmi.ts` `createConfig` and no top-level `defaultChain` prop.

## Prereq: bump tsconfig target to ES2020

`create-next-app` generates `"target": "ES2017"`. viem and wagmi use BigInt literals (`0n`, `1n`) for chain ids, gas, amounts — without ES2020 you hit `TS2737: BigInt literals are not available when targeting lower than ES2020` the moment you touch a chain id or `useReadContract`.

```bash
cd web
jq '.compilerOptions.target = "ES2020"' tsconfig.json > tsconfig.tmp && mv tsconfig.tmp tsconfig.json
```

If `jq` isn't installed, open `tsconfig.json` and change `"target": "ES2017"` to `"target": "ES2020"` by hand.

## Add Monad to `externalWalletConfig.evmConnector.config`

Find the file that renders `<ParaProvider>` (typically `web/app/providers.tsx` for Next.js App Router; sometimes `web/src/main.tsx` for Vite). Import the Monad chains from `wagmi/chains` and pass them through `externalWalletConfig.evmConnector.config`:

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
        // First chain in the array is the user-facing default.
        chains: [monadTestnet, monad /* , ...keep other chains the scaffold added */],
        transports: {
          [monadTestnet.id]: http('https://testnet-rpc.monad.xyz'),
          [monad.id]: http('https://rpc.monad.xyz'),
          // ...other transports
        },
      },
    },
    wallets: ['METAMASK', 'COINBASE', 'WALLETCONNECT', 'RAINBOW', 'ZERION', 'RABBY'],
  }}
>
  {children}
</ParaProvider>
```

Notes:
- `monad` and `monadTestnet` are exported from `wagmi/chains` directly — no need to define them by hand. If the import errors, bump `wagmi` to a recent `2.x` minor (the chains were added later in the 2.x line).
- Don't strip the other chains the scaffold added unless the user explicitly asks for Monad-only. Removing Ethereum mainnet, for example, may break wallet-side balance lookups that some external wallets do at connect time.
- Use the public RPC URLs above unless the user has a paid RPC (Alchemy / QuickNode / Ankr) — in that case wire the env-var-driven URL instead.

## Set Monad as the default chain

There is **no `defaultChain` prop** on `ParaProvider` in v2. The default chain is whichever chain sits in **position 0 of the `chains` array** inside `externalWalletConfig.evmConnector.config`. To make `monadTestnet` (or `monad`) the default, put it first:

```ts
chains: [monadTestnet, monad, mainnet]   // testnet is default
chains: [monad, monadTestnet, mainnet]   // mainnet is default
```

Pick `monad` (mainnet) or `monadTestnet` based on which network the contracts are deployed to. If both are deployed and the user wants the chain switcher to default to mainnet, put `monad` first.

## Verify

After the edits:

```bash
cd web
para doctor                    # should still pass
npm run dev                    # start dev server
```

Open the app, click connect, complete a Para auth flow, then open the chain switcher — Monad mainnet and Monad testnet should both appear, with whichever you put first selected. If they don't, the most common cause is editing a stale `wagmi.ts` from an old scaffold that the new v2 `ParaProvider` no longer consumes. Grep for `ParaProvider` to confirm which file is wired in and edit *that* one.

## Don't do these things

- **Don't pass a `defaultChain` prop to `ParaProvider`** — it does nothing in v2. Re-order the `chains` array instead.
- **Don't keep a parallel `createConfig` from wagmi** that you stop using. Para's `externalWalletConfig.evmConnector.config` takes the same `{ chains, transports }` shape and builds the wagmi config internally; a leftover `wagmiConfig` export will drift and confuse future readers.
- **Don't define Monad chain objects by hand** (`{ id: 143, name: 'Monad', ... }`). `wagmi/chains` exports them — using the export keeps the chain id, RPC defaults, explorer URLs, and native currency in sync if anything ever changes upstream.
- **Don't set the chain id as a string.** `[monad.id]: http(...)` works because `monad.id` is already a number; `["143"]: http(...)` will silently mismatch.
