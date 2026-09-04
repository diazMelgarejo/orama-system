# Phylax Monitorability Canonical Synthesis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish one canonical Phylax monitorability architecture in Orama v2 while preserving the detailed three-part implementation references and the shipped Perpetua-Tools v1 bridge.

**Architecture:** Doc 60 is the normative umbrella for ownership, vocabulary, evidence classes, authority, and lifecycle. The existing three reference documents remain focused implementation modules beneath it; the v2 index and observability ADR link readers into the new hierarchy.

**Tech Stack:** Markdown, Git, repository hygiene checks, Markdownlint-compatible CommonMark

**Spec:** `docs/v2/references/phylax-monitorability-part-1-v1-evidence-contract.md`, `docs/v2/references/phylax-monitorability-part-2-derived-inference.md`, and `docs/v2/references/phylax-monitorability-part-3-migration-assurance.md`

## Global Constraints

- Perpetua-Tools owns producer schemas, typed event/packet emitters, redaction, local evidence, and adapter projections.
- Phylax owns generic security/safety runtime checks, policy packs, monitor semantics, escalation, retention, and v2 admission.
- Orama owns application routing, workflow composition, approvals, and integration; Telos owns endpoint-specific evidence and enforcement.
- Core remains policy-free and never imports Phylax or application modules upward.
- Raw chain-of-thought, prompts, outputs, credentials, host identity, absolute paths, and raw evidence never enter normal handoff, audit, or remote export.
- Observations never merge with derived, reconstructed, interpolated, or forecast artifacts.
- Non-observed artifacts may advise or escalate only; they never authorize or block an action.
- A future block requires both an independent observable policy violation and explicit Phylax admission.
- Logs, audit events, queue admission, monitor results, and stale cleanup never refresh liveness; only explicit successful worker presence actions do.
- No hard-coded MiniGraph line count or unverified reuse claim may appear as a normative architectural dependency.

---

### Task 1: Create the normative Doc 60 umbrella

**Files:**

- Create: `docs/v2/60-phylax-monitorability-design-spec.md`

**Interfaces:**

- Consumes: the three reference modules and the accepted observability ADR vocabulary.
- Produces: the canonical ownership matrix, epistemic taxonomy, authority matrix, data flow, invariants, and migration gates used by all later tasks.

- [ ] **Step 1: Write the document skeleton**

Create sections for status, scope, definitions, ownership, architecture, canonical envelope, epistemic artifacts, decision authority, privacy, liveness, evaluation, rollout, failure behavior, and source hierarchy.

- [ ] **Step 2: Encode the normative authority matrix**

State explicitly that observed evidence may support a policy decision; derived, reconstructed, interpolated, and forecast evidence can only advise or escalate; blocking requires independent observable evidence plus explicit Phylax admission.

- [ ] **Step 3: Encode the end-to-end flow**

Document PT emission, Orama routing, Phylax fast/forensic evaluation, policy decision, audit projection, and separately governed sealed-evidence access. Keep Telos endpoint-only and Core excluded.

- [ ] **Step 4: Correct unstable reuse claims**

Reference the MiniGraph kernel through `01-kernel-spec.md` without a line count. Mark P1/P2/P6 primitive reuse as audit-gated until verified in executable source; retain confirmed P4 reuse.

- [ ] **Step 5: Validate the new document**

Run: `python scripts/review/repo_hygiene.py && git diff --check`

Expected: both commands exit zero.

- [ ] **Step 6: Commit Doc 60**

```bash
git add docs/v2/60-phylax-monitorability-design-spec.md
bash scripts/git/verify-staged-for-commit.sh
bash scripts/git/commit-clean.sh -m "docs(v2): add canonical Phylax monitorability spec"
```

### Task 2: Strengthen the three implementation modules

**Files:**

- Modify: `docs/v2/references/phylax-monitorability-part-1-v1-evidence-contract.md`
- Modify: `docs/v2/references/phylax-monitorability-part-2-derived-inference.md`
- Modify: `docs/v2/references/phylax-monitorability-part-3-migration-assurance.md`

**Interfaces:**

- Consumes: Doc 60 normative terms and invariants.
- Produces: executable detail without competing with Doc 60 for architectural authority.

- [ ] **Step 1: Add hierarchy declarations and cross-links**

Identify Doc 60 as normative and each part as subordinate implementation guidance. Link all parts bidirectionally without duplicating normative definitions.

- [ ] **Step 2: Reconcile Part 1 with shipped v1 behavior**

Record bounded identifier grammar, strict optional compatibility, caller-reported decisions, `block` rejection, opaque references, audit allowlisting, and explicit liveness isolation from Perpetua-Tools PR #379.

- [ ] **Step 3: Reconcile Part 2 with the epistemic contract**

Require source observation references, method and model versions, confidence/calibration metadata, expiry, supersession, and non-authoritative disposition for every non-observed artifact.

- [ ] **Step 4: Reconcile Part 3 with governance gates**

Add M0 decisions for the Phylax package/repository boundary and reuse inventory audit. Preserve the three-arm evaluation, red-team suite, rollback, retention, and observable-evidence blocking gate.

- [ ] **Step 5: Validate and commit the modules**

```bash
python scripts/review/repo_hygiene.py
git diff --check
git add docs/v2/references/phylax-monitorability-part-*.md
bash scripts/git/verify-staged-for-commit.sh
bash scripts/git/commit-clean.sh -m "docs(v2): align monitorability implementation modules"
```

### Task 3: Integrate navigation and observability continuity

**Files:**

- Modify: `docs/v2/README.md`
- Modify: `docs/v2/55-oramasys-agent-observability-contract-adr.md`

**Interfaces:**

- Consumes: Doc 60 and its three implementation modules.
- Produces: discoverable canonical navigation from the v2 index and the accepted observability contract.

- [ ] **Step 1: Register Doc 60 in the v2 index**

Add the numbered entry and advance the next-free-slot marker from `60-` to `61-`. Add a locked decision stating observability records operation while monitorability evaluates evidence sufficiency and decision authority.

- [ ] **Step 2: Cross-link the observability ADR**

Add a forward reference explaining that Doc 55 governs telemetry and privacy transport while Doc 60 governs monitor evidence, inference classes, and safety authority.

- [ ] **Step 3: Validate and commit navigation**

```bash
python scripts/review/repo_hygiene.py
git diff --check
git add docs/v2/README.md docs/v2/55-oramasys-agent-observability-contract-adr.md
bash scripts/git/verify-staged-for-commit.sh
bash scripts/git/commit-clean.sh -m "docs(v2): index Phylax monitorability architecture"
```

### Task 4: Verify, publish, and update the review surface

**Files:**

- Verify: all files changed in Tasks 1–3
- Update: Orama PR #340 description
- Create: downloadable canonical synthesis Markdown artifact

**Interfaces:**

- Consumes: the complete documentation tree.
- Produces: a reviewable PR and a portable handoff artifact with identical architectural conclusions.

- [ ] **Step 1: Run final repository checks**

Run: `python scripts/review/repo_hygiene.py && git diff --check`

Expected: both commands exit zero and no unrelated file is staged.

- [ ] **Step 2: Run consistency scans**

Run: `rg -n "99-line|raw CoT.*block|derived.*block|Next free slot:.*60" docs/v2/60-phylax-monitorability-design-spec.md docs/v2/references docs/v2/README.md`

Expected: no stale line-count claim, no derived-evidence blocking authority, and no stale `60-` next-slot marker.

- [ ] **Step 3: Publish the branch**

Push `2026-09-04-monitorability-v2-references` through the authenticated GitHub path and confirm the remote files match the verified local files.

- [ ] **Step 4: Update PR #340**

Describe Doc 60 as normative, the three references as implementation modules, PR #379 as the v1 bridge, and the Phase M0 Phylax repository/reuse-audit decision as an explicit pre-code gate.

- [ ] **Step 5: Publish the downloadable synthesis**

Create `Phylax-Monitorability-Canonical-Synthesis-2026-09-04.md` containing the final hierarchy, architectural decisions, implementation status, verification evidence, and remaining gated work.
