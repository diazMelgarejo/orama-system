# Plan — P0 bounded Core pin promotion and registry baseline

**Status:** draft for operator review. Planning only: this document authorizes no pin,
registry, schema or code change. Parent plan: [PLAN-R4-EXECUTION](PLAN-R4-EXECUTION.md)
(P0, prerequisite to M1). Evidence base:
[T0 record](T0-RESTORATION-AND-REGISTRY-BASELINE-2026-10-10.md).

AFRP: Type C | Level Expert | Mode 2. Scope: promote the Oramasys production Core pin
and the canonical registry baseline together, once, behind complete qualification.

## 1. Objective and non-goals

**Objective.** Move the Oramasys production dependency from pre-R3 Core
`04759a50c748444ff97136ea95c1e1289eac3a1a` to the merged R3 producer, and promote the
registry baseline (`planned` to `implemented` for the R3 fields) in the same reviewed step,
with a clean-install proof against the committed pin.

**Non-goals.** No R4 capability (T1 onward). No durable continuation claim: `ainvoke`
over a loaded state still starts at `START`. No HITL, foreign transport or provider effect.
No Core change. No change to the schema-1 `graph_id` of graphs not using R3 features.

## 2. Pin target decision (open, operator)

| Option | Value | Notes |
| --- | --- | --- |
| A (recommended) | Core merge commit `4d217f6b…` | The immutable merged revision; matches the T11 rule to promote only a reviewed merged producer revision |
| B | Candidate `34e4a8d2…` | Content-identical tree to A (`0890ef97…`) but not the merge commit; acceptable only if the install source requires it |

Decision rule: A unless the dependency manifest cannot reference the merge commit. If B
is chosen, record the tree-equality proof in the PR. Do not float on a branch or tag.

## 3. Preconditions (all must hold; re-read live, never from this document)

- [ ] Orama #392 and PT #432 merged by the operator; their merged SHAs recorded.
- [ ] Core `main` head, tree and the target commit re-read live; unchanged or re-reviewed.
- [ ] Oramasys `main` head and tree re-read live; no open PR touching the dependency,
  lock, registry fixtures or workflow pins without a coordination decision.
- [ ] Canonical and fixture registry digests re-computed and equal (baseline, policy-r3,
  core-r3); any drift stops P0 and returns to T0.
- [ ] Operator authorization to open the Oramasys PR is recorded in the thread.

## 4. Work packages

Branch name follows the dated convention. One Oramasys PR; one Orama evidence PR; one
PT append-only memory entry, in that order.

### P0-A Inventory (read-only)

Enumerate every place the old pin or candidate pin appears: dependency manifest, lock
and environment files, workflow pins, docs, registry fixtures and the candidate overlay
file. Output: a table of path, current value, intended value, owner. Anything not in
the table is not touched.

### P0-B Failing invariants first

Reproduce before changing anything:

1. Production install resolves to the pre-R3 commit and R3-dependent consumer cells are
   red or skipped. A skip is a failure, never an accepted result.
2. Registry baseline still marks the R3 fields `planned`.
3. Candidate overlays pass only because the overlay pin is test-only.

### P0-C Promotion (single reviewed step)

In one commit batch, changed together:

- production Core pin to the §2 target, in every file P0-A lists;
- registry baseline flip: R3 fields `planned` to `implemented`, add the new records,
  drop the provisional join edge kind;
- the byte-identical canonical snapshot and its pinned digest;
- docs and workflow pins named by P0-A.

Preserve the earlier baseline and both candidate profiles as history; do not delete them.
The candidate overlay file keeps its test-only role.

### P0-D Qualification matrix

Run against the committed pin in a clean environment, exact head:

| Cell | Requirement |
| --- | --- |
| Clean install | New environment, no cache reuse; resolves the target commit and prints its identity |
| Baseline profile | Complete native and oracle suites pass |
| policy-r3 and core-r3 | Both candidate lanes pass against the promoted baseline |
| Schema compatibility | Schema-1 graphs keep their `graph_id`; schema-2 only for graphs using R3 features |
| R3 behaviour | Settle-all branches, name-ordered folds, lowest-named `first_success`, atomic local-only merge |
| Combined branch | Promoted pin plus any surviving consumer branches merge and pass |
| Resume honesty | A loaded-state `ainvoke` test still asserts restart at `START` |
| Missing fixtures | A missing required fixture or oracle cell fails the run |

Environment failures are recorded separately from defects and rerun, not waved through.

### P0-E Evidence publication

After the Oramasys PR is green and reviewed: update the Orama T0-style record with the
final pin, registry digests, tree SHAs and run identities (categories and hashes only);
then one append-only PT memory entry citing the merged SHAs. Canonical Orama evidence
publishes before PT memory.

## 5. Gates and sign-off

| Gate | Pass condition |
| --- | --- |
| G1 Preconditions | §3 complete |
| G2 Reproduction | P0-B failures observed and recorded |
| G3 Qualification | P0-D all cells green at the exact head |
| G4 Review | Operator and automated review threads resolved by commits, no unresolved findings |
| G5 Merge | Operator merges; agents do not merge or work around a refused merge |

P0 is complete only when production pin, registry baseline, snapshot digests and docs
agree on one immutable Core revision and a clean install proves it.

## 6. Rollback

Revert the single Oramasys promotion commit (no history rewrite, no force-push). Because
pin, baseline and snapshot move together, one revert restores the pre-R3 production state
and the candidate profiles remain as history. A partial promotion is a defect.

## 7. Risks

| Risk | Control |
| --- | --- |
| Core or Oramasys `main` moves during review | Re-read heads before each push; refresh evidence |
| Pin updated in one file but not the lock or workflow | P0-A table is the checklist; the clean install is the proof |
| Baseline flipped without the pin | One commit batch; qualification runs the committed state |
| Candidate overlay mistaken for promotion | Overlay stays test-only; docs say so |
| Over-claiming R3 as durable continuation | Resume-honesty test and wording check in docs |

## 8. Reporting

Report separately: implemented, verified, published, reviewed, merged, enabled. Pending
is not passed. After P0 merges, T1 and T2 may start as independently reviewed slices;
T3 onward stays gated by the parent plan.

## 9. Open decisions for the operator

1. Pin target: A (merge commit) or B (candidate), per §2.
2. Where this plan lives: as `PLAN-P0-CORE-PIN-PROMOTION.md` beside the parent plan in
   the R4 reference directory, with a one-line pointer from `PLAN-R4-EXECUTION.md`.
3. Whether P0 evidence is a new record or an amendment to the T0 record. Recommendation:
   a new record; T0 stays an immutable snapshot of its date.
