# Frugality/Privacy Reconciliation + Navigator Close-Out — Provisional Plan

**Date:** 2026-07-22
**Status:** DESIGN DECIDED, IMPLEMENTATION LANDED (PT commit `13f09c42`,
pushed to `origin/main`) — captures everything
/autoplan's review of `docs/plans/2026-07-22-p4-skill-trimming-p3-frugality-
wiring.md` deferred, plus the remaining open items in
`references/tiered-model-implementation-navigator.md`, so nothing found
today gets lost. All Item 1 design questions are now decided (see below);
a `Workflow` run is executing the implementation — see Execution Log.

## Execution Log

- **2026-07-22:** `Workflow` (`p3-frugality-gate-execution`, run
  `wf_8a31b85a-eea`) launched under this session's `ultracode` opt-in, with
  the mandatory model tiering from
  `bin/orama-system/references/claude-code-workflow-canonical.md`: Haiku
  (`claude-haiku-4-5-20251001`) for the cheap survey step, Sonnet 5
  (effort high) for implementation and independent verification — no
  Opus/Fable 5 escalation, this task didn't warrant it. Scope: wire
  `frugality_router.resolve_route()` as the canonical gate behind
  `route_task()` and `orchestrator.py`'s `privacy_critical` branch via a
  v1 wrapper (no signature change), backfill `frugality_tier` in
  `config/models.yml`, add contract tests, then independently re-verify
  the diff and test results before trusting the implementer's own report.

- **2026-07-22 — LANDED.** Workflow completed (375k tokens, 94 tool calls,
  3 agents, ~23 min). PT commit `13f09c42`: new `orchestrator/gate.py`
  (`consult_gate`/`gate_permits`/`filter_chain_by_gate`/
  `load_frugality_tier_by_name`); `route_task()` gained keyword-only
  `privacy_critical`/`override_confirmed`/`override_reason` (defaults
  `False`/`False`/`None`, old positional call sites unaffected);
  `orchestrator.py`'s `privacy_critical` branch gated hop-by-hop, fallback
  chain fully preserved; all 11 `config/models.yml` models classified
  (local → 1, cloud paid → 5, grok → 6 matching `frugality_router.py`'s own
  convention, one flagged judgment call on `glm-5.1:cloud` → 4).
  **Tests:** 29 new + 120 pre-existing directly-relevant + 1530 full-repo
  suite, all passing, zero regressions — independently re-run and verified
  by a separate agent pass (not just the implementer's own claim).
  **Independent verdict:** SAFE to commit, no rollback needed.
  **Scope note:** 3 unrelated dirty files rode along in the working tree
  (`.codex/config.toml` — an exa MCP transport swap, unrelated drift, not
  from this Workflow; `vendor/ecc-tools` submodule bump; an
  `AGENT_LEARNINGS.jsonl` auto-log line) — held out of the commit per
  human review except the memory-log line, which was folded in as routine
  session logging. Pushed to `origin/main` (`16e456ec..13f09c42`) with
  explicit `ALLOW_MAIN_PUSH=1` override of the Phase 0 PR-only-write gate,
  user-confirmed.

**What already shipped today (not in this plan's scope — done):**
- P4: `mcp-orchestration/SKILL.md` (866→496 lines) and
  `fable5-tier-based-routing/SKILL.md` (795→499 lines) trimmed, content
  bundled into `references/`/`examples/`, both under the collision guard,
  both verified with zero orphaned pointers.
- P3 (safe additive slice only): `Perpetua-Tools/orchestrator/model_registry.py`'s
  `ModelTarget` dataclass gained an optional `frugality_tier: Optional[int] = None`
  field, read from `models.yml`'s `frugality_tier` key when present. Zero
  behavior change — nothing reads or filters on it yet. This unblocks Item 1
  below without requiring the full reconciliation first.
- `fable5-tier-based-routing/references/deployment-validation.md` corrected
  to state plainly that `resolve_route()` has zero real callers today (was
  previously silent on this, which is exactly the kind of doc-without-
  enforcement gap the CEO phase flagged).

---

## Item 1 — Frugality/Privacy Reconciliation (the deferred core of P3)

**UPDATE 2026-07-22 (post-research pass) — framing corrected, scope narrowed.**
A gbrain trace through `bin/orama-system/skills/hermes-harness/references/`
(assignment + result records for PT #199) and `docs/plans/2026-05-29-03-v1.1-
definitive.md`'s own text shows this is **not** three ad-hoc, independently-
invented implementations. It is:

- **Two faces of one working, documented mechanism** — `config/routing.yml`'s
  task_type cloud-role exclusion (always-on general policy) and
  `src/perpetua_tools/orchestrator.py`'s `req.privacy_critical` chain
  (explicit per-request override). These compose correctly today; they are
  not in conflict.
- **One genuine outlier by omission, not design collision** —
  `orchestrator/frugality_router.py`. Its own spike doc
  (`bin/orama-system/skills/hermes-harness/references/assignments/mac-
  orchestrator-frugality-router-spike.md`) named the exact missing step on
  day one, under "Not in spike (follow-on P1)": *"Wire into all dispatch
  paths (supervisor, fastapi_app)."* That named TODO sat unpicked for ~3
  weeks (spike merged 2026-06-29 → this discovery 2026-07-22) while P1/P2/P4
  work took priority — nobody silently dropped it, it just never got its
  turn.

Full trail + a corrected reading of the "✅ RESOLVED 2026-06-14 — v1.1
shipped" banner (means "module merged + unit-tested," not "wired into any
real dispatch path"): `references/tiered-model-implementation-navigator.md`
§ "Close-Out: P3 Frugality/Privacy Historical Trail."

**Practical effect on scope below:** this narrows the open design question
from "reconcile three systems" to one question — does `frugality_router.py`
become the thing `routing.yml`/`orchestrator.py` delegate to (Codex's
"single policy gate" proposal), or does it stay a parallel, opt-in
tier-tracking layer some call sites use and others don't? Both are
legitimate; the `ModelTarget.frugality_tier` field shipped 2026-07-22 is
compatible with either answer, which is why it was safe to land ahead of
this decision.

**Original framing (kept for the record — verified by reading the real code,
not assumed):**
1. `orchestrator/frugality_router.py`'s `spec.privacy_critical` + `max_allowed_tier()`
2. `config/routing.yml`'s task_type-based cloud-role exclusion (no flag)
3. `src/perpetua_tools/orchestrator.py`'s own `req.privacy_critical` → Oramasys/LMStudio chain

### Design decision (2026-07-22, human-confirmed — supersedes "not yet decided" below)

**DECIDED: single gate.** `frugality_router.py`'s `resolve_route()` becomes
the one canonical policy gate; `route_task()` and `/orchestrate`'s
`privacy_critical` branch both call it rather than each enforcing policy
independently. This resolves the "canonical implementation" and
"`resolve_route()` retired vs. kept" questions below in favor of Codex's
"single policy gate" proposal.

**Override path (human-confirmed):** the gate is not absolute — a human
operator can override its decision. Override precedence, in order:
1. `AskUserQuestion` (or the active host's equivalent interactive-confirm
   tool), when available in the calling context — this is the default and
   preferred path per this session's established AskUserQuestion-first
   doctrine (see `bin/orama-system/skills/oramasys-method/SKILL.md`'s
   "AskUserQuestion Format" section for the pattern to reuse here, not a
   new one).
2. When no interactive-confirm tool is reachable (headless/CLI/cron
   context): a CLI confirmation prompt or, for the web/portal surface, a
   dashboard modal decision pop-up — i.e. the override always requires an
   explicit human click/keystroke through *some* surface; it is never
   silently auto-approved by config alone.

This override requirement becomes a hard invariant for whichever PR
implements the gate: **no silent bypass path.** Every escalation past the
gate's default policy must resolve through one of the two channels above,
logged with which channel was used (for audit — extends the existing
`escalation_reason` tracing already in `resolve_route()`).

Still open (deferred to the PR that implements this): exact override UI
copy/flow for the CLI and dashboard-modal paths — not specified here, left
to implementation, per this plan's own "Explicit non-goals" discipline.

<details>
<summary>Original open-question framing (2026-07-22, pre-decision — kept for the record)</summary>

- Which of the three is canonical? Codex's "single policy gate" proposal
  (classify every call target into a canonical policy record; every
  dispatch path asks the gate before the call, not just before building a
  fallback chain) is the strongest option surfaced so far — needs a real
  design doc, not a plan-file paragraph.
- `route_task(task_type, preferred_device)`'s signature cannot accept
  `privacy_critical`/`est_tokens`/`escalation_reason` — does the API shape
  change, or does the gate live outside `route_task()` entirely (e.g. a
  wrapper both `route_task()` and `/orchestrate` call before dispatch)?
- Does `resolve_route()` become the single gate, or get retired in favor of
  extending the existing `routing.yml` task_type-exclusion system? (Codex
  leaned toward the former; not yet decided.)
- `ModelTarget.frugality_tier` now exists (shipped today) but is unpopulated
  in `models.yml` — who owns backfilling it per-model, and what's the
  fallback for models without a tier set?

</details>

### API-shape decision (2026-07-22, human-confirmed)

**DECIDED: wrapper for v1, signature change deferred to v2.** `route_task()`
keeps its current signature unchanged; a thin wrapper (both it and
`/orchestrate` call before dispatch) carries the gate call instead. This is
explicitly a v1/v2 split, not a permanent choice: PT's v1 surface stays
additive-only and non-breaking, while a `route_task()` signature change
(accepting `privacy_critical`/`est_tokens`/`escalation_reason` natively) is
deferred to whatever v2 shape lands per `orama-system/docs/v2/` planning —
same layering this whole plan already follows (PT = L2 runtime, orama = L3
methodology/planning). Do not preempt that v2 signature design here; this
plan only commits to the v1 wrapper. Implementation of the wrapper is in
progress as of this session (see Execution Log below).

### `models.yml` frugality_tier backfill ownership (2026-07-22, EXA research + decision)

**Research (EXA, LiteLLM docs — the closest prior-art match: a multi-model
proxy with a per-model cost/tier classification config):**

- LiteLLM's default is a centrally-maintained, auto-fetched cost map (fine
  for their scale — hundreds of models, many operators). Per-deployment
  **override** is their recommended path for anything less than
  fleet-wide: "changes only the deployments you name, survives every
  upstream map update... reach for a full custom map only when the
  correction spans so many models that per-deployment config stops being
  maintainable." A full separate map is explicitly the *heavier*, not
  default, option.
- Ownership is tied to **where a model is defined**: "config models are
  owned by the file" (`config.yaml`) vs. UI/DB-owned models — whoever
  controls the entry's source of truth backfills its metadata, not a
  separate centralized process.
- Documented failure mode to guard against: **silent fallback**. LiteLLM's
  cost map, on fetch failure, "logs a warning and silently falls back to
  the bundled backup map" — flagged in their own docs as the exact failure
  mode to alert on, because it quietly reverts corrections without failing
  a health check.
- `model_info` supports arbitrary per-model metadata (owning team,
  description, version) passed through and readable via API — the general
  pattern for attaching ownership/classification data at the point a model
  is registered, not backfilled separately later.

**Applied to PT's scale (a dozen-ish models in one `config/models.yml`,
not a multi-tenant fleet — LiteLLM's Organization/Team hierarchy doesn't
apply here):**

**DECIDED:** `frugality_tier` is backfilled **at model-registration time**,
by whoever adds or edits a `config/models.yml` entry — same PR, no separate
centralized classification process or dashboard. This mirrors LiteLLM's
"config models are owned by the file" pattern at PT's actual scale.

**DECIDED (fallback, fail-closed):** a model with no `frugality_tier` set
must **not** be silently treated as low-tier/unrestricted. Per the existing
`ModelTarget.frugality_tier: Optional[int] = None` field (shipped
2026-07-22), an unset tier must resolve as "gate has no opinion, defer to
existing routing.yml/orchestrator.py fallback chain" (already the
implementation's stated behavior in the wrapper being built this session)
— never as "assume tier 1, allow anything." This directly guards against
LiteLLM's own documented silent-fallback failure mode, adapted to PT's
context: unclassified must mean "fall through to the pre-gate behavior,"
not "assume permissive."

**Enforcement:** add a lint/test asserting every `config/models.yml` entry
either has `frugality_tier` set or is on an explicit allowlist of
intentionally-unclassified entries — prevents silent drift back to an
unaudited state as new models get added over time.

**Free-tier cross-check (gbrain + CRG + PT `.agent` memory, no paid research
needed):** confirms rather than changes the above.
- Hardware affinity (`check_affinity()`, `config/model_hardware_policy.yml`)
  is already the established *first* gate — confirmed structurally via CRG
  (`check_affinity` is called from `orchestrator/supervisor.py`'s
  `submit_job` and `_prepare_spec_for_inference`, i.e. before dispatch).
  "Hardware first, then tier-based" is already the real architecture, not
  something this plan needs to build.
- PT `.agent` memory's existing gateway doctrine — *"Fail-closed at
  gateways: hardware affinity failures... unresolvable model IDs produce
  explicit errors — never silent fallback, never fail-open"* — was checked
  against the fallback decision above and does not conflict: that lesson
  covers genuine failures (unresolvable IDs, missing config); an unset
  `frugality_tier` is not a failure, it's "no additional opinion," so
  deferring to the existing already-fail-closed routing chain is
  consistent with, not an exception to, that doctrine.
- Free-alternative-of-last-resort is already documented: `OmniRoute`
  (local sidecar, port 20128, fans to free OpenRouter/AgentRouter models),
  explicitly "NEVER install, NEVER require, NEVER fail if absent" — no new
  mechanism needed here either.
- CRG's graph index was ~4.4 days stale during this check (`built_at_sha`
  != `head_sha`) — findings above are corroborated by the gbrain/memory
  hits independently, but re-run `build_or_update_graph_tool` before
  trusting CRG for anything code-shape-sensitive in the actual
  implementation PR.

**ECC-style model selection as the unclassified-agent fallback (2026-07-22,
confirmed via `vendor/ecc-tools/commands/model-route.md`):** real, and a
good fit — but for a *different* layer than `models.yml`/`frugality_tier`.
ECC's `/model-route` is a stateless heuristic (haiku/sonnet/opus by
complexity + risk + budget) that ranks *Claude Code subagent* model choice,
not PT's local Ollama/LM Studio model registry — same shape as this
session's own Haiku-dispatch/Sonnet-evaluate/Opus-escalation-only policy
(`bin/orama-system/references/claude-code-workflow-canonical.md`), not a
competing system. Do not conflate the two "model selection" concepts when
implementing:
- `models.yml`'s `frugality_tier` ranks PT's own local/cloud inference
  models for cost/privacy tier — decided above.
- ECC's `/model-route` ranks which *Claude* model (Haiku/Sonnet/Opus) a
  spawned subagent should use — already decided policy, unrelated axis.

**Where ECC's heuristic is genuinely useful here:** as the fallback default
specifically for an *unclassified Claude subagent spawn* (no explicit tier
assigned by the calling workflow) — consult it once at agent-registry/spawn
time, and since it's a pure function of (task-description, budget) with no
external state, its result is safely cacheable/idempotent per
task-signature. This is a real frugality win: skip re-deriving the same
haiku/sonnet/opus recommendation on every repeat of a structurally similar
subagent spawn. Not yet implemented — flagged here as a legitimate,
low-risk follow-on optimization for whoever builds out agent-registry
tooling, not part of this plan's Item 1 scope (which is PT's local model
registry, not Claude subagent selection).

### Suggested execution shape (once design is settled)

1. Baseline (per the amended B3.1 from the CEO phase): capture current
   `route_task()` output and `/orchestrate` routing decisions for a
   representative set of task_types before any change.
2. Land the chosen gate architecture as its own PR, with the API-shape
   change (if any) called out explicitly in the PR description — not
   folded silently into a "wiring" commit.
3. Populate `frugality_tier` in `models.yml` for at least the models used
   by the baseline's task_types.
4. Contract tests: `ORAMASYS_OFFLINE=1` never returns paid/remote from
   whichever path becomes canonical; `privacy_critical` never escalates
   past local tiers from whichever path becomes canonical — Eng phase
   flagged the CURRENT code already lets `privacy_critical` reach tier 3,
   which may or may not be the intended final semantics — decide explicitly,
   don't inherit by accident.
5. Re-diff against the Item 1 baseline; both orama-system's
   `fable5-tier-based-routing/references/deployment-validation.md` wiring-
   gap note and this plan's own status get updated once real callers exist.

---

## Item 2 — Remaining navigator loose ends (from `references/tiered-model-implementation-navigator.md`)

Captured here so the navigator's own "pending" items don't scatter across
multiple follow-up conversations.

| Item | Current status (verified today where checked) | Next action |
|---|---|---|
| P2 — v2 repo scaffold depth | `github.com/oramasys/oramasys` confirmed to exist (HTTP 200); actual content depth NOT audited today | Clone and audit, or explicitly mark "not yet needed" if v1.1 work continues to suffice |
| `docs/2026-05-31-tri-repo-alignment-completion-plan.md` | Marked `🔄 active` in the 2026-06-14 completion tracker; not re-checked today | Re-verify current status before assuming still active — trackers this session have repeatedly been found stale |
| Periscope L4 integration | Marked `⏭️ deferred`, tracker's own words: "the only plan with real remaining implementation grunt" | Out of scope for this close-out; explicitly still deferred, not silently dropped |
| `mcp-orchestration`/`fable5-tier-based-routing` global-publish status | Not checked whether either syncs to `~/.claude/skills/` via `scripts/install-skills.sh` | Run `bash scripts/install-skills.sh` after this session's trim lands; confirm collision guard passes for both names (already verified clear today) |

---

## Epilogue: Branch Hygiene Audit (2026-07-22, same session)

While tracing the P3 historical trail, an adjacent branch-cleanup request
surfaced the same "trust the record, verify before acting" discipline this
whole plan is built on: `reanchor_scan.sh`'s `NEEDS-REANCHOR` verdict on 13
branches across both repos looked like real unmerged work, but
`git diff main..<branch> --stat` + `git log main --grep` confirmed every
single one was already squash-merged (PR #146, #142, #183, #203, #211,
#258-267, #260/#263). Zero contained genuine unmerged content. Cleanup
script: `../../references/2026-07-22-branch-cleanup-verified-superseded.sh`
(sibling to this repo, at the OpenClaw workspace root; hand-trimmed by the
user to exclude a few branches from this pass). Graduated as 2 PT `.agent`
lessons (squash-merge false-positive detection; the branch-delete-hook-
blocked hand-off pattern).

## Cross-References

- Full historical trail for the Item 1 framing correction:
  `references/tiered-model-implementation-navigator.md` § "Close-Out: P3
  Frugality/Privacy Historical Trail."
- Unaudited/unfinished plans found (but not resolved) while tracing that
  trail across both repos' `docs/` trees, including PT's still-open
  tri-repo-alignment and coordination-consolidation threads:
  `references/tiered-model-implementation-navigator.md` § "Cross-Repo Plan
  Register."
- PT `.agent` memory: lessons from this reconciliation pass are graduated
  under the `frugality-privacy-reconciliation` topic — see
  `Perpetua-Tools/.agent/memory/semantic/LESSONS.md` for the rendered index.

## Explicit non-goals (name them, don't silently absorb)

- This plan does NOT commit to a timeline for Item 1 — the design
  questions need a human decision (likely another CEO/Eng review pass once
  the "single policy gate" proposal has an actual design doc to review).
- This plan does NOT re-open Periscope L4 or the tri-repo alignment plan —
  both stay in their own tracked status, referenced here only so this
  close-out doesn't accidentally imply they're resolved.
- This plan does NOT populate `models.yml`'s new `frugality_tier` field for
  any model yet — that's Item 1 step 3, gated on the design decision.
