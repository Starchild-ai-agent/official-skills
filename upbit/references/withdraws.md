# Withdraws

Auth required for every command. Withdrawals move real funds — confirm currency,
network (`net_type`), address and amount with the user before running any
`create-*` command. Regional base URL rules from `setup.md` apply.

| Command | Purpose |
|---------|---------|
| `upbit withdraws retrieve-chance --currency <CODE> --net-type <NET>` | Check withdrawal availability, limits and fee for a currency/network |
| `upbit withdraws list-coin-addresses` | List registered (whitelisted) withdrawal addresses |
| `upbit withdraws list` | List withdrawal history |
| `upbit withdraws retrieve --uuid <UUID>` | Get one withdrawal by UUID |
| `upbit withdraws create-withdrawal --currency <CODE> --net-type <NET> --amount <AMT> --address <ADDR>` | Request a digital-asset withdrawal (address must already be registered) |
| `upbit withdraws create-krw-withdrawal --amount <AMT>` | Request a KRW withdrawal |
| `upbit withdraws cancel-withdrawal --uuid <UUID>` | Cancel a pending withdrawal |

Run `upbit withdraws <command> --help` for the authoritative option list; the
CLI mirrors the current Upbit REST parameters. Digital-asset withdrawals above
the regulatory threshold require Travel Rule fields — see `travel-rule.md`.
