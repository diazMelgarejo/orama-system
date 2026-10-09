# Loop/graph compatibility — revision 4 execution index

**Date:** 2026-10-09 (UTC primary). **Current status:** reviewed changes in four
open coordinated PRs. The [latest verified follow-up handoff](FOLLOWUP-VERIFICATION-AND-HANDOFF.md)
records subsequent patches and CI. Read [revision 4 execution](EXECUTION-REVISION-4.md) first.
D-LG-1's split and D-LG-4 Phase 1 are approved; broader replacement D-LG-2/3
and durable HITL remain gated.
The user authorized implementation of the reviewed corrections in this session,
not a silent declaration that the entire framework surface is compatible.

## Authority and preservation

Read [revision 3 resolutions](REVISION-3-RESOLUTIONS.md) first. They supersede
specific claims, not the historical files. `history/` preserves all eight original
archive members byte-for-byte, including the original review, both ADR drafts,
both rev2 documents and both old scripts. Do not run the historical scripts as
acceptance tests. No memory was deleted or reserialized.

Current replacement proposal: [D-LG-3 revision 3](ADR-D-LG-3-REVISION-3.md).
Ownership of reducer and join declarations: [D-LG-5](ADR-D-LG-5-REDUCER-JOIN-DECLARATIONS.md),
checked by [`ownership-registry.json`](ownership-registry.json); see erratum E12.
Meaning of fan-out, reducers and joins (R3): [D-LG-6](ADR-D-LG-6-R3-REDUCERS-JOINS-FANOUT.md).
Actual outcomes and remaining gates: [verification handoff](VERIFICATION-AND-HANDOFF.md).

Source archive SHA-256:
`872a9632aff766969db533548f7056e444ae9ee01c0821d2fed0a5f5c2da44ff`.

## Cross-repository ownership

| Owner | Deliverable | Boundary |
| --- | --- | --- |
| Orama `docs/v2` | This index, decisions, refusal contract, evidence protocol | Canonical design; not runtime authority |
| PT v1 | [Evidence plan](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/plans/2026-10-09-minigraph-compatibility-evidence-plan.md), append-only working-memory follow-up | No v2 dependency; links are documentation only |
| Perpetua Core | `abatch()` validation and real regression tests | Existing neutral adapter only; no engine growth |
| Oramasys v2 | Future native facade, optional LC/LG bridges, explicit replacement binding | Build on Core's adapters; do not duplicate the scheduler |
| Agate / Phylax / Telos | Hardware / admission / endpoint-security authority | All checks precede parity; no copied policy engine |

Cross-repository links point to PR branches because these files are not merged
into main. Publication and merge are distinct; latest exact heads and checks
are recorded in the PR comments and coordination handoff.

## Execution

Use a disposable Python 3.11/3.12 environment. Install Core's own dev requirements
and its pinned external Agate fixture; record exact installed versions locally.
Do not add LangChain, LangGraph or Pydantic AI to built-package requirements.

From this directory:

```bash
python -I evidence/alias_finder_prototype.py
python -m pytest evidence/test_evidence_scripts.py -q
python -I evidence/verify_abatch_concurrency.py --core-src /checkout/perpetua-core/src
```

From the patched Core checkout:

```bash
python -m pytest src/tests/test_langchain_adapter.py -q
python -m pytest --cov=perpetua_core --cov-report=term-missing --cov-fail-under=80
python -m compileall -q src/perpetua_core
```

The alias prototype is fake-only, assertion-based, self-contained and cleans up
its temporary modules. `packaging` is its only non-standard test dependency.
The concurrency verifier requires an explicit source path, checks the loaded
file and emits its digest. A hang, wrong exception or false assertion exits
nonzero. No provider call, grant, PR mutation or real import interception occurs.

## Promotion gates

1. Core fix passes both interpreter jobs, full suite and the 80% coverage gate.
2. Human/automated review of the exact published head before merge.
3. Pin the merged immutable Core commit in Oramasys only after it exists;
   rerun its suite. Do not substitute a branch name or fabricated SHA.
4. Apply the approved ownership split; separately ratify replacement ADRs,
   inventory exact v0.x and v1.x releases,
   then run unchanged real-framework oracle fixtures in separate locked environments.
5. Implement the [durable refusal/approval contract](../2026-10-09-compatibility-refusal-hitl-contract.md)
   as a complete security vertical slice before enabling any override path.
6. R3 reducers/joins precede R4 resume/effect recovery. Missing capabilities
   stay absent or explicitly blocked, never present-but-silently-weakened.

No fake-package evidence establishes real `Runnable` type identity, callbacks,
`astream_events`, checkpoint wire formats, pip resolution or all-public-API parity.

Current R3 qualification: [audit, replay and compatibility](../remaining-capabilities/R3-AUDIT-REPLAY-AND-COMPATIBILITY-2026-10-10.md).
The baseline ownership registry is preserved; additive policy-R3 and Core-R3
candidate profiles qualify their exact producer/consumer environments. A profile
pass is not a production-pin promotion or a full API replacement claim.
