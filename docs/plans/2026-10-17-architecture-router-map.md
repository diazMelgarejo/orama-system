# v1 Architecture Router-and-Map Plan

## Purpose

Keep v1 as the minimal operational glue for local-first workspace flows.
The root architecture map routes a reader to the owner, contract, skill,
test, evidence, and limitation instead of becoming a parallel runtime design.

## Current Starting Point

- The local workspace proof produces an extractive CSV plus a verifiable
  receipt entirely in request memory
  ([plan](2026-10-16-local-workspace.md),
  [code](../../src/orama_system/workspace.py),
  [tests](../../tests/test_local_workspace.py)).

- The portal exposes Simple and Research modes while keeping operator-console
  navigation available.

- Privacy is local by default; any sharing profile is explicit and bounded.
- CIDF owns content insertion. The skill-chain-loop-graph card selects an
  execution shape without granting authorization.

## Delivery Sequence

1. Keep the root architecture map as the top-level router and link its
   canonical CIDF escalation card.

2. For each workflow, record user outcome, artifact, owner, privacy profile,
   inputs, exit condition, verifier, and open limits.

3. Use a skill for one bounded capability; escalate to a chain, bounded loop,
   or explicit graph only when sequencing, retry, or topology needs inspection.

4. Keep maker, evaluator, approver, and external-effect owner distinct for
   consequential work. Reconcile uncertain effects with the owning system.

5. Add adapter contracts before adding retrieval, models, providers, or
   satellites. Local artifact generation and offline verification must precede
   any progressive-sharing path.

6. Expand only behind acceptance tests and receipts. Link stable decisions,
   code, and tests from the map; do not duplicate them in prose.

## Acceptance Checks

- Every route identifies an authority boundary and a stop condition.
- A local-only run can create and independently verify a real artifact.
- A privacy profile is visible in the request, output, and receipt.
- Documentation distinguishes implemented behavior from planned capability.
- PT closure and Phase 0 Wiki references remain secondary matches, not
  authority sources.

## Deferred

Configured retrieval, model adapters, durable recovery, satellite wiring,
provider serving, promotion, and qualification require separate owner
contracts, tests, receipts, and review.

## Cross-map parity

The shared five-graph taxonomy is maintained in each root map's **Shared meaning**
column. The canonical standard-library checker lives in this repository; v2 CI
uses it from an immutable v1 checkout, rather than maintaining a second parser.
Questions, grounding requirements, record shapes and other prose remain local.

Run with explicit candidate checkouts (no network calls or runtime imports):

```bash
python scripts/review/check_architecture_map_parity.py ARCHITECTURE.md /path/to/oramasys/ARCHITECTURE.md
python -m unittest discover -s tests -p test_architecture_map_parity.py -v
```

The `Architecture map parity` workflow in each repository pins its peer checkout
by full commit SHA. To change a shared meaning, prepare both map changes, run the
checker against both candidate files, then update each workflow's peer `ref` to
the reviewed counterpart commit. A check proves that exact pair agrees, not that
a later moving `main` remains synchronized. Review both PRs together and recheck
the merged pair; no runtime dependency or automatic cross-repository write is added.

2026-11-05 synthesis: retain the existing router/treasure-trail map, correct the
planned-controller boundary, add only shared definitions and automated evidence.
The accessible v1 landing reference is squash merge `832b4945` (#409); a historical
pre-squash identifier is not proof of a currently reachable commit.
