# Instruction Audit & v2 Migration Plan — Part 1: Findings, Coverage, and Proposed Edits

> **Status:** planning reference, not yet implemented. Filed in this legacy
> repository's `docs/v2/references/` at explicit user direction, alongside
> this repo's existing v2 planning docs (60–67) — the established location
> for v2 migration planning throughout this repository's own history, not a
> departure from it.
> **Scope of the plan's content:** exclusively `oramasys/*` repositories.
> Neither `diazMelgarejo/Perpetua-Tools` nor `diazMelgarejo/orama-system`
> (this repo) is a target of any proposed change below — both appear only
> as read-only evidence sources, matching the audit's own stated migration
> boundary.
> **Provenance:** synthesizes an uploaded audit report (author unstated in
> the source material) covering both `diazMelgarejo` repositories and the
> accessible `oramasys/*` org. Claude did not independently re-verify the
> `oramasys/*` findings below — that org is inaccessible to this session's
> GitHub token (a 403 from an org-level PAT-lifetime policy, confirmed
> directly this session while investigating a separate, unrelated finding).
> Findings citing this repository or PT are noted where Claude's own,
> independently-gained knowledge from this session either confirms or adds
> context.
> **Companion document:** [Part 2 — the execution program](instruction-audit-and-migration-plan-part-2-execution-program.md).

---

## 1. Highest-impact findings

"Confirmed" means the inspected text or code establishes the issue.
Predictions about how an agent would behave remain hypotheses, not
observed outcomes.

| Priority | Finding | Evidence strength | Likely consequence |
| --- | --- | --- | --- |
| P0 | Successor documentation still assigns operational authority to legacy repositories | Confirmed text conflicts with the current migration instruction | An agent may implement v2 work in v1 or introduce cross-regime dependencies |
| P0 | The portable-brain permission checker does not enforce everything its documentation claims | Confirmed static code/configuration finding; live enforcement untested | A purported safeguard may allow unknown operations or ignore declared restrictions |
| P0 | Skill loading and session startup can perform repository synchronization and memory imports | Confirmed commands; execution depends on harness/configuration | Reading instructions can unexpectedly change files, refs, or imported memory |
| P1 | Approval rules conflict across the portable brain, Codex guidance, schemas, and Superpowers | Confirmed textual contradictions | Repeated confirmation requests, premature stopping, or unclear external-action authority |
| P1 | Verification requirements repeatedly expand to full suites, unrelated security checks, and mandatory agents | Confirmed instructions | Small tasks acquire substantial unrelated work |
| P1 | Existing migration plans still direct PT-side implementation | Confirmed in this repo's Doc 66; corresponding PR remains open | Continuing an old plan would violate the current source freeze |
| P1 | Merge doctrine combines valuable preservation rules with unsafe shortcuts and excessive ceremony | Confirmed text | Incorrect conflict resolution, repeated questions, fixed waits, or misleading completion checks |
| P1 | Visual verification is both prohibited and required by different workflows | Confirmed wording conflict | UI changes can pass programmatic checks without their appearance being inspected |
| P2 | Skill metadata includes malformed descriptions, truncated triggers, broad keywords, and competing routers | Confirmed metadata | Unnecessary activation and missed specialist selection |
| P2 | Historical incidents and machine assumptions are repeated in instruction entry points | Confirmed duplication; behavioral benefit unmeasured | Context consumption and stale environmental assumptions |
| P2 | Agent definitions use inconsistent subjective completion thresholds | Confirmed text | Refinement loops without a reliable acceptance criterion |
| P2 | Worktree cleanup infers ownership from directory names | Confirmed instruction | Potential cleanup of a worktree the current task did not create |

**Claude's own corroboration on the Doc-66/PT-#382 P1 finding**: independently
confirmed and current as of this session, not merely relayed. This repo's own
`docs/v2/66-gate4-and-dedicated-dialer-combined-scope.md` was found with a
genuinely stale paragraph (still describing an already-merged prerequisite PR
as open and blocking) during separate work this session, fixed in commit
`2c550a0b` (merged to `main` in PR #347). PT PR #382 (the dedicated-dialer's
PT-facing half named in Doc 66) received two rounds of real, independently
verified security fixes this session — a DNS-rebinding/TOCTOU gap and a
credential-leak-over-HTTP gap, both confirmed via direct reproduction before
fixing, plus a Host-header RFC-7230 port-inclusion bug and two deletion-guard
script gaps found in follow-up review. All are pushed and CI-green as of this
writing. This confirms the underlying finding (a legacy migration plan still
directing PT-side work) was real, while the specific PT work itself was
executed carefully with real regression coverage — the audit's finding is
about migration *doctrine*, not a claim that the PT work in flight was done
carelessly.

The useful foundations should remain: source preservation, thin-kernel
boundaries, canonical contracts, fail-closed security decisions, private-memory
sanitation, meaningful regression tests, and verification against the actual
resulting artifact.

---

## 2. Inventory, coverage, and access gaps

Repository inspection used the GitHub connection. The following default-branch
snapshots were observed:

| Repository | Observed main commit | Tree coverage | Findings about instruction surfaces |
| --- | --- | --- | --- |
| `diazMelgarejo/Perpetua-Tools` | `a551da4fa97e` | 1,552 files; non-truncated tree | 97 SKILL.md files; 3 AGENTS.md files; 7 Cursor rule files |
| `diazMelgarejo/orama-system` | `0df2194c3bf9` | 1,941 files; non-truncated tree | 190 SKILL.md files; 3 AGENTS.md files; 131 Cursor rule files |
| `oramasys/perpetua-core` | `86225fa5c974` | 68 files; non-truncated tree | No agent instruction files matching the audited instruction-file patterns |
| `oramasys/oramasys` | `8ad257401001` | 27 files; non-truncated tree | Same |
| `oramasys/agate` | `643add949e33` | 8 files; non-truncated tree | Same |
| `oramasys/alexandria` | `072f5bdfa743` | 2 files; non-truncated tree | README and license only |
| `oramasys/telos` | `88fba4beb95b` | 10 files; non-truncated tree | Boundary documentation, package, and tests |
| `oramasys/phylax` | `8ce8f69087ef` | 9 files; non-truncated tree | Boundary documentation, package, and tests |
| `oramasys/anamnesis` | Unavailable | Repository lookup returned 404 | Cannot distinguish nonexistent repository from unavailable access |
| `oramasys/Claude-Desktop-LLM` | Not pinned in this audit | Repository metadata accessible | Implementation and instruction tree not audited |

**Note on `diazMelgarejo/orama-system`'s commit**: `0df2194c3bf9` matches
exactly the `main` HEAD this session independently fast-forwarded to before
writing this document (`0df2194c3bf94fd6d5c5a24142448feb8a2808dc`) — the
audit's snapshot and this session's own checkout are the same point in
history, confirmed directly rather than assumed from matching prefixes alone.

The inventory counts exclude files inside unexpanded Git submodules.

### Instruction audit batches

| Batch | Inspected | Coverage limit |
| --- | --- | --- |
| Current workspace | Ancestor AGENTS.md locations; global Codex configuration structure and selected non-secret settings; local agent-definition directory | No applicable ancestor AGENTS.md found; no local Codex agent-definition directory found |
| Advertised skills | Session-provided names and descriptions | Discovery metadata is not evidence that every skill body is loaded |
| Superpowers | Nine full entry files, Codex adaptation reference, plugin manifest | Remaining five entry files and most supporting references uninspected |
| Legacy skill discovery | All 83 immediate `.agents/skills/*/SKILL.md` descriptions across both sources | Selected bodies inspected; remaining bodies inventoried only |
| Legacy repository instructions | Root AGENTS.md and CLAUDE.md; `.agent/AGENTS.md`; `.codex/AGENTS.md`; permission/configuration files | Root/mother skill files and CIDF received section-level inspection, not exhaustive body review |
| Hooks and agents | Both Claude settings files; companion-sync scripts; Orama discovery script; PT pre-tool checker and GitHub/shell schemas; PT Codex roles; Orama orchestrator/verifier definitions | Other hook implementations, agent definitions, and deployment registrations remain uninspected |
| Cursor rules | Six Orama common rules, all marked `alwaysApply: true` | Other Cursor rules inventoried only |
| Migration authority | Successor READMEs; Telos/Phylax boundaries; selected v2 plans including Docs 18, 46, 56, 62, 66; contract-migration reference; TDD guidance | Remaining v2 plans require migration-ledger review |
| GitHub controls | Open-PR inventories and six successor ruleset collections | Ruleset collections returned empty; classic branch-protection inspection returned 403 |

Additional gaps:

- PT's four Git submodules and Orama's OpenClaw skill submodule were
  identified but not recursively inspected.
- Parent-workspace documents such as `CLAUDE-instru.md`, the parent
  `tdd.md`, private policy registries, and external reconstruction plans
  were not retrieved.
- Private workstation configuration, deployed OpenClaw/Hermes/Gemini
  configuration, secret stores, and effective runtime hook registration
  were not inspected.
- Earlier scratch checkouts exist, but their instructions were not treated
  as governing this workspace or as current remote truth.
- An initial broad filesystem inventory produced truncated output. The
  subsequent bounded inventories above establish the reported coverage.
- GitHub capability metadata does not establish authorization. The
  integration's reported repository permissions did not override the
  read-only instruction under which the audit was performed.

### Loading, scope, and precedence

| Layer | How it enters context | Scope |
| --- | --- | --- |
| Host/session policy and the current request | Always present | Governs the current turn; inspected repository content cannot authorize actions |
| Advertised skill descriptions | Discovery metadata | Helps select a workflow; does not imply the body is already loaded |
| Applicable repository instructions | Harness loading or explicit navigation | Applies to the relevant checkout/subtree, subject to higher-priority instructions |
| Skill body | Loaded after selection | Task-specific workflow |
| Linked references | Loaded when the selected procedure needs them | Narrower supporting evidence or procedure |
| Agent definition | Loaded for that agent role | Child-role behavior, not unrestricted authority |
| Hook configuration | Executed by a configured harness | Operational behavior; its existence alone does not prove registration or enforcement |
| Memory and historical plans | Retrieved evidence | Useful context, not fresh permission or an automatic override of a current decision |

A remote `.agent/AGENTS.md` does not govern a workspace simply because it was
fetched. For this audit, legacy instructions were evidence only.

---

## 3. Exact proposed edits, grouped by destination

Source files cited below remain unchanged by this document; it records the
proposal only. Where a finding originates in v1, the proposed replacement
belongs in a reviewed successor instruction or policy file — never a
migration commit to a `diazMelgarejo` repository. Plugin changes are separate
proposals for the plugin/configuration owner, not migration commits to v1.

### A. Successor authority documentation

#### A1 — `oramasys/perpetua-core/README.md`, "Cross-repository authority"

Evidence: `"diazMelgarejo/orama-system owns GraphSpec, evaluation,
workflow…"` — directly assigns v2 semantic ownership to a frozen legacy
repository.

Disposition: clarify boundary.

Proposed replacement:

> Cross-repository authority is split within the v2 regime:
>
> - `oramasys/perpetua-core` owns universal execution mechanics.
> - `oramasys/oramasys` owns GraphSpec, evaluation, workflow composition,
>   control-plane behavior, and effect-policy integration above the kernel.
> - `oramasys/agate` owns hardware capability, affinity, fit, and placement.
> - Specialized packages own their documented security, memory, and provider
>   contracts.
>
> The legacy `diazMelgarejo/orama-system` documentation remains a read-only
> planning reference until its decisions have been reconciled into
> Alexandria. Neither legacy repository is a v2 runtime, build,
> installation, or test dependency.

Preserves: the small kernel and one-way import boundary.

#### A2 — `oramasys/alexandria/README.md`, opening, governance, and status

Evidence: `"not yet in active use"`; `"this repo receives copies"` — the
README describes a future copy migration and retains v1 repositories in its
governance table, in tension with treating new documentation and unchanged
legacy archives as separate.

Disposition: clarify boundary.

Proposed replacement for those sections:

> Alexandria is the destination for newly authored, reconciled v2
> specifications, ADRs, threat models, cross-repository standards, and
> migration evidence. Legacy documentation remains intact in the two
> `diazMelgarejo` repositories. Alexandria does not import their archives as
> active guidance. New documents cite pinned legacy sources and state which
> decisions they preserve, revise, or supersede.
>
> Until the migration authority handover is recorded, legacy Orama planning
> documents remain read-only planning references. All new planning documents
> and migration decisions are written in Alexandria.
>
> Documentation authority transfers by an explicit coverage and acceptance
> record. Repository existence alone does not complete that transfer.

Preserves: historical evidence and a controlled authority handover.

#### A3 — Telos and Phylax `README.md` / `docs/BOUNDARIES.md`, migration posture

Evidence: `"remain the dual authorities during migration"`; `"retain the
legacy behavior"` — these statements need an explicit regime qualifier and
should not invite legacy runtime dependence.

Disposition: clarify boundary.

Proposed shared replacement:

> This package belongs exclusively to the v2 `oramasys/*` regime. Legacy
> repositories are read-only evidence sources. Their behavior may inform
> sanitized conformance fixtures, but this package must not import, execute,
> install, modify, or silently fall back to a legacy implementation.
>
> Each migrated contract requires an explicit owner, versioned semantics,
> consumer tests, and recorded differences from the legacy reference.
> Reference implementations are not production-ready merely because these
> contracts exist.

Preserves: deny-by-default behavior, explicit admission boundaries, and
honest maturity claims.

#### A4 — New `oramasys/alexandria/migration/regime-boundary.md`

Evidence: this repository's own Doc 66 still specifies a PT-facing "Half B,"
and PT PR #382 is/was open for that work — a conflict with the migration
instruction, not proof the historical plan was unauthorized when written.

Exact proposed text:

> The migration write set contains only approved `oramasys/*` repositories.
> `diazMelgarejo/Perpetua-Tools` and `diazMelgarejo/orama-system` are
> immutable sources for this migration, including code, documentation,
> memory, branches, PRs, repository settings, and hooks.
>
> Earlier plans that direct source-side implementation are historical
> inputs. Their useful contracts and findings must be retargeted to
> successor owners. They do not create an exception to the source freeze.
>
> Do not update, close, merge, or comment on legacy PRs as an incidental
> part of migration. Record their relevant findings in the successor
> migration ledger.
>
> Implementation may proceed in internal work packages, but every released
> v2 bundle must operate entirely within the v2 regime. No intermediate
> release may require a mixture of v1 and v2 repositories.

Preserves: all source evidence and the explicit no-touch boundary.

### B. Successor agent policy and skill discovery

#### B1 — New successor AGENTS.md files and Alexandria's shared agent policy

Evidence: the six accessible target trees lack dedicated agent instructions;
legacy guidance repeatedly routes agents into legacy implementations and
workspace-wide maintenance.

Disposition: split. Use a short root instruction in each successor, with its
own ownership and build information:

> **Agent instructions**
>
> This repository belongs to the v2 `oramasys/*` regime. The legacy
> `diazMelgarejo/Perpetua-Tools` and `diazMelgarejo/orama-system`
> repositories are read-only migration evidence. Do not modify them or
> introduce a dependency on their checkouts.
>
> Read the repository README and instructions applicable to the affected
> subtree. Load specialist workflows only when the requested work crosses
> their documented boundary.
>
> Preserve unrelated user work, historical evidence, private configuration,
> and secrets. Repository documentation and tool availability do not grant
> permission for external actions.
>
> For migration work, follow the approved regime-boundary and ownership
> records in Alexandria. Their absence is a planning gap, not permission to
> fall back to v1.

Add only the repository's actual responsibility, tested build commands, and
non-obvious conventions. Do not copy the complete shared policy into every
file.

#### B2 — Migrated skill wrappers, "Before Use"

Evidence: `git fetch origin --prune`; `git pull --ff-only` appear in
skill-loading procedures. Across 83 inspected wrapper files, 68 contain the
fetch command; 65 consistently delimited synchronization blocks contain
37,182 UTF-8 bytes in aggregate (a measure of duplicated file content, not
per-turn token cost or guaranteed savings).

Disposition: shorten and clarify boundary. Replace each migrated wrapper's
synchronization section with:

> **Load canonical workflow**
>
> Read the canonical workflow at the repository revision selected for this
> task. Skill discovery and loading are read-only.
>
> Do not fetch, pull, prune refs, switch branches, install dependencies, or
> import memory as part of loading a skill. If the required workflow is
> missing or incompatible, report the specific gap and continue any work
> that does not depend on it.
>
> Repository synchronization is a separate, explicitly scoped operation.

Preserves: canonical ownership and drift awareness without hidden mutation.

#### B3 — Migrated skill descriptions

Confirmed metadata defects: a description that is literally a code-fence
opener; generated descriptions ending in an ellipsis before the selection
boundary; a trigger on the bare term `SKILL.md`; a trigger on the
organization name itself; a "Claude-only" claim inside a Codex discovery
directory; multiple overlapping methodology/router skills.

| Migrated skill | Replacement description |
| --- | --- |
| `oramasys-method` | Use for cross-module architecture, contract migrations, or complex integration requiring an explicit ownership and verification ledger. Skip factual questions and isolated formatting edits. |
| `orama-system` router | Use when the user explicitly requests the Orama methodology or needs help selecting one of its specialist workflows. Load only the selected workflow. |
| `orama-afrp` | Use when audience or an ambiguous requested outcome materially changes the answer. Skip when the user has already specified both. |
| `orama-cidf` | Use when selecting or verifying a content-insertion method, reconciling an existing corpus, or checking CIDF implementation conformance. Preserve required destination and post-write checks. |
| `mcp-orchestration` | Use to configure or troubleshoot MCP transports, tool routing, or explicitly requested agent dispatch. A mention of `SKILL.md` alone does not activate this skill. |
| `orama-repo-rules` | Use to locate this repository's applicable conventions when they are not already available from AGENTS.md. Read only the guidance relevant to the affected surface. |
| `agent-methodology` | Use when explicitly assigned the project's multi-stage reasoning workflow. Supports the current harness through its documented adapter. |
| `perpetua-hardware` successor | Use for hardware inventory, model fit, affinity, or placement decisions owned by Agate. Provider startup and health belong to the runtime adapter. |
| `perpetua-config` successor | Use to inspect or change model-registry and routing configuration. Resolve hardware policy through Agate and provider state through its adapter. |
| `self-discovery` | Use when requested to inspect stack topology or diagnose a cross-component problem. Limit inspection to the components needed for the task. |
| `self-improve` | Use when explicitly capturing or reviewing a reusable lesson. Do not activate solely because a session is ending. |
| `using-git-worktrees` | Use when isolation is needed for implementation, concurrent writes, or branch integration. Inspect existing isolation before creating another worktree. |

Disposition: narrow triggers. Preserves specialist workflows. The proposed
CIDF narrowing should receive a comparison test before adoption — it is not
a recommendation to remove its executable conformance contract.

#### B4 — Migrated memory instructions, replacing source `.agent/AGENTS.md` startup obligations

Evidence: `"review before substantive work"`; `"Log every significant
action"`; ordered reading of multiple memory collections and routine
write-back — conflicts with read-only tasks and risks diverting unrelated
work.

Disposition: split and narrow trigger. Proposed replacement for the
successor memory policy:

> Retrieve memory when prior decisions, user corrections, or known failure
> patterns materially affect the current task. Start with a targeted query
> and inspect the relevant evidence.
>
> Memory backlog maintenance is a separate task. Report a relevant backlog,
> but do not process unrelated candidates before the user's requested work.
>
> During migration, PT memory is read-only. Do not invoke writers,
> graduation tools, reflection hooks, or session write-back against it.
>
> After Anamnesis is provisioned, capture follows its configured
> private-store and promotion policy. Preserve evidence and provenance;
> generated views are updated through their renderer. Promotion remains
> sanitized and push-gated.

Preserves: continuity, lossless evidence, generated views, sanitation, and
human control over publication.

### C. Permissions and automatic behavior

#### C1 — Successor permission contract; Phylax enforcement implementation

Evidence in PT: `"enforces it before any tool invocation"`, but
`check_tool_call()`: returns allow for unknown schemas/operations; does not
evaluate `blocked_patterns`; does not evaluate `requires_approval_patterns`;
does not validate `required_args` or listed preconditions; uses keyword
overlap against prose restrictions; is not registered as a `PreToolUse` hook
in the inspected Claude settings.

Disposition: clarify boundary; preserve and implement enforcement. Exact
replacement contract:

> This policy declares required behavior. It is not proof that a harness
> enforces it.
>
> Each supported harness must register and test its admission adapter. The
> adapter must normalize tool operations, validate arguments, and obtain an
> explicit allow, deny, or approval-required decision before execution.
>
> Unknown mutating operations, malformed requests, missing policy, and
> unavailable required enforcement fail closed. Natural-language keyword
> matching is not an authorization mechanism.
>
> Every enforced restriction must have a test demonstrating rejection before
> the side effect. Documentation must identify unsupported harnesses and
> unenforced controls explicitly.

This finding requires implementation in the successor security package, not
just edited prose. Preserves: the intended permission gates and improves
their verifiability.

#### C2 — Successor shared permissions policy

Evidence: PT's permission document allows draft PRs without approval, while
its Codex guide requires explicit approval for third-party modifications;
the GitHub schema's `create_pr` has `requires_approval: false`; the portable
brain separately demands a new user answer before committing.

Disposition: clarify boundary. Proposed exact policy:

> Authorization is evaluated for the specific action, target, scope, and
> consequences. Existing explicit authorization remains valid within that
> scope; do not ask for it again.
>
> - Inspection: read relevant files and approved sources within task scope.
> - Local edits and tests: proceed when requested, within the approved
>   target repository and environment. Audit-only tasks permit neither.
> - Local commits: follow the task's stated commit authorization. Memory
>   promotion follows its separate configured approval policy.
> - External messages and resource changes: require explicit authorization.
>   A draft PR is an external write and may trigger notifications or CI.
> - Deployment and production migration: require approval for the concrete
>   artifact, environment, effects, and recovery plan.
> - Deletion, history rewrite, credential changes, and permission changes:
>   require specific authorization; never infer it from a general cleanup
>   task.
>
> Permission granted for one category does not grant the others. A denied
> action must not be retried through another tool to evade the boundary.

Preserves: intentional safeguards while eliminating redundant approval
requests.

#### C3 — Successor hook configuration

Evidence: session startup invokes discovery and companion-instinct import;
companion scripts may clone a legacy repo and use `import ... --force`; PT
runs `pytest tests/` after every Edit/Write; test and lint hooks end with
`|| true`; a Stop hook complains unless legacy lesson files changed.

Disposition: split and narrow trigger. Do not migrate these hook
registrations unchanged. Proposed replacement specification:

> SessionStart performs no network discovery, installation, repository
> synchronization, or memory import.
>
> Post-edit checks are selected by changed file type and affected contract.
> They report the command, result, and exit status. Advisory checks must be
> labelled advisory; their successful hook exit is not a passing test
> result.
>
> Run the affected test suite once after a coherent change, with broader
> verification at the documented integration gate.
>
> Stop checks the requested deliverable and reports unresolved blockers. It
> must not require unrelated memory writes or mutate state.

Preserves: timely feedback, completion inspection, and explicit diagnostics.

#### C4 — Migrated command permissions

Evidence includes `Bash(git branch *)`, `Bash(find *)`, `Bash(jq *)` — names
that do not establish read-only behavior; some arguments create/delete
branches, write files, or execute commands.

Disposition: clarify boundary. Proposed replacement:

> Authorize operations by validated arguments and effects, not command-name
> prefix alone. A command classified as inspection must not invoke
> mutation, output redirection, execution callbacks, or external writes.
>
> Prefer structured read tools. Where a shell allowlist is used, enumerate
> supported read forms and route unmatched forms through normal admission.

Preserves: convenient inspection without accidentally granting mutation.

#### C5 — `oramasys/oramasys/Makefile`, test target

Evidence: `make test` installs editable dependencies before running tests.

Disposition: split. Proposed diff:

```diff
 test:
-    .venv/bin/pip install -e $(PERPETUA_CORE) -q
-    .venv/bin/pip install -e ".[dev]" -q
-    $(if $(TELOS),.venv/bin/pip install -e $(TELOS) -q,)
     .venv/bin/python -m pytest src/tests/ -v
```

Document environment preparation under a `dev-install` target; later
replace mutable setup with the approved reproducible bundle workflow.
Preserves: the test command while separating installation authority and
side effects.

---

*Continued in [Part 2 — the execution program](instruction-audit-and-migration-plan-part-2-execution-program.md): completion/testing/merge doctrine, installed-Superpowers proposals, what's worth keeping, paper stress tests, and the full M0–M9 migration work-package plan.*
