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

## Finding to commit subject (orama side)

Commit subjects, not SHAs, because SHAs may change at publication. PT-side commit subjects are in
PT #516's history and are not reproduced here.

| Item | Orama commit subjects |
| --- | --- |
| G3 | `feat(seats): pin the evaluator digest and bind a promoted card's receipt to it (G3)`; `test(seats): schema types the receipt fields; fixtures cover the G3 and G9 rules` |
| G9 | `feat(seats): no card, no promotion: dry and live cycles name the card they checked (G9)` |
| Findings 1 to 3 (orama share) | `feat: make the spend adapter a thin forwarder to Perpetua-Tools' SpendGate`; `fix: hold the spend reservation for the whole allowed launch`; `fix: settle a possibly sent live request as unknown and decode its output after the launch`; `fix: start and wait for the launcher explicitly so only a failed start releases` |
| Sandbox cleanup | `fix: close two sandbox process-cleanup gaps`; `fix: observe sandbox child exit through kqueue, not ps` |
| Finding 7 | `docs(biafra): resolve G3 and G9; drop --confirm from the runbook attest command` |
| Integration and hygiene | `fix: integrate the spend-gate and G9 lanes`; `test: check the runbook against the spend gate and tolerate its line wrapping`; the docstring commits (`docs: add docstrings ...`, `docs(tests): complete docstrings ...`); `ci: follow the Perpetua-Tools head after its audit-identifier fix`; `fix(ci): keep the CI checkout for the adapter tests that need the real guard` |

Findings 4 and 5 are not individually described in the source for this record, so they are not
mapped. Finding 6 (memory) is PT-side and additive.

## Verification so far

- PT integration (12 commits on `c90feebb`): full suite 3670 passed, 5 failed, 13 skipped at
  `23cdc03`. The same 5 fail at the base (the sandbox lacks Git state discovery). A rerun at the
  final PT head is in progress.
- Orama integration (17 commits on `bd5931a2`): 421 passed, 18 skipped across the affected suites
  against the integrated PT. Docstrings are 100 percent on all touched files; docstring-only
  commits were proven by `ast.dump` equality with docstrings stripped.

## Independent review verdicts

| Repository | Verdict | Handling |
| --- | --- | --- |
| PT | Approve; no Critical or Important findings. Four Minor items. | All four fixed or documented: settle fallback, `.migrated` marker, per-phase timeout documented, fail-closed default documented. |
| orama | Request changes. | Five fixes decided (items 11 to 15 in doc 76 section 13.2): process-group kill on abnormal exit, a sent request is never released, receipt `delta` comparison, unique pin temp file, sandbox probe check before the child starts. Being implemented in a parallel lane; not yet verified. |

## Not done

See "Later TODOs" in doc 76 section 13.5. Nothing is merged and no live gate is armed.
