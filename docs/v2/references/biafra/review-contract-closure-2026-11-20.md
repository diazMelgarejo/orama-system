# Biafra consumer review closure — 2026-11-20

PT remains the producer and sole owner of spend state. This consumer slice uses
the optional declared-output admission contract without introducing another
ledger or paid route. A governed live Cline cycle refuses with
`launcher-output-bound-unsupported` before budget reservation, attempt markers
or process launch: the pinned client's aggregate request/output bound is not
proved. Restoring live operation needs a tested enforcing boundary, not an
operator assertion or a guessed configuration field. Dry operation remains
available. The preserved historical run harnesses are not modified.

| Layer | Contract and evidence |
| --- | --- |
| Persistence | No new consumer ledger. PT uncertain holds survive failed accounting and expiry; the consumer forwards reservations and settlement to PT. |
| Contract | `SpendGuard.preflight` forwards an explicitly supplied `max_tokens`; absent values preserve the existing producer call. Unsupported live boundaries return a structured refusal before effects. |
| Callers | Live-cycle tests explicitly simulate a supported launcher when testing downstream lifecycle behavior; separate tests prove the production boundary refuses without reserving or launching. |
| Transport | Caller deny-read paths include both the supplied spelling and its resolved target, including missing descendants. Resolution failures propagate. Retargeting paths during execution remains outside this pathname policy's guarantee. |
| Lifecycle | Marker failures release unused reservations. A spent attempt retains its marker. Existing paid-launch wrappers refuse ungoverned launches. No broad cycle refactor is needed to repair these demonstrated faults. |
| Operations | The security wrapper is executed with an offline scanner stub to prove baseline argument selection, missing-baseline refusal and scanner failure propagation. Native macOS sandbox enforcement remains an independent gate. |

## Failure-catalogue repairs

The three synthetic CA-store assertions isolate managed-runtime constructor
additions only within those tests. The added runtime entry is explicitly
rejected by OpenSSL; inspecting it as though it were an accepted trust anchor
caused the assertion failures. Production TLS verification is unchanged.

The four Linux containment assertions require the documented subreaper launcher
in this container, whose PID 1 does not reap orphan zombies. A real-process
regression proves a killed but unreaped descendant keeps containment `unknown`;
reaping the owned descendant then removes the group. This does not weaken the
runtime's fail-closed result or establish native Windows/macOS qualification.

The network WebSocket refusal test now uses Uvicorn's automatic implementation
selection rather than explicitly selecting the deprecated legacy implementation.
It still asserts an actual HTTP 403 before WebSocket upgrade. Older supported
Uvicorn releases remain free to select their supported implementation.

## Publication and rollback

Publish against the exact tested PT commit in `.github/pt-dispatch-test-ref`.
No force-push is needed for #519. Reverting the fail-closed launcher boundary
would restore the unresolved aggregate-spend risk; do not do so without a
verified replacement. Dependency remediation for alert 58 is a separately tested
logical batch. Source checks and bot replies do not constitute deployment,
operator approval or serving activation.

## Published producer and source evidence

The consumer pin selects PT #516
`305c555803f75e4844624f9aaba51d3e79956aa8`, published before this consumer update.
PT full suite: 3,720 passed, 12 skipped; Orama prepared backend source: 4,324
passed, 145 skipped and 24 subtests passed. Retained compatibility warnings and
the subreaper's bounded post-suite wait diagnostic remain documented in the
[failure catalogue](unrelated-failure-catalogue-2026-11-20.md).

Alert 58 upgrades the introducing TypeScript ESLint packages rather than forcing
an incompatible minimatch major onto legacy consumers. The lock now selects
11.0.9 for that chain; retained 3.1.5 is outside the supplied affected range.
Frontend lint, type checking/build, 53 tests and a zero-advisory dependency audit
passed. GitHub alert access remains restricted, so closure on main is not claimed.
