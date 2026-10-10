# Plan — R4 preparation and execution (T0–T11)


**Status:** approved execution plan under D-LG-7. No task here is authorized to
start until its predecessor evidence and release gates pass. An unchecked box is not a shipped
capability. Decision source: [D-LG-7](ADR-D-LG-7-R4-SAFETY-COMPATIBILITY-PLATFORM.md).


## Operating rules


- Every implementation task: reproduce a named failing invariant, implement the minimal
  reviewed change, run focused and affected suites, review the diff, commit one logical
  batch. Commands come from the actual checkout, with import paths recorded.
- Proposed paths below are design decisions, not existing files. At T0 map them to current
  instructions and layout; preserve the `src` execution standard and record justified
  relocations before implementation.
- New implementation PRs start from confirmed merged baselines. Never force-push, delete
  history, close an existing PR to simplify coordination, or push to a merged PR's branch.
- Report implemented, verified, published, reviewed, merged and enabled separately.
  Pending is not passed; a local commit is not a publication.


## File map (proposed)


| Repo | Existing seam | Proposed additions |
| --- | --- | --- |
| Core | `src/perpetua_core/graph/{engine,spec,lint}.py`, `graph/plugins/` | Neutral continuation records/protocols beside the checkpointer; durable-resume tests in `src/tests/graph/` |
| Oramasys | `src/orama/graph/perpetua_graph.py`, provider and gateway contracts | `src/orama/graph/{admission,approvals,effects,recovery}.py` where no equivalent exists; transaction adapter outside the engine |
| Oramasys | Framework bridges and compatibility tests | `src/orama/compat/{manifest,diagnostics,activation}.py`; matrix runner |
| Oramasys | Provider contracts and ledgers | `src/orama/providers/foreign_transport.py` and focused adapters |
| Oramasys | Accepted controller home | Extend `src/orama/orchestrator_controller/`; no duplicate claim writer |
| Orama | `docs/v2/references/` | This set; amendments link rather than duplicate authority |
| PT | `.agent/tools/learn.py`, memory | Additive per-slice evidence and lessons through tooling |
| Telos / Phylax / Agate | Canonical owning interfaces | Only verified missing contracts, in their own repos, with consumer qualification |


## Interface vocabulary (proposed; fully typed and schema-versioned before code)


Functions return discriminated outcomes, never truthy Booleans.


| Interface | Consumes | Produces / owner |
| --- | --- | --- |
| `admit_artifact(binding, context)` | `ArtifactBinding` + authenticated context | `AdmissionDecision`; Oramasys using Phylax/Agate |
| `request_exception(operation, refusal)` | Operation key + eligible refusal | `ApprovalRequestId`; Oramasys |
| `decide_exception(request_id, decision)` | Authenticated decision | `GrantReceipt`; Oramasys |
| `reserve_effect(intent, grant_ref, expected_version)` | Intent + optional grant + CAS version | `ReservationOutcome`; Oramasys |
| `authorize_dispatch(reservation_id, epoch)` | Valid reservation + live gates | `DispatchPermit` or refusal; Oramasys |
| `dispatch_effect(permit, request)` | Bound request + permit | `ProviderOutcome`; adapter through Telos |
| `reconcile_effect(operation_key)` | Logical identity + stored evidence | `ProviderOutcome`; Oramasys/adapter |
| `prepare_continuation(checkpoint_id, context)` | Checkpoint + resume context | `ResumeDecision` + neutral cursor; Oramasys |
| Core continuation entry | Validated cursor + state + protocols | Same scheduler observations; signature fixed in the R4 subsystem spec |


No task may rely on an undefined record or an unapproved seam.
