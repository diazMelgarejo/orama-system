# Full Codex instruction-debt audit and migration report

Date: 2026-09-09. Scope: accessible session instructions, selected installed skill bodies,
legacy instruction surfaces, successor repositories, and their migration interactions.
The audit itself applied no instruction, code, settings, permission or memory changes.
The subsequent user instruction authorizes publishing this report and plans in this directory.
Read the [reconciliation](migration-harmonization-2026-09-09.md) alongside preserved Claude input.

## Highest-impact findings

| Priority | Finding | Evidence strength | Likely consequence |
| --- | --- | --- | --- |
| P0 | Legacy ownership language leaks into successor authority | Confirmed documentary conflict with current user scope | v2 work may modify or depend on v1 |
| P0 | Permission declarations exceed inspected checker behavior | Confirmed static gap; actual harness enforcement not established | False assurance that approval/deny patterns are enforced |
| P0 | Selecting wrappers can trigger repository fetch/pull | Confirmed repeated wrapper text | A read task becomes network/mutation work and may change instructions mid-task |
| P1 | Approval boundaries mix local work with external effects | Confirmed ambiguous language; prompt frequency unmeasured | Redundant stops or accidental broad authorization |
| P1 | Every-edit testing overlaps full-suite/coverage recipes | Confirmed static instructions; runtime cost not measured | Repeated unrelated tests, masked failures, premature stops |
| P1 | Legacy Gate 4 planning can route implementation back into PT | Confirmed historical plan direction, superseded by user scope | Source-freeze violation or a cross-regime dependency |
| P1 | Merge/history procedures overgeneralize real incidents | Confirmed imperative wording; behavior hypotheses below | Mandatory tours, false rewrite diagnoses or incomplete merge validation |
| P1 | UI guidance conflicts with a ban on visual verification | Confirmed text-level conflict in inspected guidance | Persisted code can pass without inspecting rendered UI |
| P2 | Discovery descriptions are broad and overlap | Confirmed inventory; selection cost requires comparison | Unrelated skill activation and avoidable loaded context |
| P2 | Machine/harness assumptions escape their original scope | Confirmed historical specifics; current runtime varies | Wrong commands or invented capability restrictions |
| P2 | Subjective scores and iteration limits obscure acceptance | Confirmed competing procedures | Review loops or false completion at an arbitrary threshold |
| P2 | Worktree cleanup and setup infer ownership/tooling too loosely | Confirmed recipes; destructive outcome is hypothetical | Wrong environment setup or removal of a shared checkout |

The setup also contains useful safeguards and durable knowledge. This is a targeted cleanup,
not a recommendation to flatten the methodology, remove security gates or erase incident history.

## Coverage, snapshots and access gaps

Repository trees were inventoried first. The following main snapshots were rechecked during
the publication preparation. Blob counts describe inventory size, not migration completeness.
All returned trees reported `truncated: false`.

| Repository | Commit | Blob files | Inspection coverage |
| --- | --- | ---: | --- |
| `diazMelgarejo/Perpetua-Tools` | `a551da4fa97e5fbc6f908ad077c7b6d8030a3220` | 1552 | Tree, selected root/agent/permission/hook files, wrapper metadata and contract evidence |
| `diazMelgarejo/orama-system` | `0df2194c3bf94fd6d5c5a24142448feb8a2808dc` | 1941 | Tree, roots, selected skills/references/rules, v2 docs and publication guards |
| `oramasys/perpetua-core` | `86225fa5c974ab2fe0b65d228a2b31888aaa440c` | 68 | Tree, README and selected package/contract surfaces |
| `oramasys/oramasys` | `8ad2574010013d9f5b40b193d316516872462130` | 27 | Tree, README and selected integration/contract surfaces |
| `oramasys/agate` | `643add949e33b39a8f47816fbc700a038e1d2ad5` | 8 | Tree and early schema/documentation surface |
| `oramasys/alexandria` | `072f5bdfa74338f7abbfb2482446577fc6263d2e` | 2 | Tree and README; documentation scaffold |
| `oramasys/telos` | `88fba4beb95b3809e0a6094fedc766b03cb95b0e` | 10 | Tree and typed contract/documentation surface |
| `oramasys/phylax` | `8ce8f69087ef56d9102695ad8d28e4c8e8d84c21` | 9 | Tree and typed contract/documentation surface |
| `oramasys/Claude-Desktop-LLM` | `ba4f3910efc6496cd6476a274b93f4b877ba12b3` | 33 | Tree inventory; provider runtime not fully audited |
| `oramasys/anamnesis` | Unavailable | Unknown | Lookup returned 404; absence and lack of access cannot be distinguished |

For pinned evidence, use the repository's `blob/<commit>/<path>` view. For example,
[Orama-AGENTS](https://github.com/diazMelgarejo/orama-system/blob/0df2194c3bf94fd6d5c5a24142448feb8a2808dc/AGENTS.md)
[Core-README](https://github.com/oramasys/perpetua-core/blob/86225fa5c974ab2fe0b65d228a2b31888aaa440c/README.md).

The `.agents` wrapper batch covered 83 files. Sixty-eight contained a fetch reference; 65
shared update blocks totaled 37,182 UTF-8 bytes. This is stored-text duplication, not measured
per-turn savings. Root file byte measurements were PT AGENTS 9,527, CLAUDE 19,255, SKILL 23,552
(52,334 combined); Orama AGENTS 12,258, CLAUDE 14,887, SKILL 13,209 (40,354 combined).
These files are not necessarily loaded together. Do not translate their sum into a context bill.

Inspected batches included PT `.agent/AGENTS.md`, permission protocols and selected schemas,
the pre-tool checker, Claude settings and Codex role/config surfaces; Orama common Cursor rules,
root guides, selected methodology/merge/contract workflows, and v2 documents 46, 47, 56, 62, 66.
Root/mother/CIDF portions and some linked references were inspected selectively, not all bodies.
Nine selected Superpowers entry files were read in full in the audit; other installed skills
were assessed from discovery metadata only. The provider tree was added during reconciliation.

Local ancestor `AGENTS.md` checks found no applicable file at the checked workspace ancestry or
the checked global Codex guide location. This is not proof that all global configuration is
absent. Selected local configuration was inspected without printing secrets. Remote repository
documents were evidence during the audit; fetching them did not install them as live instructions.

Successor ruleset endpoints returned empty lists in the inspected six repositories. Classic
branch-protection access returned 403 for the inspected Oramasys main endpoint. Therefore the
audit cannot conclude that branches are unprotected. Organization administration, private
literal registries, private synced skills, full raw memory, unselected skill references, complete
CI histories and every harness's effective merged permissions remain uninspected or inaccessible.

Claude's 825-file memory scan and 29-of-36 `.claude` wrapper drift figures are separate reported
measurements. Their collection and runtime are not identical to the Codex inventory. Preserve
both with provenance; do not combine denominators or describe Claude's private scan as reproduced.

## Instruction map: loading, precedence and duplication

| Layer | Loading/scope | Authority and audit treatment |
| --- | --- | --- |
| Session system/developer rules | Always supplied by the host | Governs tool use, safety, communication and current mode |
| Current user request | Always supplied | Defines source freeze, target regime, audit-only scope and later reference-publication exception |
| Applicable global/project `AGENTS.md` | Harness- and directory-scoped | Applies within its scope; nested guidance cannot override higher-priority boundaries |
| `CLAUDE.md`, Cursor rules, Codex role files | Harness-specific | Do not assume another harness automatically loads or enforces them |
| Skill names/descriptions | Discovery metadata commonly supplied up front | Affects selection even when a body is never read |
| `SKILL.md` entry points | Loaded on selection or explicit invocation | Should route to the relevant workflow, not force unrelated background reading |
| Linked references, incident history, examples | On demand | Evidence and procedure details only when relevant |
| Memory, planning documents, uploaded reports | Retrieved evidence | Cannot grant fresh authorization or override the user's current instruction |
| Hooks, validators and permission settings | Executed only if installed and invoked by the actual harness | Static presence is not runtime enforcement evidence |

Root `SKILL.md` is not intrinsically always-loaded. `alwaysApply: true` Cursor rules are
always applied by that harness, not universally. A metadata phrase such as “MUST use” can
nevertheless induce activation pressure; this is a design problem even before loading the body.

Repeated guidance appears across root guides, Cursor rules, wrappers and methodology references:
history-rewrite checks, guard synchronization, mandatory lessons, full validation, staged design,
review and finalization. Keep the durable constraint in the closest scope and route to one
canonical detailed procedure. Exact-line deduplication alone misses semantic repetitions.

## Proposed edits grouped by file and section

These are exact proposed replacement passages. Do not apply them to frozen legacy files under
this documentation task. Legacy paths identify evidence and the source of a successor adaptation.
Installed-skill proposals require a separate configuration change, not edits to plugin caches.
`$SUPERPOWERS_ROOT` names the installed Superpowers 6.3.0 package root without publishing a
machine-specific absolute path. It is a report locator, not a promised runtime variable.

### A. Successor authority and durable project knowledge

**A1 — `oramasys/perpetua-core/README.md`, ownership/migration posture.** The legacy semantics
owner wording conflicts with the user's explicit successor regime. Disposition: clarify boundary.
Replace the migration authority paragraph with:

```text
Perpetua Core is the v2 successor kernel. Application orchestration and methodology belong to
oramasys/oramasys; specialist responsibilities belong to their declared oramasys packages.
Legacy Perpetua-Tools is read-only contract and behavior evidence. It is not a runtime, build,
installation, test, CI or fallback dependency. Preserve pinned source lineage when mining it.
```

Preserves contract provenance and a small kernel without extending v1 ownership into v2.

**A2 — `oramasys/alexandria/README.md`, documentation migration.** Bulk migration language
risks copying an obsolete archive into the new authority. Disposition: clarify boundary.

```text
Alexandria contains newly authored, reconciled v2 documentation. Legacy archives remain in v1.
Each migrated topic records its pinned source lineage and current implementation evidence.
Transfer documentation authority explicitly after coverage and acceptance are recorded.
Historical links are provenance, not executable dependencies or permission to change v1.
```

**A3 — `oramasys/telos/README.md` and `oramasys/phylax/README.md`, migration posture.** Early
typed surfaces do not prove complete runtime behavior. Disposition: clarify boundary.

```text
This package participates only in the v2 regime. Do not import, execute, install, modify or
fall back to v1 repositories. Every exported contract names its owner, version, conformance
cases and implementation status. A schema or test fixture alone is not runtime enforcement.
```

Preserves typed specialist boundaries and honest maturity reporting.

**A4 — new successor regime-boundary reference, proposed in Alexandria.** The source-freeze
rule needs an explicit temporary documentation exception. Disposition: keep and clarify.

```text
All implementation changes target oramasys repositories. Both legacy repositories remain
independently usable. Orama v1 is temporary planning authority and PT is read-only evidence.
The approved 2026-09-09 publication may add reports/plans only under Orama v1 docs/v2/references/.
This exception does not authorize source code, settings, memory, history or unrelated PR edits.
```

**A5 — new scoped `AGENTS.md` in each successor.** Preserve build commands and conventions,
but do not import a historical repo tour. Disposition: split. Proposed common body:

```text
Read the nearest applicable instructions and only references relevant to the requested change.
This repository owns the responsibilities named in its README and versioned contracts.
Use the repository's declared setup and validation commands; do not infer a package manager
from the presence of one file. Keep setup/install actions separate from tests.
All implementation is v2-only. Treat legacy files and memory as read-only evidence.
Skill selection does not authorize synchronization, installation, memory import or publication.
Continue authorized work through relevant verification. Report exact blockers and unrun checks.
Keep private runtime records outside git; publish sanitized categories and provenance only.
```

Add the actual owner-specific commands and architectural constraints after verifying them.
Do not invent commands merely to fill a template.

### B. Skills: discovery, entry points and memory

**B1 — both legacy `.agents/skills/*/SKILL.md` wrapper batches, “Before Use” update blocks.**
Supporting excerpt: `git fetch` / `git pull`. These commands mutate refs or checkout state and
consume time when merely selecting a skill. Disposition: shorten and split in generated v2 wrappers.

```text
Read the canonical skill at the selected installed revision. Load linked references only when
their selection condition matches the task. Do not fetch, pull, install, import memory or
rewrite this checkout during skill loading. Updating the skill package is a separate task.
```

Preserves current canonical guidance at an identifiable revision and removes implicit updates.

**B2 — matching canonical skill frontmatter descriptions and generated adapters.** The broad
router/methodology/hardware/self-improvement triggers overlap. Disposition: narrow trigger.
Use these exact candidate descriptions, then run the selection comparison before rollout:

| Skill | Proposed description |
| --- | --- |
| `oramasys-method` | Use for cross-module architecture, contract migration or complex integration requiring explicit tradeoffs. Skip factual answers, formatting and isolated text fixes. |
| `orama-system` | Use when explicitly selecting or routing an Orama methodology workflow. Load only the selected workflow and its relevant references. |
| `orama-afrp` | Use when audience or framing ambiguity materially changes the requested answer or artifact. Skip when the current request already settles that choice. |
| `cidf` | Use for content insertion, placement, reconciliation or conformance governed by CIDF. Preserve its applicable policy checks. |
| MCP orchestration skill | Use to configure or troubleshoot MCP transport, routing or explicit agent dispatch. Mentioning an agent or SKILL.md alone is insufficient. |
| `repo-rules` | Use to locate missing repository conventions needed for the current change. Skip when applicable instructions already supply them. |
| `agent-methodology` | Use for an explicitly assigned staged agent workflow with a supported adapter for the current harness. |
| `perpetua-hardware` | Use for v2 hardware inventory, availability, fit or affinity decisions owned by Agate. Provider serving operations use their provider workflow. |
| `perpetua-config` | Use for model registry or routing configuration in its declared v2 owner. Do not activate for unrelated configuration files. |
| `self-discovery` | Use for a requested topology or cross-component discovery task. Limit inspection to the components needed to answer it. |
| `self-improve` | Use when explicitly capturing an authorized reusable correction or lesson. Do not activate merely because a session is ending. |
| worktree skill | Use when concurrent writes or integration work needs an isolated checkout. First detect whether a suitable owned workspace already exists. |

Map each candidate to its actual canonical source path during generation; do not assume every
display name corresponds to an identically named folder. Preserve meaningful specialist routing.

**B3 — canonical entry files and linked references.** The relevant Orama methodology,
integrative-merge and contract-migration bodies contain valuable procedures but are linked from
broader roots. Disposition: split by workflow. Proposed entry text:

```text
Select one workflow matching the requested operation. For contract migration, load the contract
workflow; for semantic branch integration, load integrative merge; for history repair, load the
history procedure. Do not load all three for an ordinary local change. Preserve exact checks
inside the selected workflow when their documented preconditions apply.
```

Stale `git-reanchor` and worktree-document references need path verification; a missing path
must be reported, not replaced by a guessed command. A referenced security-enforcer workflow
was not found in the inspected trees. Preserve the security requirement while fixing its locator.

**B4 — PT `.agent/AGENTS.md` and memory-trigger passages, successor adaptation.** Mandatory
backlog/lessons reading and writeback can turn a small task into a repository-memory operation.
Disposition: narrow trigger and clarify boundary.

```text
Retrieve only memory relevant to the current task, especially applicable prior corrections.
Backlog review is a separate requested workflow. PT memory is read-only migration evidence.
Capture an authorized reusable lesson in private v2 staging; sanitize before promotion and
publish only when that publication is authorized. Session completion does not require a push.
```

Preserves learning and provenance while preventing automatic private-data migration.

### C. Permissions, hooks and executable enforcement

**C1 — PT `.agent/protocols/permissions.md`, associated schemas and pre-tool checker.**
Supporting schema keys include `blocked_patterns`, `requires_approval_patterns`, `required_args`
and `preconditions`. The inspected checker does not enforce all declared fields, permits unknown
operation/schema paths, and relies on keyword/prose matching. Claude PreToolUse registration
for that checker was not established. Disposition: clarify boundary now, implement in Phylax.

```text
These declarations are policy requirements, not proof of enforcement. Each supported harness
adapter must normalize the operation and arguments, validate required fields/preconditions,
and produce an explicit allow, deny or approval-required result before side effects.
Unknown or malformed mutating operations must not default to allow. Test adapter registration
and negative cases in the actual invocation path. Do not claim protection from an unused file.
```

Preserves admission policy and strengthens evidence without pretending the audit fixed runtime.

**C2 — permission boundaries across root guides, schemas and session completion rules.**
Disposition: clarify boundary; do not automatically broaden permissions.

```text
Authorization is specific to the target, scope and effects. Reuse it for the same authorized
action; do not ask again because the action occurs in a later step.
Reading does not authorize edits. Requested scoped local edits and relevant local tests may
continue unless this task is audit-only. A local test may still need separate approval if it
contacts production, mutates external state or installs dependencies.
Commit/push or draft-PR publication must be within the authorized repository and scope.
External messages, deployment, production migration, destructive deletion, history rewrite,
credential rotation and permission expansion need authorization for those specific effects.
Prepare a concrete reviewable result before requesting an approval that is still required.
Never treat approval of one category as approval of another, or bypass an enforced rejection.
```

This preserves real external-action gates while removing redundant local-work stops.

**C3 — PT/Orama `.claude/settings.json` and successor hook adapters.** Supporting excerpts:
`PostToolUse`, `pytest`, `tail`, `|| true`; source Stop output is advisory. Static hook recipes
can suppress a nonzero test result or run the suite after every edit. Runtime frequency is a
hypothesis until replayed. Disposition: split and clarify.

```text
Session start may locate the workspace and expose relevant instructions; it must not discover
the network, synchronize repositories, install tools or import memory without task authority.
Post-edit checks consume the documented harness payload, select a fast affected check when
appropriate, and preserve the check's exit status even when output is truncated.
Run the applicable suite once per coherent change, then rerun only after relevant changes or
to resolve a concrete risk. Label advisory output as advisory. Stop hooks must not silently
mutate memory or substitute a reminder for validation of the requested deliverable.
```

The inline Ruff environment/stdin discrepancy deserves a fixture using the actual harness
payload; do not claim all hook failures are proven by static inspection alone.

**C4 — shell allowlists and schemas using wildcard command prefixes.** Supporting examples:
`git branch`, `find`, `sort`, `jq`. Each has mutating argument forms. Disposition: clarify boundary.

```text
Do not label a command family read-only by prefix. Admit only explicitly validated argument
forms whose effects match the authorized category. Prefer structured read APIs. Unmatched
forms go through the ordinary permission decision; they do not inherit a wildcard grant.
```

**C5 — PT `Makefile`, test target setup side effects; adapt in successor build tooling.**
The inspected target includes three package-install steps before testing. Disposition: split.

```makefile
test:
    pytest

# Keep the repository's verified development setup in a separately requested dev-install target.
```

Retain existing relevant pytest arguments in the actual implementation. Do not remove required
setup documentation; separate dependency installation from a command advertised as a local test.

### D. Validation, completion, history and merge workflows

**D1 — Orama `.cursor/rules/common-testing.mdc`, common workflow rules and methodology checks.**
Supporting fragments include `alwaysApply: true`, full-suite instructions and an `80%` coverage
floor. Broadly loaded security/review roles can activate on unrelated commits. Disposition: narrow.

```text
Choose verification by changed behavior and risk. Text changes need diff, applicable lint and
link checks. Behavior changes need a regression case and affected-consumer checks. Refactors
need evidence that the affected behavior remains covered. Configuration needs syntax and
effect checks. Database changes need upgrade, repeatability and failure/recovery evidence.
UI changes need rendered inspection of the touched view plus relevant behavior checks.
Integration and release work must satisfy declared full gates. Do not impose a universal
coverage percentage or every-review-role ceremony on unrelated changes.
```

Preserves required release/security gates and allows additional checks when a concrete risk exists.

**D2 — visual-verification prohibition in inspected guidance.** Supporting excerpt:
“never visually.” Disposition: clarify boundary.

```text
Verify persisted changes programmatically where possible. For user-visible layout or interaction
changes, also inspect the rendered result in the relevant environment. Neither code inspection
nor screenshots alone establish both behavioral correctness and visual quality.
```

**D3 — Orama `bin/orama-system/skills/oramasys-method/references/integrative-merge.md` and root
merge directives.** Supporting excerpts: “Simulate merges first”, “pytest before push”. A merge
simulation may mutate a checkout; additive record preservation needs identity-aware handling.
Disposition: narrow trigger and clarify completion.

```text
Inspect the intended change and both relevant states before semantic integration. Use a
disposable owned checkout for a trial merge; do not call it read-only. Resolve mechanical
conflicts within authorized scope. Ask only when a material semantic choice cannot be inferred.
For historical records, preserve distinct evidence and conflicting same-ID entries for explicit
reconciliation; deduplicate only demonstrably identical records. Verify the resulting target
content and applicable behavior. An empty three-dot diff alone is not proof of a correct merge.
Wait for required checks using event/status evidence and a bounded retry policy. If progress
stalls, report the exact blocker; a fixed sleep or exhausted review loop is not acceptance.
```

Preserves synthesis, history and verification without mandatory unrelated testing or idle loops.

**D4 — both root `AGENTS.md` history sections; Orama section “History-rewrite & branch
re-anchor”.** Exact excerpts: “MANDATORY before judging any branch”, “identical content,”
“HALT”, and “that contradiction means a rewrite”. Equal trees can also follow reverts or empty
commits; ancestry remains evidence even when insufficient alone. Disposition: narrow and clarify.

```text
When history rewriting is known or suspected, compare ancestry, trees and patch equivalence
before deciding what work is missing. Identical trees alone do not prove a rewrite. Preserve
old refs before authorized history surgery. Load the recovery procedure only for relevant
history operations, and obtain explicit authority for force-updating an existing remote ref.
```

Do not delete the incident record, pin-preservation procedure or rewrite approval gate.

**D5 — methodology completion scores and maximum-iteration rules.** Supporting thresholds
include `0.8` and `0.75`. Different procedures are not a single objective acceptance rule.
Disposition: clarify boundary.

```text
Define observable acceptance criteria and required evidence before implementation. Review
intensity scales to risk. A confidence score may guide another inspection but cannot waive
an unmet criterion. An iteration limit ends an unproductive loop, not the acceptance gate.
When another pass produces no new evidence, report the remaining blocker and next concrete
decision. Pass bounded relevant context to reviewers instead of the entire transcript.
```

**D6 — Orama root incident and environment sections.** Supporting headings include “Claude
Code runtime”, “On every cloud session”, and the relay-cursor naming exception. Disposition:
keep durable knowledge, split historical/environment recipes.

```text
Preserve the relay-cursor Coordinator identity exception when changing its persona or registry.
Load runtime-installation guidance only when changing the Claude installation. Apply the
relevant harness attribution procedure only when committing in that harness. Do not run
workspace-wide guard synchronization as a side effect of an unrelated repository task.
```

The source's attribution single-source policy remains useful. Implement v2 governance in a
declared successor owner with pinned consumers; do not use it to authorize changes across v1.

### E. Installed Superpowers proposals

These findings concern the inspected package at `$SUPERPOWERS_ROOT/skills/`. The following
table supplies the file/section cue, supporting excerpt, exact replacement and preserved value.
Disposition is narrow trigger/clarify unless otherwise stated. None was applied to installed files.

| File and section | Supporting cue | Exact proposed replacement | Preserves |
| --- | --- | --- | --- |
| `using-superpowers/SKILL.md`, activation | `1%` chance; invocation before any response | Select a skill when its stated task boundary materially matches the request. Do not invoke unrelated skills merely because they might conceivably help. | Relevant skill discovery |
| `brainstorming/SKILL.md`, design gate | every creative change; approval before implementation | Reuse an accepted specification. Explore alternatives when unresolved choices materially affect behavior, cost or architecture. Ask only for those choices; a typo or fully specified routine edit needs no new design approval. | Deliberate design where needed |
| `writing-plans/SKILL.md`, plan detail | full implementation code in each task | Produce concrete owners, dependencies, acceptance and verified commands. Include exact code only when the interface is known and it helps review; mark unknown interfaces for discovery rather than inventing them. | Executable, reviewable plans |
| `executing-plans/SKILL.md`, stop conditions | stop on test failure | Diagnose an expected or routine local failure within scope. Stop only for missing access, an unresolved material decision or effects needing new authority. Report the failing command and next step. | Honest blockers and review checkpoints |
| `finishing-a-development-branch/SKILL.md`, final menu | mandatory integration options | Reuse the user's established integration choice. Verify the artifact and continue through the authorized operation. Ask only when the target or integration effects are unresolved. | Safe deliberate integration |
| `test-driven-development/SKILL.md`, code written first | delete code and start over | Preserve existing and unrelated work. Demonstrate a meaningful regression failure against the prior behavior, then verify the fix. Do not delete working code merely to reconstruct a procedural history. | Evidence that the test detects the defect |
| `verification-before-completion/SKILL.md`, evidence freshness | verification in this message | Tie evidence to the exact artifact revision. Rerun after relevant changes or when a concrete risk invalidates it; do not rerun unchanged checks solely because another message intervened. | Evidence before success claims |
| `using-git-worktrees/SKILL.md`, setup and cleanup | pyproject implies Poetry; cleanup directory | Read declared setup commands, detect a suitable existing checkout, and record ownership of any created worktree. Keep installation separate. Remove only an owned disposable checkout after confirming no unpreserved work. | Isolation without inferred ownership |
| `references/codex-tools.md`, capability assumptions | detached HEAD cannot push | Use the current tool schema and observed result to determine supported operations. Detached HEAD is a checkout state, not proof that no permitted publication mechanism exists. | Tool-aware execution |
| `systematic-debugging/SKILL.md`, environment diagnosis | print environment values | Inspect only required variables and report presence or redacted shape. Do not print credentials or unrelated environment values. | Useful diagnostics without exposure |

Some paths are linked support references rather than always-loaded entry bodies. Validate the
installed package's exact locator before implementing any change. Do not remove a procedure on
the assumption that a newer model no longer needs it; use the comparison tasks below.

## Safeguards and knowledge to retain

Keep concise read-only PT Codex explorer/reviewer/docs-researcher roles. A model-version label
alone is not evidence of debt. Keep contract-oriented vertical slices, kernel boundaries,
Telos/Phylax typed separation, source lineage, private-data sanitation and identity/attribution
requirements. Preserve the Coordinator persona exception and non-obvious transport conventions.

Keep history backups before authorized rewriting and explicit approval for consequential effects.
Keep compatibility facade names when they serve users; distinguish a name from a live dependency.
Keep generic secret/topology guards independent of private-registry availability. A documented
intentional local/LAN endpoint needs policy-aware admission, not an indiscriminate prose ban that
breaks the product's declared topology. Missing enforcement must be repaired, not papered over.

## Five paper walkthroughs: predicted behavior, not executions

No database migration, UI change, failing test scenario or deployment was executed for this audit.
The “current” paths below are hypotheses based on intersecting instructions, not measured traces.

| Scenario | Request → activation → reading | Actions and approval boundary | Stopping condition and friction | Proposed behavior |
| --- | --- | --- | --- | --- |
| Typo fix | Correct one sentence → broad router/methodology/Superpowers selection → root history, lessons, staged design and wrapper update references | A wrapper may fetch/pull; every-edit hook may run pytest; design or large-document rule may ask approval already covered by the request | Stops for design/review or unrelated red suite; high effort without better text evidence | Read scoped guide and sentence context; edit; diff/lint/relevant links; finish without unrelated skill or runtime suite |
| Database migration | Add a schema field → brainstorming/TDD/executing plan → migration, security and test procedures | Write migration and regression; expected red conflicts with stop-on-failure; distinguish local isolated rehearsal from production execution | May stop at a useful expected failure, or mistake code authorization for production permission | Verify upgrade, repeatability, interrupted recovery and affected consumers; prepare production artifact/backup/rollback; obtain only still-required production approval |
| UI visual change | Adjust layout → UI/methodology/testing → design, coverage and conflicting visual rule | Code and tests may run while visual inspection is discouraged; unknown preview access can cause another stop | Claims completion from code alone or runs a broad suite that does not assess layout | Inspect persisted diff and rendered affected view; verify interaction; if rendering is inaccessible, report the specific missing evidence without claiming visual success |
| Failing local test | Fix a regression → debugging/TDD/execution workflow → competing stop and diagnose instructions | A hook's `tail`/`\|\| true` may hide failure; execution recipe may halt instead of diagnosing; setup may install packages | Stops too early or falsely passes due to masked exit; loop can continue without new evidence | Preserve real exit, classify expected/unrelated/product failure, fix within scope, rerun affected checks; stop only on an actual blocker and report unrelated baseline failures |
| Deployment requiring approval | Prepare and deploy a named release → finishing/release/permission workflows → full menu and approval text | Existing authorization may be requested again, or a broad push grant may be misread as production approval | Stops before a reviewable artifact, or acts beyond granted effects | Build and validate concrete candidate, inspect target/effects, prepare rollout and rollback; request required approval once at the final consequential step; verify after authorized rollout |

The revised paths still stop on real ambiguity, inaccessible required evidence and unapproved
consequential effects. “Continue” is not a requirement to bypass policy or invent a passing result.

## Complete migration program

The original program consists of M0–M9: baseline/authority; exhaustive coverage ledger;
foundations; contracts; specialists; Core; Oramasys integration; knowledge; release assembly;
and approved rollout. Its full actionable synthesis, owner map, dependencies, validation and
execution ledger are in the [integrated plan](integrated-v2-migration-plan-2026-09-09.md).

The required migration coverage includes code, configuration, contracts, agents, wrappers,
skills, hooks, permission adapters, source tests, memory, documentation, provider behavior,
integration, packaging and release evidence. It cannot be reduced to copying docs and skills.
All relevant source capabilities receive explicit dispositions and target acceptance evidence.

The six inspected successor trees alone do not prove independence: imports, package metadata,
installers, CI, runtime dynamic loads, shell commands and fallback behavior must be checked.
Build a release candidate with v1 repositories absent. Verify compatible pinned package versions,
real adapters and selected supported environments, not only local mocks. Keep local DNS/network
fixtures safe; do not contact metadata or production services to demonstrate a negative test.

No source changes, memory import, deployments, merges or empty permission-probe commits belong
to the original audit. The current documentation exception is narrow. Existing legacy PRs are
evidence and independent work, not authority to resume their implementation under this migration.

## Smallest useful cleanup batch and improvement checks

First update successor authority paragraphs, add short scoped owner guides, and establish the
coverage/decision ledger. This makes later implementation direction reviewable without removing
any safety gate. Next generate narrowed wrappers from one canonical owner; then fix permission
and hook enforcement with meaningful fixtures. Sanitize copied memory before any import.

Run a small before/after comparison on the same model, repository snapshot, task and tool access.
Use the five paper scenarios as isolated comparison tasks. Measure actual discovered and loaded
bytes/tokens, skills selected, references read, approval requests, tool actions, elapsed time and
verification relevance. A shorter prompt is not an improvement if an acceptance gate disappears.

Require zero unauthorized source writes and zero unrelated external effects. Check that a typo
does not run runtime suites; the database test still covers repeatability/recovery; the UI check
still renders; failing checks preserve nonzero exits; and deployment still requires the correct
approval. Replay malformed/unknown permission inputs and verify rejection before side effects.
Test missing hook registration, unsupported argument forms and private-registry absence.

For uncertain workarounds, compare one bounded task with and without the trigger while retaining
the safeguard: a branch with equal trees after a revert, a shared pre-existing worktree, a known
expected failing regression, or a rendered layout defect that unit tests miss. Keep the rule if
it demonstrably prevents the failure; otherwise narrow its precondition before considering removal.

Stop the audit when coverage/gaps, evidence, exact proposed text, scenario predictions, smallest
batch and evaluation checks are reviewable. Do not silently treat a proposal as an applied fix.
Stored-byte figures above are measured inventory; token or runtime savings remain unmeasured.
