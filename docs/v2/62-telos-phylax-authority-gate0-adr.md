# ADR 62: Telos/Phylax Authority Split — Gate 0 Decisions

**Status:** proposed, 2026-09-06
**Context doc:** `2026-09-06-telos-reconstruction-and-gap-closure-plan.md` — an
external planning document that lives outside this repo (in the operator's
local `../references/` workspace, not a tracked orama-system path or a
git submodule), so it is named here, not linked, per this repo's own
no-workstation-paths policy (`CLAUDE.md § 6`). It is not required to read
this ADR; the relevant conclusions are restated inline below rather than
assumed available.
**Related:** [Gateway Lifecycle PR](https://github.com/oramasys/oramasys/pull/1)
(portable URL). `2026-09-06-telos-phylax-initial-scaffold-handoff.md` is the
same kind of external, unlinked reference as the context doc above.

## Why this ADR exists

The gap-closure plan's Gate 0 requires "one cross-repo ADR in Orama that
states the authority table and resolves" four questions, before any Gate 4
implementation begins. That ordering was already violated once: a concurrent
agent built full local `oramasys/telos` and `oramasys/phylax` scaffolds the
same day this plan was written, without a Gate 0 decision to build against.
This ADR is the decision that should have come first. It is written knowing
the scaffold exists, not pretending it doesn't.

## Decision 1: does Telos begin as an in-process module, or a standalone repo?

**Decided: standalone repo, but not yet released or consumed.**

The plan's own default position was "start in-process behind the port... split
into a repository only when independently consumed or released" — explicitly
deferring repo creation. That default is overridden here, not because the
reasoning was wrong, but because the fact on the ground already contradicts
it: `oramasys/telos` and `oramasys/phylax` exist as separate git repositories
with their own licenses, packaging, and boundary records. Retroactively
forcing them back into an in-process module inside Oramasys would be pure
process theater — it deletes real, tested code to satisfy a sequencing rule
whose purpose (avoid premature repo proliferation) is no longer achievable
once the repos already exist.

The repos remain **unreleased and unconsumed**: no PyPI publish, no remote
push, no importer outside their own test suites. That is the actual
mitigation for "don't create a repo prematurely" — not repo non-existence,
but zero external commitment until Gate 4 validates the contract.

## Decision 2: single executable source for endpoint primitive behavior

**Decided: `oramasys/telos`'s `EndpointRef`/`EndpointUseRequest`/`EndpointUseDecision`
dataclasses become the canonical schema.** The plan's own pseudocode
(`endpoint_ref: str`) and the Gateway Lifecycle PR's `TelosPort.authorize(*,
purpose: str, endpoint: str)` are both **not** canonical — they predate the
scaffold and use a weaker, untyped string for the endpoint identity where the
scaffold uses a validated, normalized dataclass.

Required follow-up (Gate 1 exit evidence, not satisfied by this ADR alone):
the Gateway Lifecycle PR's `TelosPort` protocol must be updated to accept
`telos.EndpointRef`/`EndpointUseRequest`, not a raw `str`, before Gate 4
wiring. Until that lands, the Gateway Lifecycle PR's `TelosPort` is a
**historical draft**, not a second canonical source — it does not get
independently maintained in parallel with the `oramasys/telos` schema.

`packages/endpoint-policy` (Perpetua-Tools) and `src/utils/endpoint_policy_core.py`
remain the canonical source for **transport identity parse/build** (a
different, lower layer — see the authority map in the gap-closure plan).
They are not in scope for this decision; conflating them is exactly the
"model endpoint validation vs. transport identity vs. Telos" confusion Gate 2
exists to prevent.

### Sub-decision: Phylax gets the identical treatment, explicitly

This ADR's title names both Telos and Phylax; the decisions above are written
in Telos terms but apply symmetrically to `oramasys/phylax`, stated here so
neither is left implicit: `oramasys/phylax`'s `ArtifactRef`/`CompileRequest`/
`RuntimeAdmissionRequest` dataclasses (commit `8ce8f69`) are canonical for
artifact/runtime admission the same way Telos's are canonical for
endpoint-use authorization — no separate pseudocode or PR-draft contract
competes with them. Phylax is likewise unreleased/unconsumed, frozen pending
this ADR, and does not get a forced Core-retirement date.

### Sub-decision: conversion from transport identity into `EndpointRef`

Neither Telos nor this ADR performs that conversion. `telos/src/telos/contracts.py`
already states this explicitly (`EndpointRef` docstring): `is_public` and the
rest of the ref's fields are trusted evidence that **must** come from the
canonical endpoint-policy primitive (Decision 2's transport-identity layer,
`packages/endpoint-policy`/`endpoint_policy_core.py`) before a request ever
reaches Telos. This ADR does not design that conversion function — it belongs
to Gate 1's importer-inventory work, not Gate 0.

### Sub-decision: audit-persistence ownership

`telos.EndpointAuthorizer` currently keeps `DecisionRecord`s as an in-memory
list (`self._records`) — there is no durable audit store yet, and this ADR
does not create one. Ownership: a durable, append-only decision/evidence
store is Gate 3/Gate 4 scope (the gap-closure plan's Gate 4 exit evidence
requires "audit correlation reaches lifecycle events" and Gate 3 requires
"stored routing-state integrity validation" for the adjacent Oramasys
lifecycle store) — not a new, separate authority. Telos's own durable store,
when built, should reuse whatever storage pattern Gate 3 establishes for
`RoutingStateStore` rather than inventing a second persistence mechanism.

## Decision 3: contract/versioning strategy for shared behavior vectors

**Decided: JSON fixture vectors, checked into `oramasys/telos`, consumed by
any repo that constructs or authorizes an `EndpointRef`.** Not yet written —
this ADR authorizes the work, it does not complete it. Minimum required
vectors before Gate 4 begins: exact-match allow, exact-match deny,
unknown-purpose deny, public-endpoint-without-opt-in deny, and the
policy-version rollover case flagged as a still-open gap in the plan's
Verification matrix.

`EndpointPolicy.version` is the versioning key. A behavior-vector file names
the policy version it was generated against; a consumer failing against a
newer version's vectors is a signal to re-certify, not silently pass.

**Fail-closed on version mismatch, stated explicitly (this was previously
undecided):** when a consumer's `EndpointPolicy.version` does not match the
version a behavior-vector file was generated against, the consumer MUST
treat every decision from that policy as `deny`/`unknown_purpose` until
re-certified against current vectors — never fall back to "compat mode" or
skip vector validation. This mirrors `EndpointAuthorizer`'s own existing
deny-by-default posture (`policy.evaluate()` returns a deny reason code for
any unresolved case) rather than introducing a new, separate fallback
behavior for the versioning layer specifically.

## Decision 4: Core compatibility timeline

**Decided: no forced timeline yet — Perpetua Core's `HardwarePolicyResolver`
and `llm.py` stay as they are until Gate 5.** Setting a retirement date now,
before Gate 4 has even produced a working vertical slice, would be the same
premature-commitment mistake as the standalone-repo default in Decision 1,
just pointed the other direction. Gate 6's own exit evidence (a full
consumer/dependency inventory) is the correct place to set dates.

## What this ADR does NOT authorize

- It does not authorize wiring `TelosPort`/`PhylaxPort` into the Gateway
  Lifecycle's `run()` method — that is Gate 4, gated on Gate 3 (now
  substantially closed, see the plan's Gate 3 status note) and Gate 1
  (behavior vectors, not yet written).
- It does not authorize a PyPI release, GitHub remote, or any external
  consumer of `oramasys/telos` or `oramasys/phylax`.
- It does not retroactively bless every line of the existing scaffold as
  correct. The `/autoplan` review that produced this ADR also found and
  fixed one real security bug in the scaffold (`EndpointRef.is_public`
  previously defaulted to a caller-spoofable `False`) — fixed independently
  of this ADR, commit `88fba4b` in `oramasys/telos`. Other review findings
  (`expires_at` unused, no policy-version-rollover test) remain open and are
  tracked in the gap-closure plan's Gap assessment table, not repeated here.

## Regime boundary (added 2026-09-06, post-Gate-1 reconciliation)

v1 (`Perpetua-Tools`, `orama-system`) and v2 (the `oramasys` GitHub org) are
not a stepped evolution — they are separate regimes. **v1 receives no
implementation or migration changes.** This repo (`orama-system`) is used
going forward only as a docs/planning authority (this ADR included);
`Perpetua-Tools` is used only for `.agent/` memory and read-only mining of
its existing contract surfaces. All v2 implementation, including everything
in Decisions 2–3 above, lands exclusively in `oramasys/*` repos. Where an
earlier section of this ADR could be read as implying a PT-side edit (e.g.
"shared behavior vectors... run in PT and Orama"), read it instead as:
parity/conformance tests that live in v2 and observe v1 as a read-only
golden reference, never a file change to v1. Full detail and the reconciled
Gate 1 split: the gap-closure plan's "Regime boundary correction" section.

## Consequences

- The gate-ordering rule in the gap-closure plan needs an enforcement
  mechanism, or this will happen again. This ADR does not design one; it is
  flagged as follow-up work, not solved here.
- Gate 1 now has a concrete, non-optional first task: update the Gateway
  Lifecycle PR's `TelosPort` protocol to the canonical `oramasys/telos`
  schema before any further Gate 4 planning.
