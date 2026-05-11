# Monitoring Agent Guide

## Method
1. **Baseline** — First run: record current values in memory
2. **Compare** — Subsequent runs: compare against baseline/thresholds
3. **Detect** — Flag deviations beyond expected ranges
4. **Trend** — After 3+ observations, note directional changes

## Severity
- **INFO** — Notable but not concerning → log to memory
- **WARNING** — Approaching threshold or unusual → log + report
- **ALERT** — Threshold breached or anomaly → log + highlight + recommend action

## Output Format
```
### Status: OK | WARNING | ALERT
**Checked:** [targets]
**Findings:** [observations]
**Anomalies:** [unusual or "None"]
**Action Required:** [recommendation or "None"]
```

## Thresholds
- Store in memory for consistency across runs
- When breached, report: threshold, actual value, delta, direction
- If none defined, set reasonable defaults and document them

## Trends (3+ observations)
Look for: consistent direction, increasing volatility, cyclical patterns, sudden shifts
