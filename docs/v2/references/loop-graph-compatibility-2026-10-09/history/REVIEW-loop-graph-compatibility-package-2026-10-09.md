---
title: "Review — Loop/Graph compatibility package (2026-10-09)"
date: 2026-10-09
reviewed:
  - "orama-system docs/v2/plans/2026-10-09-minigraph-external-compatibility-convergence.md (convergence plan)"
  - "Perpetua-Tools docs/plans/2026-10-09-minigraph-compatibility-evidence-plan.md (evidence plan)"
verdict: "Approve with changes. Two blocking items (B1, B2) and one decision to confirm (D1)."
basis: "Read-only. orama-system main b131215, Perpetua-Tools main e8d7333, perpetua-core main c0795bc. Neither file is on main yet. One behavior was executed (max_concurrency=0); no test suites run."
---

# Review — Loop/Graph compatibility package

**Verdict: approve with changes.** The package is accurate where it checks code,
corrects four real errors in my D-LG-2 draft, and keeps the kernel boundary
intact. It needs two blocking fixes, one decision confirmed, and some tightening.

## 1. Claims verified

| Claim in package | Result |
|---|---|
| LangChain adapter executes the Core graph; `abatch()` honors `max_concurrency` | **True** — read in `langchain_adapter.py` |
| LangGraph exporter result runs under LangGraph's scheduler; MiniGraph interrupt/`max_steps` do not transfer | **True.** Wording nit: it exports node callables as well as topology, so "scheduler-translating exporter" is more precise than "topology-only". It also passes no `path_map`, so `declared_targets` are lost |
| Doc 57 wording "supported builder/topology API and invoke/stream surface"; events v2 and saver serialization excluded | **True** — doc 57 §17 |
| Doc 25 §5 makes the agAIntra test suite the drop-in proof | **True** |
| Linked docs 17, 24, 25, 57, 62 exist at the relative paths used | **True** |
| PT memory `MINIGRAPH_OBSERVER_PATTERN_RECONCILIATION_2026-08-27.md` exists and keeps the Pydantic AI patterns-without-runtime decision | **True** |
| "Through the existing approval mechanism" (operator identity, request digest, policy revision, scope, expiry, use limits) | **Not supported.** See B2 |

## 2. Corrections the package makes to my D-LG-2 draft — all accepted

1. **`config` was not unused.** `max_concurrency` works.
2. **A test extra is published metadata.** "Installed only via a test extra" still declares a dependency.
3. **My import-lint rule would have failed Core's own `LangGraphExporter`.** That exporter lazily imports `langgraph` by design. The right rule is "no eager or required import, with lazy outward bridges allowlisted".
4. **A total order of routing choices is not proof of equivalence.** Under supersteps, comparison needs a partial order.
5. **Effect identity must not include the attempt.** My GraphSpec sketch keyed on `run_id:node:attempt`, which was wrong.

I have applied these as errata to the D-LG-2 draft and fixed the sketch in the rev2 research file.

## 3. Blocking findings

**B1 — Real bug, which the plan's step 3 only hints at.** `abatch(config={"max_concurrency": 0})` hangs forever because of `asyncio.Semaphore(0)`. I confirmed this by running it. A negative value raises a bare `ValueError` from asyncio. The plan should name this as a defect with a regression test, not just "validation of concurrency limits". The fix belongs in Core's adapter, since the user's placement decision keeps the existing adapters in Core.

**B2 — The approval mechanism the HITL section relies on does not exist in that form.**
- The nearest record is `docs/v2/references/HUMAN-IN-LOOP-ACCOUNTABILITY.md`. It has `approval_token`, GPG-signed tokens, and one-time tokens kept in an **in-memory set cleared on restart**.
- That design does not bind an approval to a request digest, policy revision, scope or expiry.
- Its replay protection is lost on restart, which is exactly the R4 durable-resume case.

Fix by stating plainly that the binding contract is **new**: it extends the HITL reference and must give durable single-use records. Until it exists, every "approved" path stays denied/pending.

## 4. Decision to confirm

**D1 — Replacement compatibility (unchanged upstream imports).** The two documents record different things:
- The package records "replacement compatibility" as user-confirmed: existing `import langgraph` code runs unchanged.
- In this session, the answer chosen was a surface that "must work by changing nothing but the import". That is *namespace* compatibility in the package's own table.

Replacement mode is the riskiest row:
- The only workable mechanism is an explicit opt-in launcher that installs an import hook. That is import interception, even if opt-in.
- It cannot coexist with a real `langgraph` in the same environment.
- It must never publish a distribution under an upstream name, which would be dependency confusion.

The plan correctly calls packaging "a design task, not a shipped capability".

**Resolved 2026-10-09:** the user put replacement in scope now. The design is in `ADR-DRAFT-D-LG-3-replacement-compatibility-name-ownership-2026-10-09.md`.

## 5. Non-blocking findings

1. **Split the HITL/refusal contract into its own `docs/v2` record.** It is cross-cutting: it applies to any effect, not only compat. It is about 40% of the convergence plan and is restated almost word for word in the PT plan. Two copies will drift, which goes against the ecosystem's "zero fragmentation" rule. The PT plan should link to it, not restate it.
2. **Name the code target.** Your boundary rule says planned code targets `oramasys/oramasys`, but:
   - the convergence plan says "upper application layer";
   - the PT plan's handoff names Core, Orama and PT but never oramasys.

   Both should name `oramasys/oramasys`, and say that Core's two existing adapters stay in place.
3. **"One compatibility implementation" conflicts with keeping Core's adapters.** State that Core's adapters are the neutral Runnable-shape and export subset, and that the oramasys layer builds on them rather than duplicating them.
4. **Version scope is unstated.** This session's direction was v0.x **and** v1.x. The plan says only "exact upstream releases". It should list both version lines, or record that v0.x was dropped.
5. **Pydantic AI interop is missing from the release matrix.** This session's direction was to run real Pydantic AI agents as interop test targets. Add a row: a black-box agent as a graph node, with tools and structured output, no runtime dependency.
6. **Use dependency groups for oracle environments.** PEP 735 `[dependency-groups]` are not part of built-distribution metadata, so they meet the no-dependency rule more simply than separate repos or environments. Supported by recent pip and uv, but check the versions before relying on this.
7. **Effect identity across resume.** `run_id` must be the durable run/thread identity, not a per-process run. Otherwise every resume mints a new key and defeats deduplication.
8. **Evidence hygiene (doc 47).** The PT plan records "platform" and "installed artifacts" and keeps raw evidence next to normalized output. Raw evidence can contain workstation paths and hostnames. State that raw evidence stays local-only and that only sanitized evidence is tracked.
9. **Dangling citation.** Both files cite "the uploaded D-LG-2", which is not in any repository. Either commit it as a historical record or cite it as "session draft, not in repo".
10. **Attributed user statements need a pointer.** "The user confirmed …" appears several times with no link to where it was said. Add the session or record reference, so a later reader can check the scope (see D1).
11. **"V2 internal design can change freely."** Fine for the application layer. Add "within the doc 57 kernel boundary" in the same sentence, so it is not read as licence to grow `engine.py`.

## 6. Manifest note

The manifest says the Orama checkout used to prepare this package has
**pre-existing deleted files** under `bin/config/`, `bin/orama-system/skills/`
and `scripts/`. They were correctly excluded, but that working tree is dirty.
Before anyone commits these two files from it, stage only the two paths
explicitly, so the deletions are not swept into the commit.

## 7. Recommended edits, minimal

1. Add B1 as a named defect, with a regression test, to plan step 3.
2. Reword the HITL binding as a new contract extending the HITL reference (B2), and move it to its own `docs/v2` record. Have both plans link to it.
3. Resolve D1, then state version lines, the Pydantic AI interop row, and the `oramasys/oramasys` target.
4. Add the doc 47 evidence-hygiene line and the durable-`run_id` line.
