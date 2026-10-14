# 74 — Lost-run takeover: operator entry-point design

> **Repository standard:** additive — see [`46-repository-standard.md`](46-repository-standard.md).
> **Status:** DESIGN NOTE; NOT IMPLEMENTED; NOT RATIFIED.
> **Date:** 2026-10-14
> **Scope:** the operator-invoked entry point for `recover_lost_run` in the `oramasys/oramasys`
> repository (PR 38, option A). Design only; no code.
> **Parents:** [`71-operator-provisioning-and-autonomous-tier-adr.md`](71-operator-provisioning-and-autonomous-tier-adr.md)
> (no resident recovery daemon; explicit operator command).
> **Open decision:** DEC-Q-04 (terminal outcome vocabulary for operators).

## Purpose

When a run's process is lost, its lease is still held by a holder that may be dead or merely slow.
Something must be able to end that run deterministically. This note specifies the thin,
operator-invoked command that calls `recover_lost_run`, so that the policy is reviewed before any
code is written.

## Files checked for numbering

Highest-numbered existing `docs/v2` file was `73-alexandria-repository.md`. Checked: the
`docs/v2` directory listing for entries numbered 62 through 73, and for any entry numbered above
73 (none). The `docs/v2/plans` and `docs/v2/references` subdirectories use dated names, not
numbers. This note is therefore 74.

## Principles

1. **Owner-only.** The implementation accepts a caller only when it presents the run's recorded owner
   principal (the same rule as stopping a run); any other principal is refused. Whether the owner
   principal is shared with the run's own agent is a deployment property, not enforced by this
   function: if the agent can present the owner principal it can take over, which is why the
   entry point must require a distinct operator capability (open question for DEC-Q-04).
2. **Explicit.** One invocation names one run. There is no scan, no "recover all", no schedule.
3. **No daemon.** ADR 71 lists a resident privileged recovery daemon as a non-goal. The entry
   point is a short-lived process that exits.
4. **Force-takeover.** The command fences the current lease holder by advancing the lease epoch.
   A slow-but-alive holder is fenced out, not proven dead. The command's output must say so.
5. **Terminal outcome `unknown`, reason `run.process_lost`.** The command does not claim success
   or failure of the lost work. See open question 1.
6. **Idempotent.** Repeating the same invocation after success returns the recorded result and
   changes nothing.
7. **Compare-and-swap on the lease epoch.** Takeover succeeds only if the lease epoch is still the
   value the command read. A concurrent change causes refusal, not overwrite.

## Inputs

| Input | Required | Meaning |
| --- | --- | --- |
| run identifier | yes | The run to take over |
| store reference | yes | Which durable store holds the run |
| operator credential | yes | Single operator capability; read from environment or descriptor, never argv |
| expected lease epoch | no | If given, the CAS uses it; else the command reads and prints it first |
| takeover attempt identifier | yes | Opaque UUID generated once by the caller; every retry of that takeover reuses it |
| confirmation flag | yes | An explicit flag acknowledging fence-not-proof-of-death semantics |
| dry run | no | Report what would happen; make no change |

The command takes no free-text reason that changes behaviour. An operator note, if added, is
recorded but never interpreted.

## Takeover attempt identity and replay

Before advancing an epoch, the command durably records the caller-supplied attempt identifier
with the run identifier, store reference, source epoch, target epoch, and the fixed terminal
payload (`unknown`, `run.process_lost`). These fields are immutable for the attempt. The epoch
advance and attempt record are one compare-and-swap operation.

On a retry, the command looks up the attempt identifier before reading the current lease epoch.
If its immutable fields match the request, it resumes that record: a pending attempt finalizes
the terminal write at its recorded target epoch, and a completed one returns its recorded receipt.
It does not apply another fence. Reusing an attempt identifier with different immutable fields is
invalid input (code 2). A different identifier is a new takeover and must pass CAS against the
current epoch; it cannot adopt or resume another attempt's partial record.

## Output

On every invocation, to standard output as one structured object plus a short human line:

- run identifier, store reference, and outcome of the invocation (see exit codes);
- lease epoch read, lease epoch written (or "unchanged");
- holder identity as recorded, and the statement that a takeover fences the holder and does not
  prove it dead;
- terminal outcome and reason code written, or the existing terminal if already recovered;
- whether the result is a first application or an idempotent replay.

The output must never include credential bytes, seed material, or workstation paths.

## Failure modes and exit codes

Exit codes are proposed, not final.

| Code | Condition | Effect on state |
| --- | --- | --- |
| 0 | Takeover applied, or idempotent replay of an identical earlier takeover | applied or none |
| 2 | Invalid input or missing confirmation flag | none |
| 3 | Caller is not the owner capability | none |
| 4 | Run not found in the named store | none |
| 5 | Reserved: the function returns any existing receipt, so this case does not occur today | none |
| 6 | CAS conflict: lease epoch changed since read | epoch is the competitor's; no terminal from this call; retry is safe |
| 7 | Store unavailable or locked beyond the deadline | **may be partial**: the epoch may already have advanced and unstarted holds may be released with no terminal yet. Retry with the same takeover attempt identifier resumes that recorded attempt at its target epoch without another fence; a new identifier is a new CAS attempt. Hard time ceiling applies. |
| 8 | Invariant violation (corrupt lease record or digest mismatch) | none; fails closed |

Every external call (store open, write) carries a hard deadline. A timeout is code 7, never a
silent hang.

## Explicitly out of scope

- Any daemon, watcher, timer, or automatic trigger.
- Bulk recovery or listing of lost runs.
- Proving the holder dead, killing processes, or contacting the holder.
- Minting or consuming adjustment grants; that path is ADR 71 and plan 72.
- Retrying or resuming the lost work.
- Any change to quotas, isolation gates or ownership rules in ADR 71.

## Open questions

### DEC-Q-04: is `unknown` the right terminal for operators

1. Does an operator reading `unknown` with reason `run.process_lost` get an actionable signal, or
   should the command use a distinct terminal such as `lost`? A new terminal widens the vocabulary
   that downstream consumers must handle.
2. If `unknown` stays, should the output require the operator to choose between "work possibly
   completed" and "work possibly not started" as a recorded annotation, without changing the
   terminal?
3. Should a later, separately authorised step be allowed to move `unknown` to a definite terminal
   when external evidence appears, or is `unknown` final?

### Other

1. Is a confirmation flag enough, or should takeover require re-presenting the epoch read (forcing
   a read-then-act cycle)?
2. Should a dry run be mandatory before the first real invocation on a run?

## Non-claims

This note does not select option A as ratified policy, does not authorise implementation, and does
not change ADR 71.
