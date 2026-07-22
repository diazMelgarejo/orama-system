<!-- /autoplan restore point: ~/.gstack/projects/diazMelgarejo-orama-system/main-autoplan-restore-20260722-163957.md -->
# P4 Skill Trimming, then P3 Frugality Router Wiring — Synthesized Plan

**Date:** 2026-07-22
**Synthesized from:** `references/tiered-model-implementation-navigator.md`'s
Implementation Sequence (P0–P5), per explicit user direction: prioritize the
unfinished aspects — P4 first, P3 second, everything else after. P0
(rename/GOAL.md), P1 (reference files), P2 (v2 scaffold — repo exists,
depth unverified), and P5 (v1.1.1 tag) are already done; not re-litigated
here except where they inform scope.
**Branch:** `main` (this session's established direct-to-main pattern, `ALLOW_MAIN_PUSH=1`)
**Reviewed by:** `/autoplan` (this document)

---

## Premises

1. The navigator's own "P4: Skill trimming & loading optimization" and "P3:
   Frugality router integration" are real, currently-unfinished work items,
   not aspirational — grounded below with concrete evidence.
2. Trimming (P4) is lower-risk and self-contained (single repo, doc-only,
   mechanical) than wiring (P3, cross-repo, touches live dispatch logic) —
   this is the basis for the user's prioritization, not just an arbitrary
   ordering.
3. "Everything else" in the navigator (remaining P2 depth-verification,
   `docs/2026-05-31-tri-repo-alignment-completion-plan.md`'s still-`🔄
   active` tri-repo alignment anchor, the deferred Periscope L4 plan) stays
   explicitly out of scope for this plan — named, not silently dropped.

## What Already Exists (do not rebuild)

- `bin/orama-system/skills/fable5-tier-based-routing/SKILL.md` (795 lines)
  already fully documents `frugality_router.py`'s real tier-0–6 hierarchy,
  cost-guard behavior, and timeout enforcement — the DOC side of P3 is done.
  What's missing is the CODE side: nothing calls it.
- `Perpetua-Tools/orchestrator/frugality_router.py` (255 lines,
  `resolve_route()` as the public entry point) is fully implemented and
  merged (PT PR #199 spike + PR #200 bugfix), with its own test suite.
- The skillify dogfood pattern from earlier today (`examples/good/`,
  `examples/bad/`, `eval/checklist.md`, `eval/evals.json`,
  `references/*.md` for anything long) is the established modular-trimming
  shape for this repo — reuse it verbatim for P4, don't invent a new one.

## NOT in Scope

- Rewriting `frugality_router.py` itself (P3's bugs/design are PT's, not
  this plan's — only the wiring-in is in scope).
- The v2 `github.com/oramasys/oramasys` repo's actual content depth (P2) —
  confirmed to exist (HTTP 200) but not cloned/audited; separate scope.
- `docs/2026-05-31-tri-repo-alignment-completion-plan.md` (still `🔄
  active` per the 2026-06-14 completion tracker) — a distinct, larger
  cross-repo initiative, not a P3/P4 dependency.
- Periscope L4 integration (explicitly `⏭️ deferred` in the tracker, "the
  only plan with real remaining implementation grunt" per its own words —
  too large to fold into this plan).

---

## Phase A (P4) — Skill Trimming & Loading Optimization

### A0. Grounded scope (measured today, not estimated)

```
866 lines  bin/orama-system/skills/mcp-orchestration/SKILL.md
795 lines  bin/orama-system/skills/fable5-tier-based-routing/SKILL.md
430 lines  bin/orama-system/skills/hermes-harness/SKILL.md
410 lines  bin/orama-system/skills/hardware-affinity-gate/SKILL.md
```

Only the first two exceed skillify's own hard ceiling (<=500 lines for
existing/exceptional files, per `skillify/references/modular-skill-authoring.md`
§ Size Rules). Those are Phase A's targets. `hermes-harness` and
`hardware-affinity-gate` are large but under ceiling — flagged, not
in scope for this pass (avoid scope creep past the two genuine violations).

### A1. `mcp-orchestration/SKILL.md` (866 → target <500)

Current top-level sections (14, `## 1`–`## 14` plus Executive Rule / Hermes
Operator Shell): MCP Fundamentals, Routing strategy, Install Baseline,
gemini-mcp-tool, ai-cli-mcp, OpenClaw Integration, Build a New Claude
Skill, Custom MCP Server Skill, Tool Search, Troubleshooting, LESSONS.md
Pattern, Verification Checklist, Agent Instruction Block, Decision Table.

Extraction candidates (move to `references/`, keep a pointer + 2-3 line
summary in `SKILL.md`):
- `§4 gemini-mcp-tool` and `§5 ai-cli-mcp` → `references/gemini-and-ai-cli-mcp-setup.md`
  (install/config detail, not decision-time content)
- `§8 Custom MCP Server Skill` → `references/custom-mcp-server-authoring.md`
- `§10 Troubleshooting` → `references/troubleshooting.md`
- `§11 LESSONS.md Pattern` → fold into existing repo-wide lessons doctrine
  (`docs/LESSONS.md` already documents this; this section may be a stale
  duplicate — verify during execution, don't just move it if so)

Keep in `SKILL.md` (decision-time, load-bearing every invocation): Executive
Rule, Routing strategy (`§2`, explicitly marked "READ FIRST"), OpenClaw
Integration (`§6`, frequently-triggered), Decision Table (`§14`), Agent
Instruction Block (`§13`).

### A2. `fable5-tier-based-routing/SKILL.md` (795 → target <500)

Current sections: 7-Tier Hierarchy, Timeout Enforcement, Cost Guard
Behavior, Escalation Reason Tracking, Example (Complete Tier Progression),
Deployment Validation, References, Common Failure Modes, CI/CD
Integration, Version & Consensus, FAQ.

Extraction candidates:
- `Deployment Validation` (production tier routing checklist) → `references/deployment-validation.md`
- `Common Failure Modes & Fixes` → `references/failure-modes.md`
- `FAQ` → `references/faq.md`
- `Example: Complete Tier Progression with Cost Guard` → `examples/good/tier-progression.md`
  (matches the `examples/good/` convention already established)

Keep in `SKILL.md`: 7-Tier Hierarchy table (the load-bearing reference
data every caller needs), Timeout Enforcement (hard invariant), Cost Guard
Behavior (hard invariant), Escalation Reason Tracking (hard invariant).

### A3. Folder shape (both skills, matching skillify's own template)

```
<skill-name>/
├── SKILL.md          (trimmed, <500 lines)
├── examples/good/     (new)
├── examples/bad/      (new, if a real anti-pattern exists to document)
├── eval/checklist.md  (new — dogfood-loop rubric, matching skillify's pattern)
├── eval/evals.json    (new — test prompts)
└── references/        (extracted sections land here)
```

### A4. Verification

- Line count check on both trimmed `SKILL.md` files: `wc -l`, must be <500.
- Every extracted section still reachable: grep the trimmed `SKILL.md` for
  a pointer to each new `references/*.md` file — no orphaned content.
- Run `scripts/check-skill-namespace-collision.sh mcp-orchestration
  fable5-tier-based-routing` (both already global-published or not?
  verify against `scripts/install-skills.sh`'s sync list — if either is
  already syncing to `~/.claude/skills/`, re-run
  `bash scripts/install-skills.sh` after trimming to confirm no collision
  and that the sync picks up the new file layout).
- `python3 scripts/review/repo_hygiene.py .` clean.

---

## Phase B (P3) — Frugality Router Wiring

### B0. Grounded scope (measured today, not estimated)

`Perpetua-Tools/orchestrator/model_registry.py`'s `ModelRegistry.route_task()`
(line 195) is PT's REAL, currently-active dispatch mechanism — a
config-driven fallback chain read from `routing.yml`/`models.yml`. It does
**not** call `frugality_router.resolve_route()`. Confirmed via grep: zero
non-test importers of `frugality_router` anywhere in `orchestrator/`. Two
parallel systems exist today; nothing bridges them.

### B1. Integration point

`route_task(task_type, preferred_device)` returns `List[ModelTarget]` — an
ordered fallback chain. `resolve_route(spec, registry=..., escalation_tier=...)`
returns a single `ResolvedRoute` — the lowest eligible tier for one call.
These are different shapes (a chain vs. a single resolved route), so this
is not a drop-in replacement — `route_task()` needs a call to
`resolve_route()` inserted as a **pre-filter**: before returning the config
fallback chain, ask `resolve_route()` which tier is eligible for this
`task_type` under current policy (`ORAMASYS_OFFLINE`, `privacy_critical`),
and use that to prune/reorder the chain `route_task()` already builds —
not to replace `route_task()`'s config-driven candidate list, which still
carries real device/model selection data `resolve_route()` doesn't have.

### B2. Tier gates

- `ORAMASYS_OFFLINE=1` — when set, `max_allowed_tier()` should cap at tier
  2 (no `free_remote`/`free_proprietary`/`paid`/`last_resort`). Verify this
  is already enforced inside `frugality_router.py` itself (it likely is,
  per the navigator's spike-status note) — B1's job is making sure
  `route_task()` actually calls into that enforcement, not re-implementing
  it.
- `privacy_critical` — same pattern: verify enforcement lives in
  `frugality_router.py`, confirm `route_task()`'s call site passes this
  flag through from wherever PT already tracks it per-task.

### B3. Verification

- PT's existing `frugality_router.py` test suite still passes unchanged
  (wiring should not require touching that file's own logic — if it does,
  that's a signal B1's integration point is wrong).
- New test: `route_task()` called with `ORAMASYS_OFFLINE=1` never returns a
  paid/remote candidate.
- New test: `route_task()` called with a `privacy_critical` task never
  escalates past the local tiers.
- Cross-repo lockstep: if PT's `orchestrator/` changes, check whether
  orama-system's `fable5-tier-based-routing/SKILL.md` needs a version bump
  or a "verified wired 2026-07-22" note (avoid re-creating the "doc says
  done, code isn't" gap this plan just found).

### B4. Explicitly deferred within B (name it, don't silently drop)

- Full "wire into ALL dispatch paths" (the navigator's own broader claim)
  — B1–B3 wire the ONE confirmed real dispatch site
  (`ModelRegistry.route_task()`). If other dispatch paths exist elsewhere
  in PT (Cursor/Codex/Cline dispatch, OpenClaw agent routing), they are a
  separate follow-up pass, not silently assumed covered by this plan.

---

## Order of Execution

1. Phase A (P4) in full — lower risk, self-contained, single repo.
2. Phase B (P3) in full — higher risk (cross-repo, live dispatch logic),
   only after A is verified green.
3. Anything else surfaced during A/B goes to `TODOS.md`, not silently
   folded in.

## Test Plan (placeholder — Eng phase produces the real artifact)

To be written to `~/.gstack/projects/orama-system/` during the Eng review
phase per that skill's own Section 3 requirement.

---

## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale |
|---|-------|----------|-----------------|-----------|-----------|
| 1 | CEO | Mode = SELECTIVE EXPANSION (autoplan fixed override) | Mechanical | — | Per /autoplan's own CEO override rules |
| 2 | CEO | Keep P4-before-P3 sequencing as the user explicitly directed | Taste | P3 (pragmatic) | Codex argues P3 delivers more value and should go first; I independently agree P3 is the higher-value lever but do not agree the sequence must flip — "safe thing first, build momentum" is a defensible reason to hold the user's explicit order. Not a User Challenge (models don't fully agree) |
| 3 | CEO | Add explicit baseline/measurement requirement to Phase B | Mechanical (adopted from Codex finding) | P1 (completeness) | Codex correctly flagged the plan had no before/after cost/latency/egress targets — "frugality" would be unmeasured. Added B3.1 below |
| 4 | CEO | Strengthen (not remove) the B4 "one site ≠ all paths" caveat | Mechanical (adopted from Codex finding) | P1 (completeness) | A footnote doesn't close the functional gap; made the limitation a first-class open risk, not a buried caveat |
| 5 | CEO | Direct-to-main stays the execution branch (not a new feature branch) | Taste | P6 (bias toward action) | Codex flagged this as strategically risky for cross-repo runtime wiring. Valid in general, but this session has operated direct-to-main throughout with ALLOW_MAIN_PUSH=1 by explicit standing user direction — reversing that convention for this one plan would be inconsistent without the user re-opening it. Flagged for the user at the gate rather than silently overridden |

### CEO consensus (single voice this pass — see Phase 0.5 scoping note above)

| Dimension | Codex | Claude | Consensus |
|---|---|---|---|
| Premises valid? | Partially — "DOC done" premise is misleading without runtime enforcement | Agree | CONFIRMED (with amendment: reworded below) |
| Right problem to solve? | P3 is the real lever, P4 is hygiene | Agree P3 is higher-value, disagree sequence must flip | DISAGREE (taste, resolved above) |
| Scope calibration correct? | "One site" undersells the real gap | Agree, strengthened B4 | CONFIRMED (amended) |
| Alternatives sufficiently explored? | Proposes a "single policy gate" reframe over "pre-filter" | Valid alternative architecture, worth flagging for Phase B design, not blocking | CONFIRMED (noted as design input) |
| Competitive/market risks covered? | Not addressed — this is table stakes, not differentiation | Fair, but this is internal tooling, not a product-market plan — lower weight here | DISAGREE (low stakes, not re-litigated) |
| 6-month trajectory sound? | Risk: manual cross-repo lockstep goes stale without contract tests | Agree, real risk | CONFIRMED |

**Amendment to Phase B (per findings above):**
- **B3.1 (new).** Before B1, capture a baseline: run `route_task()` for the plan's actual `task_type`s today and record which candidates it returns (paid/remote included or not). After B1–B2 land, re-run and diff. This is the "measured cost/privacy/quality outcome" Codex asked for — cheap (no new telemetry infra needed), just a before/after diff of existing output.
- **B4 (strengthened).** This plan wires exactly one confirmed dispatch site. That is a **first step, not frugality coverage** — until every dispatch path is audited, the system cannot honestly claim `ORAMASYS_OFFLINE`/`privacy_critical` are enforced everywhere. State this plainly in the PR description, not just this plan file.

**CEO PHASE COMPLETE.** Codex: 6 dimensions, 3 disagreements (1 resolved as taste, 2 adopted as plan amendments). Consensus: 4/6 confirmed after amendment, 2 remain taste/scope disagreements (documented, not blocking). Passing to Eng phase.

---

## Eng Phase

### Codex eng voice — grounded in real code (verified, not taken on faith)

Codex read `frugality_router.py`, `orchestrator/model_registry.py`, and (unprompted,
correctly) `src/perpetua_tools/orchestrator.py`. Every claim below was independently
re-verified against the actual files before being accepted:

1. **CRITICAL, verified true.** `src/perpetua_tools/orchestrator.py`'s `/orchestrate`
   endpoint (lines 383–400) has its **own, already-working, completely separate**
   `privacy_critical` routing chain (Oramasys → LM Studio Win → LM Studio Mac →
   Ollama) — nothing to do with `frugality_router.py`. B1's "wire `route_task()`"
   plan only touches ONE of at least TWO real dispatch paths that both claim to
   handle privacy-critical routing, with different semantics.
2. **HIGH, verified true.** `ModelTarget` (model_registry.py:50) has no frugality-
   tier/cost/egress field at all — `route_task()` literally cannot pre-filter by
   tier without a new data-model field, which B1 never scoped.
3. **HIGH, verified true.** Three, not two, privacy-handling mechanisms exist,
   confirmed by direct inspection: (a) `frugality_router.py`'s `spec.privacy_critical`
   + `max_allowed_tier()`, (b) `routing.yml:49`'s comment: "`privacy_critical` is
   not a live PT request field [for `route_task()`]; privacy is enforced here by
   requiring `orama_available` and excluding cloud/online model roles" (task_type-
   based, no flag), (c) `src/perpetua_tools/orchestrator.py`'s own `req.privacy_critical`
   chain (finding 1). These are three different implementations of the same policy
   name, not one system with three callers.
4. **HIGH, verified true.** `route_task(task_type, preferred_device)`'s real
   signature (model_registry.py:195) cannot accept `privacy_critical` or
   `escalation_reason` — wiring `resolve_route()` in honestly requires an API-shape
   change, not an internal call insertion as B1 assumed.
5. **MEDIUM, accepted.** B3.1's baseline diff (candidate list only) is too shallow —
   real selection happens deeper, past `_resolve_candidates()`.
6. **MEDIUM, accepted.** Phase A and Phase B share no architectural dependency, only
   scheduling — confirms they can be decoupled cleanly.

### My independent assessment (Eng)

I do not have a counter-argument to findings 1–4 — they're falsifiable claims I
re-verified line-by-line against the real files, not opinions. Codex correctly
found that Phase B as originally scoped ("wire one call site" as a mechanical,
low-risk insertion) rests on a wrong premise: there is no single dispatch site to
wire, there are at least three fragmented implementations of "privacy critical"
routing that need reconciling first. Proceeding with B1–B4 as originally written
would either (a) not actually close the frugality gap the plan claims to close, or
(b) require a data-model + API-shape change well beyond what B1's "insert a call"
framing implied — which is a different, larger, and legitimately separate piece of
work needing its own design pass, not something to improvise mid-execution.

**Architecture diagram (current state, as discovered — not the plan's original
assumption):**

```
Real dispatch landscape (2026-07-22, verified):

  frugality_router.py::resolve_route()     <-- built, tested, ZERO real callers
        |
        X  (no wiring exists anywhere)

  ModelRegistry.route_task()               <-- real caller: fastapi_app.py
        |
        no privacy_critical param, no tier/cost field on ModelTarget
        |
        config-driven fallback chain (routing.yml task_type exclusion, no flag)

  src/perpetua_tools/orchestrator.py /orchestrate   <-- real caller, SEPARATE
        |
        req.privacy_critical -> Oramasys -> LMStudio Win -> LMStudio Mac -> Ollama
        (own hardcoded chain, no frugality_router involvement)
```

Three systems, one policy name, zero reconciliation. This is the real shape Phase
B needs to design against — not assumed away.

### Test diagram (Phase A only — Phase B has no safe-to-execute shape yet)

| Codepath | Test type | Exists? | Gap |
|---|---|---|---|
| `mcp-orchestration/SKILL.md` trimmed, extracted refs still reachable | Manual grep + line-count check (scripted in A4) | New (this plan) | None — mechanical, low-risk |
| `fable5-tier-based-routing/SKILL.md` trimmed, extracted refs still reachable | Same as above | New (this plan) | None |
| `scripts/check-skill-namespace-collision.sh` against both trimmed names | Existing script, already tested this session | Yes | None |
| Frugality wiring (Phase B) | N/A — no safe implementation shape exists yet per Eng findings | N/A | **Blocking**: cannot write a meaningful test plan for an architecture that doesn't have an agreed design |

### Failure modes registry

| Failure mode | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Trimmed SKILL.md loses load-bearing content (Phase A) | Low | Medium — agent misses a rule | A4's "orphaned content" grep check catches this mechanically |
| Wiring one privacy_critical path while two others remain unreconciled gives false confidence of coverage (Phase B, if executed as originally scoped) | High | High — a caller could reasonably believe frugality/privacy is now enforced when 2/3 real mechanisms are untouched | **This is why Phase B's scope is revised below, not executed as originally written** |

**ENG PHASE COMPLETE.** Codex: 6 findings (4 critical/high, all independently
re-verified true; 2 medium, accepted). Consensus: 6/6 — no disagreement this
phase, every finding held up under direct file verification. Recommendation below.

---

## Revised Recommendation (supersedes original Phase B scope)

The review did its job: Phase B as originally written ("wire one call site,
mechanical, low-risk") is based on an incomplete model of the real dispatch
landscape. The actual landscape is three unreconciled privacy/frugality
implementations, not one router with one missing caller. Wiring `route_task()`
alone would not close the gap the plan claims to close, and doing the real
fix (reconcile three systems into Codex's "single policy gate") is a
legitimately separate, larger design decision — not something to improvise
inside what was scoped as a mechanical wiring pass.

**Recommendation: execute Phase A (P4 trimming) now, in full, as originally
scoped — it has no dependency on Phase B and every Eng finding confirms it's
safe. Do NOT execute Phase B as originally written. Instead, open
`docs/plans/2026-07-22-frugality-privacy-reconciliation-design.md` (not yet
written) as its own properly-scoped design pass before any wiring code lands,
covering: which of the three privacy_critical implementations is canonical,
what `ModelTarget`'s missing tier/cost/egress field should look like, and
whether `resolve_route()` becomes the single gate all three paths call through
or is retired in favor of extending the existing config-driven system.**

This is a genuine scope change discovered by the review, not a taste call —
surfaced at the gate below for explicit confirmation rather than silently
executed or silently dropped.

---

## DX Phase (condensed — Phase B deferred, remaining scope is repo-internal doc reorg with thin DX surface)

The only DX-relevant surface left after the Eng-phase revision is Phase A:
does trimming `mcp-orchestration/SKILL.md` and `fable5-tier-based-routing/SKILL.md`
make them easier or harder for a developer (human or agent) to use correctly?

- **Getting started / TTHW:** unaffected — trimming doesn't change how a skill
  is invoked, only how its content loads.
- **Findability:** improves — the skillify dogfood pattern already validated
  this session (skillify/oramasys-method) puts decision-time content in
  `SKILL.md` and detail in `references/`, which is easier to scan, not harder.
- **Risk:** if A1/A2's "keep vs. extract" split (drafted above) is wrong —
  moving load-bearing content out of `SKILL.md` — an agent following the
  trimmed skill could silently skip a rule it used to see every invocation.
  **Mitigation already in A4:** verify every extracted section still has a
  pointer, and re-run `bash scripts/install-skills.sh` / the collision
  script after trimming to confirm nothing broke downstream.

No dual-voice pass run for this phase — the surface is narrow enough that the
Eng phase's file-level rigor already covers the real risk (orphaned content),
and running a second full ceremony here would not surface new information.

**DX PHASE COMPLETE (condensed).**

---

## GSTACK REVIEW REPORT

| Phase | Runs | Status | Findings |
|---|---|---|---|
| CEO | Codex (1x, verified) + Claude (independent) | Complete | 6 dimensions reviewed; 3 findings adopted as plan amendments (B3.1 baseline, strengthened B4 caveat); 1 taste disagreement resolved (sequencing kept per user's explicit direction) |
| Design | — | Skipped | No UI scope detected in this plan |
| Eng | Codex (1x, code-grounded) + Claude (independent, re-verified every claim against real files) | Complete | 6 findings, all confirmed true on direct file inspection; 4 critical/high findings triggered a genuine scope revision (Phase B deferred) |
| DX | Claude only (condensed, no dual-voice) | Complete | Narrow surface after Eng revision; no new risk beyond what Eng already covers |

**VERDICT:** Phase A (P4 skill trimming) is APPROVED to execute as scoped — CEO
and Eng both confirm it's safe, self-contained, and correctly sequenced first.
Phase B (P3 frugality wiring), as originally scoped in this plan, is **NOT
approved to execute** — the Eng phase found the real dispatch landscape has
three unreconciled privacy/frugality implementations, not the single missing
call site the plan assumed. Recommended path: execute Phase A now, open a
separate design-first plan for the frugality reconciliation before any Phase B
code lands.

CROSS-MODEL: Codex and Claude reached full consensus on all Eng-phase findings
after independent file verification (6/6, zero disagreement). CEO phase had
2 documented taste/scope disagreements, both resolved without blocking.

**UNRESOLVED DECISIONS:**
- Confirm: execute Phase A now, defer Phase B to a separate reconciliation-design plan (recommended), or proceed with Phase B in its originally narrower form (wire `route_task()` only, explicitly NOT claiming full privacy_critical enforcement) despite the Eng-phase risk noted above?
