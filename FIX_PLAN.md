# 🔧 Issue Fix Plan — 6 Real Problems from Live Testing

## Priority Order (fix sequence)

| ID | Severity | Issue | Fix Type |
|----|----------|-------|----------|
| FIX-1 | 🔴 CRITICAL | Liquidation data returns 0 for long/short splits | Wrapper: fallback calculation |
| FIX-2 | 🔴 CRITICAL | `liquidation_analysis` says "shorts dominate" with 0 data | Wrapper: guard logic |
| FIX-3 | 🟡 HIGH | Invalid coin → "Check API KEY" misleading error | Wrapper: error reclassification |
| FIX-4 | 🟡 HIGH | Tool outputs 25K-400K chars, small models choke | Wrapper: response truncation |
| FIX-5 | 🟡 MEDIUM | 3 toolsets have different error formats | Normalizer middleware |
| FIX-6 | 🟢 LOW | Funding rate format inconsistency across exchanges | Normalizer |

## Approach
Each fix → Python middleware in `patches/live/` that wraps the native Starchild tool.
We test by calling the REAL tool, then running our wrapper, comparing outputs.

## Acceptance Criteria
- Each fix must pass 2 consecutive live runs
- Zero mock data
- All results logged to test_results.log
