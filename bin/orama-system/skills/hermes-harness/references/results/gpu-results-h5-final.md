# H5 cross-host final — Mac 3/3 vs Win 3/3

**Fan-out:** `2026-06-28-coord-005`  
**Author:** win-autoresearcher  
**Topic:** autoresearch/gpu-done  
**Status:** CLOSED

## Result

| Host | Model | Pass rate | Iterations (clamp / pytest / refactor) | Total wall |
|------|-------|-----------|------------------------------------------|------------|
| Mac | Ollama 9B `qwen3.5:9b-nvfp4` | **3/3** | 1 / 4 / 5 | 490.17 s |
| Win | LM Studio 27B | **3/3** | 1 / 1 / 1 | 279.91 s |

**Winner (itp):** Win on all three tasks.  
**Winner (wall):** Win on all three tasks (+22s, +72s, +116s per task).  
**Quality parity:** Both hosts pass all rubrics within max 5 iterations.

## Frugal tier per step (Ladder B1)

1. Read `mac-h5-comparison.md` from Mac peer inbox — file only, no cloud.
2. Merge into `gpu-results-h5-cross.md` — synthesis only, no Win re-run.
3. Drop this final to Mac peer — `lan_peer_assign.py drop --peer`.

## Routing recommendation

Keep autoresearch-coder / multi-iteration coding on **Win 27B**; Mac Ollama 9B as latency probe and fallback when Win GPU slot busy.

**Canonical cross doc:** `gpu-results-h5-cross.md` (updated coord-005).
