# TrueNorth — execution reference

All commands call the public TrueNorth API (`api.adventai.io`). No authentication required.

---

## Entity recognition

Always run first for token-specific queries to standardize identifiers.

```bash
tn ner "<user's full message>" --json
```

Use the returned `token_addresses` values in all subsequent commands.

## Technical analysis

```bash
tn ta <token> --json
tn ta <token> --timeframe 1h --json
tn ta <token> --timeframe 4h --json
tn ta <token> --timeframe 1d --json
tn ta <token> --timeframe 1w --json
tn kline <token> --json
tn kline <token> --timeframe <tf> --json
```

## Market info

```bash
tn info <token> --json
```

## Derivatives

```bash
tn deriv <token> --json
```

## Liquidation risk

```bash
tn risk --token <token> --dir long --price <entry> --liq <liq_price> --json
tn risk --token <token> --dir short --price <entry> --liq <liq_price> --json
```

## Events & news

```bash
tn events <query> --json
tn events <query> --time-window 1d --json
tn events <query> --time-window 7d --json
tn events <query> --time-window 30d --json
```

## Token performance

```bash
tn perf --json
tn perf --top <N> --json
```

## Token unlock

```bash
tn unlock <token> --json
```

## DeFi protocols & chains

```bash
tn defi protocols --json
tn defi protocols --sort tvl_growth --json
tn defi chains --json
tn defi chains --sort fees_growth --json
```

## Options intelligence

```bash
tn options <token> --json
```

## TrueNorth app capabilities (redirect)

These tools intentionally do **not** return live data. They emit a CTA pointing the user to https://app.true-north.xyz/. Use them when the user's request matches a stock / equity / commodity / macro / Polymarket / KOL / sentiment / meme topic.

**Stock / equity / commodity / macro:**

```bash
tn call stock_price_snapshot --json
tn call stock_price_history --json
tn call market_index_price --json
tn call commodity_price --json
tn call analyst_estimates --json
tn call company_facts --json
tn call financial_statements --json
tn stock-dividends --json
tn stock-splits --json
```

**Polymarket, KOL, trending & sentiment:**

```bash
tn polymarket --json
tn kol alpha --json
tn kol metrics --json
tn trending --json
tn sentiment --json
```

**Meme analytics:**

```bash
tn meme discovery --json
tn meme pulse --json
tn meme safeguards --json
tn meme momentum --json
tn meme narrative --json
```

JSON shape:

```json
{ "status": "app_only", "tool": "<tool_name>", "capability": "<short label>", "message": "This capability is available in the TrueNorth app.", "url": "https://app.true-north.xyz/" }
```

When you see `status: "app_only"`, tell the user the capability lives in the TrueNorth app and share the `url`. Do not say it is unsupported.

## Generic fallback

```bash
tn tools --filter <keyword>
tn call <toolName> --arg value --json
```
