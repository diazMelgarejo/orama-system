# Plan — P0 bounded Core pin promotion and registry baseline

> Review follow-up: the release sequence below is superseded for execution by
> [revision 2, section 3](P0-THROUGH-T2-EXECUTION-PLAN-REV2-2026-10-10.md#3-p0---two-phase-qualification-then-promotion).
> Qualify both immutable candidate heads before the canonical promotion. This earlier
> plan remains the historical design input, not permission to merge Orama before qualification.

**Status:** corrected implementation plan. The former pre-R3 baseline is retained as a
historical registry profile; this plan promotes the reviewed R3 production baseline only
through its stated qualification gates. Parent plan: [PLAN-R4-EXECUTION](PLAN-R4-EXECUTION.md)
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

## 2. Pin target decision

Production target: Core merge commit
`4d217f6b9e94e36554a9427198b8c2c4b7febc47` (tree
`0890ef970ab26fa7982ea15fc235c0fe9d1a603f`). It is the reviewed immutable merged
producer revision. The historical `core-r3` candidate remains pinned to
`34e4a8d22212d38d6ab100c1ad7fb2b19f56cb68`; it is never substituted for the
production dependency. Do not float on a branch or tag.

## 3. Preconditions (all must hold; re-read live, never from this document)

- [ ] Orama #392 and PT #432 merged by the operator; their merged SHAs recorded.
- [ ] Core `main` head, tree and the target commit re-read live; unchanged or re-reviewed.
- [ ] Oramasys `main` head and tree re-read live; no open PR touching the dependency,
  lock, registry fixtures or workflow pins without a coordination decision.
- [ ] Canonical and fixture registry digests re-computed and equal (production baseline,
  policy-r3, core-r3, and retained pre-R3 baseline); any drift stops P0 and returns to T0.
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

1. Production tests select the production baseline explicitly, never by `HAS_R3` or any
   candidate overlay heuristic.
2. A production install at the pre-R3 commit fails the production R3 conformance cell;
   a required R3 cell cannot skip.
3. Canonical checkout bytes or a pinned digest that differ from the selected profile fail.
4. Historical policy-r3 and core-r3 profiles retain their own immutable Core pins and cannot
   satisfy a production pin assertion.

### P0-C Canonical registry and consumer promotion

In one commit batch, changed together:

- First, update the Orama-owned canonical baseline: R3 fields become `implemented`, R3
  records and literals become canonical, and the pre-R3 baseline is retained as an exact
  historical profile. Candidate profiles remain immutable historical qualification inputs.
- Then pin the Oramasys consumer workflows to the exact merged canonical Orama commit.
- In one Oramasys commit batch, promote the production Core pin to §2, replace the consumer
  baseline fixture with the byte-identical canonical baseline, update its digest and explicit
  profile assertions, and update every active workflow and test revision from P0-A.
- Candidate overlays keep their test-only role. They must not be used for production install
  proof or to choose the default registry profile.

Preserve the earlier baseline and both candidate profiles as history; do not delete them.
The candidate overlay file keeps its test-only role.

### P0-D Qualification matrix

Run against the committed pin in a clean environment, exact head:

| Cell | Requirement |
| --- | --- |
| Clean production install | New environment, no cache reuse; resolves §2 from the committed manifest and prints its identity |
| Production baseline | Explicit `production` profile; complete native and oracle suites pass with required R3 cells |
| policy-r3 | Historical schema-1 Core `04759a50…`; profile-specific cells pass without pretending to be production |
| core-r3 | Historical candidate Core `34e4a8d2…`; profile-specific cells pass without changing its recorded provenance |
| Schema compatibility | Schema-1 graphs keep their `graph_id`; schema-2 only for graphs using R3 features |
| R3 behaviour | Settle-all branches, name-ordered folds, lowest-named `first_success`, atomic local-only merge |
| Combined branch | Promoted pin plus any surviving consumer branches merge and pass |
| Resume honesty | A loaded-state `ainvoke` test still asserts restart at `START` |
| Missing fixtures | A missing required fixture or oracle cell fails the run |

Environment failures are recorded separately from defects and rerun, not waved through.

### P0-E Evidence publication

Before the Oramasys PR is opened, merge the reviewed canonical Orama registry change and
pin that exact revision in Oramasys CI. After the Oramasys PR is green, reviewed and merged,
publish a new dated Orama P0 evidence record with final pin, registry digests, tree SHAs and
run identities (categories and hashes only); then one append-only PT memory entry citing
observed merged SHAs. T0 remains its immutable date-stamped restoration record.

## 5. Gates and sign-off

| Gate | Pass condition |
| --- | --- |
| G1 Preconditions | §3 complete |
| G2 Reproduction | P0-B failures observed and recorded |
| G3 Qualification | P0-D all cells green at the exact head |
| G4 Review | Operator and automated review threads resolved by commits, no unresolved findings |
| G5 Merge | Operator merges; agents do not merge or work around a refused merge |

P0 is complete only when the merged canonical registry, consumer fixture, profile selection,
production pin, snapshot digests and workflow pin agree on one immutable Core revision and a
clean production install proves it.

## 6. Rollback

Revert the Oramasys promotion commit (no history rewrite, no force-push) to restore the
pre-R3 consumer pin and fixture. Revert the separate Orama canonical registry commit only
if its own evidence is withdrawn. Candidate and pre-R3 profiles remain history. A partial
consumer promotion is a defect.

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
