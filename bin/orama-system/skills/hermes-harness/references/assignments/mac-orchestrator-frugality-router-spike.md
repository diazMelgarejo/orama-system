# P1 frugality_router.py spike — v1.1 plan reference

**Job:** Mac orchestrator (coord-007)  
**Branch:** `subagent/mac-orchestrator/frugality-router-spike` (Perpetua-Tools)  
**Status:** spike landed — 15 tests pass; operator PR review pending

## Canonical plan

`orama-system/docs/plans/2026-05-29-03-v1.1-definitive.md` §4, §7 week 2–3, §11

## What the spike implements

| Piece | Spec |
|-------|------|
| `orchestrator/frugality_router.py` | Single chokepoint for tool/model calls |
| `ToolCallSpec` / `ResolvedRoute` | Inputs/outputs per §6.1 extended plan |
| Tier 0–6 | Stop at first eligible; tier≥3 needs `escalation_reason` |
| `ORAMASYS_OFFLINE=1` | Reject tier ≥ 3 |
| `privacy_critical` | Forbid tier ≥ 4 |
| Trace | JSONL spans with `ot.tool.tier` |
| Tier 1 | Delegates to `backend_resolver` when registry provided |

## Not in spike (follow-on P1)

- `frugality-report` dashboard script (G1 telemetry)
- `tests/v1_1/test_realistic_session.py` (100-call ≥85% gate)
- Wire into all dispatch paths (supervisor, fastapi_app)
- Sub-skill pruning G2, MCP single-source G3

## Unblocks G1

After merge + integration: re-run `mac-g1-frugality-baseline.md` checklist.
