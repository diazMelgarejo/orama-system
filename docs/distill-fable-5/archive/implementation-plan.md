# Operationalize Claude Fable 5 Distillation Plan

This document outlines the action plan and to-do list to implement the enhancement suggestions from the "Repeatable and Sustainable Frontier-Model Integration Plan for Perpetua-Tools and orama-system" document. The goal is to prepare both repositories for the first Claude Fable 5 session.

- [implementation-plan.md](orama-system/docs/distill-fable-5/implementation-plan.md)
- [TODO.md](orama-system/docs/distill-fable-5/TODO.md)

## Further Analysis Needed: Caching & Batching Frontier Models

Based on our unified routing implementation and research into Helicone proxy-caching mechanisms, here is how the latest models are efficiently cached and batched, and where this capability belongs in our stack.

**1. Is it more in line with `Perpetua-Tools` (PT) or `orama-system`?**
This is **100% in line with Perpetua-Tools (PT)**. `orama-system` is the methodology—the "brains" that decides *what* needs to be executed (the 5-stage process, the agent graphs). However, `Perpetua-Tools` is the orchestrator and infrastructure backbone. The `MultiLLMRouter` (which handles API keys, base URLs, rate limiting, and hash-based caching) sits exactly at the gateway layer of PT. It acts as your localized Helicone proxy, guarding costs and ensuring redundant prompts across agents aren't re-computed.

**2. How GPT-5.5, Claude (Opus 4.8 / Fable 5), and GROK are efficiently cached & batched together:**
The `MultiLLMRouter` pattern in your document masterfully emulates Helicone's edge-caching patterns natively in Python:

- **Deterministic Hash-Based Caching:** By stringifying and hashing the message list and model name (`hashlib.sha256(content)[:32]`), your router creates an exact footprint of a prompt. If multiple agents in `orama-system` ask Claude Fable 5 or GPT-5.5 to process the same large file block or context, the router traps it and returns the cached result via Redis or LRU instantly—bypassing the API call entirely. This mimics Helicone's exact-match caching.
- **Task-Aware Routing & Batching:**
  - **Grok (e.g. grok-build-0.1):** Put on the "fast path" for rapid coding and agentic loops, likely leveraging continuous conversation ID caching.
  - **Claude Fable 5 / Opus 4.8:** Reserved for heavy `reasoning` and `planning`. Claude's native prompt caching (which Anthropic heavily enforces) shines here when massive context windows (like massive file imports) are sent repeatedly. The PT router respects this by sending it to Anthropic's endpoints correctly, while caching the final outputs locally.
  - **GPT-5.5:** Acts as a heavyweight fallback or primary reasoner. For bulk workloads that don't need instant turnaround, the router could easily shunt GPT-5.5 requests into OpenAI's Batch API to save 50% on costs, which is another advanced Helicone/proxy pattern.
- **Resilience (Rate Limit Backoff):** By tracking `time.time()` per provider, the router acts as a traffic cop. If Fable 5 hits a rate limit, the router catches the `RateLimitError` and seamlessly fails over to Opus 4.8 or GPT-5.5.

By emulating these Helicone/LiteLLM gateway patterns directly inside `Perpetua-Tools`, you achieve the exact same performance and cost-guarding benefits of a SaaS observability platform, while remaining completely local, frugal, and structurally idempotent.

## User Review Required

> [!IMPORTANT]
> **Toolchain Selection**: The integration plan suggests evaluating several open-source tools (e.g., Langfuse vs Helicone for prompt management, ClawRouter vs Manifest for routing). Do you want to implement all of them, or should we select specific ones to start with?

## Open Questions

1. **Frontier Export Format**: What format will the Claude Fable 5 chat exports be in (e.g., JSON from API, Markdown from UI, or a rich HTML file?)? This affects the parser in `distill_session.py`.
2. **Current Repo State**: Are there any existing mock implementations of `verify_before_done.py` or `capture_lesson.py` that we need to adapt, or will we be building the `distill_session.py` wrapper around fully functional scripts?

## Proposed Changes

We will divide the implementation into 4 phased components.

### 1. Distillation Workflow Automation (`distill_session.py`)

Create the core automation wrapper to process Fable 5 exports.

#### [NEW] `orama-system/bin/orama-system/scripts/distill_session.py`

- Build CLI interface to accept Fable 5 chat exports.
- Implement parsing logic (Stage 1).
- Implement interactive prompts for Refinement (Stages 2 & 3).
- Implement output generator for SKILL.md updates, agent roles, and configs (Stage 4).
- Integrate hooks to call `verify_before_done.py` and `capture_lesson.py` (Stage 5).

#### [NEW] `orama-system/docs/distill-fable-5/` directory structure

- Set up boilerplate for storing Fable 5 artifacts, `LESSONS.md`, and `MODELS_PERFORMANCE_DELTA.md`. This is centralized in `orama-system` since all depends on PT.

---

### 2. Configuration & Orchestration Enhancements

Update Perpetua-Tools to handle new heuristics, local-first routing, and cost guards.

#### [MODIFY] `Perpetua-Tools/orchestrator/model_registry.py`

- Add support for loading new Fable-derived heuristics.
- Implement dynamic capability checking for local models vs Fable 5 thresholds.

#### [MODIFY] `Perpetua-Tools/orchestrator/cost_guard.py`

- Add specific escalation rules ("when to escalate to cloud").
- Define budget thresholds for Fable 5.

#### [MODIFY] Config YAMLs (`models.yml`, `routing.yml`, `devices.yml`)

- Update schema/stubs to include fallback chains (e.g., `Oramasys → LM Studio Win → Ollama → LM Studio Mac`).

---

### 3. Testing and Verification Pipelines

Ensure distillations are verifiable against local models.

#### [MODIFY] `tests/` directories in both repos

- Add prompt evaluation test suites.
- Integrate **DeepEval** (or similar) to compare Fable 5 outputs vs local models.

#### [MODIFY] `.github/workflows/ci.yml`

- Integrate `pre-commit` and `Claude Pre-commit` tools to validate `SKILL.md` structures and YAML configs.

---

### 4. Frugal Toolchain Inspiration (Phase 1 Recommendations)

Instead of adopting heavy vendor infrastructure, we will adapt, copy, or emulate the best patterns from open-source tools:

#### [MODIFY] `orama-system` (Inspired by Langfuse)

- **Prompt Tracing & Versioning**: Emulate Langfuse's multi-turn "trace tree" and prompt versioning concepts natively inside `capture_lesson.py` and `LESSONS.md`. This provides the deep observability needed for complex agents without a full platform.

#### [MODIFY] `Perpetua-Tools` (Inspired by ClawRouter, Manifest, & Helicone)

- **Advanced Fallback Heuristics**: Adapt ClawRouter's 15-dimension weighted scoring (complexity, cost, latency, capability, safety) and Manifest's cost-tiering logic directly into `Perpetua-Tools/orchestrator/model_registry.py` and `cost_guard.py` for highly frugal, native, local-first routing.
- **Unified Multi-LLM Caching & Batching**: Adapt the `MultiLLMRouter` (inspired by LiteLLM / Helicone gateway patterns) in `perpetua-core/multi_llm_router.py` to efficiently batch and cache prompts for GPT-5.5, Claude Opus 4.8 / Fable 5, and Grok 4.3 using Redis/LRU hash-based deterministic caching. **This logic lives firmly in Perpetua-Tools**, as it handles the cost-guarding, API keys, and rate-limiting fallbacks.

## Verification Plan

### Automated Tests

- Run `pytest` on `distill_session.py` with mock Fable 5 chat exports (JSON/Markdown/HTML) to ensure it correctly outputs PR-ready files and updates the experience logs.
- Run `pre-commit` locally to verify that the newly generated `SKILL.md` snippets pass formatting and structural validation.

### Manual Verification

- Perform a dry-run of a mock Fable 5 session distillation end-to-end.
- Check if the output artifacts properly land in `orama-system/docs/distill-fable-5/`.
- Verify the orchestrator's fallback logic correctly routes requests based on the new cost-guard thresholds.
