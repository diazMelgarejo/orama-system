# Operationalize Claude Fable 5 Distillation Plan

> **Status (2026-06-13):** /autoplan-reviewed (Codex + Claude, 6/6 eng consensus, 0 disagreements).
> **Approved scope:** offline, model-agnostic **v1**; everything model-calling/stateful **deferred to v2**.
> Live Fable 5 trial happens in **Claude Code on Claude Desktop** (RAG wired there) as the v2 kickoff.

This plan turns frontier-model session exports into PR-ready SKILL.md / agent / config updates.
The original draft tried to do that **and** stand up live frontier routing, caching, batching, an
eval framework, and emulate four OSS tools in one release. The review cut v1 to the part that ships
in days against assets we already have; the ambitious infra moved to a v2 backlog (preserved verbatim
below as rationale).

---

## V1 — Offline distillation CLI (approved)

`distill_session.py` is a **stateless orama tool**. It reads a session export, runs the existing
verification + lesson hooks, and emits **proposed** artifacts/diffs for human review. It does NOT call
models, hold routing/cache state, require API keys, touch the network, or mutate Perpetua-Tools.
Runtime changes (routing/cost) land later via a separate PT PR that applies the proposals.

### Scope
- **[NEW]** `orama-system/bin/orama-system/scripts/distill_session.py` — offline CLI.
  - `--input <export>` + `--dry-run`; parser behind a `SessionExportParser` interface
    (one concrete format for v1; **Fable 5 = a later adapter**, see v2).
  - Emits `docs/distill-fable-5/runs/<timestamp>/`: normalized transcript, extracted lessons,
    **proposed** SKILL.md / agent / config snippets (diffs, not applied), verification summary.
  - Unknown export format → clear error (`unsupported export format: got X, expected Y`), not a stack trace.
  - `--non-interactive` is the default for agent use; interactive refinement (Stages 2–3) is an opt-in human path.
- **[NEW]** `docs/distill-fable-5/fixtures/` — at least one **real** export sample (v1 builds/tests against it).
- **[INTEGRATE, existing]** call `bin/orama-system/scripts/verify_before_done.py` and
  `capture_lesson.py` through their current CLI; **fail closed** if either exits non-zero (or record an
  explicit skip reason). These scripts already exist — do not re-stub them.

### Acceptance criteria (v1 done means)
1. `python bin/orama-system/scripts/distill_session.py --input <fixture> --dry-run` exits `0`.
2. Emits a `runs/<ts>/` dir with: normalized transcript, extracted lessons, proposed PT snippets, verification summary.
3. Creates **no** router/cache state; requires **no** cloud credentials; makes **no** network calls (no-network regression test passes).
4. Existing `verify_before_done.py` + `capture_lesson.py` are invoked, or explicitly skipped with a recorded reason.
5. Unknown-format input is rejected with the documented error and a non-zero exit.

### Tests (v1)
- Parser fixture test; dry-run output structure/snapshot test; hook-invocation test (mocked); no-network regression test; unknown-format rejection test.

### Group A — tools already in Claude (immediately usable with Fable 5)

> **Emulation, not importation** — but Group A is different: these tools are built INTO Claude,
> not external OSS to evaluate or pip-install. They are usable right now with actual Fable 5 runs.
> No waiting for a "future Desktop trial" — the v2 kickoff is immediately achievable.

| # | Tool | Role |
|---|------|------|
| [6] | Claude Chat Exporter | Export real Fable 5 sessions → input for `distill_session.py`; the export format drives `FableExportParser` |
| [8] | AI Distiller | Distillation pipeline available in Claude directly; `distill_session.py` operationalizes this as an orama-native CLI |
| [11] | Claude Pre-commit | SKILL.md structural validation — available now for CI wiring |
| [12] | Pre-commit Framework | Hook framework — wired as orama hooks (`verify_before_done.py`, `capture_lesson.py`) |

**Kickoff path (immediate):** Run Claude Chat Exporter on a real Fable 5 session → pass the output to
`distill_session.py --input <export>` → discover actual Fable 5 JSON schema → build `FableExportParser`
as a drop-in `SessionExportParser` adapter. This IS the v2 kickoff, not a future prerequisite.

---

## V2 — Backlog (deferred; ADR-gated)

Kicked off once we trial **live Fable 5 via Claude Code on Claude Desktop**. Each item needs an ADR
before build because it adds runtime state, cost, or a dependency.

- **`MultiLLMRouter` — does NOT exist today (greenfield, not "adapt existing").** When built, it must be a
  **caching/batching decorator over the existing dispatch** (`orchestrator/worker_registry.py` +
  `model_registry.py` + `backend_resolver.py`), **never a parallel router** (DRY). Lives in **Perpetua-Tools** only.
- Caching correctness/safety: cache only successful, temperature-0 calls; TTL; never persist raw prompts
  (PII/secret redaction); cache-key isolation; invalidation. (Absent in the original draft.)
- Frontier routing + budgets: add Fable 5 / Opus 4.8 / GPT-5.5 / Grok thresholds to `cost_guard.py`
  **when those providers are actually called**; cloud escalation **default-deny**; "4x Fable budget" gate
  **fails closed** (blocks), keys via Keychain/.env never config.
- Eval: a **minimal output-diff harness** on a fixed prompt set first; DeepEval only if that proves insufficient.
- **OSS-pattern emulation** (emulation not importation; ADR per tool before any code):

  **Group B — v2 routing/caching patterns (4 tools, ADR-gated):**

  | # | Tool | v2 emulation target |
  |---|------|---------------------|
  | [1] | Langfuse | Trace-tree pattern → additive extension of `capture_lesson.py`/`LESSONS.md`; stays **methodology in orama**, never runtime state in PT |
  | [2] | Helicone | Proxy-caching pattern → hash-based LRU inside PT's `_dispatch`; never a separate service |
  | [3] | Manifest | Cost-tiering pattern → extend `cost_guard.py` escalation rules |
  | [4] | ClawRouter | 15-dim weighted scoring → extend `model_registry.py` dynamic thresholding |

  **Fully deferred — v2 ADR or cut (9 tools):**
  [5] NadirRouter · [7] Claude Artifact Unpacker · [9] DeepEval · [10] Agent-Distillation · [13] Cozeloop
  — each needs an ADR justifying inclusion before any implementation. Full 13-tool parity is a v2 goal, not a v2 mandate.
- Batch API "save 50%" claim: unproven for this workload — treat as a hypothesis to measure, not a target.

### V2 rationale (preserved from the original draft — caching/batching analysis)

> The `MultiLLMRouter` pattern emulates Helicone's edge-caching natively in Python:
> **Deterministic Hash-Based Caching** (hash the message list + model name → LRU), **Task-Aware Routing
> & Batching** (Grok fast-path for agentic loops; Fable 5 / Opus 4.8 for heavy reasoning with native
> prompt caching; GPT-5.5 as heavyweight fallback, bulk → OpenAI Batch API), and **Rate-Limit Backoff**
> (track `time.time()` per provider; on `RateLimitError`, fail over). This caching/cost-guarding logic
> **lives firmly in Perpetua-Tools** (L2 runtime), never in orama (L3 stateless methodology).

### V2 implementation notes (corrected — supersede Grok's AntiGravity reference)

**`perpetua-core/multi_llm_router.py` framing:** This path is the v2 target package structure from
Grok's architectural reference (AntiGravity-in.md). It is greenfield — NOT an adaptation of anything
existing. The correct v1 seam is `OrchestrationSupervisor._dispatch` at `supervisor.py:534`; the v2
caching/batching decorator wraps `_dispatch`, not the individual workers.

**Grok's model ID errors (correct before any v2 code):**

| Grok draft (wrong) | Correct API model ID |
|--------------------|----------------------|
| `claude-4-sonnet-4.6` | `claude-sonnet-4-6` |
| `claude-fable-5-max` | `claude-fable-5` |
| `claude-opus-4.8` | `claude-opus-4-8` |

**Anthropic API — not OpenAI-compatible:** Grok's reference uses `AsyncOpenAI(base_url="https://api.anthropic.com")`.
This is architecturally valid as a routing pattern, but Anthropic's API is `POST /v1/messages`,
not `POST /v1/chat/completions`. The v2 Anthropic leg must use `anthropic.AsyncAnthropic()`, not
the OpenAI client. Other providers (OpenRouter, Grok, GPT-5.5) may use the OpenAI-compatible path.

**ADR gate:** each v2 item needs an ADR before build. Next free number: ADR-030
(see `orama-system/docs/v2/` for existing ADRs).

---

## Resolved questions
- **Export format (was Open Q#1):** v1 ships with `orama-session-export-v1` + `json-transcript-list`.
  `FableExportParser` is next: Claude Chat Exporter is built into Claude and can produce a real Fable 5
  export immediately — run it, observe the schema, drop in the adapter (one `_PARSERS` append, no other changes).
- **Mock vs real scripts (was Open Q#2):** `verify_before_done.py` + `capture_lesson.py` already exist —
  call them through their current CLI contract; no stubs.
- **Toolchain deliberation (Langfuse/Helicone/ClawRouter/Manifest):** deferred to v2 ADRs; not a v1 decision.

## Program-level success metrics (v1 → v2 progression)

Three compounding metrics track whether distillation is working:

| Metric | v1 baseline | v2 target | Measurement |
|--------|------------|-----------|-------------|
| **Compounding Score** | 0% tasks solvable locally post-distill | Rising % over 30 days | Manual: count tasks completed without cloud model |
| **Mistake Rate Decline** | Baseline from current `capture_lesson.py --stats` | Declining category totals | `capture_lesson.py --stats` diff month-over-month |
| **Cost Reduction** | Baseline frontier model $ per week (PT cost_guard.log) | Declining $/equivalent task | PT `cost_guard.py` weekly report |

These are measured, not assumed. "Batch API saves 50%" is a hypothesis; measure first.

## Decision audit trail (/autoplan, 2026-06-13)

| # | Decision | Class | Principle | Rationale |
|---|----------|-------|-----------|-----------|
| 1 | Defer 4-tool emulation (Phase 4) to v2 | auto | P2/P3 | TODO already half-marked v2; out of v1 blast radius |
| 2 | `MultiLLMRouter` = decorator over existing dispatch or ADR; never parallel router | auto | P4 (DRY) | worker/model registries already route |
| 3 | Drop DeepEval from v1; minimal diff-harness | auto | P5 | explicit over a heavy dep |
| 4 | v1 ships with a real fixture + acceptance tests | auto | P1 | untestable without a real export |
| 5 | v1 offline, emits proposals, no PT mutation | auto | P4/P5 | enforces L3-stateless / L2-runtime boundary |
| 6 | Parser format-agnostic + adapter (vs Fable-specific now) | taste | P1 | survives unknown Fable export format |
| 7 | Reframe "live Fable v1" → offline model-agnostic v1, Fable live in v2 | **user challenge — APPROVED** | — | both models agreed; user confirmed, will trial Fable live via Desktop |
