# Master closure and execution handoff — 2026-11-20

This supersedes scattered status summaries by linking their evidence; it does not erase historical
plans. Legacy PT/Orama and v2 remain separate implementations. No merge, live provider request,
queue cleanup, production migration or serving activation was performed.

## Published stack and merge order

1. [PT #516](https://github.com/diazMelgarejo/Perpetua-Tools/pull/516) , head
   `305c555803f75e4844624f9aaba51d3e79956aa8` : spending, memory provenance, warning repairs and
   safe pre-generation cleanup hold.
2. [PT #517](https://github.com/diazMelgarejo/Perpetua-Tools/pull/517) , replayed on #516 at
   `c527a7247550342a927ca8fa5475be7dd343706f` . Its GitHub base is #516's branch. The original tip
   is preserved at
   [backup tag](https://github.com/diazMelgarejo/Perpetua-Tools/tree/backup/pt517-before-replay-20261120)
   . Merge #516 before #517, then retarget/reconcile #517 against merged main while preserving its
   append-only records.
3. [Orama #519](https://github.com/diazMelgarejo/orama-system/pull/519) pins PT #516's exact
   tested source. Source fixes are committed; the final consumer publication includes this
   handoff.
4. Separate [v2 draft #102](https://github.com/oramasys/oramasys/pull/102) ,
   `d005090a01e0bce15f52685453dbdee55cff6da0` : bounded retry token delivery, fresh admission and
   safe legacy-store refusal. Do not stack this independent implementation on legacy code.

No additional legacy PR was created. Existing Anamnesis
[#1](https://github.com/oramasys/anamnesis/pull/1) ,
[#2](https://github.com/oramasys/anamnesis/pull/2) ,
[#3](https://github.com/oramasys/anamnesis/pull/3) had no review comments in the audit.

## Completed software and review repairs

| Area | Result and source |
| --- | --- |
| Uncertain spending | [a7f17488](https://github.com/diazMelgarejo/Perpetua-Tools/commit/a7f1748832a9176ec689677011aa1ec044927b64): durable uncertain holds survive expiry, restart and failed settlement; old reservations and retained swept entries migrate conservatively. Declared output limits enter admission; mismatched-period ceiling changes refuse. |
| Legacy JSON import | Same commit: import commits before a business operation can reject, and archival completion is retryable after commit. No silent zero-spend restart. Already-forgotten old entries cannot be reconstructed. |
| Memory provenance | [5a93cb96](https://github.com/diazMelgarejo/Perpetua-Tools/commit/5a93cb96fb4896372cc2d41bcbed0484dd5c6fba): native supersession corrects provider-error guidance and carries first-run/retry lineage. An unintended duplicate was retracted additively. |
| LAN memory replay | #517 preserves the whole #516 prefix plus original branch suffixes and native corrections. Seventeen identity records preserve effective acceptance and retirement; original candidate snapshots stay intact. [Replay ledger](https://github.com/diazMelgarejo/Perpetua-Tools/blob/c527a7247550342a927ca8fa5475be7dd343706f/docs/coordination/lan-memory-replay-2026-11-20.md). |
| Silent worker cleanup | [305c5558](https://github.com/diazMelgarejo/Perpetua-Tools/commit/305c555803f75e4844624f9aaba51d3e79956aa8): both liveness-only release routes hold. A paused-worker process regression proves same-name and different-name replacements lose. Existing worker execution and external effects remain possible; this is not generation fencing. |
| Cline spend boundary | [7946106a](https://github.com/diazMelgarejo/orama-system/commit/7946106ae3eae6bb36b02a01495d73049064bd83): governed live cycles refuse before reservation/marker/launch until aggregate output and request count are actually enforceable. Dry operation remains available. |
| Sandbox and scanner | [94814bc1](https://github.com/diazMelgarejo/orama-system/commit/94814bc10e3278b29aebace2968a1ecb2d0bc589): deny supplied and resolved paths; propagate resolution failure; execute the scanner wrapper offline to verify baseline selection and failure behavior. |
| Seven catalogue failures | [304b76fe](https://github.com/diazMelgarejo/orama-system/commit/304b76fe9a7d12c9fc387bc4beb842980ad9caf5): isolate synthetic trust-store inspection, preserve strict trust checks, and prove killed/unreaped descendants remain unknown. Use the supported Linux subreaper launcher. |
| Alert 58 | [9757e6ee](https://github.com/diazMelgarejo/orama-system/commit/9757e6eedfc15db618504154e6049d3287d4f42a): upgrade introducing TypeScript ESLint packages to 8.73.0; their minimatch is 11.0.9. Retained 3.1.5 is outside the supplied affected range. No global incompatible-major override. |
| v2 retry | Draft #102 consumes its one token-bearing retry allowance under the write lock before delivery; later retries are token-free. Actual process-death tests cover both sides of commit. Wire schema remains 1; populated legacy stores refuse migration. |

## Verification actually performed

- PT #516 exact source head: **3,720 passed, 12 skipped**, nine intentional retained-legacy
  warnings.
- Orama prepared backend source, subsequently committed through 304b76fe: **4,324 passed, 145
  skipped**, 24 subtests passed, one retained compatibility warning. Run through the Linux
  subreaper launcher. Its bounded post-suite adopted-child wait diagnostic is retained; no proof
  that every suite-created descendant was reaped is claimed.
- PT #517 focused migration, candidate presence, recall, render, search, review and episodic
  checks: **49 passed**. Native preservation gate retains all 1,592 #516 base rows and appends 27
  records. Effective accepted claim multiset remains unchanged by identity migration.
- Frontend: lint and TypeScript/Vite build passed; **53 tests passed**; dependency audit **zero
  advisories**. Node 24.22.1. The environment's pnpm wrapper tried implicit installation and
  refused its noninteractive purge; direct locked binaries and the pnpm audit CLI supplied the
  actual successful checks.
- v2 prepared source full suite: **3,121 passed, 5 skipped**; independently integrated controller
  suite: **211 passed**. Final test annotation/docstring changes preserve stripped ASTs.
- Edited legacy Python files have complete docstring coverage. Hygiene, affected Markdown lint,
  append-only validation and Aguara agent scan passed. No security baseline was weakened.

Only executed platform cases count as evidence. Skips, source candidates and bot replies are not
host qualification.

## Next executable software slices

### L1 — complete PT private authority

Owner: PT coordination runtime. Start from the accepted F decision and the
[L-1r contract ledger](https://github.com/diazMelgarejo/Perpetua-Tools/blob/305c555803f75e4844624f9aaba51d3e79956aa8/docs/coordination/l1r-contract-migration-2026-11-20.md)
.

1. Inventory every claim/release/completion/reservation writer and retained shim.
2. Implement the explicitly started primary-POSIX private authority, generation/incarnation
   checks, task/reservation CAS, receipts, audit and outbox. Gossip must never grant ownership.
   Retain manual PT operation; no automatic daemon adoption.
3. Route protected callers through the authority; refuse old/direct writers and service-down
   paths before effects. Preserve retry counts, unresolved effects and reservation identities.
4. Prove ten-contender exclusion, paused/same-name stale completion refusal, forged gossip
   refusal, crash/restart atomicity, private-store integrity and no fallback.
5. Require actual SQLite service-interpreter and POSIX/Windows evidence before promotion.

This full authority is **not implemented** by the cleanup hold. No claimant-authentication or
transfer guarantee should be inferred from it.

### L2 — restore governed live Cline only with enforcement

Owner: Orama launcher plus PT spend producer. Demonstrate a pinned client's aggregate output cap
and request-count bound; bind the actual limit to admission and verify both enforced and refused
paths. Do not invent a CLI flag, substitute direct API routing or recreate an independent ledger.
Until then, preserve the structured refusal.

### V2-1 — reservation contract and producer integration

Owner: v2 Controller with Phylax and Telos. Read the
[queue decision record](../../queue-fencing-and-recovery/decision-record.md) and
[review-synthesis amendment](../../queue-fencing-and-recovery/amendment-2026-11-16-review-synthesis.md)
before editing.

The reservation amendment still leaves owner-pinned recipient fields/arity, refusal code and
expiry policy unresolved. Schema-1 to schema-2 replay/cutover disposition is also unselected.
Prepare the migration/caller/transport ledger once those are ratified; do not guess the wire
contract or reset outstanding stage/identity state. Real producer ports are not interchangeable
with fake consumer-local crypto.

### V2-2 — actual loaded deployment identity

Owner: v2 serving/configuration runtime. Bind immutable configuration/policy generation to actual
service consumption, reload, restart and installed verifier observations. Existing loader-only
projections are not sufficient. Test source swaps, mutation, unobserved reload, missing policy and
identity mismatch with redacted evidence. Reuse R1–R3; do not claim R4/R5 from synthetic source
tests.

### Dependencies and residual diagnostics

- Anamnesis and Kungfu integration needs their real owning contracts; existing draft dependencies
  do not establish compatibility or readiness.
- The historical connect_tcp coroutine warning remains unlocalized; traced original-order
  reproduction and final full PT run did not reproduce it. Preserve the observation; never
  suppress it to claim closure.
- Retained legacy-app import warnings intentionally preserve compatibility coverage. Removal
  remains a later explicit decision.
- Investigate the bounded post-suite adopted-child wait diagnostic using test-owned process
  identities only; never signal unrelated workloads.
- PT's default branch still reports three moderate dependency alerts. Their advisory details were
  not retrieved in this slice; triage through its security workflow without guessing identities.
- GitHub denies this integration access to Orama alert 58. The source chain is repaired from the
  operator-supplied advisory; default-branch alert closure awaits merge and GitHub re-evaluation.

## Human and actual-host gates

Both POSIX and native Windows evidence are required before promotion. Collect real filesystem
ownership/ACL/access denial, process identity/child containment, SQLite locking and crash,
installation and effective configuration/policy receipts. Canary and Windows hardware execution
remain human/host steps with exact-head evidence; a Linux skip is not a substitute.

C3d-base acceptance, schema cutover decisions, independent release review (R6), operator
generation/pin approval (R7), and scoped activation (R8) are distinct records. Serving remains off
until separately activated. Do not reuse an approval against a different commit or impersonate an
operator.

## Publication and review discipline

PT was published in one atomic push: #516 fast-forward, #517 authorized replay with an exact
lease, and original-tip backup tag. Orama is published once after the PT pin is concrete. One
separate new v2 draft PR was created.

Existing inline replies are retained; missing verified replies use exactly
`@CodeRabbitAi we fixed this in commit SHA: explanation` . Review-body nitpicks and outside-diff
findings get a disposition comment linked to the fixing commit. Broad live_cycle restructuring was
declined because lifecycle ownership should remain together; demonstrated guard faults were
repaired without that rewrite.

Before further work: fetch fresh heads and comments, inspect current source, consult PT recall
quietly, then follow the contract-migration ledger. Commit logical batches; do not repeatedly push
intermediate patches or create duplicate PRs.

## Final review follow-up and current tips

This addendum supersedes the earlier tip labels while retaining their receipts.

- PT #516: `7d7cdca04900a9e68fbc23761759574b11e33deb`. Its new commit is an
  append-only correction: unresolved liability is not settled spend. Runtime
  source is unchanged from the fully tested 305c5558.
- PT #517: `6aad91dc130cb5ffd5c78f9914618d040e461f2d`. A normal merge carries
  that correction onto the published replay without another history rewrite.
- Orama #519: `1af1bf94c9d6bfd52ec4d3d34f4d9a4322279fe1` adds a paired
  real-producer/consumer regression and updates the exact PT pin. The test fails
  against old PT 32cfd077 because expiry loses the liability, then passes against
  the repaired producer. The affected pair suite passes 133 tests. It mocks the
  launcher and simulates a supported boundary; production Cline remains refused.
- V2 draft #102: `84c281a18cdc9e7be6ac26ba6ea8ec5e39a8a515`. CI exposed a
  test-only dependency on editable installation. The child now loads only its
  test helper directory; production imports remain installed. Both crash cases
  pass against a non-editable wheel with isolated Python, and all 211 controller
  tests pass. Initial failed CI evidence is retained rather than called green.

The initial one-push publication was followed by one consolidated review/CI
repair round after new feedback. No merge or activation was performed. Default
branch security-alert closure still awaits normal merge and GitHub evaluation.

## Review closure addendum — 2026-11-21

The next published source batches supersede the earlier tip labels without
erasing their evidence. PT's producer fix is
`79bfd82da15af161e60245910726a60fb63b236e`; #517 carries it through a normal merge
at `beb397d7c27ce2bb238deab91c4c56fdc6718915`. Orama's integrated code repair is
`8ccad5e32e0af1b8abfc15d686c64b39463a9022`.

The complete new review was collated before integration: 14 Orama inline
findings, its outside-diff/minor import findings and five typing/test-layout
nitpicks, plus two v2 inline findings and admission-clock feedback.

- Card receipts bind canonical content, not merely identity and delta.
  Lifecycle status, reverted outcome and the embedded receipt are excluded
  from the hash; the trace decision separately binds the reverted flag.
  Candidate JSON is validated before any marker, run/card evaluator digests
  agree, and graduation needs an independently recorded pin. Old unbound
  receipts need a new dry cycle; archived run evidence stays unchanged.
- Both wrappers forward the optional independent dry pin. The dogfood test
  creates the pin before measurement. Caller validation before measurement
  remains an obligation; receipt content binding is not measurement authenticity.
- File-path producer packages are scoped by resolved checkout. The consumer
  verifies sibling origins and restores the prior module entry after failure.
  Explicit bad roots refuse; optional bad candidates fall through. Older
  producers that mix roots fail closed. This is import ownership, not new
  claimant authentication or hot-reload generation qualification.
- Cleanup signals an owned group before reaping an exited leader. Its real
  process regression uses readiness and non-reaping exit barriers, then cleans
  owned descendants even after an assertion failure. Already-reaped leader
  identities are not signaled. The subreaper test uses the actual repo src
  directory and proves imports without inherited paths or editable installs.
- The reservation hold test uses a fixed mid-month producer clock. Typed test
  doubles, pipe/exit helpers and fixtures document their actual interfaces.
  Moving the existing evaluator-pin tests into a separate file was declined:
  shared builders are already reused; relocation adds unrelated churn.
- V2's new reader never treats an inline legacy receipt token as authority.
  Only its separately consumed one-use row permits retry disclosure. This
  does not fence old open writers or select the held cutover disposition.
  Child imports are bound to the parent package root while preserving platform
  environment variables. Configured admission freshness also uses elapsed
  monotonic time and rejects backward wall-clock steps.

Verification before publication: PT full suite **3721 passed, 12 skipped**;
Orama full integrated suite **4345 passed, 145 skipped, 24 subtests passed**;
v2 full prepared source **3127 passed, 5 skipped**, with **217 controller tests**
passing after integration. The strengthened exited-leader proof passed
separately. Python 3.13 sandbox checks remain **79 passed, 18 skipped**.
Native host/activation gates stay open; no new provider requests or serving.
