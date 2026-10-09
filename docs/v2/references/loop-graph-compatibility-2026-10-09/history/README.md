# Loop/Graph compatibility — findings bundle (2026-10-09)

Everything produced in this session, in one folder. Nothing was committed, pushed or merged to any repository.

## Contents
| Path | What it is |
|---|---|
| 01-revised-files/…MEMORY…rev2.md | Revision 2 of the 2026-08-26 prompt/loop/graph/MiniGraph recall (re-baselined to merged reality; boundary rules; gap register) |
| 01-revised-files/…RESEARCH…rev2.md | Revision 2 of the state-of-the-art research companion (20 conventions vs live code; security overlay; LangGraph boundary; owner-tagged plan). Corrected after review: adapter description, effect-identity sketch |
| 02-adrs/ADR-DRAFT-D-LG-2… | External-framework interop draft, with errata (5 corrections) |
| 02-adrs/ADR-DRAFT-D-LG-3… | Replacement compatibility via explicit name ownership (user decision: replacement in scope now) |
| 03-review/REVIEW-… | Review of the uploaded compatibility package: approve with changes (2 blocking, 1 decision, 11 non-blocking) |
| 04-evidence/ | Repro of the max_concurrency=0 hang; throwaway import-alias prototype (fake package, not real LangGraph) |

## Key findings
1. Core's LangChain adapter runs the real graph (not topology-only); the LangGraph one is an outbound exporter that executes under LangGraph's scheduler.
2. BUG: abatch(max_concurrency=0) hangs forever; negative values raise a bare asyncio ValueError.
3. The HITL approval binding (request digest, policy revision, scope, expiry) does not exist today; the nearest reference keeps one-time tokens in memory, lost on restart.
4. Errata to my earlier drafts: test extras are published metadata; import-lint must allow lazy outward bridges; routing comparison needs partial order under supersteps; effect keys must exclude the attempt.
5. Unratified: D-LG-1 (policy-layer ownership), D-LG-2, D-LG-3. Replacement mode needs an explicit opt-in; no .pth/sitecustomize, no upstream-named packages.

## Basis and limits
Read-only checkouts: orama-system b131215, Perpetua-Tools e8d7333, perpetua-core c0795bc, oramasys d1656b0. Only the max_concurrency repro and the prototype were executed; no test suites were run. External LangChain/LangGraph behavior is unverified. Tracked content names categories only (no paths, addresses, identities, credentials).
