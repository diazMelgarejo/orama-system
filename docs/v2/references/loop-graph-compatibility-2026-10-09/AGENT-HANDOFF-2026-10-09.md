# Loop/Graph compatibility: agent hand-off — 2026-10-09

This is the coordination record for the revision-3 compatibility correction.
It is a review aid, not a ratification of any draft ADR and not authorization
to merge, close, force-push, delete, or rewrite a branch.

## Open pull requests

| Repository | PR | Branch / immutable head | Scope |
| --- | --- | --- | --- |
| Perpetua Core | [#8](https://github.com/oramasys/perpetua-core/pull/8) | `fix/validate-runnable-concurrency` / `7657cf4af98f35ca017b41fef314249d48f6bb8b` | Reject invalid `max_concurrency` before work; preserve omitted/`None` unbounded behavior. |
| Oramasys | [#23](https://github.com/oramasys/oramasys/pull/23) | `docs/compatibility-implementation-handoff` / `0c9851333330683db92d8a0a1d2b58153a785182` | Implementation boundary, policy ownership, and the post-Core pin-update rule. |
| Perpetua Tools | [#430](https://github.com/diazMelgarejo/Perpetua-Tools/pull/430) | `docs/loop-graph-compatibility-evidence-r3` / `962eda52ad7045956c3571778fa49fe132af617a` | Evidence plan and an append-only working-memory hand-off. |
| Orama System | This PR | `docs/loop-graph-compatibility-r3` / pending creation | Canonical revision-3 decision, archive-preservation, and v2 convergence plan. |

## Safe integration order

1. Review and merge Core #8 only after its CI and review are satisfactory.
2. Update the immutable Core pin in a dedicated follow-up to Oramasys #23; do
   **not** substitute a moving branch ref and do not update it before Core #8
   is merged.
3. Review the PT evidence record and Orama canonical record independently.
4. Do not claim framework parity until the real LangChain/LangGraph conformance
   matrix has run against the pinned versions.

The documentation PRs do not modify runtime behavior. The future compatibility
work remains constrained by existing hardware, authorization, egress, and
HITL-refusal policy; upstream parity is best effort only.

## Verification already performed

- Core focused adapter suite: `29 passed`.
- Core full suite: `160 passed, 1 skipped`, with `85.61%` coverage.
- Core red phase reproduced the invalid-concurrency failures before the fix.
- PT repository hygiene: `python3 scripts/review/repo_hygiene.py .` passed.
- Markdownlint passed for the active PT, Core, Oramasys, and Orama records.

## Remaining review gates

- Remote CI and review are still required for each PR; this record does not
  infer their result from local validation.
- The real-framework compatibility matrix, Python 3.11 coverage, and ratified
  ADR/HITL decisions remain future work.
- The historical archive under `history/` remains byte-preserved and is
  deliberately excluded from active-document linting. Its pointer documents
  that exception; it is not a content deletion.

## Branch-safety invariant

Every branch above was created from its recorded base with one normal commit.
No existing remote branch was deleted, force-pushed, rebased in place, merged,
or closed. Future conflict resolution must preserve all intended commits and
records, use a new branch when needed, stage exact paths, verify before one
normal push, and leave merging to an explicitly authorized human decision.

## Next agent checklist

1. Read the PR body and exact head, not only this summary.
2. Check remote CI/reviews and resolve concrete findings on a new normal commit.
3. Preserve append-only PT history; add a superseding record rather than editing
   historical evidence.
4. Keep v1 and v2 independent until an approved migration explicitly connects
   them.
5. Record any refusal and obtain HITL approval before overriding a hardware,
   authorization, or egress disallowance.
