# Instruction Audit & v2 Migration Plan — Part 2: Execution Program

**Status:** reconciled execution companion to
[Part 1](instruction-audit-and-migration-plan-part-1-findings-and-edits.md).
The historical audit evidence remains useful; current execution status is
controlled by the
[harmonization guide](migration-harmonization-2026-09-09.md) and
[integrated plan](integrated-v2-migration-plan-2026-09-09.md).

This file retains the audit's D/E instruction-remediation program and maps it to
the current successor baseline. It intentionally no longer carries a competing
full M0–M9 implementation plan.

## 1. Current successor baseline

Live successor inspection performed after the original audit changes several
future-work assumptions:

- `oramasys/perpetua-core` MiniGraph R0–R2 is implemented and tested;
- `_run()` is the sole scheduler;
- `aobserve()` is the rich trusted observation seam;
- `asteps()` is the sanitized structural projection;
- strict node-delta and route contracts, unknown-route rejection, exact
  max-step semantics, compile detachment and per-listener observer isolation
  are present;
- R3 reducers/joins remains open;
- the SQLite checkpointer is a persistence primitive, while full R4 durable
  deterministic resume remains open;
- GraphSpec ownership is targeted above Core, but an executable successor
  GraphSpec implementation was not established in the inspected Oramasys graph
  package;
- current `oramasys/oramasys/src/orama/graph/perpetua_graph.py` still directly
  uses Core hardware-policy/discovery/provider-selection helpers and is
  transitional salvage to migrate.

Therefore no instruction-cleanup work may schedule R0–R2 as new kernel
implementation.

## 2. D — completion, testing and merge doctrine

### D1 — verification follows changed behavior and risk

Replace unconditional “every test type / every commit” behavior while preserving
the project-wide coverage floor:

> Choose validation from the changed behavior and risk.
>
> - Text-only changes: inspect the diff and run applicable formatting/link
>   checks.
> - Behavior changes and bug fixes: add/use a meaningful regression and verify
>   affected consumers.
> - Refactors: preserve covered behavior and fill contract gaps where needed.
> - Configuration/security/routing changes: validate syntax and actual
>   semantics, including negative paths.
> - Database/state migrations: test existing-data upgrade, repeat execution,
>   interruption and recovery.
> - UI changes: combine programmatic checks with rendered inspection.
> - Integration/release: run the declared package/cross-package gates.
>
> Maintain at least 80% test coverage across the project. If a component
> defines a stricter coverage threshold, that stricter threshold applies and
> MUST NOT be lowered.

Expected red tests are evidence, not an automatic reason to stop before
in-scope diagnosis.

### D2 — programmatic and visual verification are complementary

> Verify persisted behavior programmatically. When correctness includes
> appearance, layout, animation or rendered content, also inspect the actual
> visual output. Neither evidence class substitutes for the other.

### D3 — semantic merge and review remediation

> Integrate against the verified target revision. Preserve unrelated work and
> distinct historical evidence. Use a disposable owned worktree for merge
> trials; a no-commit merge still mutates that worktree's index/tree.
>
> Resolve mechanical conflicts inside existing authorization. Escalate only a
> genuinely unresolved product/security/data-loss/ownership decision.
>
> Deduplicate only demonstrably identical records. Equal IDs carrying different
> evidence remain explicit reconciliation work.
>
> Wait for required checks/status evidence, not a fixed elapsed time. Verify the
> resulting target content and behavior; ancestry or an empty diff alone is not
> proof of semantic preservation.

For already-open review remediation use PT's established sequence:
Freeze → root-cause cluster → cohesive fixes → exact-head verification → fresh
post-push review sweep. Every surfaced finding is fixed, superseded or
documented; none is silently ignored.

### D4 — history rewrite diagnosis

> Ahead/behind counts or equal trees alone do not prove a history rewrite.
> Compare ancestry, trees and patch equivalence, preserve refs before authorized
> history surgery, and load rewrite recovery only when the task actually
> involves rewritten/ambiguous history.

### D5 — acceptance beats subjective scoring

> Completion follows explicit acceptance criteria and recorded evidence.
> Subjective quality scores may guide another review but cannot waive an unmet
> criterion. An iteration limit ends an unproductive loop; it does not convert
> failure into PASS.

Delegated reviewers receive bounded relevant context, not the full transcript by
default. Parent responsibility for the combined result remains.

## 3. E — installed Superpowers proposals

`$SUPERPOWERS_ROOT` means the installed Superpowers package root for this
report. It is deliberately repository/workstation-neutral; do not embed a
specific plugin-cache absolute path in tracked documentation.

| File/section | Reconciled change | Value preserved |
| --- | --- | --- |
| `using-superpowers/SKILL.md` activation | select skills whose stated boundary materially matches the task; do not activate from incidental keywords | relevant skill discovery |
| `brainstorming/SKILL.md` design gate | reuse an accepted design; ask only when an unresolved material design choice remains | deliberate design where needed |
| `writing-plans/SKILL.md` plan detail | require owners, dependencies, interfaces, evidence and gates; do not invent unknown code to make a plan look complete | executable planning |
| `executing-plans/SKILL.md` stop rule | diagnose routine/expected local failures within scope; stop for missing access, unresolved material choice or new consequential authority | honest blockers |
| `finishing-a-development-branch/SKILL.md` menu | reuse an integration decision already supplied by the user | deliberate integration |
| same file, cleanup | cleanup requires recorded ownership and proof no unique work remains | work preservation |
| `test-driven-development/SKILL.md` recovery | never delete existing/unrelated work merely to recreate test-first history; prove regression sensitivity safely | meaningful TDD evidence |
| `verification-before-completion/SKILL.md` freshness | evidence is tied to exact artifact revision; rerun after relevant change/risk invalidation, not merely because another message occurred | evidence before claims |
| `using-git-worktrees/SKILL.md` setup | determine package manager from declared repo config/commands; separate install from inspection/testing | safe isolation |
| `using-superpowers/references/codex-tools.md` capability assumptions | determine capability from current schema/observed results; detached HEAD is state, not proof no publication path exists | tool-aware execution |
| `systematic-debugging/SKILL.md` environment diagnostics | report variable presence/redacted shape only; never print unrelated credential values | useful safe diagnostics |

These are plugin-owner proposals, not authorization to patch an installed cache
inside this PR.

## 4. Permissions and automatic behavior carried forward from Part 1

### Admission/enforcement

Policy text is not enforcement. Each supported harness adapter must:

- normalize the requested operation;
- validate arguments, required fields and preconditions;
- obtain explicit allow/deny/approval-required result before effects;
- fail closed for unknown/malformed mutating operations or unavailable required
  enforcement;
- prove registration and negative cases in the real call path.

Phylax is the generic runtime-check/security-admission owner. Domain-specific
semantics stay with their owners, including Telos endpoint policy, Agate
hardware rules and Oramasys budget/route policy.

### Command admission

Do not classify a command family as read-only by prefix. Prefer structured read
APIs. Where shell use is required, explicitly validate supported argument/effect
forms and route unmatched forms through normal admission.

### Hooks

Session start does not fetch/pull/install/import memory merely to load
instructions. Post-edit checks preserve real exit status. Advisory checks say
they are advisory. Run the relevant suite after a coherent change rather than
blindly after every file write.

### Approvals

Authorization is specific to action, target, scope and consequences. Reuse
already-granted authorization for the same action; do not broaden it to external
messages, deployment, destructive deletion, history rewrite, credential changes
or permission expansion.

## 5. Five comparison scenarios

| Scenario | Reconciled desired behavior |
| --- | --- |
| typo/text fix | load only scoped guidance; edit; diff + applicable lint/link check; no runtime suite or repository synchronization |
| database/state migration | regression + upgrade/repeat/interruption/recovery proof in isolated data; production mutation requires its own concrete approval |
| UI visual change | programmatic behavior checks plus rendered inspection of affected states/viewports |
| failing local test | preserve real failure exit, classify expected/relevant/unrelated, diagnose in scope, rerun affected checks |
| deployment | prepare exact artifact/environment/effects/rollback packet, then obtain any still-required approval immediately before consequential action |

These remain comparison hypotheses until measured; they are not evidence of
runtime savings by themselves.

## 6. Ownership map used by the execution program

| Owner | Responsibility |
| --- | --- |
| `oramasys/perpetua-core` | realized graph execution and generic dependency-minimal primitives |
| `oramasys/oramasys` | application composition, GraphSpec target authority/projection, route/budget/effect policy, control plane, APIs/UI |
| `oramasys/agate` | hardware capability/fit/affinity/placement evidence |
| `oramasys/telos` | endpoint-use semantics and endpoint/network safe-transport enforcement |
| `oramasys/phylax` | generic runtime-check engine, admission, provenance/redaction, security/safety packs |
| `oramasys/anamnesis` | private runtime memory and sanitized migration/retrieval/promotion |
| `oramasys/Claude-Desktop-LLM` | Ollama/LM Studio provider operation and readiness |
| `oramasys/alexandria` | reconciled v2 specifications/standards/migration evidence |

Core's transitional `policy.py`, `llm.py` and `discovery/` do not override this
map.

## 7. Current M0–M9 mapping

The authoritative implementation detail now lives in
`integrated-v2-migration-plan-2026-09-09.md`. This companion contributes the
following instruction/audit work to those waves:

| Wave | Part-1/Part-2 contribution |
| --- | --- |
| M0 | regime/source-freeze/access evidence |
| M1 | capability/instruction/contract/document ledgers |
| M2 | successor owner guides; read-only skill loading; test/setup separation; portable instruction locators |
| M3 | admission plus route/endpoint/hardware/provider/memory/event contracts |
| M4 | real Phylax adapters, argument/effect admission and specialist conformance |
| M5 | preserve Core R0–R2; R3/R4; policy/LLM/discovery strangler migration |
| M6 | GraphSpec/application composition and migration of transitional Core-owned hardware/provider semantics |
| M7 | permissions/hook policy, skill/plugin migration, memory sanitation/import and Alexandria authority handoff |
| M8 | v2-only release assembly and dependency-boundary proof |
| M9 | concrete authorized release/recovery |

C5's Oramasys `make test`/setup separation is an M2 build-foundation concern,
not M5/Core.

## 8. Core R3/R4/R5 guardrails

### R3

No generic parallel fan-in until reducers and joins are explicit. Current
last-writer-wins helper behavior is not the future universal contract.

### R4

Do not equate `load_latest()` with deterministic resume. Define checkpoint
lineage, graph/run/schema identity, cursor semantics and external-effect
idempotency/dedupe before adding a resume API.

### R5

GraphSpec/lint/evaluation stays above Core. Validate entry/targets,
unreachable/bounded-cycle rules, fan-in reducer/join declarations, durable
effect policy, stable IDs and version/schema compatibility before execution.

## 9. Core policy/LLM/discovery guardrails

Use a strangler migration:

```text
Agate capability evidence
  -> provider readiness
  -> Oramasys route policy
  -> ResolvedRoute
  -> Core execution
```

Inventory callers/config/endpoint-policy points/return shapes/tests first.
Compare old/new decisions without double provider dispatch. Convert old Core
surfaces into delegating compatibility facades only after the first vertical
slice works and parity is proven.

## 10. Endpoint-policy guardrails

Telos secures endpoint meaning and the connection path; it does not become the
provider SDK. Provider owners keep protocol/retry/model/auth semantics. Phylax
provides generic admission/security/safety execution but does not absorb Telos
or Agate semantics. Keep private model/public fetch/telemetry/mesh endpoint
profiles distinct.

## 11. Memory migration guardrails

Before snapshot copy:

```bash
: "${PERPETUA_TOOLS_ROOT:?Set PERPETUA_TOOLS_ROOT before running Step 1}"
test -d "$PERPETUA_TOOLS_ROOT/.agent" || {
  printf '%s\n' "Missing Perpetua-Tools .agent directory" >&2
  exit 1
}
```

Then snapshot outside git, sanitize the copy, regenerate derived indexes and
embeddings, preserve IDs/provenance/status/supersession, prove idempotency and
import only through the reviewed Anamnesis contract.

## 12. M8 dependency-boundary check

Forbidden:

- legacy v1 imports/dynamic loads;
- v1 installation URLs;
- implicit sibling-checkout discovery/fallback;
- runtime shell/subprocess calls that invoke v1 scripts, binaries, memory
  writers, policy authorities or provider paths.

Allowed:

- explicitly declared target-owned provider/platform/tool subprocess adapters
  with validated args/effects, documented lifecycle/cancellation, tests and no
  v1 fallback;
- historical citations and sanitized fixture provenance.

This clarification supersedes the earlier overbroad phrase `runtime shell
calls`.

## 13. Completion condition

Instruction/migration cleanup is not complete merely because planning text is
shorter. Completion requires:

- no unexplained capability/instruction omission;
- preserved provenance and source evidence;
- real admission/permission enforcement where claimed;
- Core R0–R2 preserved rather than restarted;
- accepted R3/R4 work verified;
- GraphSpec/application policy above Core;
- specialist semantic owners used in the actual call path;
- v2 release candidate functions without v1 dependencies;
- remaining exclusions/open decisions explicitly recorded.

No runtime context/productivity gain is claimed until controlled comparison
measures it.
