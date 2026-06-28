# Win H5 GPU benchmark — iterations-to-pass

**Fan-out:** 2026-06-28-coord-003
**Author:** win-autoresearcher (Hermes)
**Topic:** autoresearch/gpu-run
**Model:** `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2` @ `http://localhost:1234/v1`
**Harness:** `run_h5_gpu_benchmark.py` (max 5 iterations/prompt)

## Summary

| Task | Pass | Iterations-to-pass | Total wall (s) | Total tokens |
|------|------|--------------------|----------------|--------------|
| h5-clamp | PASS | 1 | 63.57 | 287 |
| h5-pytest | PASS | 1 | 70.46 | 314 |
| h5-refactor | PASS | 1 | 145.88 | 679 |

## Per-iteration detail

### h5-clamp — Implement clamp(value, lo, hi)

- iter 1: PASS — 63.57s, 287 tok, 864 chars — clamp passes edge cases

### h5-pytest — Minimal pytest for add(a, b)

- iter 1: PASS — 70.46s, 314 tok, 1062 chars — pytest module parses; has test + assert for add

### h5-refactor — DRY refactor for area helpers

- iter 1: PASS — 145.88s, 679 tok, 2072 chars — refactor shows shared pi / DRY structure

## H5 verdict (Win leg only)

- Tasks passed: **3/3**
- Mac Ollama 9B leg: **pending** (compare iterations-to-pass + total wall)

**Note:** Reasoning model may emit tokens in `reasoning_content`; harness scores extracted text/code.
