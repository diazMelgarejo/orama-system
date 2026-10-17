# E1 — authority, state and effect freeze (DRAFT for ratification)

**Status:** DRAFT. Specification only. Not ratified, not implemented, not an approval to start T3
code. Every "proposed" name, field and value below is frozen only by explicit operator
ratification recorded on the review PR. Nothing here enables grant serving, promotes a pin,
registers a required check, or changes a merge decision.

**Amendment 2026-10-16 (still DRAFT).** This revision amends the merged #407 bytes in response to
the 2026-10-15 adversarial review (findings E1-R01 to E1-R09). It resolves or explicitly defers
each finding with its consequence (section 15), and marks every policy choice that belongs to the
operator as **OPERATOR DECISION** with a recommended option. It decides nothing for the operator,
records no verdict, and ratifies nothing. Any earlier ratification statement applies to earlier
bytes only. The status above is unchanged: not ratified, not authorization for T3.

**Supplements, does not replace:** [CONTRACT-DURABLE-HITL-EFFECTS](CONTRACT-DURABLE-HITL-EFFECTS.md)
(storage, records, state machines, dispatch protocol, clock policy, crash windows, acceptance
tests). Read that contract first; this draft only adds what the T3 gate requires and that
contract does not yet freeze: an authority matrix, the no-attempt disposition, the reconciliation
record, late-result and fencing rules at the operator-visible boundary, terminal labels,
rollback, a failure-test inventory, pinned contract identities, and reviewer assignments.

**Plan slice:** [T3](PLAN-R4-EXECUTION.md#t3--approval-and-effect-transaction-spine) (milestone M2).
**Governing decisions (operator, 2026-10-14):** DEC-Q-04 (outcome semantics), DEC-Q-05 (verify-only
serving and disabled capability), DEC-E-01 (distinct authority is a T3 design invariant; T3 code
stays paused until the prerequisites below are reviewed together).

## 1. Purpose and non-goals

**Purpose.** Give T3 an unambiguous, reviewable specification so that no actor, credential, process
or evidence source can both exercise a consequential capability and be the sole proof that it was
authorized or qualified.

**Non-goals.** No exactly-once execution claim. No production provider transport (the
[transport contract](CONTRACT-FOREIGN-PROVIDER-TRANSPORT.md) owns it). No group-read or cross-user
serving. No freshness bound for externally published revocation state (that belongs to the deferred
Level-1 verifier transport / public-state contract and is an open operator decision, section 11).
No schema migration, no code, no activation.

## 2. Authority matrix (proposed; ratify before T3 code)

Actors are roles, not people or products. One credential or process may hold at most the roles the
matrix allows for it.

| Actor (role) | May authorize | May execute | May observe | May settle / reconcile | May independently qualify |
| --- | --- | --- | --- | --- | --- |
| **Operator principal** (authenticated human or single operator capability) | Issue or revoke a grant request; approve or deny an exception | No as a capability of this row; execution is a separate role (section 2.1) | Yes | Initiate reconciliation for an exact target | Ratify a specification; accept evidence |
| **Phylax issuer** (authority process, holds signing material) | Sign a grant bound to an exact target tuple after operator authentication | No | Its own issuance and revocation records | No | No |
| **Phylax verifier** (read-only process, no signing material) | No | No | Issuance, key and revocation facts, read only | No | No |
| **Oramasys consumer** (policy, ledger, consumption) | No; it only spends a verified grant once | Dispatches only a recorded, authorized intent through the qualified transport | Ledger, holds, receipts | Records a reconciliation decision it was given; never decides one | No |
| **Provider transport** (T4, later) | No | Sends the recorded intent | Provider outcome evidence | No | No |
| **Reconciler** (qualified operator capability) | No | No | Evidence sources named in the record | Yes, through one authenticated, idempotent, append-only record | No |
| **Independent qualifier** (reviewer or checker not in the maker lineage) | No | No | Exact heads, receipts, tests | No | Yes |

**Separation rules (each is a test target):**

1. The serving process is verifier-only: it never loads signing material, never opens the issuer
   authority, never falls back to a privileged path when verification is unavailable.
2. Phylax never sees a balance; Oramasys carries no cryptography and no issuer logic.
3. A maker never countersigns its own security-critical result. Same-model or same-session
   agreement is not independent evidence.
4. A reconciliation that releases a hold or confirms non-application requires a **distinct stable
   principal identity AND a distinct credential identity** from the executor; a different credential
   held by the same principal is not separation of duty. The reconciliation record carries an
   independently verifiable reconciler principal and credential identity (section 4). The only
   exception is an **explicit, audited same-human bootstrap**: it is labelled non-independent, and it
   can never by itself convert `unknown` into `confirmed_not_applied` or release a hold.
5. Qualification evidence is reviewed independently of its producer; "verified" claims from the
   producer never substitute for the independent check.

### 2.1 Role composition (resolves E1-R07)

The rows above describe **capabilities held by a role**, not mutually exclusive people. One human
or credential may hold several roles only as the composition table below permits. "Operator
principal: May execute = No" means the operator-principal *capability* does not itself dispatch;
the *executor* role (the process and credential that dispatches through the consumer) is a
separate role that, in the single-operator deployment of sections 11 and 13.8, the same human may
hold. Section 13.8's "may execute work" is read this way and is not a contradiction.

| Combination held by one principal (same `(issuer, subject)` and credential) | Allowed? | Basis |
| --- | --- | --- |
| Requester + first approver + executor | Yes, single-operator deployment | Section 11 parameters; audited; effect classes with `required_approvals = 1` only |
| Any of the above + **bootstrap** reconciler | Yes, always `non_independent` | 13.1; cannot release except the 13.2 bounded exception |
| Executor + **independent** reconciler | **No** | Rule 4; independence needs distinct principal and credential |
| Requester, executor or first approver + **second approver** | **No** | 13.4, 13.8; second approver is distinct from all three |
| Second approver + independent reconciler (one independent principal) | Only if policy explicitly permits, with separate scoped role events | 13.8; still distinct from requester, executor and first approver |
| Maker of a result + independent qualifier of that result | **No** | Rule 3 and 5 |
| Operator (ratifier) + independent qualifier of the same exact head | **No** | Section 12; the ratifier accepts, the qualifier verifies |
| Phylax issuer + any consumer, executor or reconciler role | **No** | Rules 1 and 2 |

Independence rules (each is a table-driven test over every row above, allowed and forbidden):

1. Differing identity strings and credential digests are **necessary, not sufficient**. Strict
   authentication proves *who authenticated*; it does not prove the two principals are controlled
   by different humans or are free of a shared factor.
2. A principal is `independent` for a decision only if it is also recorded in the enrollment
   record (13.8) with an **independent-control attestation**: an operator-signed statement naming
   the controlling human or service owner, the authentication root and the credential custody, and
   asserting no shared recovery factor with the executor. The attestation is an enrollment
   assumption recorded for audit; it is never evidence about a provider outcome. **OPERATOR
   DECISION (DECIDED 2026-10-17: adopt the draft's bar):** the minimum evidence for that
   attestation is a different identity provider account, a hardware-bound credential held by a
   different human or a separately administered service, and a written owner name. Enrolling a
   second principal is DEFERRED (operator item I; tentatively v2.5): until then this bar is
   recorded policy only, nothing is wired early, and no second principal is enrolled. Consequence
   while none is enrolled: no second principal can be `independent`, and the bootstrap-only
   fail-closed behaviour of 13.1 continues.
3. Requester, executor and first-approver separation from the second approver and independent
   reconciler is evaluated **per decision** (13.8), using the enrolled attestation plus the
   identity comparison.
4. The audited bootstrap exception stays exactly as approved: one record, non-independent, no
   release by itself.

## 3. Outcomes: no attempt versus unknown (DEC-Q-04)

Keep `unknown` as the canonical machine outcome for an attempt that may have crossed the dispatch
boundary and has no authoritative terminal evidence. Never replace it with `failed`,
`not_attempted` or a success-shaped status to simplify a view.

| Case | Evidence required | Record | Accounting |
| --- | --- | --- | --- |
| **No attempt** | Positive durable evidence that no eligible attempt crossed the dispatch boundary | One run-level no-attempt disposition; **no** synthetic attempt id, hold or per-attempt receipt | No charge for an attempt that never existed |
| **Unknown attempt** | A durable attempt identity exists and dispatch may have started, but completion or non-application cannot be established | Attempt outcome `unknown` | Stays charged; blocks success reporting, replay, automatic retry and automatic release |

Missing records, process death, a timeout, a lost response or an unreadable event log are **not**
proof of no attempt. If the evidence cannot prove the boundary was not crossed, the outcome is
`unknown`.

## 4. Reconciliation record (proposed fields)

Reconciliation is explicit, authenticated, evidence-backed, idempotent and append-only.

| Field | Meaning |
| --- | --- |
| `schema_version` | Version of this record layout; an unknown version is refused |
| `reconciliation_key` | Unique idempotency key; a retry returns the stored record |
| `target` | Exact `run_id`, `attempt_id`, `hold_id`, operation id, provider identity and fencing epoch |
| `actor` | `issuer`, `subject`, provider name, credential digest, verification mode, `independence` (13.1), role (section 2) |
| `evidence[]` | One entry per evidence item: class (13.2), source system identity, digest, assertion id where the class has one. A multi-class proof lists every item |
| `observed_outcome` | `confirmed_applied`, `confirmed_not_applied`, or `still_unknown` |
| `decision` | One of the closed set `confirm_applied`, `confirm_not_applied_release`, `confirm_not_applied_hold`, `keep_unknown`. `confirm_not_applied_hold` records the finding without freeing budget |
| `amount`, `unit` | Reservation amount affected, in the reservation's unit; zero for `keep_unknown`. Partial amounts are not defined (13.2) |
| `expected_state_version`, `expected_accounting_version` | Versions of the hold/attempt state and the accounting projection the decision was made against (CAS inputs) |
| `authority_pair` | `(configuration_policy_epoch, authority_epoch)` in force at commit (13.8) |
| `granting_authority` | The recovery settlement/release grant spent by this record: grant id, issuer, purpose (section 14) |
| `decided_at` | UTC timestamp from the store's authoritative clock |
| `accounting_before`, `accounting_after` | The disposition of the reservation before and after |
| `supersedes` | Optional link to an earlier record; corrections are new linked events |

**Evidence sufficiency** is defined exclusively in section 13.2. An operator attestation never
suffices; the closed evidence-class list and the release predicate there control, and this section
does not restate the decision matrix. Retention is in section 13.3.

**Canonical request fingerprint (resolves E1-R05).** The fingerprint is a SHA-256 digest over a
canonical serialization of: `schema_version`, `target`, `actor` (principal and credential digest),
the `evidence[]` set sorted by (class, source, digest), `observed_outcome`, `decision`, `amount`,
`unit`, `expected_state_version`, `expected_accounting_version`, `authority_pair` and
`granting_authority`. It excludes `reconciliation_key`, `decided_at` and `supersedes`. The
serialization rule (key ordering, number and string form) is not frozen by this draft. The
refusal contract names a "canonical request digest" but no serialization rule for it, so fixing one
for this record is a pre-code item of the integrated schema contract (section 14).

**Idempotency.** Same key and same fingerprint returns the stored original result, with no new
mutation, **only if the caller is still authorized** to read it. Same key and a different
fingerprint (changed outcome, decision, amount, actor, evidence or versions) is a **conflict**
and mutates nothing. A different key against a hold that already has a disposition is refused:
there is at most one active disposition per hold, and a change is a linked `supersedes`
correction that must itself satisfy section 13.2 and spend its own grant.

**Atomic mutation.** In **one** transaction of the owning (Oramasys) store: (1) revalidate the
actor's authorization and the **current** `authority_epoch` pair, so a reconciler revoked between
validation and commit is refused; (2) check `expected_*` versions by compare-and-swap; (3) append
the reconciliation record; (4) spend the recovery grant (single use); (5) update the accounting
projection. All five commit or none do. Issuer-side Phylax records live in a different store and
cannot join this transaction: a revocation that lands there after commit is handled by the
revocation rules of 13.4, never by rewriting the record, and any cross-store notification uses an
outbox with retry rather than a distributed transaction. A crash leaves either the full result or
none; recovery re-reads by `reconciliation_key`.

Other rules: the original attempt, hold and unknown event are never edited or deleted; a release
is permitted **only under section 13.2's release rule**, whose conditions (evidence that the
attempt was not applied, and fencing that excludes a late execution) are necessary there, never
sufficient here; otherwise the reservation is preserved or consumed conservatively; no timeout,
stale-row cleanup, restart or missing response performs reconciliation.

**"Verified unused amount" is DISABLED BY DEFAULT in M2 and retained as a reserved feature; it is
not removed (operator decision, 2026-10-17: default disable only, do not remove a feature that will
be useful later).** It was an undefined alternative release basis, so it has no effect until a
later signed-policy change enables it. Release in M2 is all-or-nothing for a hold, on
`confirmed_not_applied` plus fence plus the reconciler rule. **OPERATOR DECISION (DECIDED
2026-10-17):** disabled by default and kept in the specification. Before it may be enabled, a later
change must supply: a definition of "verified" with its evidence classes; a conservation rule
(`released + consumed + in_flight <= reserved`, per unit, never negative, never above the reserved
amount); a statement that oversized or negative amounts are refused; and tests for each.
Consequence while it is disabled: a partially used reservation stays charged until the full-hold
rule can apply.

## 5. Idempotency, fencing, timeout and late result

1. **Operation identity** follows the contract (section 2 there): the logical operation id is stable
   across transport retries, an attempt id changes per delivery, reuse with changed content is a
   conflict.
2. **Takeover attempt identity.** A forced takeover records a caller-supplied attempt identifier
   with the run, store reference, source and target epoch and the fixed terminal payload before the
   epoch advances (the advance and the record are one compare-and-swap). A retry resumes that
   recorded attempt without another fence; a different identifier is a new takeover.
3. **Fencing.** A holder fenced out is not proven dead. A result arriving after its epoch was
   superseded is recorded as a late result and never applied to state or accounting; it may become
   evidence for reconciliation only.
4. **Timeout.** A timed-out store or provider call is "may be partial", never "none"; the retry
   rule above applies. Every external call carries a hard deadline, including reads and lock waits.
5. **Late completion** after reconciliation to `confirmed_not_applied` is a conflict that blocks
   further effects on that target until an operator disposition records the evidence.

## 6. Terminal and operator labels

Machine value: `unknown`. Operator presentation: **"Outcome unknown — reconciliation required"**.
Show **"No attempt made"** only for the positively evidenced run-level case. Never collapse the two
into a generic failure. Explanatory text exposes no prompts, credentials, private payloads or raw
exception text.

## 7. Serving capability and degradation (DEC-Q-05)

Grant-backed serving is a separate capability that is **off unless explicitly activated**; absence
of configuration never implies enablement. When the verifier cannot open, the capability is
`unavailable`, unrelated service continues, grant requests fail closed without ledger mutation, and
unavailability is never reported as an invalid or revoked grant. Verification is local, same-user,
private-mode, read-only; cross-user serving is prohibited until the Level-1 contract ratifies a
signed observation encoding, an authoritative clock, a freshness bound, reconciliation and failure
behaviour.

## 8. Rollback and recovery (resolves E1-R04)

Source-backed implementation boundary and proposed witness acceptance checks:
[C1 recovery and test map](E1-C1-SOURCE-RECOVERY-AND-TEST-MAP-2026-10-18.md).
This linked reconciliation is proposed for review and grants no recovery authority.

Three different things are called "rollback" and must not be mixed.

| Layer | Rollback |
| --- | --- |
| Capability | Switch the activation setting off; the service continues without grant-backed work |
| Code | Revert the slice's merge commit. The schema is forward-only, so reverting code never edits or drops data and never restores an older database |
| Evidence | Receipts and reconciliation records are append-only and are kept; a wrong record is superseded by a linked correction |

### 8.1 Offline migration rehearsal (an exit criterion for T3)

A rehearsal runs on a **copy** of a store that is not serving: backup, migrate, restore into a
scratch location, verify digests. Byte-identical digests are one migration test, **not** a safety
verdict for operational recovery, and a rehearsal result is never used to restore a live store.

### 8.2 Operational recovery (restoring a live effect store)

Restoring a snapshot that predates consumed grants, revocations, provider receipts,
reconciliations, authority epochs or clock high-water marks can resurrect spent authority or erase
an accepted effect. Therefore:

1. **Quiesce.** Turn the capability off and stop new dispatch authorization. In-flight attempts
   are not cancelled by inference; each stays as recorded and is treated as `unknown` until
   evidence says otherwise.
2. **Preserve first.** Before any restore, copy the current store, its event log and its outbox to
   an immutable location. Newer records are never deleted by a restore; the seven-year retention
   of 13.3 covers the preserved copy.
3. **Restore into quarantine.** The restored store is opened in an isolated, non-dispatching mode.
   Nothing in it authorizes dispatch, accepts a grant, or releases a hold until step 5 passes.
4. **Detect rollback.** Compare the restored store with independent witnesses that a restore
   cannot rewind: the highest `authority_epoch` and `configuration_policy_epoch` seen, the clock
   high-water mark (the contract's rule), the issuer's revocation records, the preserved event-log
   tip, and the provider's own receipts for stable keys. Any witness ahead of the restored store
   means rollback is detected.
5. **Reconstruct or stay unknown.** Replay the preserved post-snapshot events onto the restored
   store when they are intact and verifiable. For anything that cannot be reconstructed: a grant
   whose consumption cannot be excluded is treated as consumed; a principal or grant revoked in any
   witness stays revoked; any attempt with dispatch authorization after the snapshot point is
   `unknown` and charged; provider reconciliation is run for stable keys before any retry.
6. **Reopen dispatch** only when rollback is not detected, or is fully reconciled; compatibility
   (schema and contract versions) is checked; every committed batch is covered by a published
   witness (the record below); an operator disposition records the previous and accepted epochs
   and clock mark; and each pending reservation is revalidated. A backward-clock
   recovery follows the contract's clock policy. Never silently resume from an old authorization
   snapshot.

**OPERATOR DECISION (DECIDED 2026-10-17: yes, as recommended):** where the rollback witness
lives. Decided: an append-only `authority_epoch` and event-tip record that is exported outside the
store file at each commit batch (the issuer-side revocation log already is outside it).
Consequence if unset: rollback detection is limited to the issuer log and provider receipts, and
every restore ends in quarantine with affected work `unknown`.

**Witness record and publication barrier (PROPOSED; review finding, 2026-10-18).** The decision
above fixes where the witness lives, not what it holds. One witness record is appended outside the
store file for each commit batch and contains: the batch sequence number; the `authority_epoch`
and `configuration_policy_epoch` committed by that batch; the clock high-water mark; the
event-log tip digest; the highest issuer permit and revocation versions the batch used; and the
highest provider
receipt reference per stable key. Records are append-only, chained by the previous record's
digest, and never rewritten; a gap or a broken chain is itself rollback evidence.

The barrier is fail closed. A batch is not covered until its witness record is durably published
and read back. Dispatch authorization for work that depends on an uncovered batch is refused, and
while any publication is pending, failed or unverifiable the store stays quarantined: it does not
authorize dispatch, accept a grant or release a hold. A crash between commit and publication
therefore leaves the store uncovered, and recovery treats the uncovered batch as `unknown` rather
than as absent. This is a design requirement for the integrated schema review; it adds no wire
field and no code (tests E1-T-26 and E1-T-28 in 9.1).

### 8.3 Security-baseline crosswalk (PROPOSED; review finding, 2026-10-18)

The table maps three E1 control groups to the external baselines named in the 2026-10-18
review. It is chapter-level and descriptive: exact control or practice identifiers are confirmed
by the independent reviewer at the resulting head, and no mapping here claims conformance.

| E1 control group | OWASP ASVS / Top 10 | NIST SSDF | CISA Secure by Design / Default | OpenSSF | SLSA |
| --- | --- | --- | --- | --- | --- |
| Recovery procedure (8.2: quiesce, preserve, quarantine, witnesses, fail-closed reopen) | Top 10 A04 Insecure Design, A08 Software and Data Integrity Failures; ASVS business-logic and data-protection chapters | PW.1 design to meet security requirements; RV.1-RV.3 identify, assess and root-cause | Default quarantined and disabled; ownership of security outcomes | Security Insights recovery and disclosure notes | Provenance of the preserved copy is out of scope here |
| Approval-revocation cascade and cross-store barrier (13.4) | Top 10 A01 Broken Access Control, A09 Logging and Monitoring Failures; ASVS access-control and logging chapters | PW.1; PW.8 test the executable behaviour; PS.1 protect the policy table | Fail closed by default; no hidden authority | Scorecard Code-Review (independent review before merge) | Not applicable to runtime state |
| Grant-purpose separation (14) | Top 10 A01 Broken Access Control; ASVS access-control chapter | PW.1; PW.8; PW.9 secure defaults | Secure by Default: cross-purpose refused with no mutation | Scorecard Code-Review, Branch-Protection | Verifier and policy changes carry reviewed provenance |

## 9. Failure-test inventory (each must fail first)

The set below extends the contract's section 7. For each **new** invariant a named test must exist
and be shown failing against an absent or mutated implementation before T3 code merges. For
behaviour already implemented and proven (M1 seams), the requirement is a named test plus a
recorded negative mutation, not deliberately breaking proven code. IDs are placeholders until
ratified. Section 9.1 maps each row.

| ID | Case |
| --- | --- |
| E1-T-01 | No eligible attempt versus started-but-unsettled attempt are distinguished |
| E1-T-02 | Missing or corrupt evidence is never read as "no attempt" |
| E1-T-03 | `unknown` stays charged, cannot replay, cannot report success, cannot auto-release |
| E1-T-04 | Reconciliation: authorization, duplicate key, changed-payload reuse, append-only history; concurrent reconcilers; replay with changed outcome, decision, amount or actor is a conflict; a replay of an identical authorized request returns the original; reconciler revoked between validation and commit; partial failure leaves all or nothing; the full record, fingerprint and atomic transaction of section 4 |
| E1-T-05 | Late worker after fencing is recorded as late and never applied |
| E1-T-06 | Unavailable verifier, invalid grant, revoked grant remain distinct; unavailable mutates nothing |
| E1-T-07 | Duplicate and replayed effect requests resolve to one outcome |
| E1-T-08 | Partial and late completion across every crash window in the contract table |
| E1-T-09 | Authority separation: executor cannot reconcile; maker cannot qualify |
| E1-T-10 | Operator view redacts sensitive payloads and shows the two labels correctly |
| E1-T-11 | Backup, restore and redaction; the offline migration rehearsal restores byte-identical digests (8.1). Operational recovery (8.2): after the snapshot consume a grant, revoke a principal and accept a provider effect, restore the old snapshot; none becomes reusable or disappears as a recoverable obligation, and dispatch stays closed until reconciled |
| E1-T-12 | Principal and credential distinctness: same principal with another credential is `non_independent`; `attest`/`off` verification is `non_independent` |
| E1-T-13 | Same-human bootstrap exception covers exactly one record, cannot be reused, and never by itself releases a hold or yields `confirmed_not_applied`; the `bootstrap_exception` event supplies no evidence, so the section 13.7 predicate must also hold |
| E1-T-14 | Evidence sufficiency matrix per outcome (13.2): attestation alone refused; a receipt proves applied, never not-applied; one authoritative provider class suffices for applied; unknown class rejected; no combination of local facts yields `confirmed_applied`; outbox plus fence never yields `confirmed_not_applied`, including a sent-but-unrecorded case versus an unsent case with identical local rows (stays unknown and charged), including with an independent reconciler and a newer valid fence |
| E1-T-15 | Second approval and revocation timing (13.4): approval expired or revoked before issuance, between issuance and reservation, before dispatch authorization and after it, each with the stated outcome; absent is valid single approval; present-but-same-principal refused at issuance; unknown wire version refused (`grant.schema_unsupported`); inconsistent with class policy refused (`grant.malformed`) |
| E1-T-16 | Retention: reconciliation records are never deleted by a restart, cleanup or backup rotation; redaction preserves digests |
| E1-T-17 | Bounded exception (13.7): a non-independent record releases only on a mechanically verified `NOT_ACCEPTED` assertion (full 13.2 predicate: negative finality, window boundary, audience and replay, pinned key version) plus a verified fence; delayed acceptance after the assertion, a replayed old assertion, a wrong-provider or wrong-key assertion and a window-boundary race do not free a hold; receipt, lookup-only, outbox-only, attestation and unverifiable statements are refused; unresolved count and oldest age surfaced; never auto-released |
| E1-T-18 | Retention: seven-year clock starts at the later of final settlement and the final linked record; a legal, incident or dispute hold suspends deletion; redaction at write time keeps the required digests |
| E1-T-19 | Roles (section 2.1): table-driven over every allowed and forbidden composition; strings and credential digests that differ without an independent-control attestation are not independent; one independent principal may hold reconciler and second-approver only when policy permits, must be distinct from requester, executor and first approver, with separate scoped role events; an agent label or a second credential of the same human is never a second principal |
| E1-T-20 | Approval quorum: a policy value above `2`, or any attempt to encode 2-of-3 or a majority in `second_approval_ref`, is refused; an enrolled third principal has no approval power without an explicit signed policy |
| E1-T-21 | Nomination: only the operator capability may nominate; a nominee is inert until strict-mode authentication and a policy role; configuration and runtime nominations write the same audited record; an unauthenticatable nominee holds no role; distinctness is evaluated per decision |
| E1-T-22 | Enrollment idempotency and epochs: a restart or retry returns the original enrollment event or revision for the same `enrollment_key` and payload; a changed payload is refused; role or revocation changes are new linked events; a configuration change is inert until a validated restart into a new `configuration_policy_epoch`; a runtime enrollment is refused before its authority event commits and usable only for permitted role and effect policy after it; a runtime revocation refuses new authority use after its commit; every record carries the `(configuration_policy_epoch, authority_epoch)` pair |
| E1-T-23 | Grant purpose: a recovery settlement/release grant presented to the effect path, and an effect grant presented to the recovery path, are each refused with **no authority, accounting or effect mutation** (ledger, holds, outbox, receipts and grant use unchanged; business-state digests equal before and after), while a sanitized refusal audit record is allowed. The expected refusal code per direction is **not yet fixed** and is fixed by the integrated schema contract (section 14); this row cannot be an executable test until then. Also covers unknown version, missing and ambiguous discriminator, and valid-purpose controls |
| E1-T-24 | Inherited invariants map to named tests: concurrent single use; changed-payload reuse of an operation key is a conflict; provider-key stability across retries; revocation on **each side** of the dispatch-authorization transaction; no automatic replay of an unknown outcome |
| E1-T-25 | Cascade recovery witness (13.4, 13.8): issuer revocations commit atomically; consumer dispatch is refused while cascade acknowledgment or affected lineage is unavailable; duplicate notifications return one witness; all direct and transitive child runs are covered at an observation checkpoint; missing operation history is `none_recorded`, incomplete enumeration is never empty-success; the witness never releases a hold or proves a provider outcome |

### 9.1 Test map (resolves E1-R09)

[C1 existing-test audit](E1-C1-SOURCE-RECOVERY-AND-TEST-MAP-2026-10-18.md)
identifies concrete M1 nodes and their remaining E1 extensions. It distinguishes
source inspection from executed tests; the proposed nodes below remain proposals.

Columns: **Owner** is the repository expected to hold the test (O = Oramasys consumer and ledger,
P = Phylax issuer and verifier, C = Core scheduler or contract tests, R = this repository's docs
checks). **Existing/new** is stated conservatively: "M1 seam" means behaviour the merged M1
groundwork may already cover, **to be confirmed by an exact-head audit**; "New (T3)" means a new
invariant. **Planned test node** is a PROPOSED name only; **no node id in this table exists or has
been verified**, and "proving commit" is empty until a test is run at an exact head. Candidate
existing files seen in a local Oramasys working copy (for the audit to confirm or reject, not as
evidence): `test_adjustment_grant_consumer.py`, `test_budget_crash_recovery.py`,
`test_durable_accounting.py`, `test_outbound_ledger.py`, `test_execution_guard.py`.

| ID | Owner | Existing/new | Planned test node (PROPOSED) | Negative mutation the test must catch | Stage |
| --- | --- | --- | --- | --- | --- |
| E1-T-01 | O | New (T3) | `test_e1_no_attempt_vs_unsettled` | Treat a started attempt as no-attempt | T3 slice 1 |
| E1-T-02 | O | New (T3) | `test_e1_missing_evidence_not_no_attempt` | Read a missing or corrupt event log as no-attempt | T3 slice 1 |
| E1-T-03 | O | M1 seam, confirm | `test_e1_unknown_stays_charged_blocked` | Auto-release, replay or success-report an `unknown` | T3 slice 1 |
| E1-T-04 | O | New (T3) | `test_e1_reconciliation_record_atomic_idempotent` | Reused key with changed amount or actor accepted; non-atomic grant spend | T3 slice 2 |
| E1-T-05 | O | M1 seam, confirm | `test_e1_late_result_recorded_not_applied` | Apply a fenced-out late result to state | T3 slice 1 |
| E1-T-06 | O, P | M1 seam, confirm | `test_e1_unavailable_invalid_revoked_distinct` | Map unavailable to invalid or mutate on unavailable | T3 slice 1 |
| E1-T-07 | O | New (T3) | `test_e1_duplicate_effect_requests_one_outcome` | Duplicate request dispatches twice | T3 slice 1 |
| E1-T-08 | O | M1 seam, confirm | `test_e1_crash_window_<boundary>` per contract table row | Skip one window or resend after acceptance | T3 slice 1 |
| E1-T-09 | O | New (T3) | `test_e1_executor_cannot_reconcile` | Executor credential accepted as independent reconciler | T3 slice 2 |
| E1-T-10 | O | New (T3) | `test_e1_operator_view_labels_redaction` | Leak payload or collapse the two labels | T3 slice 3 |
| E1-T-11 | O | New (T3) | `test_e1_migration_rehearsal_digests`; `test_e1_restore_old_snapshot_quarantine` | Restore old snapshot and reuse a consumed grant or lose an accepted effect | T3 exit |
| E1-T-12 | O | New (T3) | `test_e1_principal_credential_distinct` | Same principal, other credential counted independent | T3 slice 2 |
| E1-T-13 | O | New (T3) | `test_e1_bootstrap_one_record_no_release` | Reuse the exception or let it release a hold | T3 slice 2 |
| E1-T-14 | O | New (T3) | `test_e1_evidence_matrix_per_outcome`; `test_e1_sent_unrecorded_vs_unsent` | Replace applied evidence with two unrelated valid classes; outbox plus fence yields not-applied | T3 slice 2 |
| E1-T-15 | P, O | New (T3) | `test_e1_second_approval_revocation_timing` | Honor a grant after its approval was revoked | T3 slice 2 |
| E1-T-16 | O | New (T3) | `test_e1_retention_not_deleted` | Restart, cleanup or rotation deletes a record | T3 slice 3 |
| E1-T-17 | O | New (T3) | `test_e1_not_accepted_predicate` | Accept a replayed, wrong-audience, expired-window or no-finality assertion | T3 slice 2 |
| E1-T-18 | O | New (T3) | `test_e1_retention_clock_and_hold` | Retention starts at the wrong event or ignores a legal hold | T3 slice 3 |
| E1-T-19 | O | New (T3) | `test_e1_role_composition_table` | A forbidden composition passes | T3 slice 2 |
| E1-T-20 | P | New (T3) | `test_e1_quorum_above_two_refused` | Encode 2-of-3 in the scalar reference | T3 slice 2 |
| E1-T-21 | O | New (T3) | `test_e1_nomination_inert_until_strict` | A nominee gains a role without strict authentication | T3 slice 2 |
| E1-T-22 | O | New (T3) | `test_e1_enrollment_idempotency_epochs` | Hot-reload a roster; duplicate enrollment event | T3 slice 2 |
| E1-T-23 | P, O | New (T3), blocked | `test_e1_cross_purpose_refused_no_mutation` (both directions) | Wrong-purpose grant mutates state; refusal code unasserted | Blocked on section 14 rule 3 |
| E1-T-24 | O | M1 seam, confirm | `test_e1_inherited_invariants` (single use, key conflict, key stability, revocation each side, no replay) | Remove any one inherited check | T3 slice 1 |
| E1-T-25 | P, O | New (T3), schema gated | `test_e1_cascade_recovery_witness` (PROPOSED) | Permit dispatch before cascade acknowledgment; omit a descendant or treat missing history as completed; let a witness release a hold | T3 slice 2, after integrated schema review |
| E1-T-26 | O | New (T3) | `test_e1_witness_coverage_blocks_dispatch` | Authorize dispatch while a committed batch has no published witness; treat a publication gap as absent | T3 exit |
| E1-T-27 | P, O | New (T3), schema gated | `test_e1_issuer_revocation_vs_permit_matrix` | Revocation before the permit still yields a permit; revocation racing the permit yields both outcomes or an order the issuer log does not show; revocation after the permit but before the consumer commit is treated as pre-authorization; a pending cascade does not refuse dispatch | T3 slice 2 |
| E1-T-29 | O | New (T3), schema gated | `test_e1_lost_permit_is_consumed_not_reissued` | Crash or timeout between permit and consumer commit leads to a second permit or a retry | T3 slice 2 |
| E1-T-30 | P, O | New (T3), schema gated | `test_e1_permit_forged_replayed_unbound_expired_unavailable` | Accept a forged, replayed, wrong-reservation or expired permit; map an unreachable issuer to valid | T3 slice 2 |
| E1-T-28 | O | New (T3) | `test_e1_witness_chain_gap_is_rollback` | Accept a restored store whose witness chain has a gap, a break or a higher epoch | T3 exit |

Stages T3 slice 1, 2 and 3 are labels for this map only (effect spine, reconciliation and
authority, operator view and retention). They are not planned work packages and do not authorize
any slice; section 12 governs ratification and the plan governs T3 sequencing.

## 10. Pinned cross-repository contract identities

Frozen identities are exact commits; nothing floats on a branch. Each identity is labelled by its
**purpose**. The purposes are distinct and need not be equal: each must match the evidence or
contract role it is named for.

| Purpose | Contract | Identity |
| --- | --- | --- |
| Current production pin | Core, as declared by the Oramasys package | `perpetua-core` `609ff0ed99cf8eca6c9ef608e764b7a25b6b9973` |
| Composition source (merged) | Phylax verify-only store and lifecycle; composition-only, not a production pin | `oramasys/phylax` `main` commit `0c3e860749b3ff8f62e102679f1f415f8acf0a61` |
| Composition source (merged) | Oramasys verify-only composition and Ubuntu interop (merged with PRs #38 to #42 in one merge) | `oramasys/oramasys` `main` commit `f8898b35d5249e483b2f4a68c097957e675a0ef4` (merge of PR #43) |
| Consumer source under qualification | The commit the M1 qualification run tests (operator choice, 2026-10-15) | `oramasys/oramasys` `f8898b35d5249e483b2f4a68c097957e675a0ef4` |
| Qualification candidates | Final-producers set named by the schema-3 manifest; set and refreshed by the M1 qualification PR | Core `6d75cfe08af95992dddffab13ae3019aa9c41350`, Telos `931b6347142e8e66b31136e3ac8159d86eb5b2f7`, Agate `172bfc3ebf00d507856e70d0f6a0e7dbd577ffbc`, Phylax refreshed to the composition source above |
| Producer registry checkout | Registry the manifest and workflows read | `diazMelgarejo/orama-system` `65ec365293c6a892cd4f978e656cfb61c0d04b9a` |

## 11. Operator decisions and what remains open

**Recorded 2026-10-15 (operator, chat; recommendations reconciled with independent review, board
rows 4556 to 4558).** The operator approved the recommendations that Codex also made; one item is a
recorded disagreement.

| # | Decision | Disposition |
| --- | --- | --- |
| 1 | Executor/reconciler separation | **Decided.** Distinct principal AND distinct credential; a same-human bootstrap exception is **allowed**, audited, labelled non-independent, and cannot release a hold or confirm non-application by itself. |
| 2 | Reconciliation evidence | **Decided.** Closed class list; an attestation alone never suffices; an authoritative provider statement or two independent corroborating classes may; retention no shorter than ledger audit retention. Reaffirmed 2026-10-17: the two-class alternative stands as a typed extension with an empty provider-origin pair list (13.2). |
| 3 | Two-person approval | **Decided by the operator over a recorded independent dissent.** An optional second-approver field is part of the E1 freeze now. *Dissent (Codex, row 4558):* a wire or schema change with undefined semantics is inferred implementation and future compatibility debt; add it only in the T4 transport/approval slice. **Condition recorded here:** E1 may not be ratified until the field's semantics are specified (see below). No Phylax or Oramasys code changes now. |
| 4 | Level-1 freshness bound and clock | **Deferred.** Acceptable for M2 entry only while serving is explicitly same-UID and local-only and cross-UID or remote publication stays rejected by configuration and documentation. No TTL value or stale-observation test at Level 0. |
| 5 | Phylax production-pin disposition | **Composition-only.** The `grant-serving` extra stays out of default dependencies. The M1 qualification PR refreshes the manifest candidate to the exact reviewed commit proven by the interop receipt (currently `0c3e860749b3ff8f62e102679f1f415f8acf0a61`), updating **every** place the candidate appears (producers entry and each final-producers candidate set); the digest then changes and is re-frozen. It is never derived dynamically from a receipt artifact. |

**Item 3 conditions.** Satisfied in section 13.4 as a proposal: who may be a second approver and
how verified, absent means single approval, an invalid or unverifiable second approver refuses the
grant (fail closed), the wire version and older-verifier behaviour, and which effect classes require
it. They stay a ratification blocker for the draft, not for the merge of the current PR stack.

**Parameters recorded on the operator's instruction "codex resolved, apply" (2026-10-15, board
row 4561).** Codex's recommendations are applied as the draft's values and remain subject to the
exact-head review and the operator's ratification comment on this PR:

| Parameter | Value |
| --- | --- |
| Retention (ledger audit and reconciliation records) | Seven years from the later of final settlement of the hold and the final linked reconciliation or correction record; a legal, incident or dispute hold suspends deletion; redact at write time (13.3). An operational policy, not a legal claim. |
| Principals and roles | The single operator stays primary approver and may execute; any bootstrap reconciliation is non-independent; the durable second principal is an independently controlled identity with its own `(issuer, subject)`, credential digest, `strict` mode and `reconciler` role (13.1, 13.8). |
| Section 13.7 part 1 | Approved **only** as the bounded exception to section 13.2 named there, with its evidence predicate; absent the synchronized amendment the independent-reconciler release rule controls. Independent review at `55be8366` confirmed 13.2 and 13.7 are synchronized and ready for ratification; the draft as a whole still needs exact-head review and the operator's ratification. |
| Authority versions | Ratified by the operator on 2026-10-15 per independent review (board row 4572): configuration changes are effective only at a validated-restart `configuration_policy_epoch`; runtime enrollment and revocation are effective at their committed, monotonic `authority_epoch`; every decision records both (13.8). |
| Approval quorum | M2 stays at `1`. The first multi-approval policy is `2-of-2` for explicitly high-impact effect classes. General M-of-N is deferred to T4 (13.4); enrollment confers no approval power (13.8). |

**Still the operator's, never assumed here.** Ratification of this draft as a whole, after the
re-review of the corrected exact head. The second principal is nominated by the operator at
configuration or runtime (section 13.8); this draft names no one.

## 12. Reviewer assignments and ratification

| Role | Assignment (proposed) |
| --- | --- |
| Specification maker | The agent that authored this draft (it may not qualify it) |
| Independent reviewers | Codex (design and contract review), Cline (checker of evidence and links) |
| Ratifier | Operator, recorded on the review PR |

**Ratification checklist:** all `TBD` fields resolved; section 2 matrix accepted cell by cell;
section 9 inventory accepted as the T3 entry criteria; the "still open" list in section 11 answered
or explicitly deferred with its consequence; the item 3 semantics specified; independent review
verdicts attached at the exact head; every **OPERATOR DECISION** in section 15 answered or
explicitly deferred with its consequence; the integrated schema contract of section 14 reviewed
and pinned before ratification, as required by operator decision 7 of 2026-10-17; the section 9.1
map filled with real test node ids and proving commits. Deferring that contract cannot satisfy
this checklist.

**Ratification order (operator, 2026-10-15).** The grant-purpose contract (section 14) is folded
into this PR. Any earlier statement that this draft was ratified therefore applies to earlier bytes
only and is superseded. The operator ratifies **one concrete substantive head**, by a comment on
this PR that names that head, after the Codex design verdict and the Cline checker verdict at that
same head and after its checks pass. A reviewed **metadata-only** status addendum then records the
ratification and points to that head and comment; any substantive difference after ratification
requires renewed review. The historical `DRAFT` filename neither confers nor invalidates
ratification.

## 13. Specifications closing the open semantics (PROPOSED; for independent review)

These sections intend to reuse verified existing types and closed vocabularies. Provisional
cascade concepts and unverified refusal-code mappings remain subject to the integrated schema
review before ratification. They add **no** new credential format,
**no** new trust protocol and **no** new closed refusal code. Wire or schema work stays in the T3 and
T4 slices.

### 13.1 Principal and credential identity (decisions 1; resolves "concrete principals and mechanism")

- **Principal identity** is the pair `(issuer, subject)` of an authenticated request result (the
  existing `AuthResult`), never a display name.
- **Credential identity** is a digest: the local secret fingerprint the fleet binding already records
  for that principal, or the provider's credential identifier hashed. The token itself is never stored.
- A reconciliation record stores `issuer`, `subject`, provider name, credential digest, the
  verification mode (`strict`, `attest` or `off`) and an `independence` field.
- **`independence = independent` only when** the verification mode is `strict`, the principal differs
  from the executor's (and from the first approver's where a second approval applies), **and** the
  credential digest differs from the executor's. Anything else is recorded `non_independent`.
- **Same-human bootstrap exception.** A `bootstrap_exception` event records the attested human
  identity, a reason, the exact reconciliation key it covers and a UTC time. It covers exactly one
  record, is never reusable, always yields `non_independent`, and can never by itself produce
  `confirmed_not_applied` or release a hold.
- **Stated consequence.** The shared bearer capability maps to one principal today, so in the current
  single-operator deployment **every** reconciliation is `non_independent`. A `non_independent`
  reconciliation **cannot release a hold except** through the mechanically verified `NOT_ACCEPTED`
  plus ledger-fence exception of sections 13.2 and 13.7; every other release path requires an
  `independent` reconciler, which needs a second principal enrolled in `strict` mode. That is the
  intended fail-closed behaviour, not a defect.

### 13.2 Evidence classes and sufficiency (decision 2)

The class list is **closed**; an unlisted class is rejected.

| Class | Meaning | Authoritative alone? |
| --- | --- | --- |
| `EV-PROVIDER-RECEIPT` | Provider receipt identifier plus payload digest | For **applied** only, when it matches the idempotency key; never for not-applied |
| `EV-PROVIDER-LOOKUP` | Provider-side lookup by the stable idempotency key | For **applied** only when it also matches receipt identifier and payload digest; an ambiguous or absent result proves nothing |
| `EV-PROVIDER-SIGNED` | Statement signed by a pinned provider key (any assertion) | Only for the assertion it makes, and only if it states application directly |
| `EV-PROVIDER-NOT-ACCEPTED` | A signed provider `NOT_ACCEPTED` assertion; its **evidence predicate** is below | Yes, for **not-applied**, within its window |
| `EV-OUTBOX-STATE` | The dispatch outbox item was never handed off (local bookkeeping) | **Never evidence of an outcome**; a condition input only (see below) |
| `EV-LEDGER-FENCE` | The holder was fenced by a lease-epoch advance | **Never evidence of an outcome**; a release *condition* only |
| `EV-OPERATOR-ATTESTATION` | An operator statement | **Never**; annotation only |

**`EV-PROVIDER-NOT-ACCEPTED` predicate (all of it, mechanically verified; resolves E1-R03):**

1. *Binding.* The assertion is bound to the operation's idempotency key **and** payload digest,
   the provider identity, and an assertion id.
2. *Negative finality.* The signed statement, or the provider's pinned protocol documentation
   referenced by the pinned trust configuration, states that after this assertion the provider
   **will not accept** a later or delayed delivery of that exact key (a terminal cancellation or
   tombstone, or an equivalent suppression), **or** a reviewed protocol demonstrates that no
   outstanding delivery can still arrive. A point-in-time "not seen yet" is **not** this class: a
   local fence cannot retract a remote socket write. A provider without this guarantee keeps the
   hold `unknown`, and the 13.7 exception does not apply to it.
3. *Time and window.* A provider timestamp and the provider's retention or deduplication window
   are present. The assertion is accepted only if the window covers the interval from the
   attempt's dispatch authorization to the decision time, plus a clock-skew allowance, judged
   against the store's authoritative clock and high-water mark. An assertion whose window ends at
   or before the decision time (boundary inclusive) is refused. **OPERATOR DECISION
   (DECIDED 2026-10-17: 60 seconds):** the skew allowance is 60 seconds, a fixed value set in the
   signed policy, never taken from the assertion itself and not configurable per call. Because the
   allowance is added to the interval the window must cover, a larger value is stricter (fail
   closed) at the cost of refusing valid negatives that carry a short window. Consequence if the
   signed policy omits it: no assertion satisfies this item and no hold is released through it.
4. *Audience and replay.* The assertion names this deployment and provider as its audience.
   Each `assertion id` is recorded when used; an id used for another target, or presented after
   the target is dispositioned, is refused. A stale assertion that predates the attempt's
   dispatch authorization is refused.
5. *Trust key.* It verifies against a **pinned** key version that was valid at the assertion's
   timestamp and is not revoked at the decision time; the key version is recorded in the evidence
   entry. A revoked, rotated-out or unknown key refuses the assertion.

An assertion missing any element, an unverifiable one, or an ambiguous lookup response is not
this class.

Two classes are **independent** only if they come from different source systems and do not derive
from the same log or credential.

| Decision | Sufficient evidence |
| --- | --- |
| `confirmed_applied` | Exactly one of: `EV-PROVIDER-RECEIPT` matching key and payload digest and provider identity; `EV-PROVIDER-LOOKUP` matching receipt identifier, payload digest and key; a verifying `EV-PROVIDER-SIGNED` assertion that **directly states application** of that key and payload. The typed provider-origin pair extension below is reserved with an **empty** qualifying list today; consequently no pair or other fallback qualifies under this policy version. Two unrelated valid classes never substitute |
| `confirmed_not_applied` | `EV-PROVIDER-NOT-ACCEPTED` meeting the full predicate above. **No other combination.** In particular `EV-OUTBOX-STATE` plus `EV-LEDGER-FENCE`, with or without an independent reconciler, never yields `confirmed_not_applied` |
| Release of a hold | `confirmed_not_applied` **and** `EV-LEDGER-FENCE` **and** an `independent` reconciler — **except** the one bounded exception below |
| `still_unknown` | Nothing; the hold stays charged and blocked |

**Per-outcome evidence rules (resolves E1-R01 and E1-R02).**

- *Local facts cannot prove remote non-application.* After dispatch authorization has committed
  (a dispatch intent and outbox item exist), a crash can occur after the worker wrote to the
  provider and before the handoff was recorded. The outbox row and the fence look the same in the
  sent and the unsent case, and a newer lease epoch or a different, independent reconciler does
  not change what the provider did. Such an attempt stays `unknown` and charged. Independence is a
  governance condition on who may sign, never a substitute for a fact.
- *Pre-authorization is a different case.* An attempt whose dispatch-authorization transaction
  never committed (the contract's crash windows "before durable reservation" and "after
  reservation, before dispatch intent") has no intent and no outbox item. That is the **no-attempt
  disposition of section 3**, proved by positive durable store evidence, not by
  `confirmed_not_applied` through this table. If store integrity cannot be established, it is
  `unknown`.
- *Transport proof is deferred.* A reviewed transport protocol that proves non-application of a
  post-authorization attempt is a T4 matter. Until one is reviewed and ratified, none exists, and
  the only route to `confirmed_not_applied` for such an attempt is the provider predicate above.
- *Ineligible by construction.* `EV-OPERATOR-ATTESTATION` (annotation only), `EV-OUTBOX-STATE`
  and `EV-LEDGER-FENCE` can never be the evidence that satisfies a `decision` row. They may appear
  in `evidence[]` as conditions or context. Every evidence entry names the application or
  non-application assertion it makes, a stable operation, provider and request binding, and its
  provenance and integrity (digest or signature).
- *Operator decision 2 is retained, with the alternative typed (operator decision, 2026-10-17: do
  not reverse the 2026-10-14 tentative allowance).* Section 11 decision 2 said an authoritative
  provider statement "or two independent corroborating classes" may suffice. That allowance
  STANDS; it is not removed. The amendment's finding (E1-R02) is that no qualifying pair is
  currently enumerated, although individual provider classes can assert application under the
  table above; a generic "any two classes" fallback would let
  irrelevant local facts manufacture `confirmed_applied`. The alternative is therefore kept as a
  reserved, typed extension: it may be used only for an explicit list of provider-origin class
  pairs, each with a direct application assertion and tests for each pair. **That list is empty in
  this draft**, so until a pair is added by a reviewed signed-policy change no combination of
  classes satisfies the alternative and the authoritative provider statement remains the only
  route. The typing preserves the operator's allowance and its future usefulness while keeping the
  fail-closed property.

**The one bounded exception (synchronized with section 13.7 part 1).** A `non_independent`
reconciler may release an `UNKNOWN` hold **only** on a mechanically verified
`EV-PROVIDER-NOT-ACCEPTED` meeting the predicate above, **plus** a verified `EV-LEDGER-FENCE`,
with an append-only audit record. A receipt proving acceptance is evidence for applied or
consumed, never for not-applied or release. `EV-OUTBOX-STATE`, `EV-OPERATOR-ATTESTATION`, an
ambiguous lookup and any statement that is not cryptographically verifiable are insufficient for
`confirmed_not_applied` **even with** an `independent` reconciler. No automatic release, expiry or
cleanup exception exists.

### 13.3 Retention (decision 2)

**Seven years**, measured from the **later of** (a) final settlement of the hold and (b) the final
linked reconciliation or correction record. A legal, incident or active-dispute hold suspends
deletion. Ledger audit retention and reconciliation-record retention are the same period. Sensitive
payload material is **redacted at write time**; the record keeps, for the full period, the digest,
the principal and credential digests, the evidence classification, timestamps, the fencing epoch
and the disposition. This is an operational policy recommendation, not a claim about universal legal
requirements.

### 13.4 Second approval (decision 3; the conditions recorded in section 11)

- **Field.** An optional `second_approval_ref` inside the **signed** grant payload, introduced with
  the next grant schema version. Its value references a distinct approval decision record (request
  digest, approver `(issuer, subject)`, decision, UTC time).
- **Who may be a second approver.** A principal holding the `approver` role whose
  `(issuer, subject)` differs from the first approver's and from the requesting and executing
  principals, authenticated in `strict` mode, and enrolled with the independent-control
  attestation of section 2.1.
- **Where it is verified.** At **issuance**: the Phylax issuer refuses to sign when a required second
  approval record is missing, is for a different request digest, is not distinct, or is expired or
  revoked. The verifier and the consumer only check structure and consistency, because the reference
  is inside the signed payload.
- **Revocation semantics (resolves E1-R06; PROPOSED, signed-policy bound).**
  *Chosen semantics:* **grant revocation is the one mechanism that invalidates an issued grant**,
  and the issuer is required to apply it as a *cascade*: revoking or expiring an issuer-side
  referenced approval record is followed in the **same issuer-side authority commit** by
  revocation of every unconsumed grant whose `second_approval_ref` points at it. Revoking the
  enrolled approver's role or identity originates in the consumer transaction of 13.8; its durable
  request causes the issuer to invalidate the corresponding approval records and revoke dependent
  grants atomically in the issuer store. Dependent consumer dispatch stays refused while that
  request is pending. A consumer role revision never becomes an issuer commit by implication.
  Nothing is inferred from an enrollment record (13.8); the cascade is an explicit issuer action,
  recorded as grant revocations that advance the revocation version. The semantics are identified
  by the approval-policy table version of this section and recorded with each decision's
  `authority_pair`, so a change needs re-ratification. The authoritative source for grant validity
  is the issuer's revocation record; for roles it is the consumer's `authority_epoch` (13.8). The
  consumer reads revocation state at the dispatch-authorization transaction, the single
  linearization point of the durable effects contract. **OPERATOR DECISION (DECIDED
  2026-10-17: cascade):** this cascade is the chosen option. The
  alternative (approval revocation is advisory after issuance; only an explicit grant revocation
  counts) is simpler but lets a revoked approver's grant stay usable.
  Consequence if unset: approval revocation after issuance has no defined effect and T3 cannot
  ratify the issuer slice.
  Outcomes by revocation time: *before issuance* the issuer refuses to sign; *between issuance and
  reservation* the cascade has revoked the grant and reservation is refused; *between reservation
  and dispatch authorization* step 4 revalidation refuses and releases the reservation under the
  contract's rules; *after dispatch authorization commits* the in-flight rule applies (cancel is
  a request, nothing is claimed undone, subsequent operations are blocked). Commit order inside
  the consumer's transaction orders only consumer-owned facts. Issuer-owned revocations (grant,
  approval, issuer) are ordered against dispatch at the issuer, by the permit of 13.4.1, so the
  cross-store case is never decided by commit order across two stores.
- **Cascade record (operator addition, 2026-10-17).** Each issuer cascade emits a durable
  notification identifying the affected approval and grants, issuer authority version and cascade
  event. The issuer records authority facts only; it does not query consumer execution state.
  Oramasys consumes that notification idempotently and appends a linked recovery witness in its
  own store. That witness covers ALL direct and transitive subagent runs durably linked to the
  affected approval or grants, recording each run's last finished operation and last known
  in-progress operation, stable operation references and effective `authority_pair`, at a recorded
  consumer observation checkpoint. "Last known" means the latest durable record at that
  checkpoint; an absent operation record is `none_recorded`, never "nothing was in progress".
  A subagent run means an execution context with a durable run identity and a recorded spawn
  relation to a parent context; it is not a model nickname or an unaudited message. Membership
  follows the transitive closure of those recorded spawn relations from the affected authority.
  Missing parent bindings, cycles or an unavailable lineage index make enumeration incomplete.
  Enrollment, admission and execution remain different facts: a recorded child gains no authority
  merely by appearing in this recovery graph.
  Incomplete lineage enumeration is recorded as incomplete, never as an empty affected set.
  Duplicate notifications return the existing witness; later observations append linked updates.
  Issuer revocation and consumer witness capture use their respective local transactions and the
  durable outbox of section 4, never a distributed transaction. A missing or pending witness is
  visible for recovery and cannot restore authority, release a hold or prove provider outcome.
  The concrete lineage wire vocabulary, field names and storage layout must be fixed
  in the integrated schema contract before ratification; these are design requirements, not new
  wire fields or implemented records.
- **Absent** means single approval and is valid for effect classes whose policy requires one.
- **Present but invalid or inconsistent** at consumption is refused with the existing `grant.malformed`.
  An older verifier that does not know the new schema version refuses with the existing
  `grant.schema_unsupported`, so the field can never be silently ignored (fail closed; no mixed-version
  acceptance).
- **Approval policy.** A table `effect_class -> required_approvals` with value `1` or `2`, default
  `1`. At M2 every class is `1`. The first multi-approval policy is a narrow **2-of-2**: the first
  approver **and** one separately enrolled independent second approver, for explicitly high-impact
  effect classes only. `second_approval_ref` is one scalar reference, so it **cannot** express
  2-of-3, a majority or any M-of-N; a threshold above `2` is refused. General M-of-N is deferred to
  T4, which must define a versioned named-principal roster, a signed policy snapshot, a canonical
  approval-set representation (not one scalar), uniqueness, revocation and expiry rules, threshold
  validation, membership-change behaviour, and old-verifier refusal. Changing the table needs E1
  re-ratification with independent review.
- **Not in this change.** No Phylax or Oramasys code or wire change; this is specification only.

### 13.4.1 Issuer-serialized dispatch permit (PROPOSED; review finding, 2026-10-18)

Proposed wire fields, lifetime, storage, crash cases and the role reconciliation:
[C2 permit wire and role reconciliation](E1-C2-PERMIT-WIRE-AND-ROLE-RECONCILIATION-2026-10-18.md).
Proposal only; nothing in it is ratified.

**Problem.** Dispatch authorization (durable-effects contract, section 4, step 4) is one
consumer transaction. Issuer-owned revocation state lives in the issuer's store. A consumer
transaction that reads that state and then commits cannot exclude an issuer commit that lands
between the read and the commit, and no distributed transaction is allowed (section 4). The
contract's statement that this transaction is the linearization point is true only for facts the
consumer store owns. This section fixes the ordering for the rest.

**Principle.** Every fact is ordered by the one store that owns it; nothing is ordered by
reading one store and committing in another.

| Fact | Owner | Ordered against dispatch by |
| --- | --- | --- |
| Role revision, `authority_epoch`, worker ownership, fencing epoch | Consumer (Oramasys) | The dispatch-authorization transaction (as the contract says) |
| Grant, approval and issuer revocation; grant use per reservation | Issuer (Phylax) | The issuer permit below, committed in the issuer's own transaction |

**Protocol.** Steps 1 to 3 of the contract are unchanged. Step 4 becomes two ordered parts:

1. **Permit request.** After a successful reservation, the consumer asks the issuer for a
   dispatch permit bound to the grant, the request and artifact digests, the reservation
   identity and the consumer `authority_pair`.
2. **Permit decision (one issuer transaction).** The issuer checks that the grant, its approval
   chain and the issuer are not revoked and that no cascade for them is pending, and that no
   permit exists for this grant other than an identical retry. In the same transaction it records
   the permit at issuer revocation version `R_p` and returns it. A revocation committed
   earlier is seen and the permit is refused. A revocation committed later has a version above
   `R_p`. Issuer commit order, inside one store, is the only order that matters.
3. **Dispatch-authorization transaction (consumer).** In one consumer transaction, verify that
   the permit is authentic, bound to this reservation, unexpired under the clock policy and not
   already recorded; verify that every issuer cascade event with version up to `R_p` is
   acknowledged here and none is pending; revalidate the consumer-owned gates; then record the
   intent, consume the use and write the outbox item, storing the permit reference and `R_p`.

**Fail closed.** Any step that cannot be shown to hold refuses dispatch and keeps the
reservation under the contract's rules: issuer unreachable, permit missing, forged, replayed,
unbound or expired, `R_p` not yet reflected in acknowledged cascade events, or a pending cascade
request. Unavailable is reported as unavailable, never as valid (E1-T-06). Nothing is inferred
from the absence of a revocation.

**Boundary.** Permit issuance is the authorization point for issuer-owned revocation. A
revocation ordered after it (version above `R_p`) is post-authorization even if the consumer has
not yet committed step 3: the consumer applies the in-flight rule (cancellation is requested,
nothing is claimed undone, subsequent operations are blocked), and the transport's last local
check before I/O refuses an unsent intent once the acknowledgement is visible. That last check
cannot be atomic with a remote write, as the contract already states; this design narrows the
issuer-side window to a single store's commit order and does not claim to remove the in-flight
case.

**Lost permits.** A permit is single-use per reservation. If the consumer cannot show that step 3
did not commit (crash, timeout), the grant is treated as consumed (section 8.2 step 5): no second
permit is issued and the work is `unknown` until evidence says otherwise. This loses a use; it
never allows a second dispatch.

**Alternatives considered.**

| Option | Verdict |
| --- | --- |
| Distributed transaction across both stores | Rejected: forbidden by section 4 and the outbox design |
| Read revocation, then commit locally (commit order in the consumer) | Rejected: the review finding; the issuer can commit between read and commit |
| Shared local file lock held across the read and the commit (Level 0 only) | Possible at same-UID local; rejected as the contract: order lives in OS state outside the evidence, and it does not survive Level 1 |
| Short permit lifetime alone, with revocation taking effect after it | Rejected: leaves a known unsafe window and calls it a default |
| Issuer-serialized permit (this section) | Chosen: one owner, one order, evidence in the issuer log, topology independent |

**OPERATOR DECISION (PROPOSED; recommended: issuer-serialized permit).** The permit adds one
issuer operation and one recorded field on the consumer side. Consequence if unset: issuer-owned
revocation racing dispatch authorization has no defined order, and T3 cannot ratify the issuer
slice or the E1-T-27 matrix. The durable-effects contract wording of step 4 needs a matching
erratum at ratification (the transaction linearizes consumer-owned facts only); this draft does
not edit the contract. Concrete wire fields, permit lifetime and storage layout are fixed in the
integrated schema review. This is specification only: no Phylax or Oramasys code or wire change.

### 13.5 Level-0 constraint (decision 4)

M2 serving is explicitly **same-UID and local-only**. A different effective user or a non-private store
is refused by the verifier's existing ownership and private-mode checks; remote or cross-UID
publication of revocation state is unsupported and documented as such. No TTL value and no
stale-observation test exist at Level 0. Level 1 must first ratify signed observation encoding, an
authoritative clock, a freshness bound, a replay and reconciliation path, and fail-closed behaviour.

### 13.6 Manifest candidate refresh (decision 5)

The M1 qualification PR changes the Phylax `grant-authority` candidate to the exact reviewed commit
proven by the interop receipt in **all three places** it appears (the producers entry and both
`final-producers` candidate sets), re-freezes the digest, and links the receipt as evidence. The
candidate is never derived dynamically from a receipt artifact.

### 13.7 Single-operator deployments: how unknown holds clear

**The problem (independent note, 2026-10-15).** With one operator every reconciliation is
`non_independent` (13.1) and cannot release a hold except through the bounded exception below, so
holds whose evidence does not meet that predicate are recorded but not freed and run budgets stay
charged.

**Part 1 — the bounded exception (approved only as follows).** Section 13.7 part 1 is approved only
as the bounded exception to section 13.2: a `non_independent` reconciler may release an `UNKNOWN`
hold only on a mechanically verified provider `NOT_ACCEPTED` assertion bound to the operation
idempotency key, payload digest, provider timestamp, provider retention or deduplication window
and a pinned trust key, **plus** a verified ledger fence, with an append-only audit record. The exception
and its evidence predicate are named identically in 13.2; absent that synchronized amendment, the
existing independent-reconciler release rule remains controlling.

**Part 2 — the durable fix.** A second principal (section 13.8) enrolled by the operator. This draft
does not choose who it is.

**Part 3 — the backlog is visible.** The operator view and readiness report the count of unresolved
unknown holds and the age of the oldest, labelled "Outcome unknown — reconciliation required". No
automatic release, expiry or cleanup ever clears one.

### 13.8 Roles and enrollment of the second principal

- The **single operator** remains the primary approver and may execute work; any bootstrap
  reconciliation they perform is `non_independent`.
- The durable second principal is an **independently controlled human or service identity**: a
  different `(issuer, subject)`, a distinct credential digest, `strict`-mode authentication, and the
  `reconciler` role.
- That same principal **may** also hold the `second-approver` role **only if** the authorization
  policy explicitly permits it, and it must still be distinct from the requester, the executor and the
  first approver. Prefer separate, scoped role grants and separate role events even when one
  independent principal initially holds both.
- A model or agent label, or a second credential held by the same human, **never** qualifies as a
  second principal.
- Additional principals are enrolled separately and acquire **no approval power by enrollment**:
  approval authority needs an explicit policy role assignment and, from T4, a signed policy that
  sets any M-of-N threshold. A reconciler is required for non-exception reconciliation; an approver
  only when an effect class's policy requires approvals. Principals are identified by canonical
  `(issuer, subject)`, never by a display or agent label.
- **Nomination.** The operator nominates the second principal either at **configuration time** (an
  operator-owned roster entry) or at **runtime** (an operator-authenticated enrollment action). This
  draft names no one. Both paths write the same audited `principal_enrolled` record: canonical
  `(issuer, subject)`, the roles nominated, the nominating operator identity, the UTC time, the mode
  (`configuration` or `runtime`), an `enrollment_key` and the immutable policy/roster version.
- **Idempotency.** The same `enrollment_key` with the same principal, roles, mode and policy version
  returns the **original** event, so a restart or a retried runtime request never appends a
  duplicate authority fact. A changed payload under an existing key is refused. A change of roles or
  a revocation is a **new, linked** event, never an edit.
- **Effective time: two explicit authority-version layers.**
  - `configuration_policy_epoch` is an immutable, validated roster and configuration snapshot. A
    **configuration** enrollment or removal becomes effective only at the next **validated restart**,
    which starts a new `configuration_policy_epoch`. The roster is never hot-reloaded; no reload
    protocol is implied to exist.
  - `authority_epoch` is a monotonic, append-only **runtime** authority revision. A **runtime
    enrollment or runtime revocation** becomes effective atomically only when its authenticated,
    idempotent authority event **commits** and advances `authority_epoch`. It is usable for decisions
    evaluated **after** that commit, never before it, and needs no restart.
  - **Revocation** advances `authority_epoch`, is consulted at **every** authentication and
    authorization check, and blocks new authority use immediately after commit. Revoking an
    enrolled approver also commits a durable cascade request and a consumer-side restriction on
    dependent approvals and grants in that same consumer transaction. The issuer processes the
    request idempotently, committing the issuer authority change and dependent grant revocations
    together as required by 13.4. These are two local commits joined by the outbox protocol of
    section 4; there is no cross-store atomic transaction. While issuer acknowledgment or the
    affected-grant mapping is unavailable, dependent dispatch stays refused, with the pending
    cascade visible to the operator. An enrollment event alone is not forged into issuer
    revocation evidence, and an operator does not need to start a later manual cascade to close
    an authorization gap. Already-dispatched work retains the in-flight rule of 13.4.
  - Every authorization, approval, reconciliation and (later) grant issuance or consumption decision
    records the effective pair `(configuration_policy_epoch, authority_epoch)`, or one canonical
    composite derived from both.
- **Rules common to both paths.** Only the operator capability may nominate; an executor, an agent or
  the nominee itself cannot. A nomination is inert until the nominee authenticates in `strict` mode
  **and** the policy assigns the role, so a roster entry confers no approval power. A nominee that
  cannot authenticate in `strict` mode holds no role (fail closed). Every enrollment and revocation
  is audited. Distinctness from requester, executor and first approver is evaluated **per decision**,
  not once at nomination.
- No code path enrolls a principal on its own.

## 14. Grant purpose separation (PROPOSED; folded into this draft by the operator, 2026-10-15)

Proposed integrated contract for rule 3 (discriminator, versions, refusal order, test outcomes):
[C2 purpose, version and refusal contract](E1-C2-PURPOSE-VERSION-AND-REFUSAL-CONTRACT-2026-10-18.md).
It fixes no wire until reviewed and ratified by exact commit.

Two kinds of authority must never be confused, because a confusion would let a ledger recovery
release authorize a provider effect, or the reverse.

| Purpose | What it authorizes | What it must never do |
| --- | --- | --- |
| **Recovery settlement or release** | Settle or release an `unknown` hold after reconciliation (the existing adjustment grant) | Authorize, or stand in for, a provider effect |
| **Effect authority** | Dispatch of exactly one logical operation to a provider | Release, settle or adjust any hold |

**Rules.**

1. **Cross-purpose presentation is refused before mutation.** Each issuer, verifier and consumer
   rejects a grant of the wrong purpose before any authority, accounting or effect state change:
   no hold, ledger, outbox, receipt or grant-use row is created or altered, and no business-state
   digest changes. **"No mutation" means exactly that.** A sanitized refusal audit or telemetry
   record (no payload, credential or raw error text) is allowed and expected, and is not a
   violation. The refusal uses the **existing** closed refusal vocabulary, once the integrated
   contract names the codes (rule 3).
2. **Effect authority is bound** to its logical operation identifier and the exact request digest of
   that operation, and is single use (the contract's use limit of exactly one).
3. **The discriminator and the code mapping are NOT frozen by this draft (resolves E1-R08).** A
   search of the repository's canonical refusal contract
   ([compatibility refusal and HITL contract](../2026-10-09-compatibility-refusal-hitl-contract.md))
   and of the R4 reference set finds no purpose discriminator and no per-direction refusal code.
   The refusal contract defines records and gates, not a code vocabulary. The names
   `grant.malformed` and `grant.schema_unsupported` used in sections 9 and 13.4 appear in this
   repository only in this draft, so their status as an "existing" vocabulary is **unverified from
   this repository's sources**; the Phylax and Oramasys implementations are the only places that
   could define them, and this draft does not read or pin them. No code is invented here.
   Therefore the following is an explicit **pre-code prerequisite for T3**: a reviewed,
   versioned, integrated schema contract that fixes (a) the purpose discriminator and its wire
   version, (b) the exact existing refusal code for each of the two cross-purpose directions and for
   an unknown version, a missing discriminator and an ambiguous one, and (c) the canonical
   serialization rule of section 4. Until that contract is reviewed, T3 stays a NO-GO for the
   purpose-separation slice. **OPERATOR DECISION (2026-10-17, item 7):** this integrated contract
   must be reviewed and referenced by exact commit before E1 ratification. Until that prerequisite
   is met, E1 cannot be ratified, no T3 purpose-separation implementation may merge, and E1-T-23
   remains a requirement rather than an executable test.
4. **Effect authority supports ordinary bookkeeping only.** A valid effect grant may drive the
   reservation, consumption and outbox bookkeeping of its own single operation. It never confers
   recovery adjustment authority (settling, releasing or adjusting any hold), and a recovery grant
   never confers dispatch.

**Inherited, not redefined.** This draft does not restate these rules; it incorporates them by
reference to the [durable effects contract](CONTRACT-DURABLE-HITL-EFFECTS.md) so there is one
definition: the exactly-one use limit and operation-key reuse conflict (its section 2), provider-key
stability across attempts and the dispatch protocol (its section 4), the dispatch-authorization
transaction as the **revocation linearization point** (its section 4, step 4), and the crash-window
table and acceptance tests (its sections 6 and 7). Rows E1-T-23 and E1-T-24 are a **test
inventory**, not named executable tests, and they do **not** pin the discriminator or any refusal
code; section 9.1 maps them to planned tests, and the integrated schema contract of rule 3 is what
fixes the mapping.

## 15. Amendment ledger, 2026-10-16 (DRAFT; not ratified; not authorization for T3)

This section records how the amendment answers the 2026-10-15 adversarial review. It states no
verdict on the review or this text, and ratification remains the operator's alone. The good
decisions the review preserved are unchanged: recovery authority separate from effect authority;
single-use grants; mandatory non-overridable gates; no remote exactly-once claim; `unknown` as
blocking; no blind replay or automatic expiry release; same-UID verifier-only serving;
append-only corrections; two explicit authority-version layers; the bounded optional approval
quorum (2-of-2, no general M-of-N); and one neutral Core scheduler.

| Finding | Disposition | Where | Consequence if unresolved |
| --- | --- | --- | --- |
| E1-R01 | Resolved: local outbox plus fence cannot yield `confirmed_not_applied`; pre-authorization is the section 3 no-attempt case | 13.2, 3 | A post-authorization crash could free a hold the provider already applied |
| E1-R02 | Resolved: per-outcome evidence combinations; generic two-class fallback replaced by a typed, currently empty, provider-origin pair list (operator 2026-10-17: allowance retained); ineligible classes by construction | 13.2, 11 | Irrelevant local facts could manufacture `confirmed_applied` |
| E1-R03 | Resolved in text: negative finality, replay, audience, window, trust-key rules. Operator decided 2026-10-17: 60-second skew fixed in signed policy | 13.2, 13.7 | The 13.7 exception becomes a generic availability escape hatch |
| E1-R04 | Resolved in text: rehearsal versus recovery, quiesce, quarantine, rollback detection. Operator decided 2026-10-17: append-only witness outside the store file | 8 | A restore could resurrect spent authority or erase an accepted effect |
| E1-R05 | Resolved in text: record, fingerprint, atomic transaction. "Verified unused amount" disabled by default and retained (operator decided 2026-10-17) | 4, 13.2 | Two dispositions or excess freed budget under concurrency |
| E1-R06 | Operator decided 2026-10-17: issuer cascade with a linked consumer recovery witness; pending consumer dispatch refused; integrated schema still required | 13.4, 13.8 | Revoked approver's grants stay usable, or behaviour is undefined |
| E1-R07 | Resolved in text: role-composition table and independence rules. Operator decided 2026-10-17: adopt the draft attestation bar; second-principal enrollment deferred | 2, 2.1, 13.8 | Same-human identities could pass as independent |
| E1-R08 | **Explicitly deferred**: no existing canonical refusal contract in this repository names a discriminator or per-direction codes, so none is frozen and none is invented. Integrated schema contract is a pre-code prerequisite; the claim that E1-T-23/24 pin the mapping is removed; "no mutation" is defined | 14, 9 | T3 purpose-separation slice stays NO-GO; E1-T-23 is a requirement, not an executable test |
| E1-R09 | Resolved in text: owner, existing/new, planned node, negative mutation, stage for T-01 to T-24. Real node ids and proving commits are **not** supplied and need an exact-head audit; exact-head verdicts and the operator comment are still required | 9.1, 12 | Sign-off cannot be tied to evidence at an exact head |

### Historical operator question list (2026-10-16; answered in the next subsection)

1. Narrow section 11 decision 2: remove the two-independent-classes alternative for
   `confirmed_applied` (recommended).
2. Skew allowance for the `NOT_ACCEPTED` window check (13.2): small fixed value in signed policy.
3. Remove "verified unused amount" for M2 (recommended) or define its proof and conservation rule.
4. Rollback witness location (8.2): epoch and event-tip record exported outside the store file.
5. Approval-revocation semantics (13.4): issuer-applied cascade to grants (recommended) versus
   advisory approval revocation.
6. Minimum evidence for the independent-control attestation (2.1).
7. Whether the integrated schema contract (section 14) must be reviewed before E1 ratification
   (recommended) or deferred with T3 NO-GO retained.

### OPERATOR DECISIONS RECORDED 2026-10-17 (applied in one batch; still DRAFT, not ratified)

The operator answered the seven questions above. The list above is kept as the original record.

1. Two-independent-classes alternative: NOT reversed. Retained as a typed extension with an empty
   provider-origin pair list (13.2, 11).
2. Skew allowance: 60 seconds, fixed in signed policy (13.2).
3. "Verified unused amount": disabled by default and retained, not removed (4).
4. Rollback witness: an append-only `authority_epoch` and event-tip record exported outside the
   store file (8.2).
5. Approval revocation: issuer-applied cascade, and each cascade event records the last finished
   and last known in-progress operation of ALL spawned subagents (13.4). This records the operator's
   intent: the issuer event and its linked consumer recovery witness together carry those facts;
   the issuer does not own consumer execution history.
6. Independence attestation bar: the draft's bar is adopted; enrolling a second principal
   (operator item I) is deferred, tentatively to v2.5 (2.1, 13.8).
7. Integrated schema contract (section 14): reviewed before E1 ratification; otherwise T3 stays
   NO-GO.

These change the specification bytes, so earlier design and checker verdicts do not cover this
text. A Codex design verdict and a Cline checker verdict are needed at the new exact head. Nothing
here ratifies E1 or authorizes T3.

### Review harmonization, 2026-10-17 (proposed; requires review at the resulting head)

The seven recorded operator decisions are preserved. Active sections 12 and 14 now require the
integrated schema review before ratification. Sections 13.4 and 13.8 distinguish the atomic issuer
cascade from consumer enrollment revocation, its fail-closed pending state, and the separately
recorded consumer recovery witness. The typed provider-pair list remains empty. Concrete cascade
schema and proving test nodes remain prerequisites; this clarification implements no T3 code.

### Review response, 2026-10-18 (proposed; requires review at the resulting head)

A CodeRabbit review of the previous head raised four points. Three are addressed in the text:
the rollback witness record and publication barrier (8.2), the cross-store issuer-revocation
issuer-serialized dispatch permit replacing the commit-order statement (13.4.1; redesigned on
2026-10-18 after the first barrier still read before it committed), and the security-baseline
crosswalk (8.3). Tests E1-T-26 to E1-T-30 are added to 9.1 as PROPOSED names. The fourth, whether to
split this
draft or its ledger into a separate reference, is an operator decision and is not taken here: the
file stays whole until the operator decides. The seven recorded operator decisions are preserved.
These edits change the specification bytes, so a Codex design verdict and a Cline checker verdict
are again needed at the resulting head. Nothing here ratifies E1 or authorizes T3.

### Not resolved from repository sources

- No purpose discriminator or per-direction refusal code exists in the canonical refusal contract
  or the R4 reference set (section 14).
- Whether `grant.malformed` and `grant.schema_unsupported` are an existing closed vocabulary
  cannot be verified from this repository.
- The canonical-digest serialization rule is not specified here (section 4).
- Which E1-T rows are already covered by M1 tests, and their node ids and proving commits.
- Exact-head design and checker verdicts and the operator's ratification comment: none exist for
  these bytes.
- The cascade witness (13.4): conceptual run membership and E1-T-25 are specified, but concrete
  wire fields, storage layout and executable proving nodes await integrated schema review.
- The typed two-class extension (13.2): no provider-origin class pair is enumerated; the list is
  empty until a reviewed signed-policy change adds one with per-pair tests.
- The proof that would allow "verified unused amount" to be enabled (4): not defined; the feature
  stays disabled.
- Witness wire fields, publication medium and read-back mechanism (8.2), and the permit, issuer
  revocation-version and cascade-acknowledgment encoding and permit lifetime (13.4.1): requirements
  only, pending the integrated schema review. The operator decision on the permit is open.
- Exact OWASP, SSDF, CISA, OpenSSF and SLSA control identifiers in the 8.3 crosswalk.
- Whether to split the draft or its amendment ledger into a separate reference (operator).
