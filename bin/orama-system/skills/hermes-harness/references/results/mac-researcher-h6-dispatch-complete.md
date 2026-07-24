# Mac researcher — H6 backlog dispatch complete

**Date:** 2026-07-22  
**Job:** `subagent/win-autoresearcher/researcher-backlog-h6`  
**Fan-out:** `2026-06-29-coord-021-h6`  
**Topic:** autoresearch/gpu-run  
**Agent card:** `.cursor/agents/win-autoresearcher-queue.md`

## Win deliverable received

| File | Status |
|------|--------|
| `gpu-results-h6-preflight.md` | In Mac inbox — H5 closed, frugal router documented |
| H5 canonical priors | `gpu-results-h5-final.md`, `gpu-results-h5-cross.md` present |

**Preflight verdict:** H5 GPU harness cycle closed. No speculative Win GPU run without Mac hypothesis card (B1 frugality).

## Mac actions (this dispatch)

1. Read `mac-coord-023-queue-ack.md` researcher backlog — GPU items gated on preflight (done).
2. Selected **Option A** — H6 real-task autoresearch via PT `autoresearch_bridge`.
3. Dropped `mac-hypothesis-h6-real-task.md` to Win peer outbox (`assignee: win`, topic `autoresearch/gpu-run`).
4. H4/H5 Mac baselines already canonical (`mac-h4-comparison.md`, `mac-h5-comparison.md`).

## Win follow-up

1. Pull hypothesis card from peer inbox (or outbox flush on next `coord_pulse`).
2. When autoresearcher idle: single LM Studio 27B pass via PT bridge on real prompt class.
3. Drop `gpu-results-h6.md` with iterations, wall-clock, rubric pass/fail.
4. Mark `win-autoresearcher-researcher-backlog-h6` complete in `win_job_queue.py`.

## Frugal tier

**B0** — file inbox synthesis + hypothesis fan-out (no GPU on Mac for this job).

**Canonical priors:** `gpu-results-h6-preflight.md`, `mac-hypothesis-h6-real-task.md`.
