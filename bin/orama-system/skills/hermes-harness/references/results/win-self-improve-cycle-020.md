# Win self-improve cycle 020 — both repos on main

**Date:** 2026-06-29  
**Fan-out:** coord-020

## Branch switch

| Repo | Was | Now |
|------|-----|-----|
| **Perpetua-Tools** | `main` | `main` (already) |
| **orama-system** | `cursor/security-pr3-swarm-approval-f559` | **`main`** (`f476a65`) |

P5 implementation stays on feature branch until PR #136 merges; operator work on `main` uses planning docs only.

## Pulled from Mac on orama main

- `coord_triple_rinse.sh` — outer loop: pulse jobs → learn/dream/push → 3×15m listen
- `mac-coord-023-queue-ack.md` — 18 inbox items reconciled
- `docs/v2/43-gossipbus-mesh-transport.md`
- `P5-STATUS.md` updated (T1–T2 on branch, T3–T7 pending)

## Queue (Win)

- **coder** 10 done / 0 pending · **autoresearcher** 4 done / 0 pending
- Mac still has `mac-orchestrator-self-improve-003` + researcher backlog

## Operator

1. Default both repos to `main` for coord rinse; feature branches for P5 implementation only
2. Use `coord_triple_rinse.sh` on Mac; Win mirrors with pulse×3 + learn + push per rinse
3. Next code work: merge P5 branch or Mac-fanned orchestrator job

## Mac peer

Drop this file after cycle 020 rinse.
