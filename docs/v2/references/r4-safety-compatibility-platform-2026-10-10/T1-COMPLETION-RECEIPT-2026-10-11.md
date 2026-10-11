# T1 completion receipt: executable identity and admission lifecycle (2026-10-11)

State: T1 MERGED across five repositories; production Core pin PROMOTED. T2 stays gated.

## What landed

| Repository | Change | Merge |
| ---------- | ------ | ----- |
| Phylax | Identity and capability decisions with expiry and revocation | PR #4 |
| Agate | Policy decisions bound to artifact digests | PR #5 |
| Telos | Endpoint authorization decisions; concurrency, expiry and revoked-decision fixes | PR #7 |
| Core | Neutral `DispatchGate` (`before_dispatch`, `before_commit`) inside the single scheduler | PR #10 |
| Core | Commit settlement lifecycle: `result_digest`, `batch_id`, `after_commit` | PR #11 |
| Oramasys | `AdmissionGate`, digest-bound admission, durable `StepLedger`, bounded observer, runner-based API | PR #29 |

Core merge commit for the production pin: `609ff0ed99cf8eca6c9ef608e764b7a25b6b9973`.
Owner candidate lane pins are the merged mains of Phylax, Agate and Telos.

## Review closure

- Telos: concurrent use no longer rejects valid connections as expired; revoked decisions
  from authorizers that issue no expiry are no longer accepted.
- Oramasys: the endpoint-authorization requirement and the ledger step limit are now checked
  against admission instead of trusted from the caller.
- Core #11: non-finite numbers are refused before the commit gate; the delta that is hashed
  is the delta that is published; a failed or cancelled settlement still publishes the
  committed state before scheduling stops.
- Bounded observer: the aggregate byte limit is enforced and released on completion,
  cancellation and sink replacement; an unidentified observer can no longer hide its stop
  request or the original sink failure.
- Docstring coverage is 100% on every changed file in every PR.

## Promotion

- Registry `core_pin` and the pinned production digest move together in this repository and
  in Oramasys; the two registry snapshots remain byte-identical.
- The six-cell result-file gate (production, policy-r3, core-r3 by Python 3.11/3.12) keeps its
  floors; tests that need the newer Core are not collected, never skipped, on older pins.
- Rollback: revert the pin commit in both repositories; the previous pair stays in history.

## Open items for the operator

- Run identifiers chosen by the client (`metadata["run_id"]`, `session_id`) can fence another
  run's lease; derive them server-side before T2.
- A fresh `StopSignal` per invocation is unreachable from outside; wire a shared stop source.
- The `/run` 503 detail exposes internal reason codes; return a stable public code instead.
- An observer built without an identity trips its circuit but records no
  `UnknownDisposition`; decide whether construction should fail instead.
