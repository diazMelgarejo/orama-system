# P0 through T2 — revision 3 synthesis (review + recombination)

**Status:** proposal for operator review. Planning only: no pin, registry, schema, code,
publication or merge is authorized by this document. Base: REV2. Inputs: the Codex dual-voice
review, REV2, and live checks of Orama, Oramasys and Core `main` on 2026-10-10.

AFRP: Type C | Level Expert | Mode 2. Scope: choose the smallest coherent design that
satisfies the review's real findings and REV2's corrections.

## 1. Verified facts that change the plan (live, not from either document)

| Fact | Evidence | Consequence |
| --- | --- | --- |
| Orama #393 is **merged** (`f5a9e005`), not an open branch | PR state | REV2's "reuse #393 while unmerged" and "existing unmerged branches" no longer hold; P0 repair is a forward commit on main |
| Canonical Orama registry on main is no longer the T0 baseline | `ownership-registry.json` `c1bf6b519f70…` at `bccc152`, `fbde64f2c3b2…` on main; policy-r3 and core-r3 also changed | Source and fixtures **drift now** |
| Oramasys main fixtures still hold the T0 digests | `c1bf6b519f70…`, `7aeed7456db1…`, `498e93836672…` | The byte-parity invariant is currently broken across repos |
| REV2's "retained pre-R3 digest" is the archived reserialization | `ownership-registry-pre-r3.json` = `ab0bcf96099e…` | REV2's defect is real: equivalent JSON is not the original bytes |
| Oramasys production pin is still pre-R3 Core | `04759a50…` in dependencies | P0 not started |
| Distribution `oramasys`, module `orama` | `pyproject.toml` | REV2's correction of the review's import example is right |
| Core has no `__commit__`/`__version__` | grep on Core main | PEP 610 `direct_url.json` is the right identity check |
| Core observer awaits listeners inline while the consumer pulls the scheduler | `run_with_plugins` | Slow-listener stall is real; REV2's bounded design is justified |
| `PLAN-P0-CORE-PIN-PROMOTION.md` and the v1 P0–T2 plan already live on main | #393 file list | The earlier standalone draft is redundant; supersede, do not duplicate |

Also stale: my earlier statement that canonical and Oramasys registry digests matched was true
at `bccc152` and is **false on current Orama main**.

## 2. Disposition of the two inputs

| Source | Keep | Drop or correct |
| --- | --- | --- |
| Codex review | Two-phase promotion idea; import smoke instead of `pip check` alone; numeric queue/timeout limits; admission lease with TTL and step bound; hermetic fake provider; cooperative then forced cancel; one matrix source of truth; failure table | Moving or fast-forwarding tags; `__commit__` assert; "budget cannot survive restart" as a contradiction; severity scores as evidence |
| REV2 | State table STAGED→SUPERSEDED, six-cell manifest, byte-restore of the original blob, durable accounting distinct from T5, no PT runtime coupling, trusted-registry `CallableRef`, guard on real execution boundaries, honest "unknown" outcomes | "Existing unmerged branches"; the assumption that main is unchanged until qualification |

## 3. The elegant core: three mechanisms become one gate

REV2 specifies admission leases (T1), stop/cancel and delivery failure (T2-A), and budget
holds (T2-B) as three subsystems that each need a pre-dispatch check. They are one concern:
"may the next unit of work start or commit?"

**One `DispatchGate`, three inputs, one decision type, one durable store.**

| Input | Owner | Meaning at the gate |
| --- | --- | --- |
| Admission lease | Oramasys, from Phylax/Agate decisions | Identity, expiry, authority epoch, max steps |
| Run control | Oramasys | `stop_requested`, delivery-uncertain, circuit state |
| Budget hold | Oramasys single writer | Reserved step/time/cost/effect-attempt units |

- `before_dispatch` and `before_commit` return one `GateDecision` (`allow`, `refuse(reason)`,
  `stop`), evaluated in a fixed order: authority, stop, delivery health, budget.
- Lease `max_steps` is **a ledger hold**, not a second counter. The ledger already makes
  reservation atomic, idempotent and crash-recoverable; admission only supplies the limit.
- Core sees one neutral protocol (`DispatchGate`), never policy, accounting or traversal.
- One outcome taxonomy for all paths: completed, interrupted, cancelled, refused, budget,
  unknown. Delivery failure, lease expiry, cancellation and crash recovery all map into it.

Why this is simpler: one seam in Core instead of three, one durable writer instead of two
counters that can disagree, one refusal vocabulary for tests and operators.

## 4. Revised work order

1. **P0.0 Reconcile current drift (new, first).** Re-read Orama, Oramasys and Core heads.
   Decide which Orama main registry bytes are intended. Restore the original baseline bytes as a
   reviewed forward commit (no history rewrite), keep the archive file as history, and update
   Oramasys fixtures to match byte for byte. Record a drift receipt.
2. **P0.1 Manifest.** One versioned six-cell manifest (3 profiles × Python 3.11/3.12) is the only
   pin table; CI generates the matrix from it. Evidence receipts live apart from the manifest.
3. **P0.2 Install proof.** Non-editable wheel in a clean environment, run from outside the
   checkout; imports of `orama`, `perpetua_core`, `GraphSpec`, `ReducerSpec`, `JoinSpec`;
   construct and run a minimal graph; PEP 610 identity equals the pinned Core; plus
   `pip check`, existing gates, and offline oracles in their own environment.
4. **P0.3 Promotion states.** Keep REV2's STAGED, QUALIFIED, CANONICAL, ACTIVATED and
   SUPERSEDED states, but
   amend it: because #393 already changed Orama main, the first transition is a **forward
   restoration**, and consumer main stays on the last qualified pair until the receipt exists.
   Never discover a baseline from Orama main dynamically; pin full SHAs.
5. **T1 admission.** `CallableRef` = key into a frozen, composition-time registry bound to
   artifact digests. Negative tests monkeypatch `importlib.import_module` to fail and assert
   artifact strings never reach it. Fakes live in a test-only package that production profiles
   cannot import (lint plus a startup assertion). Disconnected production refuses.
6. **Gate seam (one reviewed Core change).** A neutral `DispatchGate` protocol on the single
   scheduler, covering node dispatch, reducer execution and pre-commit for every fan-out branch.
   Amend Core before claiming T1 if the seam cannot guard all branches.
7. **T2-A delivery.** Per-sink bounded FIFO (1024 events, 8 MiB total payload), non-blocking
   enqueue, drop-newest with external counters and gap ranges for telemetry; critical sinks
   acknowledge at persistence boundaries with a 500 ms deadline and are never dropped. Failure
   raises neutral `CriticalDeliveryFailed`; the gate refuses the next dispatch; Oramasys maps
   it to `unknown` with a delivery-uncertain reason. Use shielded tasks with an
   `asyncio.wait` timeout and track abandoned tasks; never claim a hard deadline for a callback
   that suppresses cancellation. Limits are configurable, reject zero/unbounded, and are not
   safety evidence.
8. **T2-B accounting and stop.** SQLite single writer (WAL, `synchronous=FULL`, restrictive
   permissions), immutable events, integer units, idempotent settlement, nested calls share the
   parent context, conservative handling of started-without-receipt attempts. Two-stage stop:
   set `stop_requested`, signal cooperative cancellation, 1000 ms grace, then supported forced
   cancel; open a circuit and forbid late authority from abandoned tasks.
9. **Unknown-hold reconciliation.** Add an operator-initiated, append-only adjustment event to
   release or settle an `unknown` hold after review. Nothing edits or deletes ledger rows.
10. **Exit evidence.** Failure-class tests per REV2 §2, subprocess crash tests, exact-head
    combined Core/Oramasys qualification, canonical evidence before PT memory.

## 5. Contract choices to confirm (operator)

1. Which Orama main registry bytes are intended after #393, and may the original be restored by a
   forward commit? (Blocks P0.0.)
2. Durable accounting (recommended, matches the parent T2) versus in-memory-only budgets, which
   would amend the parent requirement.
3. One `DispatchGate` seam versus three separate seams.
4. Default limits (1024 events, 8 MiB, 500 ms, 1000 ms) as proposed starting values.
5. Whether `PLAN-P0-CORE-PIN-PROMOTION.md` on main is amended or marked superseded by REV3.

## 6. Risks that remain

- The gate seam touches Core; it needs a dedicated review and a Core release before Oramasys
  can depend on it.
- Conservative `unknown` holds can strand budget after crashes; reconciliation must be
  operator-visible and tested.
- Cross-repo promotion is not atomic; the last-qualified-pair rule is the only safeguard.
- Boundaries unchanged: no T3 effects, T4 transport, T5 continuation or exactly-once claim.
