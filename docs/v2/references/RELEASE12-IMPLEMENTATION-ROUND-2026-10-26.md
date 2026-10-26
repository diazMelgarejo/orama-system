# Releases 1 and 2: coordinated implementation round

Status: implementation in progress, not deployed or qualified.

The operator requested one NEW PR per affected repository, leaving every existing
PR unchanged. This round combines verification-only serving and the first inert
effect driver in a single consumer change. The complete roadmap is preserved in
[the reference plan](ACTIVATION-SERVING-T3-T5-REMOTE-AUTONOMY-PLAN-2026-10-25.md).

## Reconciliation

Baseline: Orama `079440292c25abda06d51c77a0c00a6546e4a763`, Oramasys
`a0a3e6728c914521e132fb677c8aaaf2df00cade`.

Current consumer code already contains Phylax verify-only composition, scoped
effect proposals and reservations, atomic dispatch authorization, one-send markers,
and unknown-first effect outcomes. Reuse those authorities; do not introduce a
second scheduler, approval authority, ledger or issuer.

Ruling: the roadmap's suggested prepared/authorized/acknowledged vocabulary is
conceptual only. Preserve the ratified E1 outcome vocabulary (confirmed, failed,
unknown) and the existing atomic intent/use/outbox transaction.

## This round

- Add separate liveness and readiness routes; readiness must not claim deployment
  qualification, issuer readiness, effect readiness or autonomous permission.
- Add an inert effect driver using the existing authorized outbox and one-send
  marker. Its receipt explicitly names an inert simulation, never a real effect.
- Retain unknown state across crashes between the send marker and settlement.
  Never retry automatically.
- No automatic serving activation, issuance, provider request, shell execution,
  or continuation. No new network endpoint for effect dispatch until the verified
  v2 grant-to-attempt production adapter is reviewed and qualified end to end.

## Remaining release gates

The inert driver is a library seam, not a complete T3 deployment. Production
composition still needs verified effect-grant binding, final-boundary revocation
checks, authenticated approval acquisition, real process/identity isolation tests,
crash scenarios, and installed-set producer/consumer qualification. A draft PR
must not describe these as complete. Each gate is required before activation.

## Local verification

Consumer validation: fresh isolated Python 3.12 environment with declared dev
dependencies and immutable Core/Telos/Agate pins installed. Full suite:
**1993 passed, 3 skipped**. Focused serving/effect regression set: **87 passed**.
This is developer verification, not the sealed non-editable release matrix.

Independent review found and blocked an unscoped inert sender. The reproduced
failure was repaired by checking the persisted inert destination and consumed
reservation inside the same transaction as the send marker. Real destinations
remain unchanged on refusal. Tests also reopen the database and prove that a
send marker without settlement remains unknown and cannot be retried. The
restart test is not a substitute for the remaining subprocess crash matrix.

## Successor batch: subprocess evidence and memory preservation

The operator requested continuation through the existing draft PRs. This batch
reuses Orama #454 and Oramasys #77; it creates no additional implementation PR.
PT #465 received the supplied qualification-gates patch and was converted to a
draft. Its memory commit is
`851c2f7971d9667ab57a415e12004e6b75ca0b92`. The patch was applied intact, with
one new candidate, one semantic lesson, its rendered view, and one episodic
append. The remote-content preservation gate confirms that all 1,195 historical
episodes remain the exact byte prefix; 18 focused memory tests pass.

Oramasys #77 at `bb234b4b7e72e8038fbffdf91daf68e961171a81` now includes seven
subprocess crash cases and a two-process send race. The detailed matrix,
reproducer and limits are in the
[candidate evidence receipt](https://github.com/oramasys/oramasys/blob/bb234b4b7e72e8038fbffdf91daf68e961171a81/docs/release12-process-crash-evidence.md).
Crash injection uses `os._exit` without cleanup. For transaction interruptions,
a trace callback observes the target write, then exits before COMMIT executes.
After reopening, the tests prove atomic authorization rollback, uncommitted
marker rollback, durable UNKNOWN after a committed marker, durable inert
settlement, and refusal of duplicate sends. The process race yields exactly one
sender and one refusal.

Fresh Python 3.11 and 3.12 environments installed the candidate non-editably and
passed the existing isolated production-install verifier from outside the
checkout. The declared immutable Core/Telos/Agate pins were retained. Each
interpreter passed the full source suite: **2,001 passed, 3 skipped**. The Telos
network-authority check and production compile check passed. Pytest's configured
source path means these are source-suite and clean-install checks, not a sealed
installed-set release qualification. The eight subprocess cases qualify only
the inert simulation seam with synthetic verifier/gate ports.

## Remaining gates after this batch

Releases 1–2 remain **not fully qualified**. No capability was activated.

| Gate | Current evidence | Required next result |
| --- | --- | --- |
| Trusted effect-grant composition | Consumer value object and recovery verifier are present | Reviewed producer effect-verifier API and bound consumer adapter |
| Final-boundary authorization | Existing Step 4.3 tested with synthetic ports | Authenticated scoped approval and verified grant/event composition at dispatch |
| Inert crash/replay behavior | Seven process-death cases and one sender race pass | Independent review at the final candidate SHA |
| Serving isolation | Developer subprocesses only | Seed-read and issuer-write denial under the actual serving identity |
| Installed release evidence | Non-editable install smoke and source tests on 3.11/3.12 | Complete registry/manifest/config digests, sealed matrix and post-merge repin rerun |
| Activation | Absent | Separate operator decision naming capability, scope and disablement |

The grant-serving extra still pins Phylax
`0c3e860749b3ff8f62e102679f1f415f8acf0a61`, the recovery verifier. Phylax's
`DispatchIssuerSigner` at inspected head
`31afe7f485bec9d305531d9edc3460ab066dc8c5` provides issuer signing, not trusted
consumer effect-grant verification. A request payload or a newly constructed
`VerifiedDispatchGrant` must not stand in for that missing producer boundary.
Until it exists and is qualified, exposing an effect route would cross an
unverified authority boundary.

The attached roadmap's T4 transport, T5 continuation and C4 autonomy releases
remain downstream gates. They require their own frozen contracts, pinned
qualification and operator decisions. Real isolation cannot be inferred from
same-user subprocess success; a green draft cannot activate serving. Preserve
the original roadmap and historical receipts as evidence rather than rewriting
their earlier observations as current qualification.
