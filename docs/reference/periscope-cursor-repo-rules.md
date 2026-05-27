# Periscope — Cursor repo rules (reference)

> **Quadrant:** Reference. **Applies to:** `diazMelgarejo/periscope` checkout opened in Cursor.
> **Canonical copy in repo:** `.cursor/rules/openclaw-fork-guide.mdc` (installed from orama-system).

## Install

From **orama-system** root:

```bash
export PERISCOPE_REPO=~/Documents/oramasys/tools/periscope   # your clone
bash scripts/periscope/install-cursor-rules.sh
bash scripts/periscope/recreate-ordered-prs-onto-merged.sh   # deps/docs PRs → merged
```

### Merge order into `merged`

| Step | Branch | Content |
|------|--------|---------|
| **1** | `onto-merged/01-deps-cargo-tauri` | Cargo lock / tauri 2.11.1 |
| **2** | `onto-merged/02-deps-npm-svelte-postcss` | svelte + postcss only (not full old `deps/2` branch) |
| **3** | `onto-merged/03-docs-cursor-cloud-agents` | `AGENTS.md` Cursor Cloud section (cherry-pick, not stale PR #4 branch) |

Commit and push the `.cursor/rules/` files on branch **`merged`** (not `main`).

## What the rule encodes

Summarizes established doctrine from:

| Doc | Topic |
|-----|--------|
| [`docs/v2/21-periscope-l4-glass.md`](../v2/21-periscope-l4-glass.md) | L4 mission, parsers, hard invariants |
| [`docs/plans/2026-05-24-periscope-l4-integration-plan.md`](../plans/2026-05-24-periscope-l4-integration-plan.md) | Phase A/B work, file paths |
| [`scripts/periscope/rebuild-deps-prs-onto-merged.sh`](../../scripts/periscope/rebuild-deps-prs-onto-merged.sh) | Deps PRs target `merged` |

### Branch model

- **`agentsview`** — grandmother (latest agentsview upstream)
- **`main`** — `latentsignal-org/periscope` mirror only
- **`merged`** — build branch; **all fork PRs base here**

### Cursor-only extras

VM Go version, CGO, frontend-before-tests, git identity, and salvage rules are in the
`.mdc` file so Cursor loads them automatically; they are **not** duplicated in `AGENTS.md`
(which stays agent-neutral).

## Related

- [Agent first-open visibility](agent-first-open-visibility.md) — orama vs periscope surfaces
- [Cursor cloud attribution](../wiki/12-cursor-cloud-commit-attribution.md) — orama-system
