# D-0 decision record — Queue Fencing and Recovery consolidated plan (2026-11-11)

Provenance: recorded by the Cline session (win-cline-bench-20261110) as integrator under the
operator's ratification directive of 2026-11-10/11 ("implement all" with the Q-68b
specification below). author=cline actor=cline identity_verified=false endorsement=none
takeover=none. Status: DRAFT pending V1-1/V2-1 audit cross-references (audits in flight).
Plan source: QUEUE-FENCING-AND-RECOVERY-CONSOLIDATED-PLAN-2026-11-11.md.

## 1. Operator ratification of the section 3 gates

The operator ratified the consolidated plan and accepted every section 3 gate as proposed:

| Gate | Decision | Blocks (per plan) |
| --- | --- | --- |
| Q-D23 | ACCEPTED — F's reduced guarantee ratified; Q1–Q3 evidence recorded at implementation time; slice A needs its own premise decision (still open) | every implementation task |
| Q-TOPO | ACCEPTED — one authority per stack on the approved primary POSIX role; other host is a client, never a replicated writer; outage means refusal | V1-2, V2-2 |
| Q-D1 | ACCEPTED — an explicitly started, request-serving PT queue authority is allowed; it may answer requests and drain committed outbox rows; no sweep, schedule, auto-transfer or auto-start | V1-2 |
| Q-D2 | ACCEPTED — shim names retained; changed availability and handle requirements for mutations observed first, then enforced; no fallback writer after cutover | V1-4 |
| Q-68 | ACCEPTED — doc 68, claim contract, envelope and migration rules amended together (reserved handoff, versioned recipient fields, old-client refusal); stale banner corrected additively | V2-3, reserved recovery |
| Q-AGE | ACCEPTED — any maximum admission age is configurable, rationale-backed and tested under lock contention; no invented default | V2-2 admission profile |
| Q-RET | ACCEPTED — no automatic purge in this slice; receipts, tombstones, generations and audit retained; capacity and backup policy accepted before activation | activation |
| Q-LAYOUT | ACCEPTED — existing PT and Controller owners extended; new executable artifacts under src per doc 46; any legacy-tree exception explicit and approved | V1-2 packaging |
| Q-SQLITE | ACCEPTED — both new ledgers refuse to open on SQLite below the c6_runtime gate and record the library version and source id; development baseline Python 3.13.18 / SQLite 3.53.1; the fix check is run, not assumed | V1-2, V2-2 |

Existing binding rules stay in force: D1, D2, D3, D23, IC-1–IC-29, separate R6/R7/R8 and C3d
gates; network authentication, TLS and v2 Telos/Phylax admission are not waived by D23.

## 2. Q-68b — HITL operator override decision (recorded with the cost stated)

Decision: **Option B — token-free delivery — selected by explicit operator override (HITL).**

- The default (option A, authorized replay returning the raw lease token) stands for slice F.
- The operator's override selects option B as the target behavior: replay returns the receipt
  without the raw token and holds a lost-response lease for conservative recovery.
- Cost, stated: a canonical honest failure (a lost response) consumes a full lease TTL before
  conservative recovery can proceed. The operator accepts this cost deliberately.
- Scope: this is slice A hardening. It is gated behind the slice A premise decision, which
  remains OPEN (V1-0/A-V1/P-H1 need their own premise decision before any work starts).
- Invariant: regardless of the option, a byte-identical captured request from another verified
  channel yields no token and no new lease unless it passes full admission; the cross-channel
  replay regression test applies to both options.

## 3. Audit cross-references

- **V1-1 COMPLETE (2026-11-11, exit 0, read-only, tree clean at 1020b58).** Deliverables preserved at
  `tasks/queue-fencing/`: `qf-v1-1-audit-report.md` (22466 B, sha256 af60f4e4e86841e3d983a28120c626ea8b703285e8b7a17e98a568a75c15df35),
  `qf-v1-1-ledger-6-1.md` (9295 B, sha256 ea99c636deaec8e3bd0cf6edf9f3eeeb0884879cb02fa2554725e6940a42a606),
  `qf-v1-1-l1a-feasibility.md` (9191 B, sha256 83c59ecc2f8506017e5a79dd3205bc2442ede1b953e590e1178d5579950801b1).
  Headline: all three L-1a premises CONFIRMED from source (V) — same-file atomicity; in-transaction
  `claimed_at` capture-and-compare; same-connection heartbeat liveness recheck. Optional-argument burden:
  `release_claim_with_event` gains `expected_claimed_at` + `require_live_holder`; `_fetch_heartbeat_events`/
  `find_agent_heartbeats` gain an optional connection parameter; `cleanup_stale_queue_claims` needs only an
  internal SELECT change (projection gains `claimed_at`). Eighteen claim writers/callers enumerated (V).
  **L-1a is GO per the plan's own gate.** Dispatched to the implementer subagent on this basis.
- V2-1 (oramasys audit): the canonical V2-1 is assigned to Antigravity on the Mac; the Cline session's
  parallel oramasys audit at f33d809 provides Windows-side cross-evidence (deliverables already written:
  audit report, six ledger rows, Q-68/Q-68b amendment draft — integration pending run completion).
  Outputs to be appended when reviewed (QF-REV-V2-1-spec claimed by this session).

## 4. Disposition cross-reference

win-researcher's review disposition: ACCEPT WITH CHANGES (ground truth verified live; findings
I-1 legacy agent_claim auto-release race outside L-1a; I-2 L-1a changes the cleanup outcome
contract; I-3 liveness recheck must reuse the exact find_agent_heartbeats scoring; I-4 Windows
environment baseline deviations — measured and confirmed by QF-V1-1b: PT venv SQLite 3.50.4
below the 3.51.3 floor, Python 3.11.15/3.12.13 below the 3.13.18 baseline). L-1a implementation
must address I-2 and I-3 explicitly.
