# Security & Agentic-Harness Excellence Plan

> **File:** `docs/v2/31-security-harness-excellence-plan.md`
> **Status:** Proposal for v2 — staged roadmap with v1 hardening folded in
> **Format:** /autoplan + /superpowers planning
> **Benchmark mandate:** exceed gstack + GBrain + Hermes-agent, mapped to OWASP
> LLM Top 10 (2025), OWASP Agentic ASI Top 10 (Dec 2025), MAESTRO 7-layer,
> SWARM system-level misalignment, and MITRE ATLAS v5.1
> **Cross-refs:** `docs/v2/23-security-preconditions.md`,
> `docs/v2/24-security-first-platform.md`, `docs/SECURITY-POLICY.md`,
> `docs/plans/2026-05-23-security-remediation-plan.md`

---

## 0. Goal (one sentence)

orama-system + Perpetua-Tools must meet or exceed the best documented practices
of agentic AI harnesses (gstack, GBrain, Hermes-agent) and pass the 2025-2026
agentic security standards (OWASP ASI, MAESTRO, SWARM, MITRE ATLAS), while
running efficiently on a MacBook Pro M2 16GB with `ollama run qwen3.5:9b-nvfp4`.

"Exceed" is measured: every control below maps to a named standard, and the
acceptance criteria in § 9 are exact commands.

---

## 1. Benchmark Targets (what we are exceeding)

### 1.1 gstack (github.com/garrytan/gstack) — copy the defense, surpass the isolation

gstack is a single-process Claude Code harness: structured SKILL.md role-switching,
not multi-agent orchestration. Its genuinely strong contribution is the
**sidebar-agent layered prompt-injection defense** (L1-L6):

| Layer | Mechanism | What to adopt |
|---|---|---|
| L1-L3 | datamarking, hidden-element strip, ARIA regex, URL blocklist, trust-boundary envelope | Apply to ALL tool/RAG outputs |
| L4 | local ONNX injection classifier (TestSavantAI BERT-small, int8, ~22MB, no network) | Port the local-classifier pattern |
| L4b | transcript classifier (Haiku pass), gated `LOG_ONLY: 0.40` to skip clean traffic | Adopt the cost-gated escalation |
| L5 | canary token in system prompt, rolling-buffer leak detection → deterministic BLOCK | Adopt verbatim (cheap, high-value) |
| L6 | ensemble combiner: BLOCK needs two classifiers agreeing at ≥ WARN (0.75) | Adopt to cut false positives |

**gstack gaps we must close:** no process sandbox (runs Claude with host
filesystem/shell/network), no agent identity, no egress control, human-sequenced
not autonomous. We add microVM/seccomp sandboxing, scoped agent identity, and
deny-by-default egress.

### 1.2 GBrain — adopt the memory trust model

GBrain is a persistent pgvector knowledge base for agents. Patterns to mirror in
orama's memory layer:

- Embedded pglite (Postgres 17 WASM + pgvector, local, no network) OR cloud
  Supabase via `GBRAIN_DATABASE_URL` (never written to argv/shell history)
- Per-repo trust triad: **read-write / read-only / deny**, stored mode-0600,
  sticky per git remote — a clean least-privilege memory pattern
- Secret-scanned cross-machine sync: AWS keys, GitHub tokens, PEM, JWT, bearer
  blocked before leaving the machine
- Semantic code graph: `code-def`, `code-refs`, `code-callers`, `code-callees`

Maps to OWASP LLM08 (Vector & Embedding Weaknesses) and ASI06 (Memory Poisoning).

### 1.3 Hermes (Nous Research) — model spec AND hosted agent

- **Function-calling standard:** tool defs as JSON schemas in `<tools>`,
  invocations in `<tool_call>`, responses in `<tool_response>`, RAG citations via
  `<co>` tags. Qwen3 chat templates already include Hermes-style tool use
  (vLLM `--tool-call-parser hermes` works for Qwen) — directly relevant to
  qwen3.5:9b.
- **Neutral alignment:** the model follows the system prompt precisely rather
  than applying built-in refusals. The harness MUST supply guardrails the model
  will not.
- **hermes-agent hosted API patterns to adopt:** bearer `API_SERVER_KEY` on all
  endpoints; session scoping via `X-Hermes-Session-Id` (transcript-scoped) and
  `X-Hermes-Session-Key` (stable per-channel, control chars rejected);
  credential pools with rotation; per-task credential leasing.

---

## 2. Threat Model (the standards we map to)

### 2.1 OWASP Agentic ASI Top 10 (released Dec 9, 2025) — primary standard

This is the most relevant list for a tool-using, memory-persistent harness:

| ID | Threat | Primary control in this plan |
|---|---|---|
| ASI01 | Agent Goal Hijack | canary token + injection classifier (§ 5) |
| ASI02 | Tool Misuse & Exploitation | least-agency allow-lists + param validation (§ 4) |
| ASI03 | Agent Identity & Privilege Abuse | scoped short-lived agent identity (§ 4) |
| ASI04 | Agentic Supply Chain Compromise | ML-BOM + signing + hash verify (§ 7) |
| ASI05 | Unexpected Code Execution | microVM/seccomp sandbox (§ 4) |
| ASI06 | Memory & Context Poisoning | pgvector trust triad + retrieval access control (§ 6) |
| ASI07 | Insecure Inter-Agent Communication | authenticated/encrypted PT channel (§ 4) |
| ASI08 | Cascading Agent Failures | blast-radius caps + digital-twin replay (§ 8) |
| ASI09 | Human-Agent Trust Exploitation | human-in-loop checkpoints (§ 8) |
| ASI10 | Rogue Agents | identity revocation + egress denial (§ 4) |

### 2.2 OWASP LLM Top 10 (2025) — model-layer coverage

LLM01 Prompt Injection, LLM02 Sensitive Info Disclosure, LLM03 Supply Chain,
LLM04 Data/Model Poisoning, LLM05 Improper Output Handling, LLM06 Excessive
Agency, LLM07 System Prompt Leakage, LLM08 Vector/Embedding Weaknesses,
LLM09 Misinformation, LLM10 Unbounded Consumption.

### 2.3 MAESTRO 7-layer threat model (Cloud Security Alliance, Ken Huang)

Architecture-level decomposition; each layer has its own threat landscape:

1. Foundation Models (theft, poisoning, backdoors)
2. Data Operations (RAG poisoning lives here)
3. Agent Frameworks (orchestration/decision logic — orama's orchestrator)
4. Deployment & Infrastructure (FastAPI, WebSocket — Perpetua)
5. Evaluation & Observability (telemetry)
6. Security & Compliance (vertical control layer)
7. Agent Ecosystem (impersonation, tool misuse, marketplace manipulation)

MAESTRO's value is cross-layer threats: supply-chain, lateral movement,
goal-misalignment cascades. The prototype validated DoS-via-replay and
memory-poisoning-via-tampered-logs on exactly a Python/FastAPI/WebSocket agent —
directly relevant to Perpetua.

### 2.4 SWARM — System-Wide Assessment of Risk in Multi-agent systems

**The framework's central thesis: system-level misalignment.**

> AGI-level risks don't require AGI-level agents. Catastrophic failures can emerge
> from the interaction of many sub-AGI agents.

This directly challenges the assumption that aligning each individual model in a
swarm is sufficient. For orama+Perpetua this is the load-bearing insight: even if
qwen3.5:9b and every subagent is individually well-behaved, the **interaction**
of the 7-agent network (orchestrator + context/architect/refiner/executor/
verifier/crystallizer) can produce emergent misalignment that no per-agent check
catches.

**SWARM-driven controls (the gap no per-agent alignment closes):**

- **System-level objective audit:** the orchestrator must periodically verify the
  aggregate behavior of the agent network against the original Spec Contract
  goal, not just each agent's local output. A swarm can satisfy every local
  objective while drifting from the system objective (see the Amplifier
  Objective Tree in the mother SKILL.md).
- **Interaction-effect monitoring:** log and analyze cross-agent message chains
  for emergent loops, mutual reinforcement of a wrong assumption, and
  responsibility diffusion ("each agent assumed another would verify").
- **Cascading-failure circuit breakers:** any subagent error that propagates to
  >2 downstream agents halts the network for human review (pairs with ASI08).
- **Adversarial system review:** before a Mode-3 network finalizes, the Verifier
  agent runs the M3 Collaborative Reasoning Safety adversarial pass at the
  SYSTEM level — "what is the strongest argument that this network's combined
  output is wrong?" — not just per-artifact.

Source: SWARM Framework (wikimolt.org/page/SWARM Framework). Treat as a living
reference; the system-level-misalignment principle is the durable takeaway.

### 2.5 MITRE ATLAS v5.1 (Nov 2025)

16 tactics, 84 techniques. Map LLM01 → prompt-injection techniques, LLM05 →
AML.T0048 supply chain, RAG Poisoning + False RAG Entry Injection → ASI06. Real
cases: Morris II self-replicating prompt worm.

---

## 3. Current State (v1) — what exists, what is exposed

From the v1 review (folded in below, see `security-efficiency-review-2026-06-14`):

**Already strong (verified against code):**
- No hardcoded secrets, no `.env` committed
- No shell injection (`shell=True`/`os.system`/`eval`/`exec` absent)
- No unsafe deserialization (`yaml.safe_load` used)
- Timing-safe token comparison (`secrets.compare_digest`)
- Async HTTP throughout (httpx/aiohttp, no sync `requests`)
- Dedicated boundary modules: `control_plane_auth.py`, `mcp_path_boundary.py`
- OpenGrep OWASP/CWE static-analysis rules in CI (PR #60)

**v1 architecture as a security asset:** orama is stateless (no secrets at rest);
all AlphaClaw traffic routes through the Perpetua-Tools adapter — a single egress
chokepoint that already serves ASI07 and egress-control goals.

---

## 4. v1 Hardening (the narrower review — PR-ready now)

These are the 8 items from the v1 review, prioritized. **Both** the code patches
and this written audit ship in one PR.

| # | Item | Severity | Fix | OWASP/ASI |
|---|---|---|---|---|
| S1 | Default-open auth when LAN-bound | Medium | Fail-closed unless loopback-only bind | ASI03, LLM06 |
| S2 | Unpinned dependencies | Medium | Hash-pinned lockfile in CI; resolve Dependabot high | LLM03, ASI04 |
| S3 | slowapi present but not wired | Low | Wire `Limiter`, per-user + per-model token budgets | LLM10 |
| S4 | `testclient` in loopback set | Low | Gate behind `ORAMA_PYTEST=1` | ASI03 |
| S5 | Cookie auth SameSite/Secure unconfirmed | Low | Confirm `HttpOnly; Secure; SameSite=Strict` | LLM02 |
| E3 | Duplicated CORS origins | Low | Dedupe 4 → 2 entries | — |
| E4 | `asyncio` pinned (stdlib no-op) | Low | Remove from requirements | — |
| E1 | Fixed-interval poll sleeps | Medium (cosmetic) | Exponential backoff with deadline | — |

### 4.1 S1 patch (fail-closed auth)

```python
# control_plane_auth.py
def auth_enforced() -> bool:
    if control_plane_token():
        return True
    insecure = os.getenv(ENV_INSECURE, "").strip().lower()
    if insecure in ("1", "true", "yes"):
        return False
    if insecure in ("0", "false", "no"):
        return True
    # Default: enforce unless explicitly bound to loopback only
    bind = os.getenv("ORAMA_LAN_BIND", "").strip().lower()
    return bind in ("1", "true", "yes")  # LAN bind -> require auth
```

### 4.2 S2 patch (pin + lock)

```bash
pip install pip-tools
pip-compile requirements.txt -o requirements.lock --generate-hashes
# CI installs from the lock; humans read the >= floors
```

### 4.3 S3 patch (rate limit, already a dependency)

```python
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/oramasys")
@limiter.limit("30/minute")
async def run_oramasys(req: OramasysRequest, request: Request): ...
```

---

## 5. v2 Sandboxing & Identity (the agentic-excellence bar)

### 5.1 Tool sandboxing (ASI05 — sandboxing is a control, not a suggestion)

Standard Docker is insufficient (shared kernel; escape = host access, MITRE
T1611). Per-node policy in `model_hardware_policy.yml`:

| Node | Sandbox | Rationale |
|---|---|---|
| M2 dev box | macOS Seatbelt (Anthropic's Claude Code pattern) | Native, reduces permission prompts ~84% |
| RTX 3080 node + any prod | Firecracker microVM or Kata | Strongest isolation for autonomous tools |

**Four mandatory layers (NVIDIA/Microsoft converge):**
1. Network egress allowlist (deny-by-default proxy) — "single highest-impact control"
2. Filesystem boundaries (read-only mounts)
3. Secrets scoping (no broad env inheritance)
4. Config-file write protection (CurXecute/MCPoison class)

### 5.2 Agent identity & least agency (ASI02, ASI03, LLM06)

- Each agent gets a scoped, short-lived cryptographic identity (non-human identity)
- Tool allow-lists per agent + parameter validation at a Tool-Executor mediator
  (mirror Anthropic's grant-verification pattern)
- Adopt GBrain's read-write/read-only/deny triad for memory access
- "Blast radius" and "least agency" as design defaults (Anthropic)

### 5.3 Inter-agent communication (ASI07)

The PT adapter is already the single chokepoint. Harden it: authenticate and
encrypt the orama ↔ PT ↔ AlphaClaw channel; treat any imported OpenClaw skills
or memories as untrusted input and scan before ingest.

---

## 6. v2 Memory Hardening (LLM08 / ASI06)

- Authenticate data sources before ingest into pgvector
- Sanitize retrieved content for injection patterns (datamarking from § 1.1)
- Enforce access control at the retrieval layer — never let the LLM decide what
  is safe to retrieve
- Log all retrievals with user context; anomaly-detect on retrieval volume/pattern
- Consider encrypted embeddings: embeddings are invertible (Morris et al. showed
  ~92% recovery of 32-token inputs), so a leaked vector store leaks content

---

## 7. v2 Supply Chain & Observability

### 7.1 Supply chain (LLM03 / ASI04)

- CycloneDX ML-BOM for model weights + pip deps; SPDX 3.0 AI profile
- Pin model versions; verify GGUF/SafeTensors hashes before load; scan model
  files for RCE payloads before load
- Sign artifacts with cosign; adopt SLSA provenance + in-toto attestations in CI
- EU AI Act Article 11/Annex IV documentation effective 2 Aug 2026

### 7.2 Observability (MAESTRO L5)

- Instrument with OpenTelemetry GenAI Semantic Conventions: spans `invoke_agent`,
  `execute_tool`, `chat`; attributes `gen_ai.usage.input_tokens/output_tokens`,
  `gen_ai.response.finish_reasons`
- Per-span token accounting catches runaway loops (50K tokens for a 3K task =
  misbehavior — ties to the frugality dashboard's tier attribution)
- Ship to a SIEM; target sub-1-hour anomaly detection on token budgets and egress

---

## 8. v2 Governance (ASI08 / ASI09 / SWARM)

- Human-in-loop checkpoints (Plan-Mode style) before irreversible actions
- Blast-radius caps: any subagent error propagating to >2 downstream agents halts
  the network for review
- Digital-twin replay harness: test agent action sequences against blast-radius
  caps before expanding any policy
- **SWARM system-level audit:** the orchestrator verifies aggregate network
  behavior against the Spec Contract system objective, not just per-agent output
  (§ 2.4)

---

## 9. Local Model Security & Efficiency (M2 16GB, qwen3.5:9b-nvfp4)

### 9.1 Ollama security (patch first)

Ollama ships without authentication by default. Mandatory:

- Upgrade Ollama to the current release (the GGUF-loader heap-read class of bug
  leaks process memory including env-var secrets; patch promptly)
- Bind to loopback: `OLLAMA_HOST=127.0.0.1`; firewall port 11434
- Never expose to network without an auth proxy + IP allowlist
- Rotate any secret ever resident in an exposed Ollama process

### 9.2 Ollama now runs natively on MLX (Apple Silicon)

**Correction applied (2026):** Ollama officially switched to Apple's MLX as the
default backend for Apple Silicon starting **version 0.19 (March 30, 2026)**.
This is real and production-ready, not a side experiment.

- **Speedups:** noticeable to massive vs the old llama.cpp Metal backend. Reviews
  report 1.6x-2x+ decode speedup generally, and up to ~7x faster decode on M1 Max
  in one technical benchmark. Strongest on M4/M5, real gains on M2.
- **Memory:** better unified-memory usage enables higher-quality quantizations
  (NVFP4 support) and longer context within the same RAM budget.
- **Trajectory:** support expanding fast — the June 11, 2026 update
  ("Highest performance on Apple Silicon yet with MLX") adds more models and
  optimizations.

**Authoritative sources:**
- Ollama Blog, "Ollama is now powered by MLX on Apple Silicon in preview"
  (Mar 30, 2026): https://ollama.com/blog/mlx
- Ollama Blog, "Highest performance on Apple Silicon yet with MLX"
  (Jun 11, 2026): https://ollama.com/blog/mlx-performance

**Reviews/benchmarks:**
- YouTube, "Ollama Switched to Apple MLX — Here's Why Everything is Faster"
  (real benchmarks, up to 7x decode on M1 Max): https://www.youtube.com/watch?v=OGJLV2H8b6I
- Gingter.org, "Ollama Goes MLX" (engineering breakdown):
  https://gingter.org/2026/04/23/ollama-goes-mlx/
- Ars Technica discussion:
  https://arstechnica.com/civis/threads/running-local-models-on-macs-gets-faster-with-ollama%E2%80%99s-mlx-support.1512366/
- Hacker News: https://news.ycombinator.com/item?id=47582482
- Medium, "Ollama 0.19 ships MLX backend":
  https://medium.com/@tentenco/ollama-0-19-ships-mlx-backend-for-apple-silicon-local-ai-inference-gets-a-real-speed-bump-878b4928f680

### 9.3 Best models for MLX on M2 16GB

Primary (your default): **`qwen3.5:9b-nvfp4`** — hybrid Gated-Delta + sparse-MoE
multimodal, 256K context, Apache 2.0; NVFP4 4-bit cuts memory-bandwidth pressure
while preserving accuracy. A 9B Q4 is ~5GB of weights, the right size for 16GB.

Other coding-capable models with similar quantization that fit M2 16GB:

| Model | Notes |
|---|---|
| `qwen2.5-coder:7b` (Q4/NVFP4) | Strong code-specialized, smaller footprint, fast |
| `deepseek-coder-v2:16b-lite` (Q4) | MoE-lite, code-focused; tight on 16GB but viable with quantized KV |
| `codestral:22b` (Q4) | Mistral code model; only with aggressive KV quant + small context on 16GB |
| `qwen3.5:9b-q4_K_M` | Same model, llama.cpp-style quant if not using NVFP4 |
| `llama3.1:8b-instruct` (Q4) | General fallback; weaker at code than the Qwen-coder line |

Recommendation: keep `qwen3.5:9b-nvfp4` as the hot path; pull
`qwen2.5-coder:7b` as the fast/low-memory coding fallback for parallel work.

### 9.4 KV cache & context on 16GB

- Enable Flash Attention: `OLLAMA_FLASH_ATTENTION=1`
- Quantize KV cache: `OLLAMA_KV_CACHE_TYPE=q8_0` (halves cache) or `q4_0`
  (~1/3, more quality loss). KV at full 128K f16 can balloon to ~16GB, so this is
  mandatory on 16GB.
- `OLLAMA_KEEP_ALIVE=-1` to avoid reload churn
- Reduce `num_ctx` to task need — KV grows linearly, attention compute
  quadratically with context

### 9.5 Parallel agents on 16GB

Even on the MLX backend, 16GB constrains concurrent model streams. Route
heavy/parallel reasoning to the RTX 3080 node (per `model_hardware_policy.yml`);
keep the M2 for single-stream local inference.

---

## 10. Staged Roadmap

| Stage | Window | Deliverables |
|---|---|---|
| **Stage 0** | This week | v1 hardening PR (§ 4): S1 fail-closed, S2 lockfile + Dependabot, S3 rate limit, S4/S5/E3/E4 cleanups; Ollama patch + loopback bind |
| **Stage 1** | Weeks 2-4 | Sandboxing (Seatbelt M2, microVM RTX/prod) + deny-by-default egress; scoped agent identity + least-agency allow-lists; GBrain memory trust triad |
| **Stage 2** | Weeks 4-8 | gstack-style layered content scanner (datamarking, local ONNX classifier, canary token); pgvector memory hardening (retrieval access control, anomaly detection) |
| **Stage 3** | Weeks 8-12 | OpenTelemetry GenAI tracing → SIEM; ML-BOM + signing + SLSA; human-in-loop checkpoints + digital-twin replay; SWARM system-level audit in the orchestrator |

---

## 11. Acceptance Criteria

- [ ] **AC-S1** `auth_enforced()` returns True when `ORAMA_LAN_BIND=1` and no token set
- [ ] **AC-S2** `requirements.lock` exists with `--generate-hashes`; Dependabot high resolved
- [ ] **AC-S3** `/oramasys` returns 429 after the configured rate limit in a test
- [ ] **AC-SB** every tool executor runs inside a sandbox profile (Seatbelt or microVM); egress is deny-by-default
- [ ] **AC-ID** each agent has a scoped short-lived identity; tool allow-list enforced at the mediator
- [ ] **AC-MEM** pgvector retrieval enforces access control + logs with user context
- [ ] **AC-SCAN** tool/RAG outputs pass through datamarking + a local injection classifier; canary leak → deterministic block
- [ ] **AC-OTEL** `invoke_agent`/`execute_tool` spans emit with token accounting; SIEM alerts on budget anomaly
- [ ] **AC-BOM** ML-BOM generated; model hashes verified before load; artifacts cosign-signed
- [ ] **AC-SWARM** orchestrator runs a system-level objective audit before any Mode-3 finalize
- [ ] **AC-OLLAMA** Ollama patched, bound to 127.0.0.1, KV cache quantized, Flash Attention on

---

## 12. Caveats (source reliability)

- gstack/GBrain figures are from the project's own ARCHITECTURE.md and read partly
  as stylized marketing (one in-source discrepancy on the classifier model size).
  The security PATTERNS are sound regardless; treat surrounding product claims
  with skepticism.
- gstack is human-sequenced role-switching, not multi-agent autonomy. Benchmark
  its defensive engineering, not its orchestration.
- Hermes "neutral alignment" means the model will not refuse on its own — the
  harness must supply all guardrails.
- OWASP Agentic Top 10 and MITRE ATLAS are living documents updated faster than
  annual cycles; re-map quarterly.
- MLX-vs-llama.cpp numbers come from community benchmarks with non-standardized
  methodology and vary by chip/quant/context; treat multipliers as directional.
- SWARM (wikimolt.org) and some 2026-dated CVEs/incidents could not be
  independently cross-verified against NVD/CVE.org in this pass; corroborate
  before treating CVE specifics as confirmed. The SWARM system-level-misalignment
  principle stands on its own merits regardless of the source's authority.

---

## 13. One-line summary

> Adopt gstack's layered injection defense and GBrain's memory trust triad, add
> the isolation/identity/egress controls they lack, govern the swarm at the
> system level (not just per-agent), and run it fast on M2 via Ollama's native
> MLX backend with a quantized KV cache.
