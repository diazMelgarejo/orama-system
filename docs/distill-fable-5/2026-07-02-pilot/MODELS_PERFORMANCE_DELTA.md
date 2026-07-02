# Models Performance Delta — 2026-07-02 pilot

Measured deltas only. Unmeasured cells are explicit TODOs.

## Measured — H6 real-task autoresearch (source: `bin/orama-system/skills/hermes-harness/references/results/gpu-results-h6.md`)

| Metric | Mac Ollama 9B (`qwen3.5:9b-nvfp4`) | Win LM Studio 27B (distilled-v2) | Delta |
|---|---|---|---|
| Iterations-to-pass (real `autoresearch_bridge` prompt) | 5 | 3 | −40% iterations |
| Wall-clock (run 1) | 70s | 45s | −36% |
| Single-pass smoke rubric (38 tests) | n/m | 10.77s, 38/38 PASS, 1 iteration | — |

**Conclusion (validated 2x):** H5 synthetic-rubric savings transfer to real PT
work. Dual-path orchestration should prefer the Win 27B whenever reachable.

## Measured — this pilot session (orchestration-level)

| Event | Value |
|---|---|
| CI root-cause (gh log vs external deduction) | 1 `gh run view --log-failed` refuted 2 external hypotheses |
| CI fix latency | restore + verify + push + green run within one session (run 28563937736, 10s) |
| Win coordination call (LM Studio 27B, 350 max_tokens) | 1 round-trip, structured VERDICT ACCEPT |
| orama full test suite on Mac | 1019 passed, 1 skipped, 41.57s |
| Claude Sonnet subagent availability | 0/5 (session limit) — fallback ladder exercised successfully |

## TODO — not yet measured

| Delta | How to measure |
|---|---|
| Fable-5-authored artifact vs Sonnet-authored artifact quality on same prompt | Re-run distill drafting via Sonnet after limit reset; diff against this folder |
| Mac 9B vs Win 27B on coordination-verdict reliability | 10x repeated VERDICT prompts per model; count format violations |
| ClinePass (cline-pass/glm-5.2) vs local 27B on bounded coding | Dispatch same coord-023 subtask to both; compare iterations + rubric |
| Token cost per pilot phase (Fable orchestration overhead) | Enable per-phase token logging in the pulse cron job |
