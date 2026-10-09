# Verification and coordination handoff — 2026-10-09 UTC

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
