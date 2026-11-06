# C1 orama-system documentation dispositions — 2026-11-06

**Register row:** C1 in the
[master closure plan](../MASTER-CLOSURE-AND-IMPLEMENTATION-PLAN-2026-11-06.md),
orama-system scope. **Base:** orama-system `main` `1a370467`.
**Input:** the 2026-11-06 architecture and migration docs review. Its findings
are claims to verify. Each one below was rechecked against the current file at
the base revision. The review itself is not tracked in this repository.

Scope: findings that concern orama-system files. These are the v1-map rows, the
link gaps, sections 4.1–4.10, section 5 and tables 7.1–7.3. Findings about
Oramasys or Perpetua-Tools files are listed only where the review groups them
with orama-system rows. Those are marked **out of scope** and routed to their
owner lanes.

## Disposition vocabulary

- **already-fixed:** corrected on `main` before this branch; the commit is cited.
- **fixed:** corrected on this branch by a dated in-file note, errata entry or
  map link.
- **fixed (routed):** corrected on this branch in the
  [status routes table](../architecture-status-2026-11-06.md#status-routes-for-documents-not-edited-in-place),
  with no in-file edit. Either the file has existing markdownlint debt (error
  count at `1a370467` given), so a changed-file lint run would fail on text this
  branch did not write, or it is the canonical source of a generated downstream
  pointer.
- **historical / superseded:** the source is a dated record and needs no change
  beyond the cited route.
- **rejected:** the recommended change was not made, for the reason given.
- **blocked:** needs an action outside this lane; the missing action is named.
- **out of scope:** belongs to another repository's owner lane.

Preserved provenance-pinned inputs were not edited.

## Section 3: map corrections and link gaps

| ID | Finding | Current state and disposition | Source |
| --- | --- | --- | --- |
| M-1 | v1 map names Telos/Phylax/Agate as current v1 owners | **already-fixed**: v1 and v2 rows split; PT owns v1 endpoint and hardware policy | `1d92fb7f`; `ARCHITECTURE.md` owner table |
| M-2, M-7, M-8, M-9, M-11 | v2-map rows | **out of scope**: Oramasys map | Oramasys lane |
| M-3 | lease wording | v1 map part **already-fixed**: job-claim leases separated from run leases. The v2-map part is **out of scope** | `1d92fb7f` |
| M-4 | `ORAMASYS-MASTERY-v3` listed as normative | **already-fixed**: labeled "review draft; not a normative graph contract" | `1d92fb7f` |
| M-5 | PT closure record cited as current qualification | **already-fixed**: labeled historical; retrospective linked | `1d92fb7f` |
| M-6 | home of design, registry and schema unstated | **already-fixed**: owner row added; schema located in `docs/schemas` | `1d92fb7f`, `6f5112b9` |
| M-10 | PT wiki citation too broad | **already-fixed**: "historical STM/mesh-security" | `1d92fb7f` |
| M-12 | PT row understates v1 role | **already-fixed**: "v1 orchestration, coordination, telemetry and memory" plus v1 endpoint row | `1d92fb7f` |
| L-1 | orama `docs/v2` link gaps | **already-fixed** for 17, 62, 68, 69, 71, 72, 74, D-LG-6, D-LG-7, refusal contract and m1-gen2 (`1d92fb7f`). **fixed** for the spec index, 23, 24, 31, 61, 67, D-LG-5, R4 index, ownership registry, activation plan, readiness baseline, R0–R2 freeze and closure register | `ARCHITECTURE.md` "Further sources" |
| L-2 | Oramasys `docs/` link gaps | **out of scope**: these are v2 sources, routed to the Oramasys map | Oramasys lane |
| L-3 | Perpetua-Tools link gaps | **already-fixed** for the saga retrospective (`1d92fb7f`). **fixed** for `AGENTS.md`, the minigraph evidence plan, the coordination README, `LESSONS.md` and the lockstep decisions record (links checked against PT `e4cd20e`) | `ARCHITECTURE.md` "Further sources" |

## Section 4: cross-document findings

| ID | Finding | Current state and disposition | Source |
| --- | --- | --- | --- |
| 4.1-a | README:260 GraphSpec owner | **already-fixed** | `1d92fb7f` |
| 4.1-b | 58 §7, 59, 57 header | **already-fixed**: dated status banners | `1d92fb7f` |
| 4.1-c | integrated plan and harmonization guide | **already-fixed** banners (`1d92fb7f`); E12 scope **fixed** | errata E12 extension |
| 4.1-d | consolidated cross-reference; instruction-audit parts 1–2 | **fixed**: dated notes plus E12 | in-file notes |
| 4.1-e | `plans/2026-08-29` GraphSpec authority | **fixed**: dated note | in-file note |
| 4.1-f | E12 scope too narrow | **fixed**: E12 now names the September documents and docs 58/59 | errata E12 |
| 4.1-g | PT unbundling map §2 | **out of scope** | PT lane |
| 4.2-a | 57, 58, 59 merge/pin/R3 status | **already-fixed** | `1d92fb7f` |
| 4.2-b | loop-graph README and D-LG-6 status lines | **already-fixed** | `1d92fb7f` |
| 4.2-c | 71 and 72 `open_grant_authority` | **fixed**: script uses `open_grant_verifier` since Oramasys `15eae8d`, verified at `fe4049e` | notes in 71, 72 |
| 4.2-d | 72 Phylax #11 status contradictions | **fixed**: #11 merged as `e41f1e8`, an ancestor of Phylax `main` | note in 72 |
| 4.2-e | 56 Anamnesis "absent" | **fixed**: scaffold `99bc106`; runtime still deferred | note in 56 |
| 4.2-f | 66 Half B status line | **already-fixed**: historical banner | `1d92fb7f` |
| 4.2-g | E10 dialer "remains migration target" | **fixed**: dated E10 update, citing the post-351 addendum and the `telos` import in `src/orama/gateway/dialer.py` | errata E10 |
| 4.2-h | Oramasys ledger, gateway pins, loaded-identity ADR | **out of scope** | Oramasys lane |
| 4.3-a | 01 §3 and §6b Core policy | **already-fixed** | `1d92fb7f` |
| 4.3-b | 04 lift table | **fixed (routed)**, 8 lint errors | status routes |
| 4.3-c | README Core policy lines | **already-fixed**: reconciliation banner | `1d92fb7f` |
| 4.3-d | 00 D4 | **fixed**: dated note | note in 00 |
| 4.3-e | v2-map Core caveat | **out of scope** | Oramasys lane |
| 4.4-a | 68 §2 owner row | **already-fixed**: "Planned `oramasys/oramasys` internal controller module", plus header correction. No further edit was needed | `1d92fb7f` |
| 4.4-b | 68 title and "satellite" wording | **rejected**: the filename and title are retained because inbound links depend on them; the header states the internal-module decision | doc 68 header |
| 4.4-c | 67 lacks IC-5 qualifier | **fixed**: dated note citing IC-5 and §6 | note in 67 |
| 4.4-d | 14 §8 builds the v2 queue in PT | **fixed (routed)**, 13 lint errors | status routes |
| 4.5-a | 63, 66 narrower Telos scope | **already-fixed** | `1d92fb7f` |
| 4.5-b | security-v2 plans | RFC **fixed** in-file; roadmap (82 errors), part 2 (28 errors) and JSON manifest **fixed (routed)** | note; status routes |
| 4.5-c | 30 v2 router in PT | **fixed (routed)**: scoped to v1 PT. An in-file note is **blocked** until a paired regeneration of PT's ADR-002 pointer, which pins doc 30's hash | status routes; `scripts/git/sync-docs-v2-pointers.sh` |
| 4.5-d | `plugin-api-public.md` auth "none" | **fixed (routed)**, 2 lint errors | status routes |
| 4.5-e | PT phase-0 master plan :117 | **out of scope** | PT lane |
| 4.6-a | doc 20 placement and "# 18" title | **fixed**: dated note. The heading was not renumbered, to preserve the text | note in 20 |
| 4.6-b | `rag-and-memory.md` | **fixed (routed)**, 2 lint errors | status routes |
| 4.6-c | 70 v1/v2 portal naming | **fixed**: note distinguishes `knowledge_gateway.py` from Oramasys `src/orama/knowledge/` | note in 70 |
| 4.7-a | HITL doc self-declared authority | **fixed (routed)**, 29 lint errors. Builds on the `1d92fb7f` status paragraph | status routes |
| 4.7-b | 70 and 32 cite HITL as canonical | **fixed**: dated notes repoint to the refusal contract and CONTRACT-DURABLE-HITL-EFFECTS | notes in 70, 32 |
| 4.8-a | `agate-mvp-design.md` wrong owner; ignores unknown keys | **fixed (routed)**, 6 lint errors | status routes |
| 4.8-b | 07 and 42 cite it | 07 **fixed (routed)**, 43 lint errors. 42 is **historical / superseded**: it is the current Agate orbit, and its citation now leads to the routed correction | status routes |
| 4.9-a | two R-gate series | **already-fixed**: glossary in status doc, README and D-LG-6 banners. Renaming to RQ1–RQ8 is **rejected** because it would rewrite dated records | `1d92fb7f` |
| 4.9-b | graph R3 "open" in September documents | **fixed**: E12 extension and notes | errata E12 |
| 4.9-c | link the Oramasys receipt from RELEASE12 round | **fixed** | note in RELEASE12 round |
| 4.10 | 73 "APPROVED" but unexecuted | **already-fixed**: banner; M-6 covers the map | `1d92fb7f` |

## Section 5: migration sequencing

| ID | Finding | Current state and disposition | Source |
| --- | --- | --- | --- |
| 5-a | no single sequencing authority | **fixed** for closure work: the README banner and 04 route name the master plan as the one register. The broader product order is C12 and is not decided here | README banner; status routes |
| 5-b | 04, 14 §8, 18, 29 §5 | **fixed (routed)**, lint errors 8 / 13 / 25 / 11 | status routes |
| 5-c | README Sequencing "NOW (May 2026)" | **fixed**: banner marks it as snapshot | README banner |
| 5-d | integrated plan R-series order | **already-fixed** banner; E12 **fixed** | `1d92fb7f`; E12 |
| 5-e | PT coordination docs | **out of scope**: PT lane (Part 2 is parity migration, not v2 deferral) | PT lane |

## Table 7.1: README, `02-modules/`, docs 00–37

| Document | Disposition | Source |
| --- | --- | --- |
| `README.md` | Status, GraphSpec, open-questions heading and next-slot **already-fixed** (`1d92fb7f`). Test counts, topology, Sequencing and the tree omitting 53–55 and 74 **fixed** | README banner |
| `00` | **fixed**: D4, D17/D19/D20 versus "Proposed", and where later decisions live | note in 00 |
| `01` | **already-fixed** | `1d92fb7f` |
| `04` | **fixed (routed)**, 8 errors | status routes |
| `05`, `09`, `10`, `12` | **historical**; **fixed (routed)**, errors 22 / 18 / 22 / 2 | status routes |
| `08` | **fixed**: historical note | note in 08 |
| `14`, `18`, `29` | **fixed (routed)** | status routes |
| `20` | **fixed** | note in 20 |
| `30` | **fixed (routed)**; in-file note **blocked** on paired PT pointer regeneration | status routes |
| `36`, `37` | **fixed**: 00 note states their "Proposed" status governs | note in 00 |
| `02-modules/README.md` | **fixed (routed)**, 1 error: path is `perpetua_core.graph.plugins.subgraphs` (Core `6d75cfe`) | status routes |
| `02-modules/plugin-api-public.md`, `rag-and-memory.md`, `alphaclaw-mcp-smoke-test.md` | **fixed (routed)**, errors 2 / 2 / 8 | status routes |

## Table 7.2: docs 38–74 and `plans/`

| Document | Disposition | Source |
| --- | --- | --- |
| `56` | **fixed** | note in 56 |
| `57`, `58`, `59`, `63`, `66` | **already-fixed** | `1d92fb7f` |
| `67` | **fixed** | note in 67 |
| `68` | **already-fixed** (§2 row and header); title change **rejected** | `1d92fb7f` |
| `69` | **fixed**: no envelope code in Core `6d75cfe`; Core ownership is planned | note in 69 |
| `70`, `71`, `72` | **fixed** | notes |
| `73` | **already-fixed** | `1d92fb7f` |
| `74` | **rejected** as a defect: "design (unratified)" is accurate, and its run-lease scope is already separated in the map | `ARCHITECTURE.md` |
| `plans/security-v2-*` | RFC **fixed**; others **fixed (routed)** | note; status routes |
| `plans/2026-08-27-*` (×2) | **fixed**: historical notes | notes |
| `plans/2026-08-29-*` | **fixed** | note |

## Table 7.3: `references/`

| Document | Disposition | Source |
| --- | --- | --- |
| `integrated-v2-migration-plan-2026-09-09.md`, `migration-harmonization-2026-09-09.md` | **already-fixed** banners; E12 **fixed** | `1d92fb7f`; E12 |
| `consolidated-cross-reference-and-execution-order.md` | **fixed** | note; E12 |
| instruction-audit parts 1 and 2 | **fixed** | notes; E12 |
| `errata-corrections-to-preserved-documents.md` | **fixed**: E10 update and E12 extension, extending the `1d92fb7f` top banner | errata |
| `HUMAN-IN-LOOP-ACCOUNTABILITY.md` | **fixed (routed)**, 29 errors | status routes |
| `ORAMASYS-MASTERY-v3.md` | **already-fixed**: map label; the doc's own status already reads "Review draft" | `1d92fb7f` |
| `agate-mvp-design.md` | **fixed (routed)**, 6 errors | status routes |
| loop-graph `README.md`, `ADR-D-LG-6` | **already-fixed** | `1d92fb7f` |
| `EXECUTION-REVISION-4` | **historical**: dated cutoff; no change | — |
| `2026-10-09-compatibility-refusal-hitl-contract.md` | **already-fixed**: linked from map | `1d92fb7f` |
| `RELEASE12-IMPLEMENTATION-ROUND-2026-10-26.md`, `activation-readiness-baseline-2026-10-26.md`, `r0-r2-contract-freeze-2026-10-26.md` | **fixed**: forward pointers to the Oramasys 2026-11-04 receipt; no closure claimed | notes |
| `P0-THROUGH-T2` rev2 | **historical**: self-declared superseded | — |
| `instruction-debt-audit-2026-09-09.md`, `instruction-debt-remediation-plan.md`, `oramasys-migration-execution-plan.md`, `portable-memory-sanitization-runbook.md` | **historical**: provenance-pinned and not edited. E12 extension states their status lines are history | errata E12 |

## C2 artifact locations (pending publication)

C2 is not closed by this ledger. Its two artifacts are being written in parallel
lanes. They are listed here as paths, not links, until each is published on its
repository's `main`:

- **Manual v1 compatibility characterization** (PT owner): Perpetua-Tools
  `docs/coordination/manual-cleanup-characterization-2026-11-06.md`. It covers
  current `liveness.py` and `claims.py` cleanup and callers. PT stays manual
  under D1, and the shims are retained under D2. *Pending publication.*
- **v2 claim contract** (Oramasys owner): Oramasys
  `docs/architecture/orchestrator-controller-claim-contract.md`. It specifies
  expiry, fencing, refusal and recovery against
  [doc 68](../68-orchestrator-controller-satellite.md) sections 9–10.1 and
  IC-1–IC-29. *Pending publication.*

C2 acceptance needs both artifacts on their `main` branches and a check against
doc 68. C2a and C3 stay blocked on that.

## Open items

- Doc 30 in-file note: blocked on a coordinated PT ADR-002 pointer regeneration.
- Files with lint debt could take in-file notes after a separate formatting
  cleanup. This ledger does not exempt or hide that debt.
- Oramasys and PT findings are tracked by their owner lanes.
