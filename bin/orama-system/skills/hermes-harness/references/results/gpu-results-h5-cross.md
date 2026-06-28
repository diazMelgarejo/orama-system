# H5 cross-host synthesis — Win + Mac (frugal ladder)

**Fan-out:** `2026-06-28-coord-004`  
**Author:** win-autoresearcher (Hermes)  
**Topic:** autoresearch/gpu-done  
**Inputs:** `gpu-results-h5.md` (Win), `mac-h4-comparison.md` (Mac), `mac-h4-synthesis.md`

## Cross-host summary

| Leg | Host | Model | H4 clamp (warm) | H5 iter-to-pass (3 tasks) |
|-----|------|-------|-----------------|---------------------------|
| Latency | Mac | Ollama 9B | **~20.2s** | pending (`mac-h5-comparison.md`) |
| Quality harness | Win | LM Studio 27B | ~33.1s | **3/3 @ 1 iter** (~280s total) |

## H4 latency — closed

Mac 9B **~1.6× faster** than Win 27B on shared `clamp` prompt class (warm wall-clock).  
**Routing:** latency-sensitive coding probes → Mac Ollama; quality-heavy multi-iter → Win 27B.

## H5 iterations-to-pass — Win complete, Mac pending

Win harness (`run_h5_gpu_benchmark.py` on branch `subagent/win-autoresearcher/h5-gpu-harness`):

| Task | Pass | Iterations | Wall (s) |
|------|------|------------|----------|
| h5-clamp | PASS | 1 | 63.57 |
| h5-pytest | PASS | 1 | 70.46 |
| h5-refactor | PASS | 1 | 145.88 |

Mac parallel H5 on Ollama 9B assigned (`mac-researcher-h5-parallel.md`) — awaiting `mac-h5-comparison.md` drop.

## Frugal ladder applied (this cycle)

1. LM Studio 27B local (Win H5 — done)
2. File inbox read Mac `mac-h4-comparison.md` (no cloud)
3. Synthesis only — no redundant Win re-run
4. Online / Codex — not used

## Verdict (provisional)

- **Latency:** Mac wins single-shot (`H3`/`H4` confirmed).
- **Iterations-to-pass:** Win 27B passed all rubric tasks on first iteration; Mac leg needed to compare iteration counts.
- **Orchestrator:** Route probes to Mac; route multi-step autoresearch-coder refinement to Win when iteration savings amortize GPU latency.

## Queue

Processed via `win_job_queue.py` — autoresearcher role, priority 1, sequential (one active job).
