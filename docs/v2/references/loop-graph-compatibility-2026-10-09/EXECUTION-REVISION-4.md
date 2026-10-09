# Loop/graph execution — revision 4

**Date:** 2026-10-09 UTC. This is the current qualification of revision 3 and the
uploaded iteration document. Historical statements describe their own cutoffs.
Approval covers D-LG-1's separate policy and D-LG-4 Phase 1. D-LG-2/3 broad
replacement and durable HITL remain gated. No all-API or flawless execution claim.

## Seven requests and eight follow-ups

| Request | Resolution | Evidence / owner |
| --- | --- | --- |
| Pydantic AI bridge | Phase 1 implemented, offline only; production/deferred approval refused | [D-LG-4](ADR-D-LG-4-PYDANTIC-AI-BRIDGE.md), Oramasys #23 |
| D-LG-1 | Separate graph_id-bound policy with application transclusion | [ADR](ADR-D-LG-1-POLICY-OWNERSHIP.md), [contract](GRAPH-POLICY-CONTRACT.md) |
| No eager imports | AST, exact typing branches, live lazy allowlist, blocked import-time tripwire, dependency metadata checks | Core #8 and Oramasys #23 |
| Tiered gap errors | ModuleNotFoundError for modules; AttributeError for symbols; explicit explain diagnostics | Oramasys #23 |
| Registers and ownership | Corrected register below; historical tables preserved | Orama #388 |
| Eight follow-ups | Current-state qualifiers, branch links, order mutation, lint, active ADR, pin-overlay evidence, mandatory stub tests, archive preservation | Four coordinated PRs |
| Greptile order-test finding | Delayed first input; completion-order mutant rejected at None/2/100; serial 1 control | Core #8 mutation script |

Returning None from a finder permits later installed finders to win; it is not
an unsupported-module gate. The test uses an uncached real temporary module.
pytest.importorskip skips our ModuleNotFoundError subtype, so conformance tests
assert it directly; supported oracle cells never use importorskip.
Symbol `__getattr__` raises AttributeError to preserve hasattr/getattr(default);
from-import can replace it with generic ImportError. explain(target,
matrix_row=...) retains the actionable reason. Dunders remain plain AttributeError.
No process-wide import interception or replacement activation ships here.

## Verification cutoff

On Python 3.12.14, real-framework Core suite: 180 passed, coverage 87.98%;
Oramasys candidate-overlay suite plus ten offline oracle cells: 271 passed;
framework-free application suite: 261 passed, 87.83% coverage. Mutation harness passes.
The framework-free environment and exact-head GitHub checks are recorded in the
publication comments and final coordination handoff. No remote pending check
is called a pass. Raw logs and machine paths remain local.

Oramasys retains production Core pin 8dde861. Its full suite is exercised against
the candidate checkout with the external Agate/Telos fixtures. A simultaneous
pip request for the pin and candidate correctly fails source resolution; install
pinned dependencies first, then install the candidate with --no-deps for testing.
After Core merges, a separate immutable pin bump must rerun the whole suite.
This includes the seven intervening registry/discovery/dependency commits,
not just the abatch change.

## Current gap register

| ID | Current disposition |
| --- | --- |
| G1–G3 | Prior stale state, pasted question and malformed YAML corrections retained |
| G4 | Full local suites and pinned real oracles now evidenced; other interpreters await CI |
| G5 | Loop-to-graph design remains a proposal, not an automatic rewrite |
| G6 | budget_exhausted implemented above Core as a non-resumable structural interrupt that stops the run (corrected in the [follow-up](FOLLOWUP-VERIFICATION-AND-HANDOFF.md)); taxonomy otherwise unchanged |
| G7 | Approved D-LG-1 ownership split and bound policy lint implemented |
| G8 | Native adapter executes Core; exporter runs node callables/topology under LG scheduler |
| G9 | Reducers/joins and durable resume remain open |
| G10 | Explicit boundaries retained |
| G11 | Agate / Phylax / Telos authority retained; bridge production refuses |
| G12 | Ledger is audit, not dedupe; durable wiring remains open |
| G13 | Graph artifact admission to Phylax remains unverified |
| G14 | Checked import contract implemented in both code repos |
| G15 | Durable single-use HITL not implemented; no override path enabled |
| G16 | Mandatory dependency-free stub and pinned real LG oracle implemented |
| G17 | Adversarial order test and mutation verification implemented |
| G18 | Tiered error primitives and semantics tests implemented; general facade remains unimplemented |
| G19 | Phase 1 bridge approved and bounded implementation complete; production remains gated |
| G20 | ConditionalEdge router/declared-target path_map export fixed and tested |

## Convention and ownership qualifications

Carry forward all twenty conventions in the archived iteration §7.2. Change
only convention 4 (declared_targets now exported), 12 (budget_exhausted wrapper),
15 (structural and policy-binding lint both tested), and 2 (independent policy
schema/revision/hash now present). Reducers/joins, checkpoint lineage, durable
effect identity, evaluator optimization and cancellation taxonomy remain open.
The default policy is lintable intent, not executable admission.

Core keeps neutral adapters and structural mechanics. Oramasys owns new
interop bridges, diagnostics, policy and future replacement facades. Orama owns
normative docs; PT owns v1 memory/evidence. Agate owns hardware, Phylax admission,
Telos endpoint transport. No upward Core dependency or v1 runtime coupling.

## Publication, preservation and next step

Use existing PRs [Orama #388](https://github.com/diazMelgarejo/orama-system/pull/388),
[PT #430](https://github.com/diazMelgarejo/Perpetua-Tools/pull/430),
[Core #8](https://github.com/oramasys/perpetua-core/pull/8),
[Oramasys #23](https://github.com/oramasys/oramasys/pull/23).
Merge order remains #388 → #430 → #8 → #23, with review and explicit merge
authorization. Current cross-links point to the published PR branches until
merge. Do not declare merged state early. Commit logical batches, publish each
branch once, reply with exact fixing SHA and re-read resulting heads.

The eight original archive members remain byte-identical. The uploaded iteration
is also preserved verbatim under history and qualified by this document.
Append-only semantic lessons qualify the earlier saga without rewriting their
candidate files or JSONL rows. D-LG-2/3, R3/R4, v0.x oracles, full framework API
parity, durable grants and production foreign egress are future acceptance gates.
