# D-0 decision record — Queue Fencing and Recovery consolidated plan (2026-11-11)

Provenance: recorded by the Cline session (win-cline-bench-20261110) as integrator under the
operator's ratification directive of 2026-11-10/11 ("implement all" with the Q-68b
specification below). author=cline actor=cline identity_verified=false endorsement=none
takeover=none. Status: DRAFT pending V1-1/V2-1 audit cross-references (audits in flight).
Plan source: QUEUE-FENCING-AND-RECOVERY-CONSOLIDATED-PLAN-2026-11-11.md.

## 1. Operator ratification status of the section 3 gates - FINAL (2026-11-11, 09:45 +08:00)

Per the operator HITL decision in chat at 09:45 +08:00 (relayed by win-researcher, my board event
  509; corroborated by the Mac session and re-confirmed directly to the Mac): ALL remaining proposed
  queue-fencing gates are ACCEPTED:

- Q-D23: slice F ratified (fencing, versions, idempotency, private ledger); slice A deferred except
  the approved replay premise.
- Q-TOPO: Mac single POSIX authority for v1/v2 queue services; Windows client; 503 on outage.
- Q-D1: an explicitly started request-serving PT queue authority is allowed; no sweeps or daemons.
- Q-D2: shim names retained; observe callers first, then enforce.
- Q-68: schema 2 reservations with old-client refusal.
- Q-SQLITE: SQLite >= 3.51.3 required by both new ledgers.
- Q-AGE, Q-RET, Q-LAYOUT: accepted as proposed.
- Q-68b: unchanged two-stage decision (attempt 1 returns the token; attempt 2 and later token-free).

Still operator-held: C3d-base, merges and pushes, activation, R6-R8, test authorization on the
  authority host, PT PR 494 status.

History: an earlier correction in this record marked the gates Proposed based on the then-current
Windows gate record (event 497); the operator ratification at 09:45 supersedes that correction.
This section is the operative one.

Existing binding rules stay in force: D1, D2, D3, D23, IC-1–IC-29, separate R6/R7/R8 and C3d
gates. Consequences: D-0 documentation must present the gates as Proposed; V1-2 and V2-2
implementation claims are HELD pending ratified gates; both L-1a commits are HELD (see
section 3b).

## 2. Q-68b — HITL operator override decision (recorded with the cost stated)

Decision: **recorded per the orchestrator tracker's operative HITL formulation — "first retry
returns the token; subsequent retries are token-free" — with the cost stated.** This session's
earlier draft recorded the simpler option-B reading; the orchestrator tracker (Antigravity,
QUEUE-FENCING-PROGRESS-TRACKER.md) carries the operative graded formulation and this record
defers to it, pending explicit operator confirmation of the graded semantics.

- The default (option A, authorized replay returning the raw lease token) stands for slice F;
  under the graded formulation the FIRST retry of an authorized replay returns the token, and
  SUBSEQUENT retries are token-free (receipt without the raw token, lost-response lease held
  for conservative recovery).
- Cost, stated: a canonical honest failure (a lost response) consumes a full lease TTL before
  conservative recovery can proceed. The operator accepts this cost deliberately.
- Scope: slice A hardening, gated behind the slice A premise decision (V1-0/A-V1/P-H1), which
  remains OPEN.
- Invariant: regardless of the option, a byte-identical captured request from another verified
  channel yields no token and no new lease unless it passes full admission; the cross-channel
  replay regression test applies to both options.

## 3. Audit cross-references

- **V1-1 COMPLETE (2026-11-11, exit 0, read-only, tree clean at 1020b58).** Deliverables preserved
  at
  `tasks/queue-fencing/`: `qf-v1-1-audit-report.md` (22466 B, sha256
  af60f4e4e86841e3d983a28120c626ea8b703285e8b7a17e98a568a75c15df35),
  `qf-v1-1-ledger-6-1.md` (9295 B, sha256
  ea99c636deaec8e3bd0cf6edf9f3eeeb0884879cb02fa2554725e6940a42a606),
  `qf-v1-1-l1a-feasibility.md` (9191 B, sha256
  83c59ecc2f8506017e5a79dd3205bc2442ede1b953e590e1178d5579950801b1).
  Headline: all three L-1a premises CONFIRMED from source (V) — same-file atomicity; in-transaction
  `claimed_at` capture-and-compare; same-connection heartbeat liveness recheck. Optional-argument
  burden:
  `release_claim_with_event` gains `expected_claimed_at` + `require_live_holder`;
  `_fetch_heartbeat_events`/
  `find_agent_heartbeats` gain an optional connection parameter; `cleanup_stale_queue_claims` needs
  only an
  internal SELECT change (projection gains `claimed_at`). Eighteen claim writers/callers enumerated
  (V).
  **L-1a is GO per the plan's own gate.** Dispatched to the implementer subagent on this basis.
- V2-1 (oramasys audit): the canonical V2-1 is assigned to Antigravity on the Mac; the Cline
  session's
  parallel oramasys audit at f33d809 provides Windows-side cross-evidence (deliverables already
  written:
  audit report, six ledger rows, Q-68/Q-68b amendment draft — integration pending run completion).
  Outputs to be appended when reviewed (QF-REV-V2-1-spec claimed by this session).

## 3b. L-1a duplicate implementations — reconciliation (2026-11-11)

Two Windows implementations of L-1a exist; both are HELD (local drafts, no push, no further
claim until the operator decides), per the authorization reconciliation:

- Antigravity `0ca6e421` (Perpetua-Tools): 25 passed, **1 FAILED** — the pinned
  retry-count behaviour test (a requeue must not touch the retry counter); the commit also
  added retry-increment and terminal-abandon handling that is out of the plan's L-1a scope,
  and its commit author metadata conflicts with the tracker credit. V1-2 (7a812adf) is
  stacked on it and inherits the failure.
- Cline `cc57cd14` (worktrees/qf-l1a-implementation, branch qf/l1a-interim-cleanup-fence):
  **36 passed, 0 failed**, including the pinned manual-cleanup characterization and the
  presence-pulse separation; strictly scoped to the plan's L-1a (optional arguments only).

win-researcher's recommendation (adopted by this record): **synthesize the canonical L-1a
from cc57cd14; mark 0ca6e421 superseded (keep it, do not revert); re-derive V1-2 on the
synthesized base.** The canonical L-1a remains the Mac/POSIX lane per the division; both
Windows commits stand as native cross-evidence.

Also recorded: V1-2 (7a812adf) and the V2-2 claim by the agy implementers are HELD pending
ratified gates; the gates read Proposed until the operator decides each one.

## 4. Disposition cross-reference

win-researcher's review disposition: ACCEPT WITH CHANGES (ground truth verified live; findings
I-1 legacy agent_claim auto-release race outside L-1a; I-2 L-1a changes the cleanup outcome
contract; I-3 liveness recheck must reuse the exact find_agent_heartbeats scoring; I-4 Windows
environment baseline deviations — measured and confirmed by QF-V1-1b: PT venv SQLite 3.50.4
below the 3.51.3 floor, Python 3.11.15/3.12.13 below the 3.13.18 baseline). L-1a implementation
must address I-2 and I-3 explicitly.
