# Biafra lockstep remediation record (2026-11-17)

Dated record for [doc 76 section 13](../../76-biafra-outer-seat-canonical-plan.md). Perpetua-Tools
(PT) PR #516 and orama-system PR #519, branch `2026-11-17-001-biafra-seat-canonical`, are open and
not merged. Their heads at review were `c90feebb` (PT) and `bd5931a2` (orama).

## Inputs

- The "2026-11-17 Restack Review" of PT #516 at `c90feebb` and orama #519 at `bd5931a2`: request
  changes, seven findings (P1: 1 and 2; P2: 3 to 7), with G3 and G9 called out as open design gaps.
- The saved PT remediation method: collect once, fix the owning abstraction once, failing-first
  tests, docstrings 100 percent, push once per PR, reply with the fixing commit, never merge
  without explicit instruction.
- Execution: isolated lane worktrees, one subagent per lane, integrator verification of every
  report, and an independent read-only reviewer per repository.

## Finding to commit subject

Commit subjects, not SHAs, because SHAs may change at publication.

### Perpetua-Tools (PR #516)

| Item | PT commit subjects |
| --- | --- |
| Finding 2 | `fix(cost): share one atomic CostGuard ledger across instances and processes` |
| Finding 3 | `fix(cost): hold a reservation for its own declared lifetime and never drop a late commit` |
| Findings 1 to 3 (gate) | `feat(cost): add SpendGate, the single preflight/settle/release path for paid provider requests`; `feat(spend-gate): export the exceptions a consumer must catch` |
| Finding 1 | `fix(harness): admit the W&B request path through the shared SpendGate before dispatch`; `fix(harness): release the reservation on a definitive provider refusal (HTTP below 500)`; `fix(harness): keep the paid answer when settle fails` |
| Finding 6 | `fix(memory): link the attestation correction with an explicit supersedes`; `fix(memory): retire the original attestation over-claim with a linked record` |
| PT review items | `fix(cost-guard): make the legacy budget import one-time even if the store is deleted`; `docs(spend-gate): per-phase timeout, fail-closed default, legacy import and rollback` |
| Hygiene | `docs(tests): complete docstrings on the files the spend remediation touched` |

### orama-system (PR #519)

| Item | Orama commit subjects |
| --- | --- |
| G3 | `feat(seats): pin the evaluator digest and bind a promoted card's receipt to it (G3)`; `test(seats): schema types the receipt fields; fixtures cover the G3 and G9 rules` |
| G9 | `feat(seats): no card, no promotion: dry and live cycles name the card they checked (G9)` |
| Findings 3 and 4 (orama share) | `feat: make the spend adapter a thin forwarder to Perpetua-Tools' SpendGate`; `fix: hold the spend reservation for the whole allowed launch`; `fix: settle a possibly sent live request as unknown and decode its output after the launch`; `fix: start and wait for the launcher explicitly so only a failed start releases` |
| Finding 5 | `fix: close two sandbox process-cleanup gaps`; `fix: observe sandbox child exit through kqueue, not ps` |
| Finding 7 | `docs(biafra): resolve G3 and G9; drop --confirm from the runbook attest command` |
| Integration and hygiene | `fix: integrate the spend-gate and G9 lanes`; `test: check the runbook against the spend gate and tolerate its line wrapping`; the docstring commits (`docs: add docstrings ...`, `docs(tests): complete docstrings ...`) |

Finding 6 (memory) is PT-side and additive.

## Verification so far

- PT integration (12 commits on `c90feebb`): full suite 3670 passed, 5 failed, 13 skipped at
  `23cdc03`. The same 5 fail at the base (the sandbox lacks Git state discovery). The rerun at the
  final PT code head (`docs(spend-gate)` commit) gave 3674 passed, 13 skipped and the same 5.
- Orama integration (all lanes plus the review fixes on `bd5931a2`): 428 passed, 18 skipped
  (macOS-only sandbox tests) across the affected suites against the integrated PT. Docstrings are
  100 percent on all touched files; docstring-only commits were proven by `ast.dump` equality with
  docstrings stripped.

## Independent review verdicts

| Repository | Verdict | Handling |
| --- | --- | --- |
| PT | Approve; no Critical or Important findings. Four Minor items. | All four fixed or documented: settle fallback, `.migrated` marker, per-phase timeout documented, fail-closed default documented. |
| orama | Request changes. | Five fixes decided (items 11 to 15 in doc 76 section 13.2): process-group kill on abnormal exit, a sent request is never released, receipt `delta` comparison, unique pin temp file, sandbox probe check before the child starts. All five implemented with failing-first tests; a real grandchild no longer hangs the cycle (about 8 s before, about 1 s after). |

## Not done

See "Later TODOs" in doc 76 section 13.5 and the execution plan for the open gaps in
[handoff-open-gaps-2026-11-17.md](handoff-open-gaps-2026-11-17.md). Nothing is merged and no live
gate is armed.
