# Para — workflow recipes

Opinionated sequences for common Para tasks. Each recipe assumes the user is already logged in (`para auth status` exit 0). If not, surface the install + login command and wait — see `para-cli.md` → "Install and auth."

This skill never scaffolds a fresh app — project scaffolding is handled by the `scaffold/` skill. Every recipe below assumes a Next.js or Vite frontend already exists in the repo (typically at `web/`).

## Integrate Para into the existing frontend

Use when: the frontend already exists and the user wants to add Para to it (e.g. the Next.js app produced by the `scaffold/` skill, or an existing Vite app).

1. **`cd` into the frontend directory** (the one with `package.json`). Don't run `para init` from the repo root if the frontend is in a subdir — `.pararc` should sit next to the frontend's `package.json`.
2. **Pin the Para project context:**
   ```bash
   para init
   ```
   This writes `.pararc` (org + project + environment). Commit it — teammates pick up the same context without manual switching. No secrets in the file.

   **If `para init` errors with `TTY initialization failed: uv_tty_init returned EINVAL`**, the shell isn't attached to a real TTY (common in sandboxed agents, Codespaces, and most CI-shaped environments). Re-run with `--no-input` — it skips the interactive prompts and uses the active org/project/env from global config:
   ```bash
   para init --no-input
   ```
   If the user hasn't run `para projects switch` / `para config set defaultEnvironment` yet, do that first, then `para init --no-input`.
3. **Install the Para SDK packages.** The exact list depends on the framework and networks. For Next.js + EVM:
   ```bash
   npm install @getpara/react-sdk @getpara/evm-wallet-connectors viem wagmi @tanstack/react-query
   ```
   Para's React hooks rely on React Query — install it if it isn't already there.
4. **Bump `tsconfig.json` target to ES2020.** viem/wagmi use BigInt literals (`0n`) which require ES2020+. `create-next-app`'s default is ES2017. Patch it before you write any onchain code:
   ```bash
   jq '.compilerOptions.target = "ES2020"' tsconfig.json > tsconfig.tmp && mv tsconfig.tmp tsconfig.json
   ```
5. **Create or pick an API key:**
   ```bash
   para keys list
   # if none for this env, or you want a fresh one:
   para keys create -n monad-app-dev --display-name "Monad App (dev)"
   ```
   Don't print the secret back to the user. The public key is what the frontend uses.
6. **Wire env vars.** Write the public key into the framework's env file with the right prefix:
   - Next.js → `web/.env.local` as `NEXT_PUBLIC_PARA_API_KEY=<public-key>`
   - Vite → `web/.env` as `VITE_PARA_API_KEY=<public-key>`

   Append (don't duplicate) — strip any prior `*_PARA_API_KEY=` line first.
7. **Wrap the app in `ParaProvider` + import Para CSS.** This is the part `para doctor` will yell about if you skip it. For Next.js App Router:

   `web/app/providers.tsx`:
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
             env: Environment.BETA, // switch to Environment.PRODUCTION for prod builds
           }}
           config={{ appName: 'My Monad App' }}
           paraModalConfig={{
             // Empty array hides ALL social login buttons. Omit the key (or list a subset)
             // to enable them. See "Configure auth methods…" below for the client-side
             // vs key-side split.
             oAuthMethods: ['GOOGLE', 'APPLE', 'DISCORD', 'TWITTER', 'FACEBOOK', 'FARCASTER'],
             disablePhoneLogin: false,
             recoverySecretStepEnabled: true,
           }}
           externalWalletConfig={{
             evmConnector: {
               config: {
                 // First chain in the array is the default users land on at connect.
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

   `web/app/layout.tsx`:
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

   The `'use client'` directive on `providers.tsx` is required — Para hooks are client-only. `para doctor` flags this if missing.

   **v2 prop shape — common pitfalls:**
   - There is no flat `apiKey` prop and no `defaultChain` prop in v2. Everything lives inside `paraClientConfig`, `config`, `paraModalConfig`, or `externalWalletConfig`.
   - Default chain = first entry in `externalWalletConfig.evmConnector.config.chains`.
   - `oAuthMethods` is a string-union array: `'APPLE' | 'DISCORD' | 'FACEBOOK' | 'FARCASTER' | 'GOOGLE' | 'TWITTER' | 'TELEGRAM'`.
   - `wallets` accepts `'METAMASK' | 'COINBASE' | 'WALLETCONNECT' | 'RAINBOW' | 'ZERION' | 'RABBY'`.
8. **Apply the Monad wiring edits.** Fetch `references/para-monad-wiring.md` for the exact shape of `externalWalletConfig.evmConnector.config` (chains + transports) and the tsconfig bump.
9. **Run `para doctor`** to verify everything is wired:
   ```bash
   para doctor
   ```
   Fix every reported error before claiming the integration works. Warnings can be addressed later, but errors will surface as runtime failures.
10. **Start the dev server**, open the connect flow, and confirm the Para modal renders with the configured auth methods + Monad in the chain list.

## Rotate an API key

Use when: a key is leaked, or the user is rotating on schedule.

1. **Identify the key:**
   ```bash
   para keys list
   ```
2. **Rotate** (this disables the old key immediately):
   ```bash
   para keys rotate            # rotates the public key (most common)
   # or
   para keys rotate --secret   # rotates the secret key
   ```
3. **Update the frontend env file** in the same change so the app keeps working. Strip the old `*_PARA_API_KEY=` line and append the new value. Don't echo the value back to the user — confirm in plain English ("rotated and updated `web/.env.local`").
4. **Redeploy the frontend** so the new key takes effect in production.
5. **If the rotated key is also used by a backend / webhook handler**, rotate the secret separately and update those env vars too.

## Configure auth methods, branding, or webhooks via CLI

Use when: the user wants to change which login methods appear in the Para modal, or update colors/fonts, or wire a webhook to a backend, without leaving the terminal.

### Client-side vs key-side — what each controls

This trips people up. There are two separate surfaces for "auth method" configuration, and `para doctor` does not catch the wrong one:

| Where | What it controls | Examples |
|---|---|---|
| **Client-side** — `paraModalConfig` on `ParaProvider` (see step 7 above) | Which **IDP buttons** appear in the modal, phone-login visibility, recovery-step toggle, modal theming/layout | Hide social login: `oAuthMethods: []`. Hide phone: `disablePhoneLogin: true`. Hide only Twitter: drop `'TWITTER'` from the array. |
| **Key-side** — `para keys config security` | Which **second-factor methods** users can register (PASSKEY / PASSWORD / PIN), allowed origins, session length, IP allowlist, transaction popups | Force passkey-only: pick `PASSKEY` and uncheck the others. Add a CIDR to the IP allowlist. |

If the user says "hide social login" or "I only want email login" — that's **client-side**, edit `paraModalConfig`. The CLI cannot turn off IDP buttons. Conversely, if they want to disallow PINs as a second factor — that's **key-side**, edit via `para keys config security`.

1. **Inspect current config:**
   ```bash
   para keys config show              # all categories
   para keys config show security     # one category
   para keys config show --json       # scriptable
   ```
2. **Edit interactively or via flags.** The five categories are `security`, `branding`, `setup`, `ramps`, `webhooks` — see `para-cli.md` → "`para keys config`" for what each controls.
3. **For webhooks specifically:** after setting the endpoint URL and event subscription, send a test event before relying on it:
   ```bash
   para keys config webhooks test
   ```
   Confirm the backend received and verified the signature.
4. **For IP allowlisting (security category):** add the user's current IP *first*, then enable enforcement. Otherwise you lock them out of their own project. Ask them for their IP — don't guess. (See `para-cli.md` → "IP allowlist gotcha.")

## Debug a broken Para integration

Use when: the dev server runs but the Para modal won't open, env vars look right but `useAccount()` returns nothing, or auth completes but the wallet doesn't appear.

1. **Run `para doctor` first.** Most integration bugs are one of: missing `ParaProvider`, missing CSS import, missing `'use client'`, wrong env-var prefix for the framework, version skew across `@getpara/*` packages. `para doctor` catches all five.
   ```bash
   para doctor
   ```
   Quote each reported error back to the user — don't summarize them away.
2. **If `para doctor` is clean but the modal still won't open**, check the browser console for `Invalid API key` or origin errors:
   - Wrong env: beta key in a prod build (or vice versa). Check `para config get defaultEnvironment` and the env-var value source.
   - Origin not allowlisted: if you set `allowed origins` in `para keys config` security, the dev URL (`http://localhost:3000`) needs to be on the list.
3. **If auth completes but no wallet appears**, the network config is the usual culprit. Confirm the wagmi config includes Monad (or whichever chain) and the chain id matches what your contracts expect (10143 for Monad testnet, 143 for Monad mainnet — verify against `wagmi/chains` since these change rarely but do change).
4. **If you suspect a Para-side outage** (rare), check `para auth status` exit code — exit 2 means API/server error. Retry once; if it persists, tell the user.

## Switch environments (beta ↔ prod)

Use when: moving from local dev to a production launch.

1. **Set the environment locally** so it's pinned to this project:
   ```bash
   para config set --local defaultEnvironment prod
   ```
   This writes to `.pararc`. Commit it.
2. **Get a prod API key:**
   ```bash
   para keys create -n monad-app-prod --display-name "Monad App (prod)"
   ```
3. **Wire the prod key into the prod frontend env** (Vercel project settings, etc.) — never paste it into a committed `.env`. Different env vars per deploy environment.
4. **Run `para doctor` against the prod build** locally with `PARA_ENVIRONMENT=prod` to confirm nothing is mis-wired:
   ```bash
   PARA_ENVIRONMENT=prod para doctor
   ```
5. **Don't switch the global default to prod** unless the user explicitly asks — keep `prod` scoped to the project via `.pararc` so other Para projects on the same machine stay in `beta`.

## Archive / delete a Para project

Use when: the user explicitly says they want to remove a Para project.

1. **Confirm by name** before running. Say the project name and org back to them and wait for explicit yes.
2. **Archive** (reversible):
   ```bash
   para projects archive
   ```
3. **Restore** if they change their mind:
   ```bash
   para projects restore
   ```

There is no hard-delete from the CLI for projects — archive is the terminal action. For keys, `para keys archive` is the equivalent and is *not* reversible from the CLI.
