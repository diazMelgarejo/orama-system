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
