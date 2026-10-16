# T0 — restoration and registry-baseline refresh

**Date:** 2026-10-10 UTC. **Status:** completed prerequisite evidence refresh; P0 remains
open. This record restores canonical documentation bytes and records the exact R3 baseline
without promoting a runtime pin or enabling an R4 capability.

## Publication-integrity correction

The earlier browser publication of this reference set saved only the visible editor portion.
The live PR head `f6cec32891fb19e7a7b37b700e3440571991d029` consequently truncated thirteen
documents, including most of `PLAN-R4-EXECUTION.md`. The complete local source survives at
Orama commit `662a360b`; it is the restoration source for this change. This is a correction
of the publication artifact, not a rewrite of the original source or a new design decision.

Before restoration, each source blob was compared byte-for-byte with the surviving local
original. The following SHA-256 values identify the restored files:

| Path | SHA-256 |
| --- | --- |
| `ADR-D-LG-6-R3-REDUCERS-JOINS-FANOUT.md` | `8efe69bc93926a6bdd6a2e09294e8a106395a06a55ee5127cd249f9bc69a897a` |
| `ADR-D-LG-7-R4-SAFETY-COMPATIBILITY-PLATFORM.md` | `f937fbc37d7d12c6479498f5945653e13d8f555c767cac6ede36ae79d924f6f3` |
| `CONTRACT-ARTIFACT-ADMISSION.md` | `813c2689ce26fc34af47babf6d44d20f6c449b4ec161f6c5cd3a289f6c87e887` |
| `CONTRACT-COMPATIBILITY-REPLACEMENT.md` | `49c4d680efc24aa197afc97caa0aa6de95c093c00badfbafe8056bf64e885be2` |
| `CONTRACT-DURABLE-CONTINUATION.md` | `6f7c5d4191d1e4ca7005e8f27d813017c38e85bdfe828654a577b44f2ce7818a` |
| `CONTRACT-DURABLE-HITL-EFFECTS.md` | `ff209bb03b3b271171ea9f5e338afb98a7f236545830f72e98697746afbcacfc` |
| `CONTRACT-FOREIGN-PROVIDER-TRANSPORT.md` | `717ef07563b413391784d3ec33b9b037019a5631c15efcb887b080f9b828d472` |
| `CONTRACT-MULTI-HOST-STAGES.md` | `18b794745266d007360485215e96778b75208d33b898fd146c7a1aec34381c3e` |
| `PLAN-R4-EXECUTION.md` | `aeab2f46d17afdf63cffbfdfa743fe7febe8a6638e8a76ba3ab405445dcc4c6a` |
| `README.md` | `8e388f0949f7165bfe9843aae13c30a9ca6c17fba7ef3d4640e3f8869208038c` |
| `REGISTER-RETAINED-V1-CONCEPTS.md` | `9a7d66b4f2dc8a0081de942e3d681a39dc015d10bb3c6cd50609acd476364276` |
| `REGISTER-TRACEABILITY.md` | `f326fc53e9138cfe36984c87fdd5347af75b205a0a1ba5aa5751cad6a6e7d4db` |
| `REVIEW-RECORD.md` | `91671f7e4bda071ffdc218e2c78f409cb7d7e7047810d49ce068c322100a676d` |

## Fresh source and registry evidence

| Surface | Exact revision | Tree SHA | Role |
| --- | --- | --- | --- |
| Perpetua Core `main` | `4d217f6b9e94e36554a9427198b8c2c4b7febc47` | `0890ef970ab26fa7982ea15fc235c0fe9d1a603f` | Merged R3 producer (Core #9) |
| Oramasys `main` | `f4dbf338138ede5967b4d3456e940750467e9b1f` | `579fd199ff254345d2f3e4dd99c65ae2720f741f` | Merged R3 consumer (Oramasys #25) |
| Orama R4 PR branch before this correction | `f6cec32891fb19e7a7b37b700e3440571991d029` | recorded by Git | Truncated publication to repair |

The canonical registry and current consumer snapshots agree byte-for-byte:

| Profile | Canonical Orama file | Oramasys snapshot | SHA-256 | Interpretation |
| --- | --- | --- | --- | --- |
| baseline | `ownership-registry.json` | `graph-ownership-registry.json` | `c1bf6b519f703184745e61142f259ae8eb73d163210bb1395437f8a82c2b402f` | Production schema-1 baseline retained |
| policy-r3 | `ownership-registry-policy-r3.json` | `graph-ownership-registry-policy-r3.json` | `7aeed7456db148383698f6df97a38632dbf72f23d411f9c773ed6cb10ab777fb` | Candidate policy qualification |
| core-r3 | `ownership-registry-core-r3.json` | `graph-ownership-registry-core-r3.json` | `498e9383667252b841845d4dc061853adfe3e3864d976a3e2f7c8a59eea3adab` | Candidate Core qualification |

Oramasys production still pins pre-R3 Core `04759a50c748444ff97136ea95c1e1289eac3a1a`.
Its candidate file pins merged Core `34e4a8d22212d38d6ab100c1ad7fb2b19f56cb68`.
The candidate profiles are evidence, not a promotion. P0 must promote the production pin and
the registry baseline together only after its complete clean-install and consumer qualification.

## T0 disposition

- The damaged publication is restored from a locally verified committed source.
- The canonical registry baseline and both candidate profiles are refreshed against current
  Core and Oramasys `main` fixtures.
- D-LG-6 remains approved with the merged Core #9 and Oramasys #25 evidence.
- This record does not claim P0, durable continuation, durable HITL, provider transport, or
  upstream replacement compatibility. Those gates remain governed by the execution plan.
