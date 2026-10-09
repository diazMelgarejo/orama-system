# Revision 3 — final-review corrections and execution decisions

This additive resolution supersedes the identified claims in preserved revision
2 inputs. It does not erase them or ratify D-LG-1/2/3. Basis: the final review and
the user's subsequent authorization to apply all corrections on 2026-10-09.
Session provenance is the supplied archive plus the conversation; no public
transcript URL was supplied and none is invented.

| ID | Historical claim / defect | Current resolution |
| --- | --- | --- |
| B1 | Core concurrency works without invalid-bound contract | `None` is unbounded; positive non-bool integers are bounded. Other values raise `ValueError` before effects, even for empty batches; sync `batch()` uses the same path |
| B2 | Approval bindings are available through an existing mechanism | New durable contract, not existing capability; see the dedicated linked record. Until implemented, override execution remains denied/pending |
| E1 | Alias prototype is reproducible from the zip | Original fixture was omitted. Revised script creates temporary fixtures, asserts outcomes and works from any directory |
| E2 | Fake identity check establishes real replacement compatibility | Fake-only evidence. No real LangGraph, LCEL, installer or checkpoint parity claim follows |
| E3 | Total routing order and no raw event-payload comparison | Compare documented public event fields and causal partial order. Preserve same-step nondeterminism only where upstream permits it; never normalize away errors, omissions, security decisions or timing guarantees |
| E4 | Pydantic AI agent runtime bridge matches "patterns only" | Not established by that decision. Patterns remain native; real agent fixtures may be research targets. Production bridge deferred to a separate explicit decision, never a P2 prerequisite |
| E5 | Research YAML mirrors complete serialized GraphSpec | Illustrative policy-envelope sketch, NOT `GraphSpec.from_dict()` input. Structural serialization requires `graph_id`, `max_steps`, metadata and actual `__start__` / `__end__` sentinels; use `GraphSpec.create().to_dict()` rather than hand-written identities |
| E6 | Merge-ref inventory proves no open PR touches graph design | Unverified outside the directly checked API scope; do not use absence of merge refs as a complete PR inventory |
| E7 | Alias same-object result preserves native metadata automatically | Import machinery can replace `__spec__`. Prototype restores native import metadata and checks pickle identity; production reload/introspection/thread safety still need oracle evidence |
| E8 | Synthetic distribution metadata proves pip compatibility | Interpreter lookup and packaging specifiers only. Pip resolves installed distribution metadata, not a runtime meta-path finder; wheel/resolver behavior is unproved |
| N1 | Two copied approval descriptions | One canonical refusal/HITL record; PT and convergence plan link to it |
| N2 | Vague upper application owner | New facade/bridges belong in `oramasys/oramasys`; Core retains the existing neutral adapters |
| N3 | One implementation means removing Core adapters | Reuse Core adapters, preserve one traversal authority; no duplicate scheduler |
| N4 | Exact releases but version lines unstated | Both v0.x and v1.x are targets; each exact release needs its own locked oracle and evidence matrix |
| N5 | Pydantic AI interop row missing | Research-only/deferred row; not a production runtime commitment |
| N6 | Published test extras are framework-free | Use isolated lockfiles or non-published dependency groups; verify built wheel `Requires-Dist` |
| N7 | Resume creates a fresh operation key | Durable run/thread + logical operation identity survives restart; attempt ID is evidence only |
| N8 | Raw evidence beside tracked sanitized records | Raw logs, installed paths and topology stay local-only. Track sanitized summary and digest, never sensitive raw content |
| N9 | Uploaded ADR citation has no repo target | All originals now preserved under `history/`; current links resolve locally |
| N10 | User statements have no provenance | Archive hash, date and session scope above; keep user decisions distinct from proposed ADR text |
| N11 | Free v2 redesign permits engine growth | Freedom is within doc 57's kernel boundary; no new scheduler or concrete security policy in `engine.py` |

## Smallest effective implementation

Reject invalid concurrency at the existing adapter entry point rather than add
timeouts to callers. Keep evidence throwaway and self-contained rather than
install an import hook into normal applications. Preserve research/history and
overlay precise corrections rather than silently rewrite accepted records.
Centralize the cross-cutting approval design rather than duplicate it in PT.

## Required evidence beyond the repaired scripts

- Positive limits, zero/negative/bool/non-integer limits, empty inputs, no effects
  on rejection, input ordering, and the synchronous bridge.
- Absent/supported/unsupported/broken optional installations; no eager imports
  or auto-install; installed distribution metadata is not proof of object origin.
- Explicit replacement activation; default shadow refusal, late-import refusal,
  unrelated prefix preservation, package/relative imports, reload, pickling,
  metadata enumeration and already-imported mixed-object handling.
- Production import binding must be serialized before worker startup; never
  let concurrent threads partially switch namespace ownership.
- Foreign runnables/agents are untrusted-effect code: no effects without
  enforceable process/sandbox egress controls and Phylax admission. An in-process
  callback or duck-type check is not a security sandbox.
- Full suites and coverage on Python 3.11 and 3.12; pinned upstream release
  matrix separately. A successful policy refusal is enforcement evidence,
  not an ordinary parity pass.

## Architecture status

The replacement scope is approved as a goal. The exact alias/metadata strategy,
GraphSpec policy ownership ADR and durable HITL runtime remain proposal-stage.
The corrected fake prototype is not shipped production aliasing code. Do not
convert its metadata or object heuristics into authorization.

## Revision 4 qualification

[Execution revision 4](EXECUTION-REVISION-4.md) is the later resolution.
The operator approved D-LG-1's independent policy binding and D-LG-4 Phase 1,
implemented in the existing Core/Oramasys PRs with real offline framework
evidence. This qualifies earlier ownership and native-pattern-only wording.
It does not ratify general replacement activation, production foreign egress
or durable grant execution. Preserve every historical source member.
