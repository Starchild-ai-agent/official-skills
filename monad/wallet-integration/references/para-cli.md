# para CLI — behavioral notes

Full syntax is available via `para --help` and `para <command> --help`. This file covers what `--help` doesn't: guardrails, gotchas, and how the CLI fits into the broader Para integration workflow.

Source of truth for the CLI itself: https://docs.getpara.com/v2/cli/commands

## Install and auth — never do these for the user

- **Don't install the CLI for the user.** The command is `npm install -g @getpara/cli` (or `pnpm add -g @getpara/cli`, or `npx @getpara/cli@latest <command>` to run without installing) — tell them, don't run it.
- **Don't run `para login` for the user.** It opens a browser tab for OAuth (with PKCE) and only the user can complete it. Credentials land in `~/.config/para/credentials.json` (file mode 0600). For headless setups there's `para login --no-browser`, but monskills is for interactive use — surface the command and wait.
- **`para auth status` is the canonical session check.** Exit 0 = valid session. Use this — not `para whoami` — when you need a programmatic yes/no on auth, since `whoami` reads local context and `auth status` round-trips to the server. The monskills hook gates `para` commands on `auth status`.
- **`para whoami` is for showing the user their current context** (org, project, environment, expiration). Use it when the user asks "who am I logged in as" or before a destructive operation so they can confirm the active context.

## Configuration resolution order

Para resolves config in this priority (highest first):

1. CLI flags (`--project-id`, `--env`, etc.)
2. Environment variables (`PARA_ENVIRONMENT`, `PARA_ORG_ID`, `PARA_PROJECT_ID`)
3. Project config (`.pararc` in the current directory)
4. Global config (`~/.config/para/config.json`)
5. Built-in defaults

When a command operates on "the active project," it's resolved through this chain. If the user runs `para` in a directory with a `.pararc`, that pin wins over their global default — handy for monorepos with multiple Para projects, but easy to confuse if they didn't realize they were `cd`'d into one.

`para config get` shows the resolved value plus where it came from. Use it when behaviour doesn't match expectations.

## `para init` — pin the project for the team

```bash
para init                # interactive
para init --no-input     # non-interactive (use this in any sandboxed/headless env)
para init --force        # overwrite an existing .pararc
```

Creates `.pararc` in the current directory pinning org + project + environment. Commit this — it's how teammates land on the same Para context without manually switching. No secrets in it.

**Headless / sandboxed terminals — use `--no-input`.** Without a real TTY, `para init` aborts with `TTY initialization failed: uv_tty_init returned EINVAL`. This hits Codespaces, most CI runners, and any agent that wraps the shell without forwarding a PTY. `--no-input` skips the interactive prompts and uses the active org / project / environment from global config — set those first via `para projects switch` and `para config set defaultEnvironment <beta|prod>` if they aren't already pinned.

If the user already has a `.pararc` in a parent directory and you run `para init` in a subdir, you'll get two pinned configs. The closer one wins. Avoid this — do `para init` once, at the same level as the frontend's `package.json`.

## `para create` is intentionally out of scope

This skill never scaffolds a fresh app. Project scaffolding is owned by the `scaffold/` skill, which produces the Next.js frontend you integrate Para into. Don't run `para create` — it would generate a parallel app and confuse the workflow. If the user asks for a fresh scaffold, redirect them to the `scaffold/` skill and come back here to wire Para into what it produces.

## `para doctor` — diagnostics, run after every wiring change

```bash
para doctor                    # human-readable
para doctor --json             # machine-readable, exits 1 on errors (CI-friendly)
para doctor --category setup   # only one bucket
para doctor --severity error   # only blocking issues
```

Categories: `configuration`, `dependencies`, `setup`, `best-practices`. Severities: `error`, `warning`, `info`.

What it checks:

- API key env var present and prefixed correctly (`NEXT_PUBLIC_` for Next.js, `VITE_` for Vite).
- Para CSS import present.
- `ParaProvider` wraps the app.
- `QueryClient` is set up (Para's React hooks need React Query).
- `"use client"` directive on Next.js components that use Para hooks.
- All `@getpara/*` packages on the same minor version.
- Required chain packages installed (e.g. `viem`, `wagmi` for EVM).
- No deprecated `@getpara/*` packages still imported.

Run `para doctor` after every Para integration step and after every dependency upgrade. With `--json` it's safe to call from a script — exit 1 means there's something to fix.

## API key management

- `para keys list` — list keys with masked values.
- `para keys get` — defaults to the active project's active-environment key. `--show-secret` prints the secret; `--copy-secret` copies it. **Never echo a value with `--show-secret` back into your response.**
- `para keys create -n <internal-name> --display-name <user-facing-name>` — new key in the active project.
- `para keys rotate` — rotates the public key by default. `--secret` rotates the secret instead. Old key is disabled immediately, so update the frontend env var in the same change.
- `para keys archive` — revokes a key. Irreversible from the CLI side; user must un-archive via the dashboard.

After rotating or archiving, update the frontend env file and redeploy. Don't print the new value back at the user — write it to the env file yourself and confirm "rotated and updated `.env.local`."

## `para keys config` — security, branding, ramps, webhooks

`para keys config show [category]` displays current settings. `--json` returns scriptable output. The five categories:

| Category | What it controls |
|---|---|
| `security` | **Second-factor methods** (PASSKEY/PASSWORD/PIN), allowed origins, session length (5–43200 minutes), transaction popups, IP allowlist (CIDR blocks) |
| `branding` | Foreground/background/accent colors, fonts, social URLs, welcome/backup-kit emails |
| `setup` | Wallet types, Cosmos prefix, Apple Team ID, iOS bundle ID, Android package + fingerprints |
| `ramps` | Buy/receive/withdraw toggles, provider ordering (RAMP/STRIPE/MOONPAY), default amounts |
| `webhooks` | Endpoint URL, event subscription, on/off toggle, test send, secret rotation |

Most of these can also be edited via the developer portal — use whichever the user prefers. The CLI is faster for repeated edits or scripted setups.

**`security` does not control which IDP buttons appear in the modal.** `PASSKEY/PASSWORD/PIN` here are the *second-factor* methods Para offers users for recovery — not the OAuth provider buttons (Google, Apple, Twitter, etc.) on the login screen. To hide social login or phone login, edit `paraModalConfig` on the `ParaProvider` (client-side); see `para-workflows.md` → "Client-side vs key-side — what each controls."

### IP allowlist gotcha

Adding an IP allowlist to a Para project's `security` config without including the user's own IP first will lock them (and their app's deployed origin) out. The CLI doesn't ship a "current IP" detection — the user provides it. Order:

1. Resolve the user's current IP (ask them or have them run `curl -s https://api.ipify.org`).
2. Add it to the allowlist via `para keys config` (security category).
3. Add any backend / serverless IPs.
4. Only then enable enforcement.

## Org / project switching

- `para orgs list` / `para orgs switch [<id>]` — interactive selector if no id.
- `para projects list` / `para projects switch [<id>]` — same.
- `para projects create -n <name> --framework nextjs|vite|react-native|...` — create from CLI without the dashboard.
- `para projects archive` is reversible via `para projects restore`. `para keys archive` is *not* reversible from the CLI.

## Environments: beta vs prod

Para has two environments: `beta` (default, for development/testing) and `prod`. They have separate API keys. Switch with `para config set defaultEnvironment <beta|prod>` (global) or `para config set --local defaultEnvironment <env>` (writes to `.pararc`).

Use `beta` for local dev and PR previews; only switch to `prod` once auth methods, branding, and webhooks have been tested in beta. Mixing beta and prod keys (e.g. beta key in production frontend) silently routes users to the wrong project — `para doctor` does not catch this; you have to verify.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | User error (bad args, not logged in, unknown project, `para doctor --json` found errors) |
| `2` | API/server error |

Don't rely on stdout content alone — check the exit code. `para doctor --json` exiting 1 is *correct* behaviour when issues exist; it means the diagnostic ran successfully and found problems.
