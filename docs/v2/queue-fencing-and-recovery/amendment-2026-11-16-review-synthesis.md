# Queue Fencing and Recovery — Dated Amendment 2026-11-16 (review synthesis)

> **Status:** additive amendment to this work package, accepted by the operator on 2026-11-16.
> The [consolidated plan](plan.md), [decision record](decision-record.md) and
> [README](README.md) remain canonical; nothing in them is rewritten. Where this file adds a
> task or a requirement, it extends them. The ratified gates (Q-D23, Q-TOPO, Q-D1, Q-D2,
> Q-68, Q-68b, Q-AGE, Q-RET, Q-LAYOUT, Q-SQLITE) are unchanged. This amendment authorizes no
> migration, credential issuance, live cleanup run, merge or activation.

## 1. Provenance

A review of the 2026-11-10 authenticated-queue plan, one of this package's three historical
inputs, found that plan superseded by this package. Seven of its points are already fixed here.
Three points were still open here: O1, O2 and O3.

The operator accepted the review's recommendations on 2026-11-16. A second, independent reviewer
re-checked O1–O3 against Perpetua-Tools main `34963a9a` and orama-system main `174a7860` and
confirmed all three, with the wording corrections that are included below. The review and the
synthesis plan are operator-held local references and are not in this repository.

The 2026-11-10 plan stays a historical input and is not to be executed. Use this package's
README task table.

## 2. New task: L-1r, the cleanup runtime liveness race (O1)

What is already closed: both release paths re-read liveness and the claim inside the same
`BEGIN IMMEDIATE` transaction as the write. The paths are L-1a's
`release_captured_queue_claims` with `_agent_alive_in_txn`, and the legacy
`_release_legacy_claim_atomically` in `heartbeat_monitor.py`. Cleanup runs only when invoked.

What remains is a runtime race. `cleanup_stale_claims` classifies an agent as DEAD from
heartbeat age, using the module constant `LIVENESS_STALLED_SEC = 1800`. Its `max_age_seconds`
argument is unused. A worker that is alive but silent is classified correctly at decision time
and released while it keeps running.

When such a worker resumes:

- `queue_complete` and `queue_fail` refuse it if a different agent reclaimed the task, or if the
  task was only released (status no longer CLAIMED).
- They **accept** its completion when the same agent name reclaimed the task.
- Legacy `agent_claim` work has no completion fence.
- External effects are fenced only if the downstream system checks the fence.

PR 493's continuing quiescence (plan section 4.3) is the interim mitigation. The source is
decision record item I-1, "legacy agent_claim auto-release race outside L-1a". L-1b covers
cutover refusal and routing, not this race.

| Task | Owner and parent row | Deliverable and acceptance | Needs |
| --- | --- | --- | --- |
| L-1r | PT, C2/C5 (master row C5a) | Failing-first real-process schedule: pause a worker past the DEAD threshold, run cleanup, let another agent claim, resume the paused worker and attempt complete and an external effect; include the same-agent-name reclaim case. Write the expected outcome before code: refusal, or a recorded hold for anything that cannot be fenced. Before V1-2: hold, refuse or explicit operator confirmation only, because no generation exists to fence with. After V1-2: the persistent generation fences the resumed worker. Reuse the exact `find_agent_heartbeats` scoring (I-3); record the changed cleanup outcome in the contract-migration ledger (I-2); POSIX and native Windows evidence (D3) | C5, L-1a; V1-2 for the generation step |

Order: L-1r's pre-generation step may land after L-1a. Its generation step lands after V1-2 and
before V1-4. It stays separate from V1-3, L-1b and V1-4, so a recovery or cutover change cannot
be reported as fixing it.

Method: `oramasys-method`, which means the AFRP gate, the TDD gate and the contract-migration
method; and `orama-system`, which means verify before done and the cross-agent provenance
invariant, with no fabricated pulse on release.

## 3. Credential inventory for V1-0 and V1-4 (O2)

Per lane, from `orchestrator/control_plane_auth.py` at Perpetua-Tools main `34963a9a`:

| Lane | Sources |
| --- | --- |
| PT | `PT_CONTROL_PLANE_TOKEN`; the repository-local file `.state/control_plane_token` |
| Orama | `ORAMA_CONTROL_PLANE_TOKEN`; `ORAMA_CONTROL_PLANE_TOKEN_LOCAL` |
| Peer (outbound only) | `ORAMA_CONTROL_PLANE_TOKEN_PEER`; never accepted inbound by `accepted_control_plane_tokens` |

- **V1-0 adds:** list these sources by lane, and where every worker launcher gets its
  environment from.
- **V1-4 adds:** rehearse that a launched worker's environment holds none of the lane token
  variables, and that the worker's OS identity is denied reading `.state/control_plane_token`.
  The denials must be real on both hosts.
- **Section 11 adds:** until the slice-A premise decision (V1-0, A-V1, P-H1), a worker with the
  lane token or the token file has that lane's operator capability. Lane scoping is not worker
  isolation either way.

The two services differ, so state each separately:

| Service | Inbound acceptance, from the source |
| --- | --- |
| Perpetua-Tools (`orchestrator/control_plane_auth.py`, `accepted_control_plane_tokens`) | Lane-scoped even in joint mode: scope `pt` accepts the PT lane only, scope `orama` the Orama lane only; the peer token is never accepted inbound. |
| orama-system (`src/utils/control_plane_auth.py`, `accepted_control_plane_tokens`, used by `token_matches_control_plane(..., scope="orama")` in `src/orama_system/portal_server.py`) | **Not lane-scoped in joint mode:** when both lanes have keys it accepts the union, so a PT-lane token authorizes Orama portal requests and the reverse. With a single lane configured it falls back to the other lane's tokens ("Legacy" branch). The peer token is not accepted inbound. |

The earlier sentence "inbound lane scoping is correct" (review 2026-11-16, O2) was verified for
the PT implementation only. For the Orama service, the V1-0 inventory must record this joint-mode
cross-lane acceptance as part of the credential inventory, and the V1-4 rehearsal covers both
lane variables for a launched worker. Whether to tighten the Orama check is a separate design
decision for its owner; this amendment changes no code.

## 4. Model tiers for execution (O3)

This adds to plan section 12, step 3. On Claude Code, dispatch through the `Workflow` tool under
its own opt-in gate, with model and effort set explicitly and never inherited:

- Haiku dispatches and controls non-Claude workers (Cline, Codex, agy and others).
- Sonnet at medium effort evaluates and integrates their output.
- Opus or Fable runs only on the operator's explicit request or a confirmed escalation.

Local-model workers follow the OpenClaw invariant: never Ollama and LM Studio under concurrent
heavy load on the Mac. Worker output is data until verified. Source:
`bin/orama-system/references/claude-code-workflow-canonical.md`.
