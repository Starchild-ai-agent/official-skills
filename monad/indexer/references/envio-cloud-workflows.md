# Envio Cloud — workflow recipes

Opinionated sequences for common indexer tasks. Each recipe assumes the user is already logged in (`envio-cloud token` exit 0).

## First deploy

Use when: the user wants to take a local HyperIndex project and put it on Envio Cloud for the first time.

1. **Confirm the repo is pushed to GitHub.** Envio Cloud deploys from GitHub, not from local files. If the project is local-only, stop and ask the user to push it first.
2. **Set the org context (once):**
   ```bash
   envio-cloud config set-org <org>
   ```
   Ask the user for their org slug if you don't know it. Don't guess.
3. **Register the indexer:**
   ```bash
   envio-cloud indexer add --name <name> --repo <owner/repo>
   ```
   The `--repo` argument is `owner/repo`, not a full URL.
4. **Wait for the deployment to build.** The add command returns a commit SHA. Poll with:
   ```bash
   envio-cloud deployment status <name> <commit>
   ```
   Don't busy-loop — wait at least 5s between polls. If it stays pending for >5 minutes, check logs.
5. **Wait for the initial build to finish, then push an empty commit to guarantee the indexer starts.** Envio Cloud has a quirk where `indexer add` sometimes creates the deployment but never starts the indexer — the deployment looks "deployed" in status but the indexer never advances past `startBlock`. Empirically, pushing an empty commit *after the first build completes* always kicks off a fresh build that does start the indexer. Do this unconditionally rather than gating on a stuck-detection check — it costs one extra build but removes the failure mode entirely.

   First, wait for the initial deployment to finish building (don't push the empty commit while the first build is still in progress, or you'll race it):
   ```bash
   envio-cloud deployment status <name> <commit>
   ```
   Once the build is complete, push the empty commit from the indexer repo:
   ```bash
   (cd indexer && git commit --allow-empty -m "trigger envio-cloud rebuild" && git push)
   ```
   Envio Cloud auto-picks up the new commit and supersedes the previous deployment. Grab the new SHA and use it for the rest of this recipe:
   ```bash
   NEW_COMMIT=$(cd indexer && git rev-parse --short HEAD)
   ```

   Then verify the new deployment is actually indexing. The authoritative check is the indexer's own `_meta` (one entry per chain), not the control-plane metrics. Resolve the endpoint and query:
   ```bash
   INDEXER_URL=$(envio-cloud deployment endpoint <name> "$NEW_COMMIT" <org> -q)
   curl -sf "$INDEXER_URL" \
     -H 'Content-Type: application/json' \
     -d '{"query": "{ _meta { chainId startBlock progressBlock sourceBlock isReady readyAt eventsProcessed } }"}' \
     | jq '.data._meta'
   ```
   Interpret the result:
   - **Healthy:** `isReady: true`, `readyAt` has a timestamp, and `progressBlock` is at or approaching `sourceBlock` (which is the indexer's own view of the chain tip — use it in-band instead of a separate RPC call). Gap between `progressBlock` and `sourceBlock` = still syncing historical blocks; it will close over time.
   - **Do NOT treat `eventsProcessed: 0` as stuck.** A contract that has emitted no events since `startBlock` will sit at zero forever while the indexer is perfectly healthy.

   Do this transparently — the user shouldn't have to know about the empty-commit workaround.
6. **Promote to production when indexing is actually progressing:**
   ```bash
   envio-cloud deployment promote <name> "$NEW_COMMIT"
   ```
   Use the post-empty-commit SHA (`$NEW_COMMIT` from step 5) — that's the deployment that's actually indexing. Only promote after confirming the indexer is syncing and returning data as expected.
7. **Wire the GraphQL URL into the frontend automatically** (see "Get the GraphQL endpoint URL" recipe below). If the project has a frontend (e.g. `web/`), resolve the endpoint and write it to `web/.env.local` as `NEXT_PUBLIC_INDEXER_URL` without handing a URL back to the user to paste themselves.
8. **Report the indexer name and promoted commit** to the user so they can reference it later.

## Deployment exists but never started indexing

Use when: `deployment status` looks healthy/deployed but the indexer's `_meta` shows `isReady: false`, `readyAt: null`, and `progressBlock == startBlock`. This is a known Envio Cloud quirk — the deployment was created but the indexer process never actually kicked off. It's distinct from a failing deploy (which shows error status in `deployment status` / stack traces in `logs`) and from slow syncing (which has `progressBlock` increasing toward `sourceBlock`).

Fix it by pushing an empty commit to the indexer repo so Envio Cloud triggers a fresh build:

1. **Confirm the symptom first** — don't do this for a deploy that's actually progressing. Query the indexer's own `_meta` (this is what the frontend will see, so it's the authoritative signal):
   ```bash
   INDEXER_URL=$(envio-cloud deployment endpoint <indexer> <commit> <org> -q)
   curl -sf "$INDEXER_URL" \
     -H 'Content-Type: application/json' \
     -d '{"query": "{ _meta { startBlock progressBlock sourceBlock isReady readyAt } }"}' \
     | jq '.data._meta'
   ```
   The quirk signature is `progressBlock == startBlock`, `isReady: false`, `readyAt: null`, holding for minutes. Do not use `eventsProcessed: 0` as the signal — that can be legitimate for a contract with no events since `startBlock`. `deployment metrics <indexer> <commit>` is a softer cross-check from the control plane.
2. **Push an empty commit from the indexer repo:**
   ```bash
   (cd indexer && git commit --allow-empty -m "trigger envio-cloud rebuild" && git push)
   ```
   Envio Cloud watches the repo and auto-deploys the new commit. The previous commit's deployment is superseded.
3. **Poll the new deployment until indexing starts:**
   ```bash
   NEW_COMMIT=$(cd indexer && git rev-parse --short HEAD)
   envio-cloud deployment status <indexer> "$NEW_COMMIT" --watch-till-synced
   ```
   `--watch-till-synced` streams status until all chains are 100% synced. Safe to use here because you already verified the indexer is now actually running (non-zero metrics); it would hang if the indexer were still stuck.
4. **Re-promote** if the stuck deployment had been promoted (otherwise the promoted URL still points at the broken deployment):
   ```bash
   envio-cloud deployment promote <indexer> "$NEW_COMMIT"
   ```
5. **Re-resolve and re-wire the endpoint URL** (see the GraphQL endpoint recipe). Commit SHA changed, so the URL may have changed — update `NEXT_PUBLIC_INDEXER_URL` in the frontend env file.
6. **Do this transparently.** The user doesn't need to know about the envio-cloud quirk — just report "indexer is now syncing" once it's unstuck.

## Debug a failing deploy

Use when: `deployment status` shows `failed`, `errored`, or the indexer is stuck syncing.

1. **Read the logs first:**
   ```bash
   envio-cloud deployment logs <indexer> <commit>
   ```
   Quote the relevant error back to the user — don't summarize away the details.
2. **Check metrics for sync lag:**
   ```bash
   envio-cloud deployment metrics <indexer> <commit>
   ```
   Persistent lag with no errors usually means underpowered resources or an RPC-side bottleneck, not a code bug.
3. **Common causes, in order of likelihood:**
   - Missing or wrong env var — check with `envio-cloud indexer env list`.
   - Schema/handler mismatch that the CI build did not catch.
   - RPC endpoint rate-limited or wrong chain.
4. **If you fix code**, the user pushes a new commit to GitHub, then re-deploy by running `indexer add` is **not** needed — the cloud should pick up the new commit automatically. Check with `deployment status <indexer> <new-commit>`.
5. **If you only changed env vars**, restart the current deployment:
   ```bash
   envio-cloud deployment restart <indexer> <commit>
   ```

## Rotate env vars

Use when: the user rotated an API key, RPC URL, or database credential and needs the indexer to pick up the new value.

1. **Set the new value:**
   ```bash
   envio-cloud indexer env set <KEY> <new-value>
   ```
   Ask the user to paste the value directly into their terminal — do not ask them to send it to you.
2. **Restart the deployment** so the new value is loaded:
   ```bash
   envio-cloud deployment restart <indexer> <commit>
   ```
3. **Verify it's running** by tailing logs for a few seconds.
4. **Never print the new value back** to the user. A generic "updated" confirmation is fine.

## Allowlist an IP

Use when: the user wants to restrict the indexer's API to specific IPs (e.g. their backend servers).

1. **Add the user's current IP first** so enabling the allowlist doesn't lock them out:
   ```bash
   envio-cloud indexer security add-ip <user-ip>
   ```
   Ask the user for their IP — don't assume.
2. **Add any additional IPs or CIDRs** they want allowlisted.
3. **Enable the allowlist:**
   ```bash
   envio-cloud indexer security enable
   ```
4. **Confirm the current state:**
   ```bash
   envio-cloud indexer security get
   ```

## Get the GraphQL endpoint URL (and wire it into the frontend)

Use when: an indexer has been deployed for this project and the frontend needs to read its data. Do this automatically as the final step of the indexer flow — don't hand the URL back to the user and wait for them to paste it somewhere. If there's a frontend in the project, Claude is responsible for completing the wiring.

1. **Gather the identifiers from context.** You already know the indexer name, the promoted commit SHA (from `deployment status` / `deployment promote`), and the org (from `config get-context` or earlier steps). If any are missing, resolve them before continuing — don't ask the user for things you can derive.
2. **Resolve the URL:**
   ```bash
   INDEXER_URL=$(envio-cloud deployment endpoint <indexer> <commit> <org> -q)
   ```
   The command prints just the URL, so capture it directly into a shell variable.
3. **Query `_meta` before writing the URL anywhere.** `_meta` is the indexer's self-reported state (one entry per chain) and tells you both whether the endpoint is live and whether indexing is actually progressing:
   ```bash
   curl -sf "$INDEXER_URL" \
     -H 'Content-Type: application/json' \
     -d '{"query": "{ _meta { chainId startBlock progressBlock sourceBlock isReady readyAt eventsProcessed } }"}' \
     | jq '.data._meta'
   ```
   - If `curl` exits non-zero, the endpoint isn't serving yet — do NOT wire it in. Check `deployment status` / `deployment logs` first.
   - If it responds but `isReady: false`, `readyAt: null`, and `progressBlock == startBlock`, the indexer is stuck — jump to the "Deployment exists but never started indexing" recipe before wiring.
   - Only wire the URL into the frontend once `isReady: true` and `progressBlock` is advancing (at or approaching `sourceBlock`, the indexer's view of the chain tip). `eventsProcessed: 0` is fine if the contract has emitted nothing since `startBlock`.

   Wiring a dead or stuck URL into the frontend leaves the user debugging the app when the root cause is the indexer.
4. **Write it into the frontend env automatically.** Find the frontend dir (typically `web/`) and add `NEXT_PUBLIC_INDEXER_URL` to its `.env.local`. Append if the file exists, create if it doesn't, and overwrite any existing `NEXT_PUBLIC_INDEXER_URL` line rather than duplicating:
   ```bash
   ENV_FILE=web/.env.local
   touch "$ENV_FILE"
   # Remove any previous entry, then append the fresh one
   grep -v '^NEXT_PUBLIC_INDEXER_URL=' "$ENV_FILE" > "$ENV_FILE.tmp" && mv "$ENV_FILE.tmp" "$ENV_FILE"
   echo "NEXT_PUBLIC_INDEXER_URL=$INDEXER_URL" >> "$ENV_FILE"
   ```
   Adjust the path if the frontend lives somewhere other than `web/`. For non-Next.js stacks, use the framework's convention (`VITE_INDEXER_URL` for Vite, etc.).
5. **Add a minimal GraphQL client** if the frontend doesn't already have one. A plain `fetch` wrapper is enough — don't add Apollo/urql unless the user asked for them:
   ```ts
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
   Query shape comes from `indexer/schema.graphql` — whatever entities the handlers write, the frontend can read by the same names.
6. **Confirm to the user what you did** — which env var was written, which file it lives in, and the test-query result — rather than dumping the raw URL for them to act on. Example: "Wired `NEXT_PUBLIC_INDEXER_URL` into `web/.env.local` and verified the indexer is returning block 1,234,567. Restart the Next.js dev server to pick up the new env var."
7. **Cluster override is rare** — only pass `--cluster` to `deployment endpoint` if the user explicitly asked for a non-default cluster.

## Delete an indexer

Use when: the user explicitly says they want to remove an indexer.

1. **Confirm with the user by name** before running delete. Say the indexer name and org back to them and wait for explicit yes.
2. **Run delete:**
   ```bash
   envio-cloud indexer delete <name> <org>
   ```
3. This is irreversible. Don't add retry logic around it.