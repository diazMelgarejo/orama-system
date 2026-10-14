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
4. A reconciliation decision cannot be recorded by the credential that executed the effect it
   reconciles.
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

Rules: reuse of a key with a different target or evidence fingerprint is rejected; the original
attempt, hold and unknown event are never edited or deleted; a release is allowed only when evidence
confirms dispatch did not occur or establishes a verified unused amount **and** fencing proves no
late execution can race the adjustment; otherwise the reservation is preserved or consumed
conservatively; no timeout, stale-row cleanup, restart or missing response performs reconciliation.

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

## 10. Pinned cross-repository contract identities

Frozen identities are exact commits; nothing floats on a branch.

| Contract | Identity |
| --- | --- |
| Phylax verify-only store and lifecycle (merged) | `oramasys/phylax` `main` commit `0c3e860749b3ff8f62e102679f1f415f8acf0a61` |
| Oramasys verify-only composition and Ubuntu interop | `oramasys/oramasys` PR #43 — **TBD: exact merge commit at ratification** |
| Core production pin | `perpetua-core` `609ff0ed99cf8eca6c9ef608e764b7a25b6b9973` |
| Producer registry checkout | `diazMelgarejo/orama-system` `65ec365293c6a892cd4f978e656cfb61c0d04b9a` |

## 11. Open decisions for the operator

1. Roster and qualification of "qualified operator" and "reconciler" capabilities.
2. Allowed evidence classes and retention period for reconciliation evidence.
3. Whether any effect class needs two-person approval.
4. The Level-1 freshness bound and authoritative clock (deferred; blocks cross-user serving only).
5. Whether Phylax receives a `production_pin` in the schema-3 manifest or stays composition-only.

## 12. Reviewer assignments and ratification

| Role | Assignment (proposed) |
| --- | --- |
| Specification maker | The agent that authored this draft (it may not qualify it) |
| Independent reviewers | Codex (design and contract review), Cline (checker of evidence and links) |
| Ratifier | Operator, recorded on the review PR |

**Ratification checklist:** all `TBD` fields resolved; section 2 matrix accepted cell by cell;
section 9 inventory accepted as the T3 entry criteria; open decisions in section 11 answered or
explicitly deferred with their consequence; independent review verdicts attached at the exact head.
