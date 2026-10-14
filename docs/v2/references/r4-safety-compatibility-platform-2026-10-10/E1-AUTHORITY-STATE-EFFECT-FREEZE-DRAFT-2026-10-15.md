# E1 — authority, state and effect freeze (DRAFT for ratification)

**Status:** DRAFT. Specification only. Not ratified, not implemented, not an approval to start T3
code. Every "proposed" name, field and value below is frozen only by explicit operator
ratification recorded on the review PR. Nothing here enables grant serving, promotes a pin,
registers a required check, or changes a merge decision.

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
| **Operator principal** (authenticated human or single operator capability) | Issue or revoke a grant request; approve or deny an exception | No | Yes | Initiate reconciliation for an exact target | Ratify a specification; accept evidence |
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
| `reconciliation_key` | Unique idempotency key; a retry returns the stored record |
| `target` | Exact `run_id`, `attempt_id`, `hold_id` and fencing epoch |
| `actor` | Authenticated principal and role (section 2) |
| `evidence_source`, `evidence_digest` | What proved the disposition, and its digest |
| `observed_outcome` | `confirmed_applied`, `confirmed_not_applied`, or `still_unknown` |
| `decision` | Chosen disposition, from a closed vocabulary |
| `decided_at` | UTC timestamp from the store's authoritative clock |
| `accounting_before`, `accounting_after` | The disposition of the reservation before and after |
| `supersedes` | Optional link to an earlier record; corrections are new linked events |

**Evidence sufficiency** is defined exclusively in section 13.2. An operator attestation never
suffices; the closed evidence-class list and the release predicate there control, and this section
does not restate the decision matrix. Retention is in section 13.3.

Rules: reuse of a key with a different target or evidence fingerprint is rejected; the original
attempt, hold and unknown event are never edited or deleted; a release is permitted **only under
section 13.2's release rule**, whose conditions (evidence that dispatch did not occur or a verified
unused amount, and fencing that excludes a late execution) are necessary there, never sufficient
here; otherwise the reservation is preserved or consumed conservatively; no timeout, stale-row
cleanup, restart or missing response performs reconciliation.

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

## 8. Rollback

| Layer | Rollback |
| --- | --- |
| Capability | Switch the activation setting off; the service continues without grant-backed work |
| Code | Revert the slice's merge commit; schema is forward-only, so rollback restores from the backup taken before migration, never edits history |
| Evidence | Receipts and reconciliation records are append-only and are kept; a wrong record is superseded by a linked correction |

A rollback rehearsal (backup, migrate, restore, verify digests) is an exit criterion for T3.

## 9. Failure-test inventory (each must fail first)

The set below extends the contract's section 7 and must exist as named failing tests before T3
code merges. IDs are placeholders.

| ID | Case |
| --- | --- |
| E1-T-01 | No eligible attempt versus started-but-unsettled attempt are distinguished |
| E1-T-02 | Missing or corrupt evidence is never read as "no attempt" |
| E1-T-03 | `unknown` stays charged, cannot replay, cannot report success, cannot auto-release |
| E1-T-04 | Reconciliation: authorization, duplicate key, changed-payload reuse, append-only history |
| E1-T-05 | Late worker after fencing is recorded as late and never applied |
| E1-T-06 | Unavailable verifier, invalid grant, revoked grant remain distinct; unavailable mutates nothing |
| E1-T-07 | Duplicate and replayed effect requests resolve to one outcome |
| E1-T-08 | Partial and late completion across every crash window in the contract table |
| E1-T-09 | Authority separation: executor cannot reconcile; maker cannot qualify |
| E1-T-10 | Operator view redacts sensitive payloads and shows the two labels correctly |
| E1-T-11 | Backup, restore and redaction; migration backup restores byte-identical digests |
| E1-T-12 | Principal and credential distinctness: same principal with another credential is `non_independent`; `attest`/`off` verification is `non_independent` |
| E1-T-13 | Same-human bootstrap exception covers exactly one record, cannot release a hold, cannot yield `confirmed_not_applied`, cannot be reused |
| E1-T-14 | Evidence sufficiency matrix: attestation alone refused; a receipt proves applied, never not-applied; one authoritative provider class suffices for applied; unknown class rejected |
| E1-T-15 | Second approval: absent is valid single approval; present-but-same-principal refused at issuance; unknown wire version refused (`grant.schema_unsupported`); inconsistent with class policy refused (`grant.malformed`) |
| E1-T-16 | Retention: reconciliation records are never deleted by a restart, cleanup or backup rotation; redaction preserves digests |
| E1-T-17 | Bounded exception (13.7): a non-independent record releases only on a mechanically verified `NOT_ACCEPTED` assertion plus a verified fence; receipt, lookup-only, outbox-only, attestation and unverifiable statements are refused; unresolved count and oldest age surfaced; never auto-released |
| E1-T-18 | Retention: seven-year clock starts at the later of final settlement and the final linked record; a legal, incident or dispute hold suspends deletion; redaction at write time keeps the required digests |
| E1-T-19 | Roles: one independent principal may hold reconciler and second-approver only when policy permits, must be distinct from requester, executor and first approver, with separate scoped role events; an agent label or a second credential of the same human is never a second principal |
| E1-T-20 | Approval quorum: a policy value above `2`, or any attempt to encode 2-of-3 or a majority in `second_approval_ref`, is refused; an enrolled third principal has no approval power without an explicit signed policy |
| E1-T-21 | Nomination: only the operator capability may nominate; a nominee is inert until strict-mode authentication and a policy role; configuration and runtime nominations write the same audited record; an unauthenticatable nominee holds no role; distinctness is evaluated per decision |
| E1-T-22 | Enrollment idempotency and epoch: a restart or retry returns the original event for the same `enrollment_key` and payload; a changed payload is refused; role or revocation changes are new linked events; configuration changes are inert until a validated restart into a new policy epoch; runtime revocation is honoured at the next authentication check; every record carries its effective policy epoch |

## 10. Pinned cross-repository contract identities

Frozen identities are exact commits; nothing floats on a branch.

| Contract | Identity |
| --- | --- |
| Phylax verify-only store and lifecycle (merged) | `oramasys/phylax` `main` commit `0c3e860749b3ff8f62e102679f1f415f8acf0a61` |
| Oramasys verify-only composition and Ubuntu interop (merged with PRs #38 to #42 in one merge) | `oramasys/oramasys` `main` commit `f8898b35d5249e483b2f4a68c097957e675a0ef4` (merge of PR #43) |
| Core production pin | `perpetua-core` `609ff0ed99cf8eca6c9ef608e764b7a25b6b9973` |
| Producer registry checkout | `diazMelgarejo/orama-system` `65ec365293c6a892cd4f978e656cfb61c0d04b9a` |

## 11. Operator decisions and what remains open

**Recorded 2026-10-15 (operator, chat; recommendations reconciled with independent review, board
rows 4556 to 4558).** The operator approved the recommendations that Codex also made; one item is a
recorded disagreement.

| # | Decision | Disposition |
| --- | --- | --- |
| 1 | Executor/reconciler separation | **Decided.** Distinct principal AND distinct credential; a same-human bootstrap exception is **allowed**, audited, labelled non-independent, and cannot release a hold or confirm non-application by itself. |
| 2 | Reconciliation evidence | **Decided.** Closed class list; an attestation alone never suffices; an authoritative provider statement or two independent corroborating classes may; retention no shorter than ledger audit retention. |
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
verdicts attached at the exact head.

## 13. Specifications closing the open semantics (PROPOSED; for independent review)

These sections reuse existing types and closed vocabularies. They add **no** new credential format,
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
| `EV-PROVIDER-SIGNED` | Statement signed by a pinned provider key (any assertion) | Only for the assertion it makes |
| `EV-PROVIDER-NOT-ACCEPTED` | A signed provider `NOT_ACCEPTED` assertion; its **evidence predicate** is below | Yes, for **not-applied**, within its window |
| `EV-OUTBOX-STATE` | The dispatch outbox item was never handed off | No |
| `EV-LEDGER-FENCE` | The holder was fenced by a lease-epoch advance | No |
| `EV-OPERATOR-ATTESTATION` | An operator statement | **Never**; annotation only |

**`EV-PROVIDER-NOT-ACCEPTED` predicate (all of it, mechanically verified):** the assertion is bound
to the operation's idempotency key **and** payload digest, carries a provider timestamp and the
provider's retention or deduplication window **covering the elapsed time**, and verifies against a
**pinned** trust key. An assertion missing any element, an unverifiable one, or an ambiguous lookup
response is not this class.

Two classes are **independent** only if they come from different source systems and do not derive
from the same log or credential.

| Decision | Sufficient evidence |
| --- | --- |
| `confirmed_applied` | One authoritative provider class for applied (`EV-PROVIDER-RECEIPT`, or `EV-PROVIDER-LOOKUP` matching all three bindings, or a verifying `EV-PROVIDER-SIGNED` applied assertion); otherwise two independent non-attestation classes |
| `confirmed_not_applied` | `EV-PROVIDER-NOT-ACCEPTED`; otherwise `EV-OUTBOX-STATE` plus `EV-LEDGER-FENCE`, both requiring an independent reconciler |
| Release of a hold | `confirmed_not_applied` (or a verified unused amount) **and** `EV-LEDGER-FENCE` **and** an `independent` reconciler — **except** the one bounded exception below |
| `still_unknown` | Nothing; the hold stays charged and blocked |

**The one bounded exception (synchronized with section 13.7 part 1).** A `non_independent`
reconciler may release an `UNKNOWN` hold **only** on a mechanically verified
`EV-PROVIDER-NOT-ACCEPTED` meeting the predicate above, **plus** a verified `EV-LEDGER-FENCE`,
with an append-only audit record. A receipt proving acceptance is evidence for applied or
consumed, never for not-applied or release. `EV-OUTBOX-STATE`, `EV-OPERATOR-ATTESTATION`, an
ambiguous lookup and any statement that is not cryptographically verifiable remain insufficient
without an `independent` reconciler. No automatic release, expiry or cleanup exception exists.

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
  principals, authenticated in `strict` mode.
- **Where it is verified.** At **issuance**: the Phylax issuer refuses to sign when a required second
  approval record is missing, is for a different request digest, is not distinct, or is expired or
  revoked. The verifier and the consumer only check structure and consistency, because the reference
  is inside the signed payload.
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
- **Effective time (one fail-closed rule).** Authority is *expanded* only at a deliberate boundary and
  *reduced* immediately:
  - A **configuration** enrollment or removal becomes effective only after a **validated restart
    into a new immutable policy epoch**. The roster is never hot-reloaded; no reload protocol is
    implied to exist.
  - A **runtime enrollment** likewise takes effect only in a new policy epoch (expansion is
    epoch-gated).
  - A **runtime revocation** is resolved from the append-only authority store at **every**
    authentication check and takes effect on the next check.
  - Every authorization, approval and reconciliation record stores the **effective policy epoch** it
    was decided under.
- **Rules common to both paths.** Only the operator capability may nominate; an executor, an agent or
  the nominee itself cannot. A nomination is inert until the nominee authenticates in `strict` mode
  **and** the policy assigns the role, so a roster entry confers no approval power. A nominee that
  cannot authenticate in `strict` mode holds no role (fail closed). Every enrollment and revocation
  is audited. Distinctness from requester, executor and first approver is evaluated **per decision**,
  not once at nomination.
- No code path enrolls a principal on its own.
