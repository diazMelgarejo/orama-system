# Win autoresearcher — H5 iterations harness

**Assignee:** win (autoresearcher, Hermes)  
**Topic:** autoresearch/gpu-run  
**Fan-out:** 2026-06-28-coord-003  
**Branch:** `subagent/win-autoresearcher/h5-gpu-harness`

## Task

1. Read Mac peer inbox: `mac-h4-synthesis.md`, then `mac-h4-comparison.md` when landed.
2. Run H5 Win leg on 27B — 3 rubric prompts, max 5 iterations each.
3. Branch `subagent/win-autoresearcher/h5-gpu-harness` for any harness tweaks.
4. Drop `gpu-results-h5.md` to Mac (`drop --peer`).

## Start signal

Mac co-orchestrator fan-out `2026-06-28-coord-003` — mesh green, subagent branches enabled.
