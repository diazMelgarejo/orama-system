# 71 — Operator-provisioned recovery grants and C4 autonomous tier

> **Repository standard:** additive — see
> [`46-repository-standard.md`](46-repository-standard.md).
> **Status:** APPROVED POLICY; NOT DEPLOYED.
> **Date:** 2026-10-13
> **Decision scope:** Phylax grant authority and Oramasys recovery consumer.
> **Document owner:** `orama-system` (canonical ADR home). **Implementers:** `oramasys/phylax`
> (grant authority) and `oramasys/oramasys` (recovery consumer).
> **Parents:** [`03-safety-v2.5.md`](03-safety-v2.5.md),
> [`32-agentic-security-controls.md`](32-agentic-security-controls.md),
> [`45-single-operator-lan-threat-model-descope.md`](45-single-operator-lan-threat-model-descope.md),
> [`60-phylax-monitorability-design-spec.md`](60-phylax-monitorability-design-spec.md)
> **Does not supersede:** any numbered doc; it adds a grant-issuance and autonomous-quota policy
> beside the parents above.
> **Provenance:** drafted as `56-` in `oramasys/oramasys` PR #34, where that slot was free.
> Renumbered to `71-` here because this repository's `56-` is already
> [`56-anamnesis-runtime-memory-migration.md`](56-anamnesis-runtime-memory-migration.md). A
> reference to "ADR 56" in Task 6 coordination records means this document.

---

## Context

The adjustment-grant contract separates durable grant issuance and verification
from ledger consumption. The baseline is deliberately deny-all until a Phylax
verifier is composed into Oramasys. Recovery must remain auditable and
fail-closed when ownership, revocation freshness, quota state, or downstream
admission cannot be proven.

This ADR records the C4 policy selection. It does not provision keys, activate
autonomous recovery, or alter an existing deployed service.

## Decision

### Ownership

- **Phylax** owns seed provisioning, signing, public-key registry, issued-grant
  index, revocation, immutable key tier, issuance intent, and quota admission.
- **Oramasys** owns authenticated hold creation, durable recovery intent,
  injected verification, and transactional consumption against the StepLedger.
- The web-serving process uses a verify-only Phylax interface. It must not load
  a seed, P5 secret, or issuer-write capability.

### C4 caps

| Policy level | Grant constraints | Rate limit | Activation |
| --- | --- | --- | --- |
| Level 0 | `settle` only, `steps` basis, units `1..3`, fixed 900-second lifetime | 6 autonomous grants per rolling 3600 seconds per authenticated principal | Explicit Level 0 policy registration |
| Level 1 | Same immutable per-grant constraints | 12 autonomous grants per rolling 3600 seconds per authenticated principal | Reviewed isolated-issuer deployment plus explicit operator activation |

Quota counts accepted autonomous issuances across all runs, key rotations, and
policy revisions in the authoritative issuer domain. Expiry, revocation, and
consumption do not refund quota. Exact durable issuance retries return the
stored grant without consuming another slot. Human-gated grants do not consume
the autonomous quota solely because both may settle a hold.

### Recovery and identity

- A passive UNKNOWN hold never causes issuance. Recovery starts only through an
  explicit operator command.
- Recovery identity is a versioned canonical object that binds authenticated
  principal, store/run/hold identifiers, fencing epochs, requested units and
  basis, action, and evidence digest. It is persisted before issuance.
- New holds persist an authenticated creating principal. Legacy NULL-owner
  holds refuse autonomous recovery. Their existing authenticated human-tier,
  P5-gated settlement compatibility path remains available without inventing
  historical ownership.
- A later owner repair is a separate human-authorized, audited operation; it is
  never an automatic bulk backfill.

### Revocation and serving

Verification reads public registry data, the issued-grant index, and revocation
state through a read-only SQLite connection. A revocation observation older
than `REVOCATION_MAX_AGE_SECONDS = 60` refuses verification. The serving path
does not create, migrate, or write issuer state.

## Level 1 activation gate

Different file-owner UIDs, file modes, ACL output, key labels, or caller flags
do not activate Level 1. Before the higher quota is enabled, the operator must
approve evidence that demonstrates all of the following:

1. An isolated signer account and authenticated, run-scoped issuer invocation.
2. The serving and agent identities cannot read seeds or issuer-write state.
3. The verifier has an independently reviewed local transport or signed public
   state publication with a revocation-freshness proof.
4. The server is proven seed-free by startup, file-access audit, and read-only
   database-write refusal tests.
5. A versioned deployment-policy activation record binds the evidence to the
   selected quota level.

Until those conditions are met, Level 0 is the only permitted autonomous
policy. No automatic inference or configuration value may raise the cap.

## Consequences

- The shared control-plane bearer identifies one local-operator capability, not
  distinct agents. All callers using it share the Level 0 quota bucket.
- Same-user Level 0 remains an explicitly documented trust limitation: a
  process under the same OS identity can potentially access both seed files.
- The policy is intentionally separate from implementation rollout. PR merges
  do not demonstrate provisioning readiness, secret isolation, or autonomous
  activation.

## Non-goals

- No resident privileged recovery daemon.
- No automatic recovery, automatic legacy-owner assignment, or UID-only cap
  upgrade.
- No cryptographic implementation, key material, local paths, or credentials in
  this record.

## Required implementation evidence

The implementation must provide focused red/green tests and a real file-backed
issuance-to-authenticated-consumption flow covering exact retry, revocation,
seed-free serving, and read-only verification. The merge order remains Phylax
grant authority before Oramasys adjustment composition, because the latter
imports the former's public interfaces.

## References

- [Phylax adjustment-grant design](https://github.com/oramasys/phylax)
- [Oramasys adjustment-grant consumer](https://github.com/oramasys/oramasys)

The [Task 6 operator-provisioning and autonomous-tier plan](72-task6-operator-provisioning-and-autonomous-tier-plan.md)
is the implementation roadmap for this decision. Both documents live in this repository;
`oramasys/oramasys` ([PR #34](https://github.com/oramasys/oramasys/pull/34)) holds only a
temporary draft that becomes a link-only pointer. This ADR controls policy;
implementation details in the plan must not weaken its quotas, isolation gate,
or recovery rules.

---

## Status note, 2026-10-14: interim serving gap

This note is additive. It records facts observed on 2026-10-14 and changes nothing above it.
Each statement is labelled **V** (verified against a named source at the time of writing) or
**P** (proposed, not verified, not in effect).

- **V:** this ADR requires the serving process not to load the issuer seed or the approval-signing
  secret, and to read the authority SQLite store through a read-only connection (see "Ownership"
  and "Revocation and serving" above).
- **V:** as of Phylax `main` at `e41f1e8`, the serving composition script loads both secret
  references and calls the full-authority opener. Issuer state is written when that opener runs.
  The verifier handed to Oramasys therefore wraps the full authority. The serving path does not
  yet meet the verify-only requirement. This matches the plan's own statement that the current
  composition is "not the final verify-only deployment"
  ([plan 72](72-task6-operator-provisioning-and-autonomous-tier-plan.md), section 1).
- **V:** a verify-only repair exists as an uncommitted local workspace in Phylax. It is not
  committed, not published and not reviewed. It introduces a public-key-only verifier, a read-only
  store, and an `open_grant_verifier` composition entry point. 225 Phylax tests passed locally
  in that workspace.
- **V:** grant serving is OFF by default, so the gap does not expose an active serving path in the
  default configuration.
- **P:** the local repair is the intended shape of plan 72 Tasks 1 and 5. Its disposition
  (publish, revise, or discard) is owned by operator decision DEC-Q-05.

This note does not:

- change the status of this ADR (it remains APPROVED POLICY; NOT DEPLOYED);
- claim that the repair is ratified, reviewed, countersigned or merged;
- claim that serving is verify-only, seed-free or read-only today;
- alter any quota, isolation gate, or recovery rule in this ADR or in plan 72.
