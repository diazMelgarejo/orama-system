# Loop/Graph coordination handoff — verified follow-ups

Date: 2026-10-09 UTC. This is a later coordination snapshot; revision 3 and
revision 4 records and archived inputs remain preserved.

## Authorization and publication

The operator authorized subsequent corrective patches and publication until
this review batch is complete. The earlier one-update limit no longer blocks
these repairs. Merge approval remains separate. All four PRs remain open;
no force update, history deletion or merge was performed.

| PR | Reviewed/published head | Scope |
| --- | --- | --- |
| [Core #8](https://github.com/oramasys/perpetua-core/pull/8) | `82ce99190e25f9e06513c0fd47326eba4a6ab802` | Concurrency validation, order evidence, optional export contracts and import-family checks |
| [Oramasys #23](https://github.com/oramasys/oramasys/pull/23) | `172231848efc6d2b7a6182716010756cc9b44fe6` | Bounded offline bridges, graph policy, gap diagnostics, oracle bootstrap and regressions |
| [PT #430](https://github.com/diazMelgarejo/Perpetua-Tools/pull/430) | `3ddfc9f6a205e2b153877b4aec225799ba3b4319` | Evidence/memory records and immutable historical revision-3 link |
| [Orama #388](https://github.com/diazMelgarejo/orama-system/pull/388) | Parent of this documentation follow-up: `bea13564f40c02c733624022e4173e8b514e64ba` | Canonical design and coordination evidence |

The final Orama commit is the commit containing this file. Read the live PR head
for its exact SHA; a file cannot embed its own containing commit without recursion.

## Completed review corrections

1. Core's advisory `declared_targets` no longer restricts valid native
   destinations. Finite export maps include every native node and END.
   Dependency-free wiring tests and real routing tests exercise declared,
   undeclared and terminal destinations. This remains topology export;
   it does not establish scheduler or superstep parity.
2. Core and Oramasys import checks match exact framework family roots and
   underscore-prefixed family modules. The AST classifier and subprocess
   blocker use matching rules. Pydantic and independent lookalikes remain
   outside those families.
3. The oracle snapshot pins `editables==0.5` alongside `hatchling==1.27.0`.
   The exact no-deps/no-build-isolation editable installation and pip check
   pass in both supported interpreter jobs.
4. A successfully completed graph without its configured output key now
   raises a descriptive RuntimeError. Failed/interrupted runs continue to
   reject stale output.
5. The oracle-only Core candidate is the exact published Core follow-up SHA.
   The application oracle contains its own declared/undeclared/END regression.
   The production Core pin remains unchanged.
6. PT's revision-3 index is pinned to the immutable historical Orama
   commit `19a81cdff1ef6031f5b31a1b982f6eb46fc84033`.
7. Core and Oramasys PR titles and human summaries now describe the actual
   expanded implementation and current evidence. Existing bot sections were retained.

## Fresh remote verification

| Suite | Python 3.11 | Python 3.12 | Evidence |
| --- | --- | --- | --- |
| Framework-free Core | 180 passed, 1 optional-module skip | 180 passed, 1 optional-module skip | [Core run](https://github.com/oramasys/perpetua-core/actions/runs/37940470376), 87.88% coverage |
| Application and real offline oracles | 279 passed | 279 passed | [Oracle run](https://github.com/oramasys/oramasys/actions/runs/37940594529) |
| Regular Oramasys CI | Passed | As configured by repository workflow | [CI run](https://github.com/oramasys/oramasys/actions/runs/37940594560) |

Core's regular CI skips the optional real-LangGraph test module. The application
oracle matrix supplies fresh real-framework routing evidence; do not describe
Core's framework-free run as execution of that module.

PT and this Orama documentation update trigger their normal checks. Assess the
live exact-head checks before merging. Automated review may produce later
findings; this record is a verification snapshot, not perpetual certification.

## Publication integrity and runner limitation

The previous session's local follow-up evidence is preserved in the revision-4
handoff. The resumed shell stalled even on echo, so fresh local suite execution
was unavailable. Fresh test results above come from GitHub Actions.

Publication used GitHub git-data operations with each exact current remote head
as parent, its tree as the explicit base, and non-force branch updates. The
full remote tree delta was checked for exactly the intended paths, with no
deletions; every changed file was fetched and compared with the intended
content before ref movement. The new published commits reconstruct the fixes
and add oracle coverage; they are not asserted to have the same object IDs or
complete tree as the older local commits. Do not replay the older mail patches
over these already-fixed remote heads.

## Remaining release and integration gates

- Keep all PRs open until explicit merge approval and fresh substantive review.
- Existing review order remains Orama #388, PT #430, Core #8, then Oramasys #23.
- After Core merges, promote only its merged immutable production SHA and
  rerun application and oracle tests. The current candidate is test-only.
- Full LangChain/LangGraph replacement API compatibility, broader/versioned
  oracle cells, streaming/checkpoint/superstep fidelity, durable resume and
  effect recovery remain separate, unfinished capabilities.
- Durable refusal/HITL bindings and use accounting, Telos-owned transport,
  hardware/effect admission and production foreign execution remain gated.
  Operator approval never silently bypasses enforcement.
- Do not ratify D-LG-2/3 or claim 100% parity from this bounded test matrix.
- Preserve v1/v2 independence and all historical memory/source attachments.

## Final scanner and evidence-test follow-up

A broader review included nitpicks outside inline threads. Core's scanner could
miss literal concatenation and literal-only f-strings passed to dynamic imports.
It now evaluates those bounded expressions and reports unresolved import
arguments as DYNAMIC_UNRESOLVED for explicit review. This is a conservative
check, not arbitrary Python evaluation. Core and Oramasys use the same logic.

The test-first commit `c002407cf16675136876ecfc510dc6de36ddb1a8` produced
exactly four expected failing tests on Python 3.11 and 3.12, with the prior 180
passing tests unchanged. The fixing commit passes those regressions.

| Final code PR | Exact head | Fresh evidence |
| --- | --- | --- |
| Core #8 | `b9b44775633c393ed709176a9bb1332014ab9320` | [Python 3.11/3.12 run](https://github.com/oramasys/perpetua-core/actions/runs/37941447515): 184 passed, 1 optional-module skip each; 87.88% coverage |
| Oramasys #23 | `1669fe6bfbc93c9e0017dea9a364856bc2d37208` | [Python 3.11/3.12 oracle run](https://github.com/oramasys/oramasys/actions/runs/37941459074): 283 passed each; [regular CI](https://github.com/oramasys/oramasys/actions/runs/37941458861) also passed |

The Oramasys test-only Core candidate pins the final Core head above. Do not
substitute the earlier candidate from the first snapshot. Production promotion
still requires Core merge approval and a merged immutable SHA.

Orama's active evidence check was converted from unittest to pytest, preserving
the isolated subprocess and all nine prototype checks. The README command was
updated and the normal Test Suite explicitly invokes this evidence test.
The test/build workflow at `c494d7f0fa0eb9f80c006cd2e7a7aeeeb2cb7d3b` was
still running when this final record was written; check the current containing
commit's CI before merge. Historical source attachments remain unchanged.

The earlier tables are deliberately retained as dated intermediate evidence.
This final section supersedes their candidate heads and counts. No broad
replacement-parity or durable approval gate was waived.

## Budget stop and portable gap errors

A later review of the published heads found two remaining Oramasys defects,
fixed in [Oramasys #23](https://github.com/oramasys/oramasys/pull/23) at
`d938dac`:

| Finding | Fix | Evidence |
| --- | --- | --- |
| On `UsageLimitExceeded`, `as_node` returned an error delta, so downstream nodes (including effect nodes) still ran and the run ended `done` | Raise Core's structural `Interrupt` with reason `budget_exhausted` and `resumable: false` | Two-node oracle test asserts the downstream node never runs; it fails on `1669fe6` |
| Gap error classes could not be unpickled (two-argument constructors) | Rebuild from constructor arguments | Round-trip test; fails on `1669fe6` |

Local Python 3.12 against Core candidate `b9b4477`: oracle environment 284
passed; framework-free application suite 271 passed. Core needed no further
change. Check the live exact-head CI before merge; this does not waive any
gate listed above.
