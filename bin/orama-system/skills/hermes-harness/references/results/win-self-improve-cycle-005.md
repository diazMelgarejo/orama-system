# Win self-improve cycle 005 — summary

**Fan-out:** `2026-06-28-coord-005`  
**Author:** win-co-orchestrator (Hermes)  
**Topic:** self-improve/lessons  
**Date:** 2026-06-28

## What happened

| Event | Outcome |
|-------|---------|
| Queue hygiene | `prune` + `complete-pending` cleared stale mac-* noise; coord-003 reconciled |
| 15-min monitor | `coord_monitor.ps1` detected `win-autoresearcher-h5-finalize.md` at tick 5 |
| Monitor fix | Em-dash in PS script caused ParserError; fixed to ASCII-only strings |
| H5 finalize | Mac `mac-h5-comparison.md` merged; `gpu-results-h5-final.md` dropped to Mac |
| PT lessons merge | Mac `learn.py` rows unioned with Win round 7 on `git pull` conflict |
| Queue idle | autoresearcher 4 done; coder 0 pending (awaiting Mac coder card) |

## H5 closed (routing)

- Mac 3/3 @ 1/4/5 itp, 490s wall
- Win 3/3 @ 1/1/1 itp, 280s wall
- **Route autoresearch-coder to Win 27B**; Mac Ollama 9B for latency probes / fallback

## Frugal tiers used

| Step | Tier |
|------|------|
| Read Mac H5 results | B1 file inbox + git pull |
| Cross synthesis | B1 synthesis only (no GPU re-run) |
| Monitor | B1 local probe + enqueue |
| Online / Codex | not used |

## Open items

- Coder: bridge PR verify (`subagent/win-coder/bridge-http-local` -> PT main)
- Mac: optional merge `subagent/mac-researcher/h5-ollama-parallel`

## PT learn

Round 8 lessons via `learn.py` + `auto_dream.py`; operator approved ALL to `.agent/memory/semantic/lessons.jsonl`.
