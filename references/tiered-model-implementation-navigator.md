# Tiered Model Implementation Navigator

**Version:** 2026-07-22  
**Purpose:** Unified index for tiered model dispatch, frugality routing, skill trimming, and the ultrathink→oramasys migration.  
**Canonical location:** `references/tiered-model-implementation-navigator.md`  
**Cross-repo:** Also referenced from `Perpetua-Tools/docs/adr/` (ADR pointers to orama v2 decisions)

---

## Overview

This document maps the complete landscape of tiered model routing, context optimization, and the oramasys successor plan. Every decision, implementation plan, and reference file is linked here for navigation and cross-repo consistency.

**Key concepts:**
- **Tiers 0–6:** Frugality router dispatch hierarchy (local → cached → cheap external → expensive external)
- **Skill loading & context trimming:** Reducing bloat via selective reference bundling
- **Ultrathink → oramasys:** Complete rename + v2 repo migration (github.com/oramasys/oramasys)
- **Implementation roadmap:** P0–P5 phases, AC gates, dogfood evals

---

## Tier-1 Plans (Highest Relevance — Direct Match)

### 1. **`docs/plans/2026-05-29-03-v1.1-definitive.md`** ⭐ PRIMARY
**Canonical frugality router implementation plan.**

- **Content:** Complete v1.1 specification for tiers 0–6, tool routing, escalation rules
- **Sections:**
  - `§4`: Tier definitions (local/cached/cheap/expensive), escalation gates
  - `§7 (week 2–3)`: Implementation timeline
  - `§11`: Test/validation approach
- **Status:** Spike landed; 15 tests pass; operator PR review pending
- **Depends on:** Perpetua-Tools `orchestrator/frugality_router.py` implementation
- **Ref:** `bin/orama-system/skills/hermes-harness/references/assignments/mac-orchestrator-frugality-router-spike.md`

**Action:** Read this first for tier architecture and routing logic.

---

### 2. **`docs/v2/29-oramasys-mastery-implementation-plan.md`** ⭐ PRIMARY
**Complete successor plan: ultrathink → oramasys + v2 migration.**

- **Content:** Meta-layer integration (M1–M6), v2 repo scaffold, dependency order
- **Sections:**
  - `§1`: Current state snapshot (2026-06-13)
  - `§2`: Diff to add to `bin/orama-system/SKILL.md` (~50 lines, 0 changed)
  - `§3`: New reference files (collaborative-reasoning-safety.md, communication-guidelines.md)
  - `§4`: GOAL.md AC1 prerequisite (agent-methodology card fix)
  - `§5`: v2 repo migration path (flat structure, new skills)
  - `§6`: Programmatic deduplication checks
  - `§7`: AC gates (10 ACs, progression P0–P5)
- **Status:** Approved for execution — v2 migration active
- **Depends on:** GOAL.md AC1 (agent-methodology divergent 5-stage fix)
- **Outputs:** v2 repo scaffold, renamed skills, new reference files

**Action:** Read for mastery meta-layers, v2 structure, and AC progression.

---

### 3. **`bin/orama-system/skills/hermes-harness/references/assignments/mac-orchestrator-frugality-router-spike.md`**
**Spike implementation record: frugality router live code.**

- **Content:** Spike status, what's implemented vs deferred
- **Sections:**
  - Tier 0–6 definitions, `ToolCallSpec` / `ResolvedRoute` types
  - `ORAMASYS_OFFLINE=1`, `privacy_critical` gates
  - JSONL span tracing with `ot.tool.tier`
  - Follow-on work (frugality-report dashboard, test_realistic_session.py, full dispatch wiring)
- **Status:** Landed; unblocks G1 (re-run mac-g1-frugality-baseline.md checklist post-merge)
- **Depends on:** Perpetua-Tools spike branch merged
- **Ref:** SKILL.md author = Perpetua-Tools coord-007 (Mac orchestrator)

**Action:** Read for current spike status and what's deferred to P1 follow-on.

---

## Tier-2 Plans (Supporting Context — Related Architecture)

### 4. **`docs/v2/37-manifest-cost-tiering-pattern.md`**
**Cost-aware tiered dispatch pattern (generalized beyond frugality router).**

- **Content:** How to structure cost metrics, per-tier budgets, backpressure
- **Relevance:** Orthogonal to frugality tier 0–6 but compatible pattern
- **Uses:** Manifest-driven config for multi-model cost allocation

---

### 5. **`docs/v2/30-multi-llm-router-caching-batching-decorator.md`**
**Multi-model routing with caching and request batching.**

- **Content:** How tiers 3+ (expensive external) batch calls and cache responses
- **Relevance:** Caching strategy for tier 3+ escalations

---

### 6. **`docs/v2/36-clawrouter-scoring-pattern.md`**
**Router scoring: how to pick the right model per tier.**

- **Content:** Confidence scoring, latency vs quality tradeoffs
- **Relevance:** Model selection within a tier once tier is chosen

---

### 7. **`docs/plans/2026-05-29-01-cursor-PLAN.md`**
**Cursor integration plan (related to ultrathink/oramasys adoption in Cursor).**

- **Content:** How Cursor harness routes to oramasys (post-rename)
- **Status:** Design phase; related to broader CLI wiring

---

### 8. **`docs/plans/2026-06-14-plan-completion-tracker.md`**
**Master tracker: completion status of all tier/frugality/mastery plans.**

- **Content:** Checkpoints for each plan's AC gates, current status
- **Relevance:** Overall progress tracking across P0–P5

---

## Supporting References

### Frugality & Search Policy

- **`bin/orama-system/SKILL.md` § Search Policy**
  - Frugality chain: gbrain → CRG → Brave → Perplexity → Grok
  - Non-negotiable: stop at first tool that answers
  - Integrated with AFRP Type routing

- **`bin/orama-system/skills/oramasys-method/references/search-frugality.md`**
  - Decision tree: semantic intent → gbrain, symbol def → gbrain code-def, etc.
  - Harness fallback ladders (graceful-degradation.md)

### Skill Architecture & Trimming

- **`references/skill-architecture-guide.md`**
  - Why skills bundle examples/, eval/, references/
  - Cross-repo vs single-repo skill constraints
  - Canonical repo files (1536-char frontmatter, ../../references/) vs packaged .skill files (1024-char, metadata: envelope)

- **`bin/orama-system/skills/skillify/references/skill-folder-template.md`**
  - Standard folder shape for any new skill
  - examples/, eval/, references/ structure

- **`bin/orama-system/skills/skillify/references/dogfood-upgrade-log.md`**
  - Procedure for self-referential skill upgrades (skillify upgrading itself)
  - Audit notes from 2026-07-22 pass (both skillify and oramasys-method upgraded, .skill packaging validated)
  - Post-merge incident: ~/.claude/skills name collision (gstack's skillify vs orama-system's skillify) — **resolved 2026-07-22**: recovered gstack's clobbered file, renamed this repo's own colliding `gstack` skill to `gstack-gbrain`, extracted a shared `scripts/check-skill-namespace-collision.sh` guard called at both naming-time (skillify intake) and publish-time (`scripts/install-skills.sh`)

### Claude Code Mode 3 Execution + Model Tiering

- **`bin/orama-system/references/claude-code-workflow-canonical.md`** ⭐ NEW 2026-07-22
  - Canonical mapping: orama-system MODE 3 roles → Claude Code `Workflow` tool primitives (`agent()`/`parallel()`/`pipeline()`/`phase()`)
  - **Mandatory model tiering** for every MODE 3 `agent()` call — never inherit the parent session's model/effort:
    - Tier 1 (dispatch/control of non-Claude models — Codex, Cline, Kimi, Cursor, Grok, Perplexity, OpenClaw, Hermes): Haiku
    - Tier 2 (evaluate/integrate tier-1 output only): Sonnet 5, effort medium
    - Tier 3 (Opus / Fable 5): escalation-only — explicit user request, or `AskUserQuestion`-confirmed escalation; never automated
  - Wired from `bin/orama-system/SKILL.md` MODE 3, `oramasys-method/SKILL.md` Type→Mode mapping, `references/collaborative-reasoning-safety.md`
  - Distinct from the frugality router's tiers 0–6 above (that's TOOL routing — gbrain/CRG/Brave/Perplexity/Grok, local vs cached vs expensive external); this is MODEL routing for spawned Claude subagents specifically

### Ultrathink → Oramasys Rename

- **`GOAL.md`** (orama-system root)
  - AC1–AC10 gates for complete rename
  - Current status: AC1 (agent-methodology card) blocking AC2–AC10
  - Rename scope: ultrathink → oramasys in all public APIs, schemas, config, headings

- **`docs/LESSONS.md`**
  - Continuous learning log; lessons from each session
  - Cross-linked to `.claude/lessons/LESSONS.md` (thin wrapper, canonical is docs/)

### Portable Memory & Topology

- **`docs/v2/47-portable-memory-local-topology-invariant.md`** ⭐ CRITICAL
  - Banned: hardcoding workstation paths, credentials, device endpoints in tracked files
  - Allowed: `$WIN_CODER_ENDPOINTS`, `$OMNIROUTE_TOKEN`, portable-memory local-only registry
  - Supersession ≠ sanitization: delete the source row, regenerate derived views

### Multi-Agent Collaboration & Merging

- **`bin/orama-system/references/integrative-merge.md`**
  - PR merge doctrine: synthesize, never amputate
  - Six merge modes: additive → union → superset → synthesize → architecturally-correct → api-correct
  - Mandatory for nested-branch integration (oramasys Method Step 2)

---

## Cross-Repo Grounding (Required Before Any Decision)

**INVARIANT:** orama-system and Perpetua-Tools are interdependent. Always inspect BOTH repos.

| What | Canonical Location | NOT here |
|---|---|---|
| Frugality tier implementation | `Perpetua-Tools/orchestrator/frugality_router.py` + `orama-system/docs/plans/2026-05-29-03-v1.1-definitive.md` § 4,7,11 | — |
| Mastery meta-layers (M1–M6) | `orama-system/docs/v2/29-oramasys-mastery-implementation-plan.md` § 2–3 | — |
| Runtime state (L2 dispatch) | `Perpetua-Tools/orchestrator/` | orama-system (L3, stateless) |
| PT ADR pointers | `Perpetua-Tools/docs/adr/ADR-NNN-*.md` | Generated from orama v2 decisions |
| v2 repo bootstrap | `orama-system/docs/v2/29-oramasys-mastery-implementation-plan.md` § 5 | github.com/oramasys/oramasys |

---

## Implementation Sequence (P0–P5)

```
P0: Rename (GOAL.md AC1–AC10)
    ├─ Fix agent-methodology card (AC1)
    └─ Rename all public APIs (AC2–AC7)
       |
P1: Apply SKILL.md diffs + reference files (§ 2–3)
    ├─ Add Meta-layers (Spec Contract, Amplifier Tree, Collaborative Safety, Output Discipline)
    └─ Create reference files (collaborative-reasoning-safety.md, communication-guidelines.md)
       |
P2: v2 repo scaffold (flat structure, new skills)
    ├─ skills/oramasys, skills/oramasys-method
    └─ skills/prompt-engineering, skills/spec-contract
       |
P3: Frugality router integration (PT v1.1)
    ├─ Wire orchestrator/frugality_router.py into all dispatch paths
    └─ Implement tier gates (ORAMASYS_OFFLINE, privacy_critical)
       |
P4: Skill trimming & loading optimization
    ├─ Selective reference bundling (examples/, eval/ per tier)
    └─ Dogfood evals for shrunk skills
       |
P5: Tag v1.1.0 lockstep (orama-system + Perpetua-Tools)
```

---

## GBrain + Code-Review-Graph Alignment

Both use **Ollama bge-m3** (1024-dim, local, free):
- **gbrain:** 5 sources (AlphaClaw 478pp, PT 725pp, orama-src 192pp, periscope 14pp, default 1599pp)
- **CRG:** 1,461 nodes, 1,257 bge-m3 embeddings, 12 communities (orama-system graph)
- **Storage roadmap:** v2.1 LanceDB + bge-m3 for RAG/session memory; v2.5 DuckDB for fleet analytics
- **GossipBus:** Job/decision-history migration to LanceDB (not bespoke persistence) — validated live 2026-07-12

---

## Key Files Summary Table

| File | Purpose | Tier | Status | Action |
|------|---------|------|--------|--------|
| `docs/plans/2026-05-29-03-v1.1-definitive.md` | Frugality tier 0–6 spec | 1 | Spike landed | Read §4,7,11 |
| `docs/v2/29-oramasys-mastery-implementation-plan.md` | Mastery + v2 migration | 1 | Approved | Read §1–7 for context & ACs |
| `bin/orama-system/skills/hermes-harness/references/assignments/mac-orchestrator-frugality-router-spike.md` | Spike status | 1 | Live | Read for current state |
| `docs/v2/37-manifest-cost-tiering-pattern.md` | Cost dispatch pattern | 2 | Design | Skim for orthogonal approach |
| `docs/v2/30-multi-llm-router-caching-batching-decorator.md` | Caching for tier 3+ | 2 | Design | Reference if escalating to expensive |
| `docs/v2/36-clawrouter-scoring-pattern.md` | Model selection within tier | 2 | Design | Reference for scoring logic |
| `bin/orama-system/SKILL.md` | Mother skill | Core | Live | Frugality chain in step 1 |
| `bin/orama-system/skills/oramasys-method/SKILL.md` | oramasys user skill | Core | Live v1.3.2 | Read for AFRP + 5-stage + frugality |
| `GOAL.md` | Rename gates AC1–AC10 | Core | In progress | AC1 blocking, track for P0 completion |
| `docs/v2/47-portable-memory-local-topology-invariant.md` | Security/hygiene | Core | Canonical | Read before any config edits |
| `bin/orama-system/skills/skillify/references/dogfood-upgrade-log.md` | Self-upgrade audit trail | Reference | Live 2026-07-22 | Read for skill upgrade procedure |
| `bin/orama-system/references/claude-code-workflow-canonical.md` | Mode 3 → `Workflow` tool mapping + mandatory model tiering | Core | Live 2026-07-22 | Read before authoring any MODE 3 `Workflow` script |

---

## How to Use This Document

1. **Planning a tier/routing change?**
   → Read `docs/plans/2026-05-29-03-v1.1-definitive.md` § 4 (tier definitions)

2. **Implementing v2 migration?**
   → Read `docs/v2/29-oramasys-mastery-implementation-plan.md` § 5–7 (scaffold + ACs)

3. **Applying a frugality optimization?**
   → Follow `bin/orama-system/SKILL.md` Step 1 (search frugality chain)

4. **Upgrading a skill (skillify on itself)?**
   → Follow `bin/orama-system/skills/skillify/references/dogfood-upgrade-log.md` (procedure)

5. **Cross-repo consistency check?**
   → Verify both Perpetua-Tools and orama-system before deciding (see "Cross-Repo Grounding" above)

6. **Checking current progress?**
   → Consult `docs/plans/2026-06-14-plan-completion-tracker.md` (master status)

---

## Related Concepts

- **AFRP gate** (oramasys Method Step 0): Type A/B/C/D, Novice/Practitioner/Expert, Mode 1/2/3
- **CIDF** (Content Insertion Decision Framework): Rank-1–6 insertion protocol before any content lands
- **TDD gate** (oramasys Method Step 4): Programmatic verification before "done"
- **Integrative merge** (oramasys Method Step 2): Additive harmonization, never delete-and-replace
- **Search frugality** (oramasys Method Step 1): gbrain → CRG → Brave → Perplexity → Grok

---

## Close-Out: P3 Frugality/Privacy Historical Trail (2026-07-22)

**Why this section exists:** the 2026-07-22 `/autoplan` pass on this navigator found `orchestrator/frugality_router.py` has zero real callers, and initially framed this as "three unreconciled privacy/frugality implementations." A gbrain trace back through the hermes-harness assignment/result records and `v1.1-definitive.md`'s own text corrects that framing — the gap is real, but it is not an accidental architectural collision. It is a **named, deferred TODO from the original spike that was simply never picked back up.**

**The trail, most-recent-development back to original motivation:**

1. **2026-05-29** — `docs/plans/2026-05-29-03-v1.1-definitive.md` §4/§6.1 specifies `frugality_router.py` as "a single chokepoint for tool/model calls." This is the origin of the "should be the one gate" intent.
2. **2026-06-14** — same plan's header gets a `✅ RESOLVED` banner: "v1.1 shipped: oramasys AC rename + frugality + tiered OpenRouter via PR #76 (`89283e8`), #74, #82." **"Shipped" here means the module merged with its own unit tests passing — not that any real dispatch path calls it.** This is a genuine wording risk in the historical record (a stale reader could reasonably take "shipped" as "wired"), but it is not a fabricated claim.
3. **2026-06-29** — `bin/orama-system/skills/hermes-harness/references/assignments/mac-orchestrator-frugality-router-spike.md` (the actual spike assignment) explicitly lists, under **"Not in spike (follow-on P1)"**: *"Wire into all dispatch paths (supervisor, fastapi_app)."* The wiring gap was named and scoped out on day one — never silently dropped.
4. **2026-06-29** — `bin/orama-system/skills/hermes-harness/references/assignments/win-coder-pt199-frugality-review.md` + its result `references/results/win-pt199-frugality-reconcile.md`: Win coder reviewed PR #199 (the spike), confirmed 15/15 unit tests pass, found no blocking issues, and recommended merge — **the review's own scope was "does the module work in isolation," not "is it wired in."** Approved on those terms.
5. **2026-07-22 (this session)** — `docs/v2/30-multi-llm-router-caching-batching-decorator.md` (a *separate*, later ADR, dated 2026-06-15 in its own footer) independently documents `ModelRegistry.route_task` as **"HTTP `/orchestrate` only"** and explicitly forbids the dispatch path (`supervisor.py`'s `_dispatch`) from calling it — i.e., `route_task()`'s scope (general task-type routing) and `_dispatch`'s scope were already deliberately kept separate **by design**, not by accident. This ADR never mentions `frugality_router.py` at all — confirming the two systems evolved on independent tracks with no cross-reference, which is itself the root cause of the fragmentation (not malice or carelessness, just two efforts that never got introduced to each other).

**Revised framing (supersedes "three unreconciled implementations"):**

- `config/routing.yml`'s task_type exclusion + `src/perpetua_tools/orchestrator.py`'s `req.privacy_critical` chain are **two faces of one documented, working mechanism**: general routing policy (routing.yml, always-on) plus an explicit per-request override (orchestrator.py, opt-in via request field). They are not in conflict — they compose today, in production, right now.
- `orchestrator/frugality_router.py` is the **outlier**, and it is an outlier by omission, not by design collision: its own spike doc named the exact follow-on task ("wire into all dispatch paths") that would have prevented today's finding, and that task simply sat unpicked for ~3 weeks (2026-06-29 → 2026-07-22) while other P1/P2/P4 work took priority.
- **Practical implication for `docs/plans/2026-07-22-frugality-privacy-reconciliation-and-navigator-closeout.md` Item 1:** this is closer to "finish a known-deferred integration task with a design decision attached" than "resolve a three-way architectural dispute." The design question that still needs a human call is narrower than originally scoped: *does `frugality_router.py` become the thing `routing.yml`/`orchestrator.py` delegate to, or does it stay a parallel, optional tier-tracking layer that only some call sites opt into?* Both are legitimate answers — Codex's "single policy gate" proposal answers "delegate to it"; the additive-only `ModelTarget.frugality_tier` field shipped 2026-07-22 is compatible with either answer, which is why it was safe to land ahead of the decision.

**Lesson for future navigator upkeep:** a plan's own "Not in spike / follow-on" section is a load-bearing TODO list, not throwaway scoping prose — when auditing "is X actually wired," check the spike doc's own deferred-work section before concluding the gap is undocumented. It usually isn't.

### Cross-Repo Plan Register — unaudited/unfinished plans found while tracing this trail (2026-07-22)

Not absorbed into this navigator's scope or into the frugality/privacy
reconciliation plan — listed here so they don't scatter across future
sessions, per the same "name it, don't silently drop it" discipline as the
reconciliation plan's own "Explicit non-goals" section.

| Plan | Repo | Status (as found 2026-07-22, not re-verified) | Relation to this navigator |
|---|---|---|---|
| `docs/plans/2026-06-14-plan-completion-tracker.md` | orama | Says `COMPLETE` (2026-06-14) — **stale**: this session's own P3 trail shows live open work postdating it | Superseded by this navigator + the reconciliation plan for P3; treat the 2026-06-14 "COMPLETE" claim as outdated for frugality |
| `docs/plans/2026-06-24-optimization-priorities.md` | orama | `🔄 ACTIVE` — L1 skipped, L6 schemas still "📋 planned" | Independent backlog; not frugality-related, but shares the "stale-looking, actually still open" pattern found this session |
| `docs/plans/2026-07-14-orama-housecleaning-leftovers-next-steps.md` | orama | Next-steps doc, not status-tagged | Unaudited this session — check before assuming closed |
| `docs/plans/2026-07-06-orama-skill-upgrade-roadmap.md` | orama | "PR 1 planning artifact" | Unaudited whether PR2+ landed; the P4 skill-trimming work done 2026-07-22 (this session) may partially satisfy it — not cross-checked |
| `Perpetua-Tools/docs/2026-05-31-tri-repo-alignment-completion-plan.md` | PT | Own header: "active resume anchor" | Genuinely still open per its own text; this navigator's Item 2 (closeout plan) already flags it needs re-verification, not yet done |
| `Perpetua-Tools/docs/references/phase0-and-orama-open-work-closure-plan-2026-07-18.md` | PT | "planning handoff; no implementation or merge authorized by this file" | Recent (2026-07-18), unaudited against current state — check before next Phase 0 work |
| `Perpetua-Tools/docs/next/2026-07-17-coordination-module-consolidation-plan.md` + its review `docs/references/coordination-consolidation-plan-review-2026-07-18.md` | PT | `/autoplan` CLOSED — Parts 1/1b/1c/1d dispatch-ready; Part 2 drafted not executed; Part 3 deferred | Active, adjacent workstream (coordination/queue module) — unrelated to frugality/privacy but same repo, same era; worth a status re-check in the same pass that revisits tri-repo-alignment |

**Verdict on this register:** none of these are frugality/privacy-topic
matches — they're independent unfinished threads surfaced as a byproduct of
walking both repos' `docs/` trees for this trace. Recorded here rather than
silently ignored; resolving them is out of scope for the P3 reconciliation
work above.

---

## Close-Out: Item 1 Design Decisions — Full Circle (2026-07-22)

All design questions this navigator's P3 trail surfaced are now decided and
recorded in `docs/plans/2026-07-22-frugality-privacy-reconciliation-and-
navigator-closeout.md` § "Item 1." Summarized here so this navigator stays
the single index — full reasoning lives in the plan doc, not duplicated.

1. **Canonical gate:** `frugality_router.py`'s `resolve_route()` becomes the
   single policy gate `route_task()` and `orchestrator.py`'s `privacy_critical`
   branch both call — human-confirmed, with a mandatory override contract
   (`override_confirmed` + `override_reason`, never a silent bypass).
2. **API shape:** `route_task()` keeps its v1 signature unchanged; a thin
   wrapper carries the gate call. A signature change is explicitly deferred
   to whatever v2 shape lands per `docs/v2/` planning — not decided here.
3. **`frugality_tier` backfill ownership:** at model-registration time, by
   whoever edits `config/models.yml` — EXA research into LiteLLM's
   "config models are owned by the file" pattern, applied at PT's actual
   scale. Unset tier means "gate has no opinion, defer to existing
   fallback chain" — never "assume permissive." Guards against LiteLLM's
   own documented silent-fallback failure mode.
4. **Free-tier cross-check (gbrain + CRG + PT `.agent` memory — no paid
   research needed, confirmed rather than changed anything):** hardware
   affinity (`check_affinity()`) is already the real first gate, wired
   ahead of dispatch (CRG-confirmed caller graph: `supervisor.py`'s
   `submit_job` / `_prepare_spec_for_inference`); PT's existing "fail-closed
   at gateways, never silent fallback" doctrine does not conflict with the
   backfill decision (unset tier isn't a failure, it's an absence of
   opinion); `OmniRoute` is already the documented free-alternative-of-
   last-resort, no new mechanism needed.
5. **ECC-style model selection (`vendor/ecc-tools/commands/model-route.md`,
   confirmed real):** a distinct, correctly-scoped axis — ranks *Claude
   subagent* model choice (haiku/sonnet/opus by complexity+risk+budget),
   not PT's local model registry. Legitimate as the fallback default for
   an *unclassified Claude subagent spawn*, and safely cacheable/idempotent
   per task-signature since it's a pure function with no external state.
   Flagged as a follow-on optimization, not folded into Item 1's PT-local
   scope — kept the two "model selection" concepts distinct rather than
   merged, per this session's own established discipline against
   conflating adjacent-but-different systems.

**Genuinely still open (implementation-time, not design-time):** exact
override UI copy/flow for CLI/dashboard-modal paths; `models.yml` per-model
tier values themselves (the ownership rule is decided, the actual backfill
data entry is not); the ECC-model-route caching optimization (flagged,
not built).

**Execution status:** a `Workflow` run (Haiku-survey → Sonnet-implement →
Sonnet-verify, launched under this session's `ultracode` opt-in) is
wiring the decided architecture into Perpetua-Tools as of this entry —
see the plan doc's Execution Log for the actual diff and test results
once it lands.

---

**Last updated:** 2026-07-22  
**Maintained by:** orama-system + Perpetua-Tools coordination (two-repo grounding)  
**Feedback:** Append to `docs/LESSONS.md` with session + discovery
