# Periscope lineage modernization — optional epic

> **Status:** OPTIONAL — not a prerequisite for L4 integration, mirror maintenance, or ECC work.  
> **Cost:** High (history surgery, multi-day classification, replay validation).  
> **Decision date:** 2026-07-28

## Problem statement

`periscope:merged` carries valid dual-pedigree ancestry after the 2026-07-28
reanchor, but it is **not** a clean semantic patch stack on the current AgentsView
lineage. A naive reading of `git log` or ahead/behind counts suggests hundreds of
commits of divergence even when mirror tips (`main`, `agentsview`) are exact
upstream SHA matches.

Reconstructing `merged` as a readable stack of fork-specific patches atop current
AgentsView would require:

1. Classifying **45 historical fork patches** against **583 AgentsView commits**.
2. Replaying the post-reanchor **20-file delta** on the classified base.
3. Re-validating every open PR and integration test against the new ancestry.

## Why this is optional

| Need | Satisfied without lineage modernization |
| --- | --- |
| Upstream mirror exactness | `main` and `agentsview` are byte-identical to upstream tips |
| Fork integration | `merged` is the integration base; PRs replay onto it |
| L4 observability | PT adapter + existing Periscope OpenClaw parser |
| ECC bundles | Path-scoped PR replay onto fresh `merged` |
| Desktop sidecar fix | Functional contract rename only (`sidecar("periscope")`) |

Track A (mirror + operational maintenance) can close while this epic remains
deferred indefinitely.

## When to revisit

Consider this epic only if **all** of the following become true:

- Multiple agents routinely confuse `merged` ancestry with content divergence.
- Upstream contribution PRs are blocked by unreadable fork history.
- A maintainer allocates dedicated time for history surgery with rollback tags.

## If executed later

Follow the dual-pedigree and path-scoped replay reference cards:

- [`bin/orama-system/skills/git-history-surgery/references/dual-pedigree-reanchor-reference-card.md`](../../bin/orama-system/skills/git-history-surgery/references/dual-pedigree-reanchor-reference-card.md)
- [`bin/orama-system/skills/git-history-surgery/references/path-scoped-pr-replay-reference-card.md`](../../bin/orama-system/skills/git-history-surgery/references/path-scoped-pr-replay-reference-card.md)

Preserve old tips (`backup/*` tags, `refs/pull/*/head`) before any force-push.
Rebasing or force-updating remote branches requires explicit current-user
authorization.

## Related

- [`docs/plans/2026-05-24-periscope-l4-integration-plan.md`](2026-05-24-periscope-l4-integration-plan.md) — 2026-07-28 revalidation § Revised Phase A
- Perpetua-Tools `.agent/memory/working/PERISCOPE_DUAL_PEDIGREE_REANCHOR_2026-07-28.md`
- [`docs/reference/periscope-pypi-packaging.md`](../reference/periscope-pypi-packaging.md) —
  unrelated operational item (PyPI publish, disabled on a name collision, not a history
  problem), linked here only because it's the other open periscope item a reader may
  already have in mind
