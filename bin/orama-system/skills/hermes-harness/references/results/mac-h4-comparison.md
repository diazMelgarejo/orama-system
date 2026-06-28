# Mac H4 comparison — Ollama 9B vs Win 27B (clamp prompt)

**Fan-out:** 2026-06-28-coord-003  
**Author:** mac-researcher (OpenClaw / Ollama)  
**Topic:** autoresearch/gpu-done  
**Branch:** `subagent/mac-researcher/h4-mac-benchmark`  
**Inputs:** `gpu-results-h4.md` (Win), `mac-h4-synthesis.md`

## Prompt (shared class)

```
Write a Python function clamp(value, lo, hi) that returns value bounded to the
inclusive range [lo, hi]. Include type hints. Output only the function, no tests
or explanation.
```

**Settings:** `POST /v1/chat/completions`, `max_tokens=512`, `temperature=0`

## Results

| Metric | Mac Ollama 9B | Win LM Studio 27B |
|--------|---------------|-------------------|
| Model | `qwen3.5:9b-nvfp4` | `qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2` |
| Endpoint | `localhost:11434` | `localhost:1234` |
| Wall-clock (warm) | **~20.2s** | **~33.1s** |
| Wall-clock (cold) | ~56.1s | — |
| Total tokens | 560 | 161 |
| Completion tokens | 512 (hit cap) | 161 |
| Visible content | 0 chars | 0 chars |
| Reasoning field | ~1902 chars (`reasoning`) | thinking tokens (reasoning model) |

**Warm runs:** 20.63s, 20.17s (back-to-back after model loaded).

## H4 latency leg — **Complete**

| Verdict | Finding |
|---------|---------|
| Single-shot coding (`clamp`) | Mac 9B **~1.6× faster** than Win 27B on warm wall-clock (20.2s vs 33.1s) |
| H3 extension | Non-trivial coding prompt still favors Mac for per-request latency |
| Quality / iterations | **Unmeasured** — requires H5 shared harness |

## Routing (unchanged from mac-h4-synthesis)

- **Latency-sensitive** (probes, one-shot coding, orchestrator chatter) → **mac** / `ollama-mac` `:11434`
- **Quality-heavy** (multi-step autoresearch-coder refinement) → **win-rtx3080` / 27B — provisional until H5

## Caveats

1. Both models are reasoning/thinking variants; visible `content` empty, tokens in thinking/reasoning fields.
2. Mac hit `max_tokens=512` cap; Win stopped at 161 tokens — token counts not directly comparable.
3. Cold-start Mac run (~56s) excluded from headline; Win cold not measured.

## Win action

- Read this file from Mac peer inbox.
- Proceed with H5 iterations-to-pass harness (`win-autoresearcher-h5-gpu.md`).
