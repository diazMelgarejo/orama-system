# Mac H5 Ollama benchmark — cross-host comparison

**Fan-out:** 2026-06-28-coord-004  
**Author:** mac-researcher (OpenClaw)  
**Topic:** autoresearch/gpu-run  
**Branch:** `subagent/mac-researcher/h5-ollama-parallel`  
**Mac model:** `qwen3.5:9b-nvfp4` @ `http://localhost:11434/v1`  
**Win model:** `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2` @ `http://localhost:1234/v1`  
**Harness:** `run_h5_gpu_benchmark.py` (max 5 iterations/prompt, same 3 rubric tasks)

## Cross-host summary

| Task | Mac pass | Mac itp | Mac wall (s) | Mac tokens | Win pass | Win itp | Win wall (s) | Win tokens | itp Δ (Mac−Win) | wall Δ (Mac−Win) |
|------|----------|---------|--------------|------------|----------|---------|--------------|------------|-----------------|------------------|
| h5-clamp | PASS | 1 | 86.0 | 1073 | PASS | 1 | 63.57 | 287 | 0 | +22.43 |
| h5-pytest | PASS | 4 | 142.61 | 9430 | PASS | 1 | 70.46 | 314 | +3 | +72.15 |
| h5-refactor | PASS | 5 | 261.56 | 15641 | PASS | 1 | 145.88 | 679 | +4 | +115.68 |

**Totals:** Mac 3/3 pass, **490.17 s** wall, **26144** tokens · Win 3/3 pass, **279.91 s** wall, **1280** tokens

## Mac per-iteration detail

### h5-clamp — Implement clamp(value, lo, hi)

- iter 1: PASS — 86.0s, 1073 tok, 3744 chars — clamp passes edge cases

### h5-pytest — Minimal pytest for add(a, b)

- iter 1: FAIL — 41.54s, 1071 tok — syntax error (indent)
- iter 2: FAIL — 47.93s, 2150 tok — syntax error (indent)
- iter 3: FAIL — 37.96s, 2968 tok — syntax error (indent)
- iter 4: PASS — 15.19s, 3241 tok — pytest module parses; has test + assert for add

### h5-refactor — DRY refactor for area helpers

- iter 1: FAIL — 40.3s, 1127 tok — syntax error (indent)
- iter 2: FAIL — 47.12s, 2203 tok — syntax error (indent)
- iter 3: FAIL — 48.55s, 3275 tok — syntax error (indent)
- iter 4: FAIL — 49.22s, 4345 tok — syntax error (indent)
- iter 5: PASS — 76.37s, 4691 tok — refactor shows shared pi / DRY structure

## H5 verdict

- **Iterations-to-pass:** Win 27B wins all 3 tasks (1/1/1 vs Mac 1/4/5). Mac 9B needed rubric feedback loops on pytest and refactor.
- **Wall-clock:** Win faster on every task (+22s clamp, +72s pytest, +116s refactor); Mac total **1.75×** Win wall.
- **Tokens:** Mac 9B emitted far more tokens (thinking + retries); Win reasoning model still more token-efficient per pass.
- **Quality parity:** Both hosts eventually pass all rubrics within max 5 iterations — hypothesis from H4 synthesis holds for Win on first-try quality.

**Frugal routing:** Keep autoresearch-coder / multi-iteration coding on **Win 27B**; Mac Ollama 9B viable as fallback only.
