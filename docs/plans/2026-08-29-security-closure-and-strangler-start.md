# Autonomous Execution Plan: Security Closure + Strangler Migration Start

**Status:** authorizes autonomous agents to begin now. Broad strokes by
design — implementers resolve specifics; verification happens after, not
before.

**Read first, don't re-derive:**

- [`plans/security-v2-roadmap.md`](security-v2-roadmap.md) +
  [`plans/security-v2-roadmap-part2.md`](security-v2-roadmap-part2.md)
  (already an agent-execution bundle) +
  [`plans/security-v2-rfc-v1.md`](security-v2-rfc-v1.md)
- PT `.agent/memory/semantic/PT_UNBUNDLING_MIGRATION_MAP_2026-08-29.md`
- `docs/2026-08-12-endpoint-policy-standardization-reconciliation.md` §"Next Steps"

---

## Track A — Security closure (parallel, independent of Track B)

1. **De-duplicate endpoint-policy.** PT's `packages/endpoint-policy` is
   already a real, tested package. Orama-system's
   `src/utils/endpoint_policy_core.py` is a parallel copy, kept in sync
   only by CI contract-parity, not shared code. Make orama-system import
   the real package instead of maintaining its own. Strangler style: add
   the import path, dual-run/diff against the old copy, remove the copy
   only once parity is proven — never a silent single-commit swap.
2. **Execute I1/I2 for real**, per the reconciliation doc's own
   still-open Next Steps: entrypoint inventory across the three repos,
   one `DEFAULTS.md`, a CI check that fails on drift. Nothing here is
   started; start it.
3. **Do not touch doc 03 (MAESTRO/SWARM).** Explicitly v2.5-deferred by
   design — leave it stubbed.

## Track B — Strangler migration start (after Track A or in parallel, not blocking)

1. Finish R2.5 → R3 → R4 → R5 → R6 on the current MiniGraph PR before
   starting new extractions — don't fork attention mid-reconciliation.
2. Run a real dependency-graph inventory of PT's modules (not filename
   intuition) per the unbundling map's own strangler algorithm (§13).
3. First extraction candidate: endpoint-policy (Track A already puts it
   in motion — reuse that work, don't duplicate it as a second effort).
4. Do not touch the memory satellite. `oramasys/anamnesis` doesn't exist
   yet; PT `.agent` stays the authority per D26. No exceptions.

---

## Non-negotiable invariants for every agent, every change

Pointers, not restatement — read the source before acting:

- Strangler only: inventory → contract tests → new interface →
  dual-run/diff → migrate consumers → announce sunset → delete legacy.
  No big-bang swaps (`PT_UNBUNDLING_MIGRATION_MAP` §13).
- No silent dual writable source of truth, ever.
- Fail closed on any missing/unprovisioned dependency — never fall back silently.
- Core (`perpetua-core`) never imports upward from policy/application repos.
- Historical/append-only records (PT `.agent`, `GossipBus`) are never rewritten to fit a new format.
- `mutator != evaluator` holds after every split.
- Every semantic move ships with regression/contract evidence, not just a description of intent.

## Verification note

This plan authorizes autonomous execution now, with compliance review
after the fact — not a request for pre-approval on each step. Agents
should over-document evidence (tests, diffs, dual-run results) precisely
because review is deferred, not skipped.
