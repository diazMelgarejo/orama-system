# Instruction Audit & v2 Migration Plan — Part 2: The Execution Program

> **Status:** planning reference, not yet implemented.
> **Scope:** exclusively `oramasys/*`. See
> [Part 1](instruction-audit-and-migration-plan-part-1-findings-and-edits.md)
> for the audit's scope note, provenance, and findings 1–2, and sections
> A–C of the proposed-edits inventory.

---

## 3 (continued). Exact proposed edits — D and E

### D. Completion, testing, and merge doctrine

#### D1 — Successor verification standard and migrated Cursor rules

Evidence: `"Before ANY commit"`; `"Test Types (ALL required)"`; `"Verify
80%+ coverage"` — unconditional in inspected `alwaysApply` Cursor rules.
Source TDD guidance also requires a full suite before every commit, while
separately permitting documentation/configuration exceptions.

Disposition: narrow trigger. Exact replacement:

> Choose validation from the changed behavior and its risk.
>
> - Text-only changes: inspect the diff and run applicable
>   formatting/link checks. Do not add behavioral tests merely to
>   accompany the edit.
> - Behavior changes and bug fixes: use a meaningful regression test and
>   verify the affected consumers.
> - Refactors: preserve covered behavior; add coverage where the relevant
>   contract is otherwise unprotected.
> - Configuration changes: validate syntax and test behavior when the
>   setting affects security, routing, deployment, or runtime semantics.
> - Database changes: test existing-data upgrade, repeat execution,
>   interruption, recovery, and all affected readers/writers.
> - UI changes: combine programmatic checks with rendered visual
>   inspection.
> - Integration/release: run the declared package and cross-package gates.
>
> Coverage thresholds apply only where explicitly defined for the
> component. Do not invent unrelated tests or expand scope to meet a
> generic percentage.

Preserves: TDD's regression value and stronger gates for consequential
changes.

#### D2 — Migrated `oramasys-method`, verification wording

Evidence: `"Verify programmatically, never visually."` — later wording
says `"never visual only,"` which is materially different.

Disposition: clarify boundary. Replace the conflicting wording with:

> Verify behavior and persisted results programmatically. For changes
> whose correctness includes appearance, layout, animation, or rendered
> content, also inspect the actual visual output. Neither form of
> evidence substitutes for the other.

Preserves: CIDF's requirement to verify actual insertion, while allowing
necessary UI inspection.

#### D3 — Migrated merge reference and portable-brain merge procedure

Evidence: every conflict requires a separate user question; a fixed
ten-minute wait is required between merges; "simulate" uses a command that
changes the index/worktree; JSONL collisions are resolved by keeping the
first record; the doctrine says preserve everything, but also allows taking
corrected behavior.

Disposition: clarify boundary and shorten. Proposed replacement:

> Integrate the requested branches against the verified target revision.
> Inspect conflicting intent and preserve unrelated work and historical
> evidence.
>
> Use a disposable worktree for a merge trial; a no-commit merge still
> changes its index and working tree. Do not describe it as read-only.
>
> Resolve mechanical conflicts within existing authorization. Ask only
> when the conflict requires an unresolved product, security, data-loss,
> or ownership decision.
>
> Preserve both records when equal identifiers contain different
> evidence. Deduplicate only demonstrably identical records; render
> derived views through their canonical generator.
>
> Wait for the required checks and current mergeability state, not a
> fixed elapsed time. Use a bounded retry policy and report the specific
> unresolved condition.
>
> Before completion, inspect the resulting target content and run the
> relevant acceptance checks. A merge label, ancestry relationship, or
> empty diff alone does not prove every intended behavior survived.

Preserves: lossless integration, user control over consequential choices,
and real verification.

#### D4 — Migrated root instructions, rewritten-history section

Evidence: `"N behind + identical content" … "means a rewrite"` — identical
trees with different histories do not uniquely establish a rewrite; reverts
or empty commits can also produce that state.

Disposition: shorten and clarify boundary. Proposed replacement:

> Across a known or suspected history rewrite, do not use ahead/behind
> counts alone to decide whether work is missing. Compare ancestry, tree
> content, and patch equivalence, then inspect the intended changes.
>
> Identical trees establish content equivalence at those tips, not the
> cause of their different histories.
>
> Load the history-recovery workflow only for rewrite recovery, branch
> salvage, or ambiguous integration. Preserve original refs before
> authorized history changes.

Preserves: the safeguard against losing work after rewrites.

#### D5 — Migrated orchestrator/verifier definitions

Evidence: one section requires elegance ≥0.8; another permits proceeding
when the iteration limit is reached; another uses 0.75. A verifier is
mandatory for every task, and delegated agents receive "full context."

Disposition: clarify boundary. Proposed replacement:

> Completion is determined by explicit task acceptance criteria and
> recorded verification evidence. Subjective scores may inform review but
> cannot waive a failed requirement.
>
> Delegate only bounded work with the relevant files, constraints, source
> revision, expected output, and acceptance criteria. Do not send the
> entire transcript by default.
>
> Use independent review where the task's risk or agreed workflow
> requires it. The parent remains responsible for inspecting the combined
> result.
>
> When repeated attempts stop producing new evidence, report the tested
> hypotheses and remaining decision. Do not treat an iteration limit as
> PASS.

Preserves: independent review, bounded retries, traceability, and parent
accountability.

### E. Installed Superpowers proposals

These paths are under
`/root/.codex/plugins/cache/openai-curated-remote/superpowers/6.3.0/`. They
should be changed through a reviewed plugin update or maintained
customization, not an incidental cache patch.

| File / section | Supporting excerpt | Disposition and exact replacement |
| --- | --- | --- |
| `skills/using-superpowers/SKILL.md`, activation | "even a 1% chance" | Narrow trigger: "Select skills from their stated task boundaries. Read a body when its workflow is likely to affect the work, or when explicitly requested. Do not activate skills from incidental keywords." |
| `skills/brainstorming/SKILL.md`, hard gate | "EVERY task on EVERY path" | Clarify boundary: "For authorized bounded work, use existing requirements and proceed after stating necessary assumptions. Ask before implementation only when a material design choice remains unresolved or explicit design approval is required. For audit/plan requests, produce the complete requested review artifact without implementation." |
| `skills/writing-plans/SKILL.md`, no placeholders | "code blocks required for code steps" | Split: "A program plan defines owners, dependencies, interfaces, acceptance evidence, and decision gates. Add executable code-level steps after the relevant contracts and repository state are verified. Mark unknowns with an owner and closure gate; do not invent implementation details to make a plan appear complete." |
| `skills/executing-plans/SKILL.md`, stop conditions | "test fails" | Clarify boundary: "Treat a test failure as evidence to diagnose within scope. Continue through locally resolvable failures. Ask only for missing authorization, unavailable required access, or an unresolved decision that changes the intended outcome." |
| `skills/finishing-a-development-branch/SKILL.md`, menu | "Wait for their answer" | Clarify boundary: "Carry out the integration action already authorized for the verified target. Ask only if the integration choice or target remains unresolved." |
| Same file, cleanup | "under `.worktrees/` … we own cleanup" | Clarify boundary: "Cleanup requires recorded task ownership, verification that no unique work remains, and applicable authorization. Directory name alone does not establish ownership." |
| `skills/test-driven-development/SKILL.md`, recovery | "Delete code. Start over" | Clarify boundary: "Do not delete existing or unrelated work to recreate a test-first sequence. Add a meaningful regression test and demonstrate its sensitivity safely. Prefer test-first development for new behavioral changes." |
| `skills/verification-before-completion/SKILL.md`, freshness | "in this message" | Shorten: "Use evidence from the exact artifact revision being claimed. Repeat checks when relevant inputs or code changed, or when nondeterminism invalidates the evidence. State the actual scope of each check." |
| `skills/using-git-worktrees/SKILL.md`, setup | `pyproject.toml` → poetry install | Clarify boundary: "Determine the package manager from repository configuration and documented commands. The presence of `pyproject.toml` does not imply Poetry. Separate installation from inspection and testing." |
| `skills/using-superpowers/references/codex-tools.md`, capability assumptions | "detached HEAD … cannot branch/push/PR" | Clarify boundary: "Use the current tool schema and observed capability errors. Detached HEAD is repository state, not proof of a permission restriction. Do not change configuration to manufacture capabilities." |

These replacements preserve planning, isolation, testing, review, and honest
completion. Their predicted efficiency improvements require comparison
testing.

A further confirmed issue appears in the debugging skill's diagnostic
example: it prints environment-variable values. Replace value-printing
diagnostics with presence-only checks and redacted structured evidence.
Debugging must not introduce credential disclosure.

---

## 4. Instructions worth keeping

- PT's Codex explorer, reviewer, and documentation-researcher definitions
  are concise and read-only.
- The contract-migration reference correctly follows persistence →
  contracts → callers → transport → lifecycle → operations.
- Telos distinguishes endpoint-use authorization from transport safety and
  paid-call reservation.
- Phylax explicitly states that scaffold evidence checks are not
  cryptographic provenance verification.
- The successor kernel's one-way dependency boundary is valuable.
- `PerpetuaToolsGatewayFacade` currently delegates within v2; its
  legacy-shaped name alone is not evidence of a v1 dependency.
- Private-memory sanitation, generated-view ownership, history
  preservation, UTF-8 handling, and protection against accidental file
  loss remain useful.

Model pins, incident references, and specialist procedures should not be
removed merely because they are old. Retain them until compatibility
evidence or a comparison task justifies a change.

---

## 5. Paper stress tests

These walkthroughs are hypotheses, not executed scenarios. Legacy paths
describe what could happen if their instructions were imported into a
successor setup unchanged.

| Scenario | Request → activation → reading | Actions and approval boundary | Predicted stopping problem | Intended completion |
| --- | --- | --- | --- | --- |
| Typo fix | Broad skill router → repo rules → lessons/mother skill; a PR edit can activate merge doctrine | Wrapper may fetch/pull; edit hook may run all tests; commit/design rules may ask again | An isolated text correction becomes a repository tour, synchronization task, and approval exchange | Inspect affected text, make authorized edit, run relevant formatting/link checks, inspect diff, finish |
| Database migration | Brainstorming → contract-migration reference → TDD → permissions | Build migration and tests locally; actual database execution requires scoped approval | Execution skill may stop on the first failing test even though red-first is expected; plan may confuse sandbox rehearsal with production mutation | Prove upgrade, retry, interruption, compatibility, and recovery in an isolated environment; prepare concrete production approval packet |
| UI change requiring visual inspection | Brainstorming → TDD → method/CIDF → frontend workflow | Implement and programmatically test; render and inspect | "Never visually" can suppress required inspection; 80%/all-test-type rules may expand scope unnecessarily | Inspect rendered states and supported viewports, interactions, accessibility essentials, and relevant programmatic checks |
| Failing local test | Executing-plans → stop rule versus systematic-debugging → investigate | Reproduce, isolate, fix within authorized scope | One workflow asks for help immediately; another mandates diagnosis; a hook may hide the failing exit status | Resolve in-scope cause and rerun relevant checks; report a concrete access/decision blocker only if diagnosis cannot proceed |
| Deployment requiring approval | Finish-branch workflow → permission policy → deployment gate | Build, verify, inspect diff/configuration, prepare artifact and rollback information | Generic integration menu may appear despite an existing decision; other prose might imply automatic push/merge | Stop immediately before the unapproved deployment, with exact artifact, environment, changes, evidence, rollback, and approval request |

For database migration, preparing code, rehearsing against disposable data,
and changing a real database must remain separate operations.

---

## 6. Complete migration execution plan

The program plan for implementation after review. It deliberately does not
claim that every legacy capability has already been mapped or that the
current target code is release-ready.

### Migration invariant

The implementation can be delivered in internal work packages. The released
system must be a coherent v2 bundle from its first supported release. No
work package establishes permission to modify v1 or ship a mixed-regime
runtime.

"Clean room" here means separate successor repositories and an
independently functioning v2 system. It does not imply that legal
clean-room provenance has been established; retained code and packages
still need license and attribution review.

### Ownership map

| Owner | Responsibilities | Boundary |
| --- | --- | --- |
| `oramasys/perpetua-core` | Universal execution mechanics, MiniGraph scheduling/state mechanics, minimal reusable execution contracts | No application policy, provider operation, hardware selection, or reverse import from Oramasys |
| `oramasys/oramasys` | Graph/workflow semantics, control plane, orchestration, lifecycle, routing composition, accounting integration, product APIs/UI, remaining application behavior | Consumes specialist decisions instead of duplicating them |
| `oramasys/agate` | Hardware inventory/capability, model fit, affinity, placement constraints | Provider lifecycle remains with the provider adapter |
| `oramasys/telos` | Semantic endpoint-use authorization and its canonical typed contracts | Authorization is distinct from DNS, connection pinning, and provider execution |
| `oramasys/phylax` | Security admission, provenance-verifier integration, redaction, runtime checks, safety/monitorability policy | Does not absorb endpoint-purpose authorization or orchestration state |
| `oramasys/anamnesis` | Private runtime memory, retrieval, provenance-preserving migration, sanitized promotion | No write-back to PT; no implicit fallback when unavailable |
| `oramasys/Claude-Desktop-LLM` | Provider-native local-model operation and readiness | Does not own hardware placement or general orchestration |
| `oramasys/alexandria` | New specifications, decisions, standards, threat models, migration ledger, release evidence | Documentation only; legacy archives stay in v1 |

One ownership decision must be recorded explicitly: where the reusable
endpoint-normalization and transport-safety primitives live in v2. Current
Telos documentation deliberately excludes those responsibilities. Preserve
that semantic separation; do not silently turn Telos's authorization method
into a parser/dialer. The existing model-server dialer can remain in the
Oramasys adapter layer until an explicit extraction decision is justified.

**Note relevant to this session's own PT PR #382 work**: this dovetails
directly — the dialer, DNS-rebinding fix, and Host-header/RFC-7230 fix
landed this session are exactly the kind of "endpoint-normalization and
transport-safety primitive" this ownership decision concerns. If/when that
extraction decision is made, this session's PT-side implementation (real,
tested, currently the *only* working version of this logic anywhere) is the
concrete reference to port from — not a reason to duplicate the work from
scratch in `oramasys/oramasys`.

The direct-successor relationship does not mean copying every PT feature
into the kernel. Universal mechanics go to Core; application behavior and
offloaded services follow the ownership map.

### Work package M0 — Establish the immutable evidence baseline

Deliverables, proposed in Alexandria: `migration/regime-boundary.md`,
`migration/source-baseline.md`, `migration/ownership.md`,
`migration/decisions.md`.

Steps:

1. Record full source and target commit IDs.
2. Inventory source branches and open PRs for unmerged knowledge.
3. Classify each as accepted behavior, pending proposal, superseded work,
   or unresolved evidence.
4. Record source freeze and permitted successor write set.
5. Reconcile current instructions against historical migration exceptions.
6. Resolve Anamnesis availability/access and identify the provider-adapter
   baseline.
7. Record which authority decisions remain open.

Exit evidence: every source reference is pinned; no source operation is
required by the implementation plan; every unresolved decision has an owner
and a gate it blocks; legacy PR #382 and Orama PRs #349/#350 remain
untouched, relevant evidence accounted for.

### Work package M1 — Build the exhaustive capability and instruction ledger

Proposed files: `migration/capability-ledger.csv`,
`migration/instruction-ledger.csv`, `migration/contract-ledger.csv`,
`migration/document-lineage.csv`.

Each capability row: `source_repo`, `source_commit`,
`source_path_or_symbol`, `capability`, `observable_contract`,
`source_tests`, `current_target_evidence`, `target_owner`, `target_path`,
`disposition`, `dependencies`, `acceptance_cases`, `status`,
`decision_reference`.

Permitted dispositions: reimplement in successor; extract and adapt with
provenance; consume an existing specialist package; preserve a
compatibility surface within v2; retain solely as historical evidence;
exclude only through an explicit accepted decision.

Inventory must include: PT orchestration, coordination, discovery,
hardware/startup intelligence; endpoint-policy and network utility
packages; AlphaClaw adapters/MCP, local-agent and MCPB packages; memory
controllers, `.agent` tools, renderers, protocols, and hooks; Orama APIs,
workflow/methodology tools, agent definitions, MCP servers; frontend,
platform launch/install behavior, configuration, CI, and guards; optional
integrations and vendored/submodule functionality.

Exit evidence: every relevant source file/package has a disposition; every
supported user workflow maps to successor acceptance tests; every active
instruction has a scope, owner, loading mode, and migration decision; no
functionality disappears because it was absent from a short feature list.

### Work package M2 — Establish v2 governance and build foundations

Proposed locations: root `AGENTS.md` in each successor;
`alexandria/standards/agent-policy.md`, `standards/verification.md`;
runtime/package configuration under the relevant successor; executable
validation tools and tests under `/src`; platform-required files such as
`.github/workflows/*` at their required locations.

Steps: apply the approved small instruction policy; separate inspection,
setup, tests, publication, and deployment commands; establish package
build/release metadata and artifact provenance; define compatible version
constraints and reproducible dependency resolution; add meaningful package
CI; review repository protection requirements with the repository
administrator; preserve required attribution and license notices; record
any necessary layout exceptions rather than silently violating Doc 46.

Exit evidence: each package builds from its own declared inputs; no setup
assumes legacy siblings or workstation paths; permission enforcement is not
claimed without registration tests; CI and release gates are explicit;
inaccessible GitHub protection settings remain a tracked administrator
task.

### Work package M3 — Freeze cross-package contracts

Proposed Alexandria documents: `contracts/execution.md`,
`contracts/routing.md`, `contracts/endpoint-use.md`,
`contracts/security-admission.md`, `contracts/hardware-placement.md`,
`contracts/provider-lifecycle.md`, `contracts/memory.md`,
`contracts/events-and-accounting.md`.

Specify: ownership and import direction; request/result schemas; stable
identifiers and versioning; denial/error semantics; cancellation, retries,
deadlines, and idempotency; observation versus inference/evaluation
evidence; redaction and persistence boundaries; accounting
reservation/settlement boundaries; compatibility and expiry/revocation
behavior.

Exit evidence: each shared contract has one executable owner; consumers use
its released or pinned contract; golden vectors live in v2 and contain
sanitized, reproducible inputs; unknown or incompatible versions have
explicit failure behavior; no contract depends on reading a legacy checkout
at runtime.

### Work package M4 — Complete specialist packages

| Package | Implementation work | Required evidence |
| --- | --- | --- |
| Agate | Turn the current specification into the required runtime capability/placement surface; reconcile hardware helpers retained in Core | Forbidden placement, unavailable devices, stale capability evidence, model fit, supported fallback behavior |
| Telos | Complete authorization lifecycle, policy version handling, expiry/revocation where required, conformance vectors | Allow/deny/unknown purpose, version mismatch, spoof-resistant evidence boundaries, redacted decision correlation |
| Phylax | Implement effective admission adapters, provenance-verifier integration, redaction and monitorability controls | Unknown-operation rejection, malformed/missing evidence, verifier failure, denied action causes zero side effect |
| Anamnesis | Provision backend and implement memory contracts | Private defaults, namespace isolation, lossless import, repeat-safe migration, sanitation, promotion and push controls |
| Provider adapter | Reconcile and expose supported provider-native operations | Readiness, timeout, cancellation, unavailable provider, duplicate-start prevention, repeat-run idempotency |

Production readiness must not be inferred from mock-only integration or
in-memory decision stores.

### Work package M5 — Reconcile and minimize Perpetua Core

Existing paths requiring classification: `src/perpetua_core/graph/`,
`src/perpetua_core/state.py`, `src/perpetua_core/message.py`,
`src/perpetua_core/discovery/`, `src/perpetua_core/policy.py`,
`src/perpetua_core/llm.py`.

Steps: preserve and verify current execution semantics; map retained
hardware/provider helpers to their future owners; replace policy ownership
with injected contracts where required; remove package dependencies only
after proving remaining consumers do not require them; preserve public
compatibility deliberately, do not remove working behavior by directory
cleanup; keep scheduling ownership singular.

Exit evidence: state isolation and deterministic execution remain correct;
observer behavior, cancellation, retries, and plugin failures satisfy the
accepted contracts; Core has no reverse dependency on Oramasys or
specialist application policy; retired helper behavior has a verified
successor and a compatibility decision.

### Work package M6 — Complete Oramasys composition and remaining application behavior

Existing anchors: `src/orama/api/`, `src/orama/graph/`,
`src/orama/gateway/`, `src/tests/`.

Implement successor-owned versions of: control-plane identities and
authorization; coordination claims, source revision binding, liveness, and
heartbeat; route resolution using Agate and provider evidence; endpoint
authorization and transport-safe execution; artifact admission and runtime
security checks; durable workflow/routing state and recovery;
budget/accounting controls where paid dispatch is supported; product APIs,
UI, adapters, and optional integrations identified in M1.

Retarget PT dialer findings here or to the approved specialist owner. Do
not connect v1 PT to the new dialer.

Exit evidence: a full workflow works with real v2 adapters; every denial
stops effects before they occur; repeated requests do not duplicate
provider work, accounting, or telemetry; lifecycle progress includes
genuine heartbeat/liveness behavior where needed; missing required
specialists produce explicit errors, optional integrations degrade only as
documented.

### Work package M7 — Migrate memory and new documentation without changing v1

Memory procedure: read a pinned PT evidence snapshot; preserve original
identifiers, dates, provenance, epistemic class, status, and supersession
relationships; keep conflicting same-ID evidence for reconciliation, do not
silently keep the first; sanitize destination material through the
successor's rules; verify counts, identities, relationships, representative
retrieval, and private/public separation; repeat the migration and prove no
duplication or loss; activate automatic legacy import only after
successful Anamnesis provisioning, according to the accepted contract;
retain human approval for promotion pushes unless an operator explicitly
configures otherwise.

Documentation procedure: author new v2 documents from reconciled decisions;
cite pinned legacy evidence; mark acceptance status and implementation
evidence separately; keep historical implementation incidents in
references, not universal startup instructions; record document-by-document
authority transfer.

Exit evidence: PT memory and both legacy document trees are unchanged;
Anamnesis retrieval retains useful knowledge without importing obsolete
authority; Alexandria covers every accepted active v2 decision; legacy docs
remain accessible as historical sources.

### Work package M8 — Prove a coherent v2 release bundle

Proposed locations: `oramasys/src/integration_tests/`,
`oramasys/src/release/`, `alexandria/releases/`.

Test the complete bundle with both legacy repositories absent. Required
checks: clean installation from declared artifacts; public API and CLI
workflows; cross-package version compatibility; hardware selection and
provider readiness; endpoint authorization and safe transport;
compile/runtime admission; memory initialization, capture, retrieval, and
recovery; UI visual inspection where applicable; cancellation, timeouts,
retries, interruption, and duplicate requests; event redaction and
non-duplicated accounting/telemetry; supported platform behavior using real
platform runners where necessary.

Add a dependency-boundary check that rejects legacy imports, installation
URLs, runtime shell calls, and implicit sibling lookup. Permit historical
citations and sanitized fixture provenance.

Exit evidence: no installed v1 package, checkout, service, or memory writer
is required; every capability ledger row is proven or explicitly excluded
by an accepted decision; all package versions and artifact digests form one
tested release manifest; no critical security enforcement relies solely on
instructions.

### Work package M9 — Release approval, cutover, and recovery

Prepare a concrete release packet: exact repository commits and package
versions; artifact digests; compatibility matrix; tests and visual evidence
actually obtained; remaining limitations; deployment environment and
effects; data migration plan; recovery procedure; documentation
authority-transfer record.

Approval remains immediately before the external publication/deployment or
real-data migration it covers.

Recovery operates within the v2 regime. Before first release, failed
validation prevents activation. After release, recovery restores the
previous known-good v2 bundle and its compatible data state. Existing v1
installations remain independently usable and unchanged.

Exit evidence: the deployed v2 bundle matches the approved manifest;
post-deployment checks pass; Alexandria becomes the active v2 documentation
authority through a recorded handover; both source repositories remain
unchanged by the migration.

### Program completion condition

Migration is complete only when: the capability and instruction ledgers
have no unexplained omissions; the accepted v2 workflows operate together
without v1 dependencies; memory and documentation provenance are preserved;
security and permission boundaries are demonstrably enforced; the approved
release is validated in its intended environment; remaining exclusions are
explicit decisions, not unfinished work described as completion.

---

## 7. Smallest useful cleanup batch

The smallest practical first batch is documentation-only in successors:

1. Correct authority language in the Core, Alexandria, Telos, and Phylax
   READMEs/boundary documents.
2. Add Alexandria's regime-boundary and ownership records.
3. Add short successor `AGENTS.md` files.
4. Record the legacy PRs and historical plan exceptions as read-only
   evidence.
5. Inventory the skill wrappers without importing their synchronization
   hooks.

Do not combine that batch with permission-code changes, global plugin
changes, memory migration, or deployment. Those need their own concrete
diffs and verification.

---

## 8. Checks that would establish improvement

Run a controlled before/after comparison using the same five scenarios,
repository snapshots, model configuration, and tool access.

| Metric | Improvement sought |
| --- | --- |
| Instruction bytes/tokens actually loaded | Lower unnecessary loading; preserve required references |
| Skill activations | Fewer unrelated activations |
| User confirmation turns | No repeated request for already-granted authority |
| First useful action latency | Less startup ceremony |
| Files and repositories inspected | Scope matches the task |
| Tests executed | Relevant coverage without unrelated suite expansion |
| Unauthorized mutations attempted | Zero |
| Source-repository writes attempted | Zero |
| Required approvals preserved | All |
| Correctness and completion | No regression |
| Visual inspection for UI tasks | Present when required |
| Memory retention and provenance | No loss or silent supersession |

Add focused permission tests for unknown operations, shell argument
variants, missing hooks, denied effects, and approval reuse. Add wrapper
tests proving that loading a skill performs no synchronization or import.

No runtime context savings or productivity gains have been measured yet.
The confirmed evidence supports the cleanup proposals; the comparison tasks
establish whether they improve behavior without weakening existing
safeguards.

---

## 9. Harmonization notes (this synthesis's own additions)

Per the request to harmonize additively and bias toward the more elegant
combination — three connections worth naming explicitly, none of which
change the plan above, only tie it to work already real and verified this
session:

1. **C1's Phylax-enforcement finding and this session's own Phylax v1/v2
   design work are the same effort, different repos.** `docs/v2/60-67` and
   `docs/v2/references/phylax-monitorability-part-{1,2,3}` (already in this
   repository) specify the v1 evidence contract, the v2 epistemic-status
   taxonomy, and the migration ladder for exactly the admission-enforcement
   gap C1 names. When Phylax implementation work (M4) begins, start from
   those already-reviewed, already-CI-tested documents rather than
   redesigning the contract from this audit's C1 section alone.

2. **The coordination-round envelope design
   (`docs/superpowers/specs/2026-09-04-coordination-round-envelope-design.md`,
   also already in this repository) is a concrete instance of D-series
   discipline** — closed models (`extra="forbid", frozen=True`),
   admission-time-not-construction-time validity checks, and a
   resolver-computed (never self-reported) status — all landed and verified
   this session, independent of this audit. It's cited here as a working
   example of D1/D2's abstract "verify programmatically, check the actual
   result" principle already implemented once.

3. **This session's PT PR #382 work is the concrete precedent for what
   "meaningful regression test" (D1) and "fail closed" (C1) look like in
   practice**, not just in policy prose: real vulnerabilities reproduced
   directly before fixing (not assumed from a finding's description), real
   RED-then-GREEN verification, and an honest test-rigor gap caught and
   fixed in the tests themselves before trusting them. Cite as a reference
   example, not as migration-ready code — it lives in PT (v1) by design,
   per Doc 66's own regime boundary, and is not itself proposed for
   porting into any `oramasys/*` repo by this document.
