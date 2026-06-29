# Mac G1 frugality baseline — partial (post #199)

**Date:** 2026-06-29  
**Host:** mac (OpenClaw)  
**PT `main`:** `frugality_router.py` merged (#199)

## Tests (Mac)

| Suite | Result |
|-------|--------|
| `tests/test_frugality_router.py` | **15/15** |
| `tests/test_autoresearch_bridge.py` | **38/38** |
| Combined | **53/53** |

## Still missing for G1 ratio

| Artifact | Status |
|----------|--------|
| `frugality-report` script | not on `main` |
| `tests/v1_1/test_realistic_session.py` | not on `main` |
| `.state/traces/*.jsonl` | absent |

**G1 tier≤2 ratio:** still **not measurable** — harness + trace sink gap remains.

## Next

Land `frugality-report` + session harness, or Win `win-g1-frugality-win-baseline.md` drop when traces exist.
