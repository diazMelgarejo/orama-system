# H5 cross-host synthesis — Win + Mac (frugal ladder)

**Fan-out:** `2026-06-28-coord-004` → closed `2026-06-28-coord-005`  
**Author:** win-autoresearcher (Hermes)  
**Topic:** autoresearch/gpu-done  
**Inputs:** `gpu-results-h5.md` (Win), `mac-h5-comparison.md` (Mac), `mac-h4-comparison.md`, `mac-h4-synthesis.md`

## Cross-host summary — H5 closed

| Task | Mac pass | Mac itp | Mac wall (s) | Win pass | Win itp | Win wall (s) | itp Δ (Mac−Win) | wall Δ (Mac−Win) |
|------|----------|---------|--------------|----------|---------|--------------|-----------------|------------------|
| h5-clamp | PASS | 1 | 86.0 | PASS | 1 | 63.57 | 0 | +22.43 |
| h5-pytest | PASS | 4 | 142.61 | PASS | 1 | 70.46 | +3 | +72.15 |
| h5-refactor | PASS | 5 | 261.56 | PASS | 1 | 145.88 | +4 | +115.68 |

**Totals:** Mac **3/3** pass, **490.17 s** wall · Win **3/3** pass, **279.91 s** wall

| Leg | Host | Model | H4 clamp (warm) | H5 iter-to-pass |
|-----|------|-------|-----------------|-----------------|
| Latency | Mac | Ollama 9B | **~20.2s** | 1 / 4 / 5 |
| Quality harness | Win | LM Studio 27B | ~33.1s | **1 / 1 / 1** |

## H4 latency — closed

Mac 9B **~1.6× faster** than Win 27B on shared `clamp` prompt class (warm wall-clock).  
**Routing:** latency-sensitive coding probes → Mac Ollama; quality-heavy multi-iter → Win 27B.

## H5 iterations-to-pass — closed

- **Win 27B:** 3/3 tasks pass on **iteration 1** (63.57 + 70.46 + 145.88 s).
- **Mac 9B:** 3/3 pass within max 5 iterations (1 / 4 / 5 itp); **1.75×** total wall vs Win.
- **Verdict:** Win wins iterations-to-pass and wall-clock on rubric coding harness; Mac viable as fallback when Win GPU busy.

## Frugal ladder applied (coord-004 → 005)

| Step | Tier | Action |
|------|------|--------|
| Win H5 harness | B1 local | LM Studio 27B — no cloud |
| Mac H5 read | B1 file inbox | `mac-h5-comparison.md` — no re-run |
| Cross synthesis | B1 synthesis | Update tables only — no redundant GPU |
| Online / Codex | — | not used |

## Orchestrator routing

- **Probes / single-shot latency:** Mac Ollama 9B (`H3`/`H4` confirmed).
- **Autoresearch-coder / multi-iteration refinement:** Win 27B when iteration savings amortize GPU latency.
- **Queue:** `win_job_queue.py` — one active job per role; coord-005 autoresearcher finalize before coder cards.
