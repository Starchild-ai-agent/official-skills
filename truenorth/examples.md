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

## Generic fallback

```bash
tn tools --filter <keyword>
tn call <toolName> --arg value --json
```
