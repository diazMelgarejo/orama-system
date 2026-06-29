# Mac hypothesis — H6 real-task autoresearch (Option A)

**Date:** 2026-06-29  
**Fan-out:** 2026-06-29-coord-021-h6  
**Assignee:** win (autoresearcher)  
**Topic:** autoresearch/gpu-run  
**Priority:** 10

## Claim

Win 27B iteration savings observed on H5 **synthetic rubric** tasks transfer to a **real** Perpetua-Tools `autoresearch_bridge` prompt class (not clamp/pytest/refactor stubs).

## Falsification

| Criterion | Fail if |
|-----------|---------|
| Iterations-to-pass | Win 27B ≥ Mac 9B on same real prompt |
| Wall-clock | Win total time > 1.5× Mac Ollama 9B on same prompt |
| Quality | Bridge output fails PT smoke rubric (import/syntax/test) |

## Mac deliverables (prerequisite — done)

- H4/H5 Mac Ollama baselines via researcher queue (`mac-researcher-h4-benchmark`, `mac-researcher-h5-parallel`).
- This card unblocks Win GPU harness after Mac comparisons land.

## Win executes

1. Wait for Mac `mac-h4-comparison.md` / `mac-h5-comparison.md` in peer inbox (or proceed if H5-final already canonical).
2. Single LM Studio pass via PT `autoresearch_bridge` on agreed real prompt class.
3. Drop `gpu-results-h6.md` with iterations, wall-clock, rubric pass/fail.

## Frugal policy

- B0: file inbox for synthesis
- B1: Win 27B for multi-iteration harness; Mac 9B for latency probe
- No cloud unless both local tiers fail twice

**Canonical prior:** `gpu-results-h5-final.md`, `gpu-results-h6-preflight.md`.
