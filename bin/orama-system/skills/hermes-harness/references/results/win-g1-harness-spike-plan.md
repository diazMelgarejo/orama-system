# G1 frugality harness — spike plan (ingredients only)

**Date:** 2026-06-29  
**Fan-out:** coord-017  
**Blocked by:** none (parallel to P5)

## Goal

Make G1 tier≤2 ratio **measurable** per v1.1 §11 (≥85% local-first).

## Spike deliverables (future PR)

| # | Artifact | Location | Notes |
|---|----------|----------|-------|
| 1 | `frugality-report` | `bin/orama-system/skills/code-review/scripts/frugality-report` | `--dry-run`, `--last 1h`; reads `.state/traces/*.jsonl` |
| 2 | `test_realistic_session.py` | `tests/v1_1/test_realistic_session.py` | 100-call session sim; asserts tier distribution |
| 3 | OTel tier spans | PT `frugality_router` integration | `ot.tool.tier` on dispatch |

## v1 scope guard

- No Redis
- File-based traces under `~/.openclaw/state/traces/` or PT `.state/traces/`
- Win + Mac both run report after traces exist

## Sequencing

```text
P5 (parallel)  |  G1 harness spike  →  measure ratio  →  tune router
```

**Do not implement until operator approves spike PR scope.**
