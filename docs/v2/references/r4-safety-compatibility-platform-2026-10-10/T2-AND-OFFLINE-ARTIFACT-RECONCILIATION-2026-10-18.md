# T2 and offline artifact evidence reconciliation

Status: dated additive reconciliation, 2026-10-18. This record qualifies older
open-gap descriptions with later source and executed tests. It does not rewrite
their historical claims, ratify E1 or activate any capability.

## T2 delivery gap has a later implementation

Historical T2 receipts described a real gap: the admission gate consumed delivery
health, while the normal runner did not drain Core's observations into delivery.
The current implementation is
[commit 99283f789f078689404653d5105b597e614160b0](https://github.com/oramasys/oramasys/commit/99283f789f078689404653d5105b597e614160b0).
Its `src/orama/graph/admission_runtime.py` composes Core's plugin runner and
per-run delivery; authoritative attempt identities come from the ledger. Critical
delivery failures stop progression and produce conservative terminal records.

Source reviewed: Oramasys main
`b5f3821804715665b716ab600ea8419810bea920`. Runtime tests executed in the
isolated G1 checkout at `3518beb1e1edf01bc25f6233a2e9091611287f0b`, whose
runtime and these test files equal that main source:

```text
src/tests/core_gate/test_admitted_observation_delivery.py
src/tests/core_gate/test_admitted_observation_unknown_disposition.py
src/tests/core_gate/test_delivery_seam.py
Result: 12 passed.
```

Broader generation-2 qualification is recorded separately in the
[accepted evidence receipt](../m1-gen2-qualification-evidence-receipt-2026-10-18.md):
consumer `133553a6`, harness `902d2a8e`, run `39070456148`, hosted Ubuntu with
Python 3.11 and 3.12. Operator acceptance is explicit in that receipt.

The historical gap therefore must not initiate another observation adapter or
invented attempt/hold identity. This closure does not imply durable graph
continuation, remote-effect reconciliation or grant serving.

## The first deterministic CSV proof also exists

The grounded-graphs architecture plan's first offline slice is implemented in
`src/orama/workspace/{workflow,verify,api}.py` and documented by the repository's
[local workspace plan](https://github.com/oramasys/oramasys/blob/b5f3821804715665b716ab600ea8419810bea920/docs/plans/2026-10-16-local-workspace.md).
The later hardening is
[commit daa153fb41b3c0df37b1c3eeaa3f4ce8574993e3](https://github.com/oramasys/oramasys/commit/daa153fb41b3c0df37b1c3eeaa3f4ce8574993e3),
merged through Oramasys #54.

The writer produces extractive CSV in request memory. The separate verifier
reparses the CSV, checks source support, spreadsheet safety, row count, artifact
digest and version-2 reconstruction of the hashed input. The API bounds input
and keeps control-plane authentication. Version-1 receipts retain their explicit
limited legacy verification path.

Executed at G1 head `28f33123ce49df2e0f2381ad0efcbc5a92e1ffc4`, with these
runtime/test files unchanged from the main source above:

```text
src/tests/test_local_workspace.py
Result: 29 passed.
```

Tests include unsupported inputs, formula cells, receipt/input tampering,
a network-blocking assertion for the default local profile, no-disclosure
checks across every privacy profile, metadata redaction, input limits, a
bare-carriage-return CSV round trip and unknown receipt versions. This is
bounded extractive attribution evidence. It does not establish source
authenticity or semantic entailment.

## Remaining work is explicit

- Publish the complete requirement-to-node map from the original grounded-graphs
  plan and obtain independent scope review before closing all of its artifact gates.
- Durable artifact storage/publication, replay keys, crash recovery and configured
  retrieval/model adapters remain separate follow-on work; the current receipt
  expressly limits itself to request memory and no external effects.
- E1 integrated schemas, independent review and operator ratification still
  precede T3. T4/T5, remote autonomy and serving retain their own gates.
- Physical hardware execution and non-Ubuntu platforms are outside the accepted
  generation-2 receipt's scope.

The [C1 source and test map](E1-C1-SOURCE-RECOVERY-AND-TEST-MAP-2026-10-18.md)
provides the owner boundaries and exact existing M1 nodes for the next E1 review.
