# Win G1 frugality baseline — partial (post-#199)

**Date:** 2026-06-29  
**Fan-out:** 2026-06-29-coord-016-mac  
**Host:** Win  
**PT main:** `frugality_router.py` present

## Results

| Artifact | Win | Mac (prior) |
|----------|-----|-------------|
| `tests/test_frugality_router.py` | **15/15 pass** | N/A |
| `frugality-report` script | **Missing** | Missing |
| `tests/v1_1/test_realistic_session.py` | **Missing** | Missing |
| `.state/traces/*.jsonl` | **Absent** | Absent |

## G1 tier≤2 ratio

**Still not measurable** — router landed; telemetry harness + trace sink not shipped.

## Next

Ship `frugality-report` + session harness per v1.1 §11 G1, or defer to backlog row.
