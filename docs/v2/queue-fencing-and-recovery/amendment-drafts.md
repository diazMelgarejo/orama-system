# QF V2-1 — Draft Amendment Text for Q-68 and Q-68b

> **Status: DRAFT for operator review.** Nothing here is ratified, implemented, published or activated. Produced by the V2-1 read-only audit per plan section 5 row V2-1 and section 3 rows Q-68/Q-68b. Baseline facts labeled **V** were verified in this clone at head `f33d809ac77e708d925d2180c0564e5d8a262484`; **U** marks plan-only text, external-repository content, or owner decisions. All paths are repository-relative; no secrets, addresses, host names or user paths appear.

## Part 1 — Q-68 amendment draft

### 1.1 The decision Q-68 requests (plan text; U as a decision, V as plan wording)

Plan line 112: "Amend doc 68, the claim contract, envelope and migration rules together: reserved handoff, versioned recipient fields, old-client refusal. Correct the stale 'no runtime implementation' banner additively." Gate owner: Orama design owner and operator; downstream tasks V2-2 (plan line 196) and V2-3 (plan line 197).

### 1.2 Baseline being amended (V, this clone)

- The envelope declares `schema_version` exactly `"1"` (`envelope.py:29`; exact match enforced at `envelope.py:203-204`; `test_envelope.py:60-61` refuses `"2"` and integer `1`).
- The envelope field set (`envelope.py:51-71`) contains **no recipient field**; a case-insensitive search for `recipient` across the controller sources, tests and architecture docs returns no matches (V of absence). This matches plan line 58 ("schema version 1 has no recipient field").
- Handoff today is `release` (lease → `released`, task → `pending`, version +1, `store.py:462-466`) followed by a separately admitted `claim` (contract doc lines 84–86; `test_ports.py:233-249`). **There is no reservation**: between a release and the successor claim, any principal with a covering capability can claim the task, because the store refuses a claim only for non-`pending` states (`store.py:395-396`) — a released task is `pending`.
- Migration discipline: each migration is pinned by a reviewed SHA-256 digest; a new migration requires new statements and a new reviewed digest changed together; a database recording a newer schema refuses older code at open (`migrations.py:42-96,99-134`; contract doc lines 59–67).

### 1.3 Draft amendment text

**A1 — doc 68 envelope amendment (orama-system repository; the normative text is external to this clone, U for its current wording):**

> Amend §4.2: the claim-panel envelope schema version becomes `"2"`. The legacy recipient fields are re-admitted as explicitly **versioned** fields: each recipient field is declared per schema version and validated like every other field (no defaults for required fields, unknown fields refused, opaque values that must not look like topology). A request that declares schema_version `"1"` after the bump is **refused with a determinate 400 refusal**; old clients are refused, not negotiated down. The version bump and the recipient fields land in the same amendment; no intermediate version exists.

*Open point (U):* the authoritative names and arity of the legacy recipient fields live in the legacy authenticated-queue envelope and doc 69 §7 (external to this clone). The design owner pins them; this draft uses `recipient_*` as placeholders.

**A2 — doc 68 release/handoff amendment (reserved handoff):**

> Amend §4.3: reserved handoff stays `release` followed by a separately admitted `claim`. The `release` atomically establishes a **versioned reservation** binding the released task to the intended successor (and to the task version at which the release occurred) so that, in the gap before the successor's claim, an unrelated principal cannot take the task. The reservation is refused or invalidated by the same compare-and-set version discipline as every other transition; a stale reservation cannot mutate. Forced takeover remains controller-only expiry and recovery (IC-18); no client operation takes over a reserved task.

**A3 — doc 68 status-banner correction (additive):**

> Add, do not rewrite: the earlier register statement that no runtime implementation exists is superseded by this note. A partial runtime implementation of the claim store, request envelope, refusal vocabulary, Telos/Phylax ports with deny-all defaults, transactional outbox and opt-in expiry worker exists in the oramasys repository under `src/orama/orchestrator_controller/`; it is not reviewed, not deployed, not activated, and no serving path composes it. The prior wording is preserved as history; this note is added, nothing is rewritten.

*Scoping note (U):* the stale "no runtime implementation" banner itself lives in the orama-system doc 68, which is not in this clone; its exact current wording could not be verified here. What is verifiable here is the corrected state: the in-repo status lines already say "partial implementation" and are accurate at this head (`docs/architecture/orchestrator-controller-invariants.md:3`; contract doc lines 3–6; `ARCHITECTURE.md:28,85`) — V.

**A4 — claim contract amendment (this repository):**

> Bump the executable contract to schema version 2 together with doc 68: (a) the envelope field table gains the versioned recipient fields and the new schema version; (b) a new refusal code for old-client refusal is added to the closed vocabulary — proposal: `envelope.schema_unsupported`, status 400 (alternative: reuse `envelope.invalid`; decision point for the design owner); (c) the state machine gains the versioned reservation on `release` (new fields via migration version 2, below); (d) existing idempotency receipts, which store the full receipt including the raw lease token, are handled per the option chosen in Q-68b; (e) the IC-1…IC-29 mapping table in §9 is updated and remains complete.

**A5 — envelope code amendment (this repository):**

> `SCHEMA_VERSION` becomes `"2"`; the versioned recipient fields join `_REQUIRED` or `_OPTIONAL` per the design; the unknown-field refusal (`envelope.py:197-199`), the projection-equality check (`envelope.py:184-189`) and the canonical request digest (`envelope.py:257-274`) must cover the new fields so that claim-scope idempotency (IC-12/IC-13) keeps separating identical from changed content.

**A6 — migration rules amendment (this repository):**

> Add `Migration(version=2, name="claim_store_v2_reservations", …)` with additive statements (new reservation fields; no destructive change) and pin its reviewed digest in `REVIEWED_MIGRATION_DIGESTS` in the same reviewed diff (`migrations.py:94-96`). Fresh stores are created at v2; existing stores migrate at open via `apply_migrations`; a database recording v2 refuses older code at open (`migrations.py:112-113`) — this is the store-layer counterpart of old-client refusal. Rollback rule unchanged: never delete active or `reconcile` data to make rollback pass.

**A7 — tests amendment (this repository):**

> Envelope tests for the new and the old schema version; old client denied with the new refusal; reservation creation on release, reservation refusal for an unrelated principal, reservation expiry and refusal policy; replay matrix across versions; the §9 IC mapping table stays complete (plan line 229). Existing suites that must stay green: `test_envelope.py`, `test_store.py`, `test_migrations.py`, `test_conformance.py`.

### 1.4 Explicitly out of Q-68 (per plan)

- `reconcile` resolution tooling stays out of this slice; no operator bypass returns a `reconcile` task to `pending` (plan lines 156–157; the store has no such transition today — V of absence).
- `verified_at` and any maximum age enter only through Q-AGE, checked inside the write transaction before idempotency or task lookup (plan lines 154–155).
- Forced takeover stays controller-only expiry and recovery (plan line 151).

## Part 2 — Q-68b amendment draft

### 2.1 The decision Q-68b requests (plan text; U as a decision, V as plan wording)

Plan line 113: "Replay delivery: A keeps authorized replay returning the token (default, F). B returns the receipt without the token and holds a lost-response lease for conservative recovery (hardening, A)". Gate: Q-D23 (plan line 296: "Q-68b and slice A stay closed until the answer"); owner decision; downstream task V2-2 (plan line 196: "replay rule per Q-68b"). Plan §2.3 (lines 87–91) supplies the reasoning: token-free replay mainly protects against a stolen database or a hostile channel, and it makes the canonical honest failure — a lost response — cost a full lease TTL; so the F slice keeps authorized replay as today, and token-free delivery becomes Q-68b with the cost stated.

### 2.2 Baseline behavior today (V, this clone)

- An identical claim replay (same claim-scope key, same request digest) returns the original committed receipt **including the raw lease token**, marked `replayed` (`store.py:111-132,362-370,381-386`; `test_store.py:186`; contract doc lines 128–131).
- Every replay re-passes the Telos transport port and the Phylax capability port first (`service.py:58-65`; `test_ports.py:222`); a captured request alone does not carry a channel attestation (plan lines 82–86).
- The token is stored only as a SHA-256 digest in `leases` (`store.py:408-411`) and never enters `audit` or `outbox` (`outbox.py:27-38`; `test_outbox.py:90-98`; `test_ports.py:266-285`); the receipt JSON holding the raw token lives only in the private idempotency row of the controller-owned 0600 database (`migrations.py:72-75`; `test_migrations.py:40-44`).

### 2.3 Draft decision text

> **Q-68b — replay delivery for an idempotent claim whose first response was lost.**
> **Option A (default, F slice).** Keep authorized replay as implemented: for an identical captured request that re-passes the transport and capability ports, the store rebuilds the stored receipt, including the raw lease token, and returns it marked `replayed`. No envelope, schema or store change.
> **Option B (optional hardening, A slice; gated on Q-D23).** Return the replayed receipt **without the token** and hold a **lost-response lease** for conservative recovery: the controller records that a claim's first response was never delivered, so expiry recovery holds rather than reissues the work. **Stated cost: a lost response consumes a full lease TTL** before the controller clock rule expires the lease and recovery decides its disposition. Token-free delivery must also answer the D23 questions for a stolen database or a hostile channel.
> **Applies to both options.** A byte-identical captured request arriving from another verified channel yields no token and no new lease unless it passes full admission (transport, capability, store), and a cross-channel replay regression test is required whichever option is chosen (plan lines 91, 152–153, 231).

### 2.4 Implementation notes per option (draft)

- **Option A:** no change to `ClaimReceipt.to_json`/`from_json` (`store.py:111-132`); existing idempotency receipts remain valid; the only work is the cross-channel regression test.
- **Option B:** the idempotency row would store the receipt without the token (or redact it on rebuild); a lost-response lease records that the first response was never delivered so recovery holds instead of reissuing (plan line 113); an existing-store migration is needed because old receipts already contain a raw token — "old receipts handled per the chosen option" (plan line 228); the lease-TTL consumption is the accepted cost.
- **Either option keeps:** replay refusal for key reuse with a different digest (`store.py:368-369`); refusal of a revoked principal's read-back (`test_ports.py:222`); `replayed` marking of rebuilt receipts (`store.py:132`).

### 2.5 Cross-channel replay regression test (applies to both options; plan lines 91, 152–153, 231)

Draft sketch (not implemented here; no tests were run or added during this audit): submit a claim through a verified channel; capture the byte-identical request; replay it through a different verified channel, or with no channel attestation: expect either full admission (and then the identical receipt per the chosen option) or `401 transport.unverified` — never a token without full admission and never a second lease. Related existing evidence: `test_ports.py:222` (a revoked principal cannot read back a replay) and `test_conformance.py:398` (a lost claim response retried by replay yields one lease and the same token — same channel). The dedicated cross-channel test is absent today (V of absence) and is the proving test named in the plan's Transport row.

### 2.6 Open points for the operator (U)

1. Confirm option A as the default or authorize option B; confirm the stated cost (a lost response consumes a full lease TTL) is accepted.
2. Pin the authoritative recipient field names and the old-client refusal code for Q-68 from the legacy envelope definition (external to this clone).
3. Confirm the additive banner wording for doc 68 with the Orama design owner.
4. Record the answers in the D-0 decision record per plan section 5 row D-0 and section 12 (plan lines 189, 335–337).

---

## Deliverable verdicts (one line each)

- **qf-v2-1-audit-report.md:** PASS — audited revision recorded; 28 of 29 ICs mapped to source and tests (IC-20 unlocatable, owner-held under C3d); replay, migration, port and composition findings match the plan; no conflicts.
- **qf-v2-1-ledger-6-2.md:** PASS — all six section 6.2 old-contract rows verified against source with no deviation; new-contract items correctly absent (V of absence).
- **qf-v2-1-q68-q68b-amendment-draft.md:** DRAFT COMPLETE — amendment text for Q-68 (reserved handoff, versioned recipient fields, old-client refusal, schema bump, additive banner correction) and Q-68b (option A default vs option B with the stated lease-TTL cost, cross-channel regression test for both) is drafted for operator review; nothing ratified.