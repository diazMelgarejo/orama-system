# E1 C2 (Part 3): ratification acceptance packet

**Status:** RATIFIED BY OPERATOR DECISION on 2026-10-22 for Section 3.3 only (see Section 5);
items 3 and 5 below remain unmet and are recorded as such. Before that decision this packet read
INCOMPLETE. This packet records what an operator needs before deciding on the Part 3
ratification surface, and the current status of each item. It is not itself a ratification.
**Amendment:** [Part 3 amendment][amend], whose
[Ratification surface](E1-C2-INTEGRATED-SCHEMA-PART3-AMENDMENT-2026-10-19.md#ratification-surface)
marks Section 3.3 as the only section proposed for ratification.

## 1. What a ratification of this surface means

A ratification of [Section 3.3][s33] is a contract and specification decision only: it fixes
the bootstrap-anchor protocol, the atomic persisted identity/version/digest/floor record, and
the $R_p \ge$ anchor_version floor rule, with the consumer-local refusal and quarantine
semantics defined there. It authorizes no implementation, no serving, no production emission,
no pin promotion and no activation. `ORAMA_GRANT_SERVING` stays unset. The revocation body,
cascade body, pruning/retention/archival, checkpoints beyond the anchor and witness fields
remain proposed release prerequisites and are not decided. A merge, a clean review thread or an
agent endorsement is not a ratification.

## 2. The six items and their current status

| # | Packet item | Current status | What is needed |
| :--- | :--- | :--- | :--- |
| 1 | Exact 40-hex commit | **Not supplied.** Placeholder: `COMMIT = <40-hex SHA, operator fills>`. Any abbreviated prefix, including those in review notes, is not acceptable. | The operator names the full commit of the reviewed amendment. |
| 2 | Canonical digest | **Not supplied.** Placeholder: `SHA256 = <64-hex, operator fills>`. | Method below, computed at the commit named in item 1. |
| 3 | Test evidence: cold bootstrap, checkpoint acknowledgement, repeated pruning, identical retry, lower-floor rejection | **Does not exist.** Conformance tests for these are not written. This is an explicit release prerequisite, and nothing in this packet claims otherwise. See the crosswalk in the amendment's Section 6. | Executed output for cold `bootstrap_anchor`; bootstrap at anchor $N > 1$ initializes `acked_through = N`, permits at and above $N$ use that checkpoint-aware coverage, and a gap at $N + 1$ does not advance it; a later prune from $N$ to $M > N$ leaves only $M$ hot and archives $N$; identical retry is a no-op; a conflicting retry refuses and quarantines; clearing needs the audited operator procedure; a permit with $R_p$ below the floor is refused as `anchor_floor.permit_below_floor` with no authority write and the reservation unconsumed; crash-safety of the atomic record. |
| 4 | Named contract references | **Present in the amendment.** Part 1, Part 2 Step 4.3 and Capacity and retention, E1 Sections 13 and 14, and the status addendum are linked by name and anchor. | Operator confirms the list. |
| 5 | Reviewer verdicts | **Not complete.** AntiGravity returned NOT READY on the prior head, with a hardening list (scope carve-out, lower-floor refusal, quarantine semantics, link normalization, missing artifacts). This revision addresses the first four; the fifth is items 1 to 3 here. No re-review verdict, and no Codex or Cline verdict, is recorded in this packet. | Reviewer verdicts at the exact commit of item 1, recorded here with the reviewer and head named. |
| 6 | Recorded operator decision | **Recorded in Section 5.** Packet completion remains incomplete because items 3 and 5 are unmet. | The recorded decision covers the Section 3.3 contract/specification only. Item 3 remains a release prerequisite before implementation is merged; item 5 remains a review-record and packet-completion requirement. |

## 3. Canonical digest method

The digest is the SHA-256 of the exact bytes of the amendment file as stored in git at the
commit of item 1, with no newline, whitespace or encoding normalization:

```text
git show <COMMIT>:docs/v2/references/r4-safety-compatibility-platform-2026-10-10/E1-C2-INTEGRATED-SCHEMA-PART3-AMENDMENT-2026-10-19.md | shasum -a 256
```

The operator fills the digest only from that command's output at that commit.

## 4. Operator record (fill when complete)

```text
COMMIT   = <40-hex SHA>
SHA256   = <64-hex digest>
TESTS    = <link to executed conformance output>
REVIEWS  = <reviewer, head, verdict>
DECISION = <ratify | defer>, <date>, <operator>
```

[amend]: E1-C2-INTEGRATED-SCHEMA-PART3-AMENDMENT-2026-10-19.md
[s33]: E1-C2-INTEGRATED-SCHEMA-PART3-AMENDMENT-2026-10-19.md#33-consumer-anchor-floor-invariant-additional-consumer-local-gate

## 5. Operator decision (recorded 2026-10-22)

Recorded by claude-fable-5 (identity not independently verified) from the operator's instruction in the
session: "ratify Part 3: name commit 6459b30e and limit it to §3.3". The operator is the ratifying
authority; this section records the decision and does not make it.

```text
COMMIT   = 6459b30e77a6ab22297307374e64dd8872c9b796
SHA256   = 984065ab236f7bd9178049de312d54c501b2a393eccb229b6d8f42360b3143f4
TESTS    = none exist (item 3 unmet); ratification is a contract/specification decision only
REVIEWS  = agent advisory only, at an earlier head: AntiGravity NOT READY (hardening since applied);
           three Sonnet steelman reviewers RATIFY_AFTER_EDITS; Codex hardening commit 6459b30e itself.
           No reviewer verdict recorded at the exact commit (item 5 unmet).
DECISION = ratify, 2026-10-22, operator
SCOPE    = Section 3.3 only (bootstrap-anchor protocol, atomic persisted identity/version/digest/floor
           record, R_p >= anchor_version floor rule, with its consumer-local refusal and quarantine semantics)
```

The digest was computed with the Section 3 command at the commit above. The decision authorizes no
implementation, no serving, no production emission, no pin promotion and no activation;
`ORAMA_GRANT_SERVING` stays unset. Conformance tests (item 3) remain an explicit release prerequisite
before any implementation is merged. Everything outside Section 3.3 stays proposed.

## 6. Follow-up evidence for items 3 and 5 (2026-10-22)

Recorded by claude-fable-5 (identity not independently verified). This section adds evidence; it does
not rewrite the table above and changes no decision.

**Item 3, test evidence.** An executable conformance suite now exists in
`tests/e1_part3_conformance/` (31 tests, all passing: `python3 -m pytest tests/e1_part3_conformance`).
It runs against a test-only reference model of Section 3.3, **not** against the Oramasys consumer
store, which does not implement `bootstrap_anchor`. It covers cold bootstrap, bootstrap at
$N > 1$ with `acked_through = N`, a gap at $N + 1$ not advancing it, digest, key and signature
refusals that persist nothing, identical retry as a no-op, conflicting retry with quarantine and the
persisted values kept, quarantine blocking only that issuer, no automatic clearing, audited clearing
with an append-only log, lower-floor refusal `anchor_floor.permit_below_floor` with no authority write
and the reservation unconsumed, crash safety of the atomic record, and repeated pruning from $N$ to
$M$. Not covered: gate order when several rules fail together, and concurrent floor commits. The
suite must be pointed at the real consumer store before any implementation merges.

**Item 5, reviewer verdict at the exact commit.** AntiGravity (`agy`, text-only, shown Section 3.3
and the tests, not the repository) at commit `6459b30e77a6ab22297307374e64dd8872c9b796`:
APPROVE_WITH_CHANGES. Its gaps (key-identity divergence, read-only inspection under quarantine,
append-only log, pre-anchor acknowledgements, exact refusal string) were addressed in the suite; gate
order and concurrency remain open. No Codex or Cline verdict is recorded.

**Update, same day: real-store conformance.** The same rules now also run against the real consumer
store in draft Oramasys PR 72 (`src/tests/test_dispatch_anchor.py`, 24 tests, all passing; the full
Oramasys suite passes). Item 3 is therefore met against real code once that PR is merged by the
operator. Still not covered: gate order when several rules fail together, concurrent floor commits,
and a production trusted-key adapter. The implementation is consumer-local and adds no transport,
serving path or pin promotion.
