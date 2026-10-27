# Activation, serving, T3–T5 and remote-autonomy plan

**Date:** 2026-10-25 (Asia/Manila)

**Status:** planning and rehearsal only — no activation, serving, remote autonomy, push, merge, or
ref movement was performed.

**Normative design inputs:** Orama ADR 71; Task 6 plan (Doc 72); R4 contracts for durable
effects, foreign-provider transport, and durable continuation; E1 ratification/addendum material;
M1 generation-2 receipt.

**Primary safety rule:** a merged PR, a green CI run, a ratified specification, or a qualified
M1 evidence run is **not** an authorization to enable serving or autonomy.

## 1. Executive decision

Proceed in four separately authorized capability releases:

1. **Activation readiness:** prove that an installed composition can remain fail-closed and
   identify its exact producer/consumer inputs.
2. **Serving:** expose verification/readiness only, without signing secrets, automatic recovery,
   effects, provider transport, or continuation.
3. **T3–T5:** deliver durable effects, one constrained transport cell, then true continuation
   as separate vertical slices.
4. **Remote autonomy:** add only after the preceding slices qualify and an operator separately
   activates the C4 policy level with the required isolation evidence.

Each release has its own contract freeze, implementation PRs, candidate qualification,
post-merge qualification, operator decision, and reversible disablement path. No release
implicitly enables the next one.

## 2. Current evidence and boundaries

| Fact | Evidence / interpretation | Operational consequence |
| --- | --- | --- |
| M1 generation-2 evidence run passed and was operator accepted | `m1-gen2-qualification-evidence-receipt-2026-10-18.md` records a 3.11/3.12 sealed run, not activation. | It supports the frozen installed-set evidence only. |
| E1 Parts 1–2 are ratified and later Part-3 acceptance material exists | E1 documents fix wire/refusal rules. | Treat these as contract authority; still require code-level acceptance at exact heads. |
| `ORAMA_GRANT_SERVING` is fail-closed when unset | E1 addendum. | Unset is the safe default and must remain so until the serving release decision. |
| ADR 71 is approved policy, not deployed capability | It allocates Phylax and Oramasys ownership and specifies C4 Level 0/1 constraints. | No key, account, issuer, or automation setup follows merely from ADR approval. |
| T3 effects, T4 provider transport, T5 continuation remain separate contracts | R4 reference set. | Do not “test through” a live effect/remote request before its own release gate. |

## 3. No-push three-way rehearsal

### Method

On 2026-10-25, each committed candidate was merged into a fresh disposable worktree created from
the then-live `origin/main`, using `git merge --no-commit --no-ff`. The merge was aborted and the
disposable worktree removed. No source working tree, local branch, remote ref, or GitHub PR was
changed.

This is a real three-way rehearsal: **candidate base → candidate** is compared with
**candidate base → live main**, then Git computes the merge result. It is more trustworthy than
ahead/behind counts, which are not authoritative across the repository’s prior history rewrites.

| Repository | Candidate base | Candidate head | Live `main` examined | Rehearsal result | Decision |
| --- | --- | --- | --- | --- | --- |
| `diazMelgarejo/orama-system` | `c04b50ad4e58` | `372f2ea13024` | `6281e969353f` | Conflict in `ownership-registry.json`. That canonical path changed after the candidate. | Do **not** revive or merge. Preserve commits `97370cf6`, `372f2ea1` as historical candidate evidence; derive any still-needed receipt delta from today’s registry. |
| `oramasys/oramasys` | `08495af459f8` | `d5df4049f4f0` | `68f063017b52` | Conflicts in CI manifests, pins, registry fixture, observer, and oracle tests; every candidate path has later live changes. | Do **not** revive or merge. Live admitted-observation delivery and current M1/E1 work supersede its scope. Any gap must begin as a fresh, narrowly scoped PR from live `main`. |

### Other local material

| Location | State | Merge decision |
| --- | --- | --- |
| `core-rev3-execution` | Uncommitted edits to `engine.py` and `observer.py`, plus untracked delivery/test files; no immutable candidate commit exists. | Not mergeable or reviewable as a candidate. Preserve without staging; extract a fresh proposal only if a current-gap review shows unique behavior. |
| `oramasys-rev3-execution` | Two untracked October planning files. | Documentation scratch only; no merge operation exists. Compare content with current canonical plans before reusing any section. |
| earlier P0/R4 repair worktrees | Historical branches, several with unrelated working-tree deletions. | Do not inspect via destructive cleanup, rebase, reset, or branch revival. Use current `main` records and tree-twin/history protocol if a specific historical fact is needed. |

### Rehearsal conclusion

The correct continuation is **not** to solve the conflicts in place. It is to preserve the candidate
evidence, write an additive successor receipt if the historical finding still matters, and implement
any current requirement against the latest pinned contract. This avoids overwriting newer M1/E1
composition and avoids reintroducing an obsolete Core pin.

## 4. Release 0 — activation-readiness baseline

**Goal:** prove exactly what can be installed and composed while all active powers remain denied.

### Work

1. Create a dated baseline receipt with the exact `main` SHAs, producer pins, registry digest,
   manifest digest, and required-check result for Core, Oramasys, Phylax, Telos, Agate, and Orama.
2. Reconcile the E1 ratification records with current producer/consumer code. Record any pending
   Part-3 section separately; no ambiguous “ratified” label may substitute for an exact head and
   test matrix.
3. Define a single runtime capability record with independent default-deny bits for `serving`,
   `effects`, `transport`, `continuation`, and `autonomous_settlement`. It must be signed/configured
   by the owning control plane, observable, and included in readiness output.
4. Add a startup refusal test for every invalid combination, especially serving without a
   verify-only authority, effects without a valid permit verifier, transport without Telos policy,
   and autonomy without the C4 activation record.
5. Declare the public error vocabulary and stable correlation/receipt fields before any endpoint is
   exposed. Do not leak grant identifiers, keys, paths, or policy internals.

### Acceptance gate

- Fresh non-editable install on the Python qualification matrix: the repository CI matrix
  (3.11, 3.12, 3.13) is the required set. The v2 documents state a 3.11+ policy, so 3.10, which
  the root package still declares via `requires-python = ">=3.10"`, is not qualified by this plan
  and must be reconciled with that declaration before any 3.10 claim is made. The M1 receipt
  covers 3.11 and 3.12 only; 3.13 needs its own qualification evidence.
- Runtime source/pin assertion and registry-digest assertion.
- Every capability is disabled by default; every forbidden combination refuses before dispatch.
- Independent review confirms no signing seed, issuer-write capability, or P5 material is reachable
  from the web-serving process.

## 5. Release 1 — verification-only serving

**Goal:** provide a useful, observable local serving surface without granting a power to mutate
issuer state, settle unknown holds, run effects, or contact a provider.

### Architecture

- **Phylax:** read-only public-key, issued-grant-index, and revocation verifier. It owns public
  verification and revocation freshness semantics.
- **Oramasys:** authenticated request handling, admission composition, response shaping, and durable
  audit references. It never signs in the web process.
- **Telos:** endpoint exposure, authenticated local transport, TLS/bearer policy where applicable,
  network allowlist, and stable `503` readiness code.
- **Phylax monitorability:** receives redacted delivery/decision evidence. A monitoring failure must
  not turn into an effect permission.

### Work packages

1. Implement the verifier-only process opening: SQLite/read model is read-only; startup neither
   creates nor migrates authority state.
2. Add `/healthz`, `/readyz`, and a narrowly scoped verification/readiness route. Readiness must
   separately report verifier-ready, issuer-ready, serving-enabled, and autonomous-policy-ready; it
   must not infer one from another. Map each route to the kernel security contracts in
   [01-kernel-spec.md](../01-kernel-spec.md) §6b before Wave 1 qualification: the `Capability` it
   requires (`public` for the health probes, `read` for verification), the `AuthContext` it
   consumes, the `SecurityDecision` and `AuditEvent` it emits, and the `EndpointPolicy` that
   governs exposure. The Wave 1 gate also records the control mapping to the baseline in
   [24-security-first-platform.md](../24-security-first-platform.md) (OWASP, NIST SSDF, CISA Secure
   by Design, OpenSSF, SLSA).
3. Bind feature enablement to an explicit operator record. `ORAMA_GRANT_SERVING` remains
   absent/unset until the approval is recorded and exact binary/config digests match.
4. Exercise denial paths: stale revocation, unknown key, malformed grant, revoked grant, missing
   capability record, unauthorized caller, and unavailable verifier all fail closed with a stable
   public response.
5. Run a real process test under the serving identity proving it cannot read seed files or write
   authority state.

### Acceptance gate

The first serving release allows only verification/readiness. It has no recovery command, no grant
issuance, no StepLedger adjustment, no provider request, and no effect driver. Rollback is setting
serving disabled and draining requests; it does not delete receipts, holds, revocations, or quota
records.

## 6. Release 2 — T3 durable HITL effects

**Goal:** make effects possible only through a durable, user-authorized, idempotent state machine.

### Contract freeze before code

Freeze the effect-attempt identity, approval binding, reservation/fencing epoch, outbox item,
dispatch receipt, terminal taxonomy, redaction envelope, and replay rules. The owner map is fixed:

| Owner | T3 authority |
| --- | --- |
| Core | neutral scheduler mechanics and lifecycle seams; no policy or provider-specific effect code |
| Phylax | approval/grant verification, revocation, evidence integrity and monitoring contract |
| Oramasys | effect-attempt ledger, durable reservation, idempotency/fencing enforcement, composition |
| Telos | endpoint/egress policy and health constraints |
| Agate | hardware eligibility evidence only where the requested effect requires it |

### Implementation sequence

1. **State first:** reuse the ratified E1 outcome vocabulary (`confirmed`, `failed`, `unknown`)
   and the existing atomic intent/use/outbox transaction — do not freeze a second T3 state machine.
   The roadmap labels `prepared → authorized → dispatched → acknowledged/unknown/refused` remain
   conceptual only (see [RELEASE12-IMPLEMENTATION-ROUND-2026-10-26.md](RELEASE12-IMPLEMENTATION-ROUND-2026-10-26.md)).
   Every externally visible effect still uses a durable idempotency key and a fencing epoch. The
   rule set below is the plan's wording of the contract freeze
   [§4](r0-r2-contract-freeze-2026-10-26.md#4-terminal-taxonomy-mapping) and must not differ from it:
   - Pre-dispatch refusal stays required: revocation or a cascade that blocks work before the
     outbox send writes a terminal refusal record (`AuthorizationRefused`, the
     `authorization_refused` disposition) for that attempt identity under the same idempotency
     key, in the authorization transaction. The record is an append-only overlay that fences the
     attempt; the reservation and outbox row are kept.
   - A replay by the bound principal returns that same refusal (stored code and opaque
     `receipt_ref`), so the attempt can neither stay pending nor dispatch. A caller that is not the
     bound principal, or an unknown `attempt_id`, gets the identical HTTP 401
     `deny.unauthorized_caller` body with no `receipt_ref`; neither caller sees the stored refusal.
   - No terminal refusal is written after the send marker (`send_started = 1`). Stored `failed` is
     only a post-dispatch target refusal (R4 `confirmed_not_applied`).
   - After a send may have started, unsettled work remains `unknown`; an in-doubt dispatch is
     answered HTTP 503 `deny.verifier_unavailable` with its `receipt_ref`, never a refusal record.
   - An unauthenticated caller on an exposed route gets HTTP 401 `deny.unauthorized_caller` in the
     contract body.
   - There is no separate disabled-serving code, and `deny.grant_conflict` (409) is the public
     answer only to a definitive, non-retryable ledger consumption conflict on `/adjustments`.
2. **Authorization second:** verify the bound approval/permit at the final execution boundary.
   Revocation and cascades refuse future dispatch, including attempts not yet dispatched (the
   pre-dispatch refusal above); already uncertain work becomes an explicit `unknown` disposition,
   never a silent rollback.

   The send path is single: the attempt store's final-boundary send is the only way an effect is
   sent. The send-time checks (expiry, revocation, divergence and quarantine state, clock and
   anchor checks, consumer lease validation) live in one shared helper called by every send entry
   point; a composer verifies and binds into that path and never sends around it. The fencing
   epoch (store-owned monotonic mark stamped on the attempt) and the lease epoch (the consumer's
   lease generation, a verified grant fact) are distinct and neither implies the other; see the
   contract freeze [§5](r0-r2-contract-freeze-2026-10-26.md#5-release-2-frozen-items).
3. **Driver third:** introduce one local, inert/dry-run effect driver. It accepts a sealed command
   envelope and returns a receipt; it cannot execute arbitrary shell text.
4. **HITL fourth:** require explicit, scoped human approval for the concrete attempt identity.
   UI/API confirmation cannot be reused for a changed payload, principal, target, epoch, or expiry.
5. **Observation and recovery:** redacted receipts, bounded delivery, crash recovery, and
   operator-visible reconciliation arrive with the first real driver—not as later optional
   hardening.

### Required adversarial tests

- double submit, duplicate delivery, stale epoch, post-approval payload substitution, revocation
  race, timeout after dispatch, process crash at every durable boundary, replay after restart, and
  concurrent reservations;
- no effect without a matching durable authorization; no second effect for the same attempt
  identity;
- unknown is preserved when outcome cannot be proven; manual reconciliation is authenticated,
  append-only, scoped, expiring, and single-use.

### T3 release gate

One driver, one effect class, one deployment cell, explicit operator enablement, and a tested
emergency stop. No provider transport or remote autonomy rides in this release.

## 7. Release 3 — T4 one-cell foreign-provider transport

**Goal:** add a single provider transport cell without weakening T3 authorization or Telos egress
controls.

### Work

1. Freeze a provider-neutral request/response/error envelope and a compatibility matrix. Preserve
   the external framework behavior required by the LangChain/LangGraph compatibility contract; do
   not silently fall back to another provider.
2. Telos enforces exact allowlists, canonical URL parsing, TLS for bearer-bearing requests,
   proxy/environment handling (`trust_env=False` where the policy requires), request size limits,
   deadlines, retry classification, and circuit state. The existing redirect contract
   (`32-agentic-security-controls.md`) binds the T4 provider transport: redirects are denied by
   default, every hop is revalidated if redirects are ever enabled, and credentials are never
   forwarded to a rejected address. The qualification tests assert each of the three behaviors.
3. Bind each remote request to a T3 effect attempt, admission evidence, cost/time reservation, and
   redacted telemetry receipt.
4. Begin in **shadow/dry-run** mode: construct and validate requests, but do not send. Then enable
   one pre-approved provider/model/endpoint cell only.
5. Limit concurrency and spend using durable holds. A timeout or lost response is an unknown remote
   outcome; it cannot be retried as a new effect without idempotency evidence.

### Qualification

- deterministic fake-provider and fault-injection suite;
- integration test against an explicitly approved non-production endpoint or controlled test double;
- credential non-disclosure tests, SSRF/redirect tests (default denial, per-hop revalidation, and
  no credential forwarding to a rejected address), response-size and malformed-wire tests,
  idempotency tests, and fallback-refusal tests;
- staged operator review before each expansion of the provider/model/endpoint allowlist.

## 8. Release 4 — T5 durable continuation

**Goal:** resume a graph safely from a durable checkpoint without re-running or duplicating a
dispatched effect.

### Invariants

- A checkpoint is not “restart from `START` with loaded state.” It has a versioned graph identity,
  canonical state digest, frontier/scheduler position, completed-attempt receipts, pending attempts,
  epoch, and compatibility/version policy.
- Any attempt that may have crossed an effect/transport boundary is reconciled before resumption.
- The engine never guesses that it did not run.
- State-schema, graph-definition, reducer, or plugin incompatibility refuses continuation and
  requires an explicit migration/replay procedure.
- The default continuation policy is conservative: restart only from a known safe boundary; retain
  the old checkpoint and receipt chain.

### Implementation sequence

1. Define `DurableCheckpointV1` and migration/refusal rules; add canonical serialization tests.
2. Persist checkpoints only after the corresponding ledger/effect state is durably settled or
   conservatively marked unknown.
3. Add recovery discovery and operator-visible resume planning; this phase plans only and writes no
   new effects.
4. Add one controlled resume path with a crash matrix covering checkpoint write, dispatch intent,
   external acknowledgement, settlement, and post-settlement checkpoint publication.
5. Qualify compatible resumption, refusal on every incompatibility class, and
   exactly-once/no-duplicate-effect behavior.

### T5 release gate

T5 may be enabled only for the graph/profile/schema set explicitly represented in the qualification
receipt. It is neither a blanket retry service nor remote autonomy.

## 9. Release 5 — remote autonomy (C4)

**Goal:** allow bounded autonomous settlement only after it is demonstrably safer than the manual
alternative for the exact narrow case.

### Level 0: explicit, bounded same-user policy

Implement only after serving, T3, T4 (if remote transport is in scope), and T5 relevant recovery
tests are qualified:

- explicit operator command starts recovery; a passive UNKNOWN hold never mints a grant;
- Phylax owns issuance, public registry, revocation, quota, and immutable key tier; Oramasys owns
  recovery intent and transactional consumption;
- fixed `settle`/`steps` semantics, 1–3 units per grant, 900-second lifetime, six accepted
  autonomous grants per principal per rolling hour;
- canonical recovery identity binds principal, store/run/hold, fencing epochs, units, action,
  evidence digest, issuance/expiry, policy revision, and single-use grant ID;
- exact retry returns the stored grant; changed payload refuses; expiry/revocation/consumption do
  not refund quota;
- legacy NULL-owner holds refuse autonomous recovery. There is no automatic owner backfill.

### Level 1: separately reviewed isolated issuer

Level 1 cannot be activated by UID, file-mode, account-name, config flag, PR merge, or test success
alone. Require all ADR-71 evidence:

1. isolated signer account and authenticated run-scoped issuer invocation;
2. serving/agent identities demonstrably cannot read seeds or issuer-write state;
3. independently reviewed local verifier transport or signed public-state publication with
   revocation freshness proof;
4. seed-free server startup, effective-access-denial, and read-only database refusal tests from the
   real serving identity;
5. versioned deployment-policy activation record with operator approval.

Only then may the policy raise the autonomous issuance ceiling to twelve accepted grants/hour.
Level 1 changes only the ceiling (six to twelve): the bucket stays per principal over a rolling
hour, and every Level 0 rule (single-use, retry, payload binding, expiry, revocation, consumption,
no quota refund) remains in force. Key rotation and policy change cannot reset the quota bucket.

### Remote-autonomy abort conditions

Immediately disable new autonomous issuance (while preserving evidence and allowing safe
verification) on signer-isolation failure, revocation freshness breach, quota inconsistency, unknown
issuer state, unexpected transport capability, audit-chain failure, or unqualified binary/config
drift. An abort never erases holds or fabricates their outcome.

## 10. Delivery order, PR shape, and gates

| Wave | Deliverable | Repositories | Merge condition |
| --- | --- | --- | --- |
| 0 | Baseline/activation-readiness receipt and capability-record contract | Orama docs, Phylax/Oramasys as needed | Exact heads and fresh-install proof reviewed |
| 1 | Verify-only authority and serving composition | Phylax → Oramasys → Telos, with Orama receipt | Seed-free and write-refusal E2E proof |
| 2 | T3 durable effect state and one inert driver | Core seam if required; Phylax → Oramasys → Telos | State-machine, crash, idempotency, and HITL tests |
| 3 | T4 shadow then one provider cell | Telos → Oramasys, Core only for neutral interface | Fault injection and egress/credential evidence |
| 4 | T5 checkpoint and conservative resume | Core → Oramasys → Phylax evidence | Crash matrix and no-duplicate-effect evidence |
| 5 | C4 Level 0 recovery | Phylax → Oramasys → Orama receipt | Real issuance-to-consumption flow plus operator activation |
| 6 | C4 Level 1 isolation upgrade | deployment material + Phylax/Oramasys evidence | Separate operator decision on isolation evidence |

For every wave: candidate pins first; qualify the exact candidate set; merge producer before
consumer; repin consumer to the producer’s actual merge SHA; rerun post-merge qualification; publish
one dated successor receipt. One PR per repository at a time, one final non-force push per branch
after all local checks, and no force push, branch deletion, or history rewrite.

## 11. Universal qualification checklist

- [ ] Exact source, wheel, registry, manifest, policy, and configuration digests recorded.
- [ ] Fresh environment proof on the supported Python matrix; no editable-install substitution.
- [ ] Required collection, targeted regression, full affected suite, and fault/crash scenarios pass.
- [ ] Producer/consumer interoperability runs both directions where a shared wire exists.
- [ ] Red-team refusals prove defaults, expiry, revocation, stale epochs, retries, malformed input,
  and unavailable dependency behavior.
- [ ] Serving identity access audit proves least privilege and absence of secrets.
- [ ] Rollback stops new work without deleting evidence or invalidating already issued receipts.
- [ ] Two independent reviews at final candidate heads; post-merge rerun at actual merged pins.
- [ ] Operator decision explicitly names the capability, scope, expiry/review date, and disablement
  control.

## 12. Immediate next action

Do **not** merge either October candidate. Start Wave 0 with a current-head reconciliation review
that produces the activation-readiness receipt and a precise capability-record schema. That smallest
next step resolves the only prerequisite common to serving, T3, T4, T5, and autonomy while leaving
every powerful capability fail-closed.

## 13. Assumptions ledger

- The current live heads examined in the rehearsal were Core `6d75cfe08af9`, Oramasys
  `68f063017b52`, Orama `6281e969353f`, and Perpetua-Tools `cd82cc76a5e4`.
- This plan does not assume branch protection status, deployed credentials, local account isolation,
  public network exposure, or a live provider account.
- “Remote autonomy” here means the ADR-71 bounded recovery/settlement capability, not permission for
  arbitrary remote commands, autonomous code changes, autonomous pushes, or unbounded provider
  spend.
- Any material change to a frozen wire, state machine, threat model, or deployment identity returns
  the affected wave to contract review.
