# Win coder — PT #183 bridge draft review

**Assignee:** win (coder)  
**Topic:** code-review/bridge-merge  
**Fan-out:** 2026-06-28-coord-006  
**Priority:** 1 — one active coder job

## Task

1. Read inbox context: `win-bridge-pr-ready.md` already delivered.
2. Compare `subagent/win-coder/bridge-http-local` vs `cursor/review-bridge-http-local-c4ae` (PT #183 draft).
3. Run `pytest tests/test_autoresearch_bridge.py` — expect 38 pass.
4. Drop `win-pt183-reconcile.md` to Mac peer with merge recommendation.

**Frugal:** local tests only; no cloud.

## Queue

```powershell
python win_job_queue.py enqueue
python win_job_queue.py next coder
python win_job_queue.py complete coder --note "win-pt183-reconcile.md"
```
