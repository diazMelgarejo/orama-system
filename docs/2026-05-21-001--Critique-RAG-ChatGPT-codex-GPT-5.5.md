> 📄 **REFERENCE 2026-06-14** — review/critique/notes input, not an execution plan.

# Critique: RAG + Memory + Optional gstack Planning Set

**Date:** 2026-05-21
**Reviewer:** ChatGPT Codex
**Scope reviewed:**
1. `docs/superpowers/specs/2026-05-21-rag-memory-gstack-design.md`
2. `docs/superpowers/plans/2026-05-21-rag-memory-v1-plan.md`
3. `docs/superpowers/plans/2026-05-21-gstack-optional-submodule-plan.md`
4. `docs/v2/20-rag-and-memory-design.md`
5. `docs/v2/19-gstack-optional-integration.md`

> Note: request says “6 docs” but only 5 were listed/provided in the prompt and present in repo.

---

## Executive verdict

Overall quality is **strong**: the set has clear decision traceability, practical fallback design, and good separation of v1 execution vs v2 evolution.

Main gaps are not architectural—they are **operational precision gaps**:
- inconsistent “planned vs done” language across docs,
- missing explicit SLO/error-budget targets,
- incomplete governance around retention/privacy controls for memory data,
- missing hard ownership/deadline metadata in task checklists,
- no formal deprecation calendar for v1→v2 tool transitions.

If addressed, the plans become both implementation-ready and audit-ready.

Evaluate each along these dimensions:

### A) Precision and falsifiability
- Concrete acceptance criteria and measurable outcomes.
- Explicit non-goals to prevent scope drift.
- Versioned assumptions (model/provider/infrastructure constraints).

### B) V1 execution quality (short-term)
- Dependency graph + critical path realism.
- Testability per milestone (unit/integration/e2e/rollback drills).
- Operational readiness: observability, failure modes, migration safety.

### C) V2 architecture durability (long-term)
- Stable interfaces and boundary ownership.
- Backward compatibility and data model evolution.
- Optionality economics (Gstack as optional submodule without hidden coupling).

### D) Risk and governance
- Security/privacy treatment for memory + retrieval data.
- Cost/latency budgets with guardrails and kill-switches.
- Change-management cadence and deprecation strategy.

### E) Plan quality standards (especially for item #2)
- Actionable task granularity (owner, artifact, exit criteria, deadline).
- Explicit “definition of done” at phase and plan level.
- Clear handoff from strategy docs to implementation docs.

---

## Scorecard (A–E)

| Dimension | Score | Rationale |
|---|---:|---|
| A) Precision & falsifiability | 7.5/10 | Good acceptance intent, but quantitative thresholds are not consistently explicit or machine-checkable. |
| B) V1 execution quality | 8.5/10 | Critical path is plausible and test-heavy, but rollback drills and production-like fault injection are underspecified. |
| C) V2 durability | 8/10 | Strong optionality boundaries and interface direction; needs explicit versioning/compat contracts and migration policy table. |
| D) Risk & governance | 6.5/10 | Failure fallback is good; privacy/security/cost governance not yet explicit enough for long-term operation. |
| E) Plan quality standards (#2 emphasis) | 7/10 | Task granularity is high, but owner/artifact/deadline/DoD metadata should be normalized per phase and plan-wide. |

---

## 1) Doc-by-doc findings

## 1. Spec — `2026-05-21-rag-memory-gstack-design.md`

### Strengths
- Excellent decision-trail table (AI suggestion vs user override) improves reproducibility and prevents architectural amnesia.
- Clear hybrid retrieval strategy (FTS5 + LanceDB + RRF) with explicit fallback mechanics.
- Practical reliability guardrails (`_pending_embeds`, `embed_status`, capped pending task set).

### Gaps / risks
- “~50ms added to every emit” appears as an assumption but is not defined as measured percentile (p50/p95/p99) nor tied to test environment.
- Fire-and-forget drop policy (“cap at 500 then leave pending”) is sensible but lacks explicit backlog drain objective and stale-pending threshold.
- Security/privacy handling of `payload_json` embeddings is implicit; no explicit classification, redaction, retention, or deletion semantics.

### Recommended upgrades
1. Add measurable SLO block in spec:
   - emit added overhead target (`p95 <= X ms`),
   - retrieval latency (`p95 <= Y ms`),
   - embedding success ratio (`>= Z%/24h`),
   - max pending rows age threshold.
2. Add non-goals section with explicit exclusions (cross-tenant retrieval, encrypted-at-rest vectors, auto-repair daemon in v1).
3. Add data-governance section: what can/can’t be embedded, retention window, redaction hooks, and erase workflow.

---

## 2. Implementation plan — `2026-05-21-rag-memory-v1-plan.md` (**most important**)

### Strengths
- High task detail with file-level mapping and test-first sequencing.
- Commit partitioning (retrieval then generation) reduces risk and improves bisectability.
- Strong fallback principle (FTS5 always available).
- Very good use of concrete tests for FTS, embed status, and graceful degradation.

### Gaps / risks
- Paths reference local machine absolute directories (`/Users/...`) which weakens portability/reproducibility in CI and other contributors’ environments.
- “Two commits” is useful but should not be treated as an invariant unless policy-enforced; can conflict with iterative fixups.
- Owner/deadline/exit criteria structure exists conceptually, but checklist tasks do not uniformly carry explicit owner and due date fields.
- Missing explicit rollback drill definition per milestone (e.g., disable LanceDB, simulate Ollama outage, verify service behavior & alerts).
- Plan includes extensive expected failures but not explicit “gate criteria table” mapping each phase to ship/no-ship outcome.

### Recommended upgrades (high priority)
1. Add **Phase Gate Table** per milestone:
   - Inputs, checks, required pass %, rollback tested (Y/N), approver role.
2. Convert each major task to metadata template:
   - **Owner**, **Artifact**, **Exit Criteria**, **Deadline**, **Dependencies**.
3. Replace absolute paths with repo-relative commands and add CI-equivalent command list.
4. Add explicit Definition of Done:
   - plan-level DoD,
   - phase-level DoD,
   - operational DoD (dashboards + runbook + kill-switch verified).
5. Add migration safety checklist:
   - schema forward/backward compatibility,
   - startup on existing DB,
   - idempotent init,
   - recovery from partial rollout.

---

## 3. gstack submodule plan — `2026-05-21-gstack-optional-submodule-plan.md`

### Strengths
- Optionality posture is correctly maintained (not hard dependency).
- Good idempotent installer/check-only approach and multi-source detection strategy.
- Clear “never raise” philosophy for tooling status pathways.

### Gaps / risks
- Detection contract semantics need stronger normalization (e.g., precedence rules, version parsing schema, timeout behavior) for long-term API stability.
- Optional tool status endpoint should define caching/TTL and refresh semantics to avoid expensive repetitive checks.
- Installer trust/supply-chain controls not explicit (pin, checksum, provenance expectations).

### Recommended upgrades
1. Specify `tool_status` JSON schema version (`schema_version`) and compatibility policy.
2. Define timeout and retry policy for `gbrain --version` / query calls.
3. Add supply-chain guardrails for submodule updates (approved tag/commit policy).
4. Add deprecation path if CLI wrapper transitions to MCP transport.

---

## 4. v2 RAG/memory design — `docs/v2/20-rag-and-memory-design.md`

### Strengths
- Good staged maturity model: v1 base, v2.1 circuit breaker, v2.5 reaper/fleet analytics.
- Backward compatibility intent is explicit around `scratchpad["context"]` shape stability.
- Circuit-breaker design is pragmatic and easy to reason about.

### Gaps / risks
- Document mixes “planned” and “DONE” language while v1 is not merged; this can create governance confusion.
- Circuit breaker is process-local; multi-instance behavior and observability expectations are not defined.
- Reaper + fleet architecture lacks ownership boundaries for conflict resolution and data consistency (who is source of truth when duplicates/divergence occur).

### Recommended upgrades
1. Normalize status taxonomy across docs: `Planned`, `In Progress`, `Merged`, `Released`.
2. Add breaker observability contract:
   - state metrics, open/close counters, cooldown events, alert thresholds.
3. Define consistency model for fleet dataset merge and idempotency strategy.
4. Add explicit migration sequence for v1→v2.1→v2.5 with rollback points.

---

## 5. v2 gstack integration — `docs/v2/19-gstack-optional-integration.md`

### Strengths
- Strong optional-sidecar design and good separation from core execution path.
- Clear invariants table (system starts without gstack; graceful no-op behavior).
- Portal UX direction is operationally useful.

### Gaps / risks
- API contract for sidecar transport switching (CLI vs MCP URL) is conceptual; not versioned with explicit behavior matrix.
- “register at import if available” may create startup-time side effects and environment-coupled behavior unless deterministic initialization policy is defined.
- Deprecation path from v1 wrapper to v2 sidecar module needs timeline and compatibility promises.

### Recommended upgrades
1. Define transport strategy matrix:
   - preferred transport, fallback order, timeouts, error mapping.
2. Move conditional tool registration to explicit startup hook with deterministic logs.
3. Add deprecation calendar for v1 wrapper and support window.

---

## 2) Cross-document consistency issues to fix now

1. **“Planned vs Done” inconsistency**
   - Some v2 docs label v1 components as “DONE” while plan/spec position them as pending. Use one canonical status vocabulary.

2. **Reference and repo-path drift**
   - Implementation plan references paths that may not match current repo layout in this branch context (absolute local paths). Make all commands reproducible in branch CI from repo root.

3. **Missing sixth document pointer**
   - Request references 6 docs; only 5 enumerated and present. Add explicit missing-doc placeholder if intended.

4. **Acceptance criteria fragmentation**
   - Criteria appear in prose/tests but not centralized. Add one single acceptance matrix per plan.

---

## 3) Dimension-by-dimension evaluation

## A) Precision & falsifiability

### Current state
- Strong qualitative direction and many concrete test examples.
- Not enough quantified thresholds and versioned assumptions as first-class artifacts.

### Required improvements
- Add explicit measurable targets for latency, reliability, recall quality proxy, and fallback behavior.
- Introduce assumption registry table: model version, Ollama version, LanceDB version, SQLite/FTS5 expectations, hardware profile.
- Add non-goals for each phase.

---

## B) V1 execution quality (short-term)

### Current state
- Dependency flow is sensible; critical path is viable.
- Good test decomposition across unit/integration.

### Required improvements
- Add rollback drills as mandatory gates (Ollama down, LanceDB unavailable, FTS table corruption, schema upgrade interruption).
- Add operator runbook requirements per milestone (symptom → diagnosis → mitigation).
- Add migration safety acceptance tests on pre-existing DB snapshots.

---

## C) V2 durability (long-term)

### Current state
- Stable conceptual boundaries: core retrieval substrate vs optional gstack sidecar.
- Thoughtful future phases (breaker/reaper/fleet).

### Required improvements
- Define stable interfaces with semantic versioning and ownership (module owner + change authority).
- Add data evolution policy for `gossip` schema and Lance table schema.
- Add compatibility matrix across versions (v1/v2.1/v2.5) and support windows.

---

## D) Risk & governance

### Current state
- Technical fallback risk is addressed (keyword-only mode, graceful degradation).

### Required improvements
- Security/privacy:
  - classify payload sensitivity,
  - PII handling/redaction prior to embedding,
  - retention and right-to-delete semantics.
- Cost/latency:
  - request budgets + breaker thresholds + kill-switches documented and testable.
- Change management:
  - release cadence and deprecation timeline with communication triggers.

---

## E) Plan quality standards (especially #2)

### Current state
- High-detail checklist with good engineering intent.

### Required improvements (must-have)
- Every top-level task should include:
  - owner,
  - artifact,
  - dependencies,
  - exit criteria,
  - deadline,
  - rollback verification step.
- Add explicit phase DoD and global DoD sections.
- Add strategy→implementation trace table linking spec decisions (D1..D7/OQs) to exact implementation tasks/tests.

---

## 4) Proposed edits (priority order)

### P0 (before implementation starts)
1. Normalize status language across all five docs.
2. Add centralized acceptance criteria + gate table to `2026-05-21-rag-memory-v1-plan.md`.
3. Add security/privacy and retention section to spec + plan.
4. Replace absolute paths with repo-relative runnable commands.

### P1 (during v1 execution)
1. Add explicit rollback drill tasks and expected outcomes.
2. Add observability checklist (metrics/logs/alerts) and attach to DoD.
3. Add tool-status schema version + transport/error behavior in gstack docs.

### P2 (before v2.1 starts)
1. Publish compatibility & deprecation matrix.
2. Add breaker/reaper operational playbooks.
3. Define fleet consistency semantics for Lance dataset merge.

---

## 5) Recommended acceptance matrix template (drop-in)

Use this for each phase in plan #2.

| Gate | Metric | Target | Evidence | Owner | Pass/Fail |
|---|---|---|---|---|---|
| Functional | FTS search correctness | 100% test pass | `pytest ...test_gossip_search.py` | Eng | |
| Resilience | Ollama outage fallback | No request failure, keyword mode active | fault-injection test | Eng/Ops | |
| Performance | emit added latency | p95 <= agreed threshold | benchmark report | Eng | |
| Operability | breaker visibility | metrics + alert route present | dashboard + alert screenshot | Ops | |
| Migration | existing DB upgrade | zero data loss, idempotent init | migration test logs | Eng | |

---

## Final recommendation

Proceed with the v1 implementation plan **after P0 edits** above are merged into the planning docs. The architecture is directionally right and pragmatically scoped; tightening measurability, governance, and status consistency will significantly reduce execution risk and make the plan durable for both rapid delivery and long-term maintenance.
