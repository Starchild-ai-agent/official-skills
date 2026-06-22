# Upbit CLI Setup

Guide the user through installing the Upbit CLI and configuring API credentials.

## Step 0 — Select Environment

Detect the user's language:

- **Korean**: assume `kr` environment. Do not ask — proceed directly with KR defaults. Omit `--environment` flag from all commands (KR is the CLI default).
- **Other language**: ask which environment they are using before proceeding:
  > "Which environment are you using?"
  > - `kr` — Korea (https://www.upbit.com)
  > - `sg` — Singapore (https://sg.upbit.com)
  > - `id` — Indonesia (https://id.upbit.com)
  > - `th` — Thailand (https://th.upbit.com)

Store the selected environment and use it throughout all subsequent steps — in API key management URLs, verification commands, and examples.

Environment reference table:

| Value | Base URL | API Key Management |
|---|---|---|
| `kr` | https://www.upbit.com | https://www.upbit.com/mypage/open_api_management |
| `sg` | https://sg.upbit.com | https://sg.upbit.com/mypage/open_api_management |
| `id` | https://id.upbit.com | https://id.upbit.com/mypage/open_api_management |
| `th` | https://th.upbit.com | https://th.upbit.com/mypage/open_api_management |

---

## Step 1 — Prerequisites

Check Node.js availability:

```bash
node --version
```

Requires Node.js 18 or later. If not installed, direct the user to https://nodejs.org.

---

## Step 2 — Install upbit CLI

```bash
npm install -g @upbit-official/upbit-cli
```

After installation, verify:

```bash
upbit --version
```

If `upbit` is not found after installation, the user may need to update their PATH. Common fixes:

- **macOS/Linux (npm global bin not in PATH)**:
  ```bash
  export PATH="$(npm bin -g):$PATH"
  ```
  Add to `~/.zshrc` or `~/.bashrc` to persist.

- **Windows**: Restart the terminal or check `npm config get prefix` and add the `\bin` subdirectory to the system PATH.

---

## Step 3 — Check Current IP Address

Upbit API keys can be restricted to specific IP addresses. Before the user creates their API key, retrieve and display their current public IP:

```bash
curl -s https://api.ipify.org
```

Show the result to the user and advise them to add this IP when configuring allowed IPs on the API management page.

> If the user is on a dynamic IP or plans to use the CLI from multiple machines, they may want to add multiple IPs or leave the IP restriction empty (less secure).

---

## Step 4 — Get API Keys

Direct the user to the API key management page for their selected environment (from Step 0).

Required permissions for full CLI functionality:

| Permission | Required for |
|---|---|
| 자산 조회 (Asset inquiry) | `accounts list`, `api-keys list` |
| 주문 조회 (Order inquiry) | `orders list-open`, `orders list-closed` |
| 주문하기 (Place orders) | `orders create`, `orders cancel` |
| 출금하기 (Withdraw) | `withdraws create-withdrawal`, `withdraws create-krw-withdrawal` |
| 입금 주소 발급 (Deposit address) | `deposits create-coin-address` |

Public endpoints (`tickers`, `orderbooks`, `candles`, etc.) do not require API keys.

---

## Step 5 — Configure Credentials

`upbit config set` requires an interactive terminal (TTY) — it cannot be run by Claude or via the `!` prefix in Claude Code. The user must run it directly in a separate terminal.

Instruct the user to:
1. Open a new terminal window
2. Run:
   ```bash
   upbit config set
   ```
3. Enter the Access Key and Secret Key when prompted
4. Return here when done

Credentials are saved to `~/.upbit/config` and automatically used for all subsequent CLI commands.

---

## Step 6 — Verify Setup

After `upbit config set` completes, verify credentials are saved correctly:

```bash
upbit config show
```

Expected output:
```
access_key:  xxxx****xxxx  (source: file)
secret_key:  xxxx****xxxx  (source: file)
config_file: ~/.upbit/config
```

Then test with a live API call:

- **KR**: `upbit accounts list`
- **Other**: `upbit accounts list --environment <selected-environment>`

A successful response returns the user's asset balances. An authentication error means the keys were entered incorrectly — run `upbit config set` again.

---

## Credential Priority

The CLI resolves credentials in this order (highest priority first):

1. CLI flags: `--access-key`, `--secret-key`
2. Environment variables: `UPBIT_ACCESS_KEY`, `UPBIT_SECRET_KEY`
3. Config file: `~/.upbit/config` (set via `upbit config set`)

To check the active credential source:

```bash
upbit config show
```

To check the config file path:

```bash
upbit config path
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `upbit: command not found` | `npm install -g @upbit-official/upbit-cli` and check PATH |
| `401 Unauthorized` | Re-run `upbit config set` with correct keys |
| `403 Forbidden` | API key lacks required permissions — update on the API management page |
| `No credentials configured` | Run `upbit config set` to save credentials |
| Keys set but not picked up | Check `upbit config show` — env vars override config file |
