# Windows native qualification evidence and gaps (2026-11-10)

Author/actor: Claude Code on the Windows host acting as win-researcher, with the local Cline
session for the lock
tests (both self-reported, identity_verified=false). This is evidence, not a qualification and not
an approval.
V = run on the Windows host in this session. P = reported by a peer, not rerun here. U = unverified.
Nothing here changes trust, credentials, serving, firewall or any system setting.

## Verdict

**Windows is NOT qualified.** Windows-side evidence for the lock and process behaviour is now
native and
discriminating (it fails when the code is broken). The register items below that are physical,
human-only or
need account, trust or credential changes stay open and belong to the operator. Both hosts stay
UNQUALIFIED.

## Native evidence added by this change (V)

| Test file | What it proves on a real Windows host | Mutation check |
| --- | --- | --- |
| `tests/test_autoresearcher_lock_native.py` with `tests/_lock_helper_native.py` (written by the Cline session, hashes verified by Windows) | real OS lock, two real processes: one acquire wins, the other is refused; a hard-killed holder is never read as free; a reused start identity is unverified, not dead; release keeps the file; reconcile needs an operator and a note | lock attempt forced to succeed: 5 of 5 fail |
| `tests/test_cline_native_process_windows.py` | a real `cline.cmd` shim resolves to node plus the entry script; a prompt full of cmd metacharacters, quotes and a percent variable reaches the child byte for byte; real nonzero exit is `unknown`, real zero exit `completed`; an unexecutable file is `not-sent`; a hung child is killed and no longer running | prompt routed through the shim: 3 of 5 fail |

Limits: one host, one run each, a fake Cline (node script) and no network. The launch path for the
real Cline
3.0.74 install was exercised separately by the Cline session (plan-mode probe, one run, exit 0).

## Real Cline CLI run and the L4 root cause (V)

`tests/test_cline_real_cli_windows.py` is opt-in (`RUN_REAL_CLINE=1` plus `CLINE_MODEL`, spends a
few credits).
On the Windows host with Cline 3.0.74, one plan-mode call through `dispatch_cline` from a scratch
directory
completed in 5.7 s and echoed the requested marker, with the model pinned to the current ClinePass
coding lane.

The same call WITHOUT a pinned model failed in 4.7 s: a "hook dispatch failed" line, then "model
not found".
So the earlier benchmark's L4 failure was not repository-scope hooks (that guess is withdrawn):
this run was in a
scratch directory and reproduced it. The cause is that the global Cline configuration names a
retired default
model; the hook error is a misleading side effect. Fix on the operator side: set `CLINE_PROVIDER`
and
`CLINE_MODEL` for the controller and the watcher. A controller improvement (a clear "model not
found, pin
CLINE_MODEL" hint) belongs in the backend-lock pull request and is passed to its owner.

## Register status (from the Windows hardware canary handoff, H01 to H10)

| ID | Item | Windows status | Why / what is left |
| --- | --- | --- | --- |
| H01 | Three-profile hardware canaries | OPEN, operator-only | physical per-host collector evidence on three profiles; no collector CLI exists to invent |
| H02 | Private-key and trust-state ACL proof | OPEN, operator-only | needs a separate standard-user account for access-denial attempts: creating accounts and changing security settings is not done by an agent |
| H03 | Hardware-policy and Hermes walkthrough | OPEN | not run in this session |
| H04 | Model, partner and graph canaries | OPEN | not run in this session; a local model run was attempted earlier and recorded as a negative result |
| H05 | Bidirectional TLS canary with receiver receipts | PARTIAL | files crossed both directions over the pinned-CA https wire this session (V); the receiver acknowledgements cite byte counts, not a content-hash-bound receipt (U); queued historical items were not retargeted |
| H06 | Trust, credential and fleet-identity decisions | OPEN, operator-only | CA comparison, token rotation, OS-wide trust, stable names, fleet CA: human decisions |
| H07 | Bootstrap, mesh and heartbeat | PARTIAL | the 30-minute read-only pulse and the stack run on the RTX 3080 host (V); the watcher is still hand-launched until the autostart change in this stack is merged; the RTX 5080 node is not covered |
| H08 | Native Windows runtime and process qualification | PARTIAL, most advanced | shim resolution, quoting, spawn failure, exit classification, timeout kill: native evidence above (V). Not covered: grandchild processes of a real Cline, PATHEXT edge cases, permissions on the lock directory under another user |
| H09 | Serving identity and installed deployment | OPEN, operator-only | needs the provisioned identity and authority files; the identity checker uses POSIX primitives, so a Linux pass is not Windows proof |
| H10 | Owner decisions | OPEN, operator-only | thresholds, 3080 versus 5080 verdicts, concurrency and the MCP startup gate |

## Stack and merge order

This change sits on the AutoResearcher watcher autostart branch, which now contains the backend
lock branch by
ancestry, so merging in order is conflict-free: backend lock, then watcher autostart, then this
evidence change.
The Perpetua-Tools memory stack (three pull requests) is separate and already ordered.

## Addendum after the merges (2026-11-10, V on the Windows host)

State: orama main f7036d97 and Perpetua-Tools main f9564bed, Windows stack restarted from them outside
the app job. Windows is still NOT qualified; H10 (scope) is deferred by the operator, so no
qualification can be claimed either way.

| ID | Item | Status now | Evidence |
| --- | --- | --- | --- |
| H03 | Hermes policy walkthrough | PARTIAL | Phase B verify passes; Phase C policy CLI and the launcher gate pass; a policy-allowed model validates for Windows (exit 0) and a Mac-only model is refused (exit 1, negative control without editing any config); Phase A and E config parts N/A (no OpenClaw config on this host); Phase D cloud canary not run |
| H04 | Local model canary | PARTIAL | one exact-reply call on the loaded policy-allowed chat model, 20 s, finish reason stop; partner and graph round trips not run |
| H05 | TLS both ways with receipts | PARTIAL | both directions: sent, accepted, receiver receipt with raw bytes and SHA-256 that matched the sender's independent record; must be repeated after both certificate renewals |
| H07 | Bootstrap, mesh, heartbeat (3080 node) | PARTIAL | all stack processes outside any job object and alive after the launcher exited; status output matches listener PIDs; pulse process alive; the RTX 5080 node is offline and not covered |
| H08 | Native runtime and process | MOST ADVANCED | cmd, bat and ps1 shims in a path with spaces and non-ASCII letters, quoting, PATHEXT pick, spawn failure, exit classification, timeout kill including a grandchild: native tests above. Not covered: a detached grandchild, permissions under another user |
| H01, H02, H06, H09 | Physical canaries, ACL proof, trust, serving identity | OPEN, operator-only | unchanged |
| H10 | Owner decisions | DEFERRED | by the operator |
