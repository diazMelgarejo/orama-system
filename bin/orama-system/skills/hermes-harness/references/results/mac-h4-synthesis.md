# Mac H4 synthesis — post Win coding-loop benchmark

**Fan-out:** 2026-06-28-autoresearch-002  
**Author:** mac-researcher (OpenClaw / Ollama)  
**Topic:** autoresearch/hypothesis-done  
**Inputs:** `gpu-results-h4.md` (Win), `mac-hypothesis-v2.md`, `gpu-results.md` (H3)

## H4 verdict — **Partial (Win-only)**

| Dimension | Finding |
|-----------|---------|
| Win 27B single-shot coding (`clamp`) | **~33.1s** wall, 161 tokens (reasoning model; 0 visible chars) |
| Mac Ollama 9B same prompt class | **Not run** — comparison incomplete |
| Iterations-to-pass | **Unmeasured** — requires shared task harness on both hosts |
| Latency vs H3 baseline | Win coding prompt **~3.3× slower** than Win trivial prompt (~10.1s); Mac 9B expected faster still |

**H4 quality claim** (Win 27B reduces iteration count vs Mac 9B despite higher per-token latency) remains **unfalsified and unsupported**. Win partial run only confirms per-request latency penalty persists on non-trivial prompts.

## Routing recommendation (latency vs quality)

| Workload class | Route | Rationale |
|----------------|-------|-----------|
| Latency-sensitive — probes, one-shot checks, orchestrator chatter, small edits | **mac** / `ollama-mac` `:11434` | H3 falsified Win for trivial latency; H4 partial shows Win 27B ~33s even for small coding prompts |
| Quality-heavy — autoresearch-coder, multi-step refinement, train.py edits | **win-rtx3080** / 27B `@ :1234` | **Provisional** — keep `routing.yml` affinity until H4/H5 complete; quality advantage not yet demonstrated |
| Never | Mac passive LM Studio `:1234` + Win `:1234` double-barrel | Confirmed in mac-hypothesis-v2; Mac coder = Ollama only |

**Orchestrator mental model:** Default Mac for speed; escalate to Win only when task class is explicitly quality-heavy *and* iteration savings are expected to amortize LAN + GPU latency. Do not route latency-sensitive autoresearch probes to Win.

## Mac Ollama 9B parallel benchmark — **still needed**

Yes. H4 cannot close without Mac-side run on the **same prompt class** (small Python function, e.g. `clamp`):

1. Run Ollama 9B on Mac with identical prompt + max_tokens settings as Win H4 run.
2. Record wall-clock, tokens, visible content.
3. Drop `mac-h4-comparison.md` to Win peer inbox.

This completes the single-shot latency leg of H4. Iteration comparison remains blocked until H5 harness exists.

## Hypothesis ledger (updated)

| ID | Verdict | Notes |
|----|---------|-------|
| H1 | **Supported** | File inbox primary coordination wire |
| H2 | **Partial** | Win→Mac drops work post Mac peer-file restart; 10-cycle auth retest deferred |
| H3 | **Falsified (latency)** | Trivial prompts: Mac 9B faster than Win 27B |
| H4 | **Partial** | Win-only coding prompt; quality/iterations unmeasured |

## Proposed H5 — shared iterations-to-pass harness

**Claim:** For a fixed 3-prompt autoresearch-coder rubric (pass/fail per iteration), Win 27B achieves fewer iterations-to-pass than Mac Ollama 9B, and total wall-clock (iterations × per-request latency + LAN overhead) still favors Win for at least one prompt class.

**Test:**

1. Define 3 prompts with explicit pass criteria (e.g. correct `clamp`, simple pytest, minimal refactor).
2. Run identical harness on Mac Ollama 9B and Win 27B; cap at 5 iterations each.
3. Compare: iterations-to-pass, total wall-clock, token cost.

**Falsify:** Mac 9B matches or beats Win on iterations *and* total wall-clock for ≥2/3 prompts.

**Win action:** Implement or adopt shared harness script; execute Win leg after Mac drops `mac-h4-comparison.md`.

## Mac next actions

- [ ] Run Ollama 9B H4 parallel benchmark → drop `mac-h4-comparison.md` to Win
- [ ] Draft H5 harness prompt set (3 rubric-scored tasks)
- [ ] Optional: `mac-routing-review.md` cross-check vs `Perpetua-Tools/config/routing.yml` (assignment pending)
