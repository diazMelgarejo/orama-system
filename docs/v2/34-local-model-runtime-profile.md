# Local Model Runtime Profile

> **Status:** operational profile extracted from the former security-harness plan
> **Security plan:** [`31-security-harness-excellence-plan.md`](31-security-harness-excellence-plan.md)
> **Prior mixed source:** [`33-security-harness-source-material.md`](33-security-harness-source-material.md)

---

## 1. Scope and caveat

This file contains local-runtime and model-selection guidance. It is intentionally separate from the security roadmap because model availability, quantization support, context limits, and performance change quickly. Treat vendor pages as Tier 1 for current capabilities and community benchmarks as directional only.

---

## 2. Security controls for Ollama / local model endpoints

- Bind local model servers to loopback unless an authenticated proxy and explicit allowlist are in place.
- Do not expose Ollama/LM Studio directly to the LAN without an auth layer.
- Do not pass control-plane bearer tokens to model probes or discovery endpoints.
- Keep model-server processes free of broad runtime secrets where possible.
- Patch promptly, especially after parser/model-loader security releases.
- Verify hashes for locally managed model files where feasible.

---

## 3. Ollama MLX on Apple Silicon

Ollama describes MLX support on Apple Silicon as a preview announced on March 30, 2026, powered by Apple’s MLX framework: https://ollama.com/blog/mlx. A June 11, 2026 Ollama update says the MLX engine was updated for higher performance, lower memory use, and NVFP4 support: https://ollama.com/blog/mlx-performance.

**Reframed recommendation:** say “MLX-backed Ollama is the preferred Apple Silicon path when the installed Ollama version and selected model support it,” not “Ollama universally switched to MLX as the default backend.” Ollama’s own language includes “preview,” and compatibility varies by platform/model.

---

## 4. qwen3.5:9b-nvfp4 profile

Ollama lists `qwen3.5:9b` and `qwen3.5:9b-nvfp4` under the Qwen 3.5 family. The Ollama library describes Qwen 3.5 as multimodal and lists a 256K context for current tags: https://ollama.com/library/qwen3.5/tags and https://ollama.com/library/qwen3.5%3A9b. The NVFP4 tag metadata is exposed in Ollama blobs such as https://ollama.com/library/qwen3.5%3A9b-nvfp4/blobs/d0883072e018.

**Caveat:** model cards and tags are mutable. Re-check the Ollama tag and upstream model card before encoding runtime assumptions in policy or CI.

**Recommendation for M2 16GB:** keep `qwen3.5:9b-nvfp4` as a candidate hot-path model only after local smoke tests confirm load, context, latency, and quality. Keep a smaller coding fallback such as `qwen2.5-coder:7b` or another locally verified model for parallel work.

---

## 5. Context and KV cache

- Enable Flash Attention if supported by the installed Ollama build and model.
- Use KV-cache quantization only after task-specific quality checks.
- Reduce `num_ctx` to task need; long context increases memory and attention cost.
- Do not assume advertised maximum context is practical on 16GB for multi-agent workloads.

---

## 6. Parallel agents on 16GB

Even with MLX improvements, a 16GB Apple Silicon machine is a constrained multi-agent host. Prefer single-stream local inference on the M2 and route heavy parallel reasoning to a larger GPU node when available.

---

## 7. Benchmarking checklist

Before updating this profile, record:

- machine model and RAM
- macOS version
- Ollama version
- model tag and digest
- prompt/context size
- time to first token
- decode tokens/sec
- peak memory
- failure modes
- whether tools/vision/thinking were enabled

Community videos/blogs can suggest experiments, but should not be treated as authoritative performance evidence without local reproduction.
