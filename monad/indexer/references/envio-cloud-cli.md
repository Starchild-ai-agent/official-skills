# envio-cloud — behavioral notes

CLI syntax is available via `envio-cloud --help` and `envio-cloud <command> --help`. This file covers what `--help` doesn't: guardrails, gotchas, and context for how the CLI fits into the broader workflow.

Source of truth for the CLI itself: https://docs.envio.dev/docs/HyperIndex/envio-cloud-cli

## Install and auth — never do these for the user

- **Don't install the CLI for the user.** The command is `npm install -g envio-cloud` (or `npx envio-cloud <command>` to run without installing) — tell them, don't run it.
- **`envio-cloud` requires `gh` (GitHub CLI)** to be installed and authenticated, since Envio Cloud deploys from GitHub. If `gh` is missing or not authenticated, tell the user to install it (`brew install gh` on macOS) and run `gh auth login` themselves — both require browser interaction.
- **Don't run `envio-cloud login` for the user.** It opens a browser tab on envio.dev and only the user can complete it. Sessions last 30 days.
- **`envio-cloud token` is the canonical session check.** Exit 0 = valid session. The monskills hook gates `envio-cloud` commands on this; use it whenever you need to know if the user is authenticated.

## GraphQL endpoint — what the frontend talks to

`envio-cloud deployment endpoint <indexer> <commit> <org>` prints the URL the frontend queries. **The indexer is useless to the frontend until this URL is wired in.** After a healthy deployment, resolve this URL and write it to the frontend's env file (typically `web/.env.local` as `NEXT_PUBLIC_INDEXER_URL`) — don't hand the URL back to the user to paste themselves. See `envio-cloud-workflows.md` for the full wiring recipe.

Gotchas:
- **Use the URL exactly as printed.** Don't rewrite it, add a trailing slash, or strip query parts.
- **`--cluster` override is rare.** Only pass it if the user explicitly asked for a non-default cluster. Valid values: `hyper`, `hypertierchicago`, `ip-projects`, `prodaws`, `staging`.
- **`-q` suppresses informational messages** — use it when capturing the URL into a shell variable.
- **You can only resolve endpoints for orgs you are a member of** (exit 1 otherwise).
- The URL is computed locally from deployment parameters; only the cluster is resolved via the API. Fast, but still requires authentication.

Frontend wiring (Next.js + `fetch`) — adapt the env var name for non-Next.js stacks (`VITE_INDEXER_URL` for Vite, etc.):

```ts
// web/.env.local
// NEXT_PUBLIC_INDEXER_URL=<URL printed by `envio-cloud deployment endpoint`>

// web/lib/indexer.ts
export async function query<T>(gql: string, variables?: Record<string, unknown>): Promise<T> {
  const res = await fetch(process.env.NEXT_PUBLIC_INDEXER_URL!, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: gql, variables }),
  });
  const { data, errors } = await res.json();
  if (errors) throw new Error(errors[0]?.message ?? 'GraphQL error');
  return data as T;
}
```

Query shape comes from `indexer/schema.graphql` — whatever entities the handlers write, the frontend can read by the same names. Don't reach for Apollo/urql unless the user asks; `fetch` is enough.

## Environment variables

- **Never echo secret values back to the user.** If you read env vars via `envio-cloud indexer env list`, don't include the values in your response.
- **Setting an env var does not restart running deployments.** Follow up with `envio-cloud deployment restart <indexer> <commit>` if the change needs to take effect on an active deployment.

## IP allowlist — order matters

Enabling the allowlist without adding the user's current IP first will lock them out of their own indexer's API. Always:

1. Add the user's current IP via `envio-cloud indexer security add-ip <ip>`
2. *Then* enable via `envio-cloud indexer security enable`

Ask the user for their IP — don't assume.

## Indexer deletion is irreversible

`envio-cloud indexer delete <name> <org>` cannot be undone. Confirm by name with the user before running it. Don't add retry logic around it.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | User error (bad args, not logged in, unknown indexer) |
| `2` | API/server error |

Don't rely on stdout content alone — check the exit code.