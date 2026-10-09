# Verification and coordination handoff — 2026-10-09 UTC

**Historical cutoff:** sections through Remaining release work record revision 3
before its first publication. The later Revision 4 section qualifies them.

## Actual changes

- Core adapter validation and regression tests on base
  `c0795bcea810a9f7cec19e50a617bba91fe5e33d`; no engine/dependency changes.
- Orama preserves all eight original archive members and adds current corrections,
  revised replacement proposal, a new durable HITL draft and portable evidence.
- PT plan and new append-only working-memory follow-up cite the same authority.
- Oramasys handoff cites the design and Core repair without changing its pin.

No commit, push, PR edit, merge, branch deletion or history rewrite. Existing
Orama worktree deletions were not staged, restored or included in these changes.

## Evidence actually observed

| Check | Outcome |
| --- | --- |
| Core new tests before fix | 13 failed, 16 passed; zero timed out, invalid inputs had wrong/absent exceptions |
| Core adapter tests after fix | 29 passed |
| Core full suite, Python 3.12.14 | 160 passed, 1 skipped; 13 expected existing hardware-policy deprecation warnings |
| Core coverage gate | 85.61%, above required 80% |
| Alias prototype portability test before fix | Failed: missing `orama_native` fixture |
| Alias prototype after fix | 9 asserted fake-only checks; subprocess test passes from another working directory |
| Concurrency smoke | 7 checks pass; verifies explicit Core source and emits adapter digest |
| Authored Markdown | 10 files pass the repository-pinned checker; original historical members exempted narrowly to preserve bytes |
| Packaging | Eight historical members compared byte-for-byte; archive integrity and each base patch checked |

The first sandboxed full-suite run stalled in the SQLite worker. A bounded run
outside that restriction passed the entire suite. This was not repaired by
changing SQLite/checkpointer code or hiding tests. Interrupted test processes
are not counted as successful runs.

Test environment: disposable Python 3.12 venv with system-site packages visible;
not a hermetic upstream oracle. Relevant versions: pytest 9.1.1,
pytest-asyncio 1.4.0, pytest-cov 7.1.0, hypothesis 6.168.5, aiosqlite 0.22.1,
pydantic 2.13.5, packaging 26.3. External Agate fixture is pinned at
`41a0da9d52e0131049a1469234ac56f6990fc635`. Reproduce clean/locked oracles
separately before any compatibility release claim.

Python 3.11 is not available locally and must pass CI before promotion. The
real LangGraph oracle test is skipped because no framework is installed in the
normal Core test environment. No real LangChain/LangGraph/Pydantic AI conformance
suite was run. PT/Orama/Oramasys runtime suites were not run: their changes are
documentation/evidence only, not production runtime modifications.

## Remaining release work

1. Review/publish the bounded Core repair and run Python 3.11 CI. Do not merge
   without explicit instruction and required review.
2. Publish the coordinated Orama/PT records to the selected existing branches
   only when instructed; stage exact paths, never `git add -A` in the dirty tree.
3. After Core merge, update Oramasys's immutable dependency pin and run its suite.
4. Ratify D-LG-1/2/3 and durable approval design before broader production work.
5. Build real-framework release oracles; run R3/R4 security/recovery evidence.

Nothing here guarantees flawless full replacement execution. It closes the
verified immediate defects and makes remaining uncertainties explicit gates.

## Revision 4 — later resolution, 2026-10-09

The earlier sections are the revision 3 pre-publication cutoff. Four existing
PRs were subsequently created; this coordinated revision reuses them.
It does not erase the earlier local verification or turn it into merge evidence.
See [execution revision 4](EXECUTION-REVISION-4.md) for the seven requests,
eight follow-ups, approved D-LG-1/D-LG-4 slice and remaining gates.

Core real-framework suite: 180 passed, 87.98% coverage. Framework-free Core:
176 passed, one optional LG test module skipped, 87.88% coverage.
Oramasys: 261 framework-free tests; 271 with ten pinned real offline oracle cells.
The candidate overlay retains the production Core pin. Wheel policy-data smoke
and the input-order mutation harness pass. These are Python 3.12.14 observations;
3.11 and the resulting exact-head GitHub runs must be assessed separately.

The final coordination handoff and PR comments bind each logical fixing commit
and published head. Each branch receives one normal parent-preserving update.
Nothing is merged, closed, force-pushed or deleted. Merge order remains
Orama #388 → PT #430 → Core #8 → Oramasys #23, with review and explicit instruction.
