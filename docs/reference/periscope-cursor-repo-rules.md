# Periscope — Cursor repo rules (reference)

> **Quadrant:** Reference. **Applies to:** `diazMelgarejo/periscope` checkout opened in Cursor.
> **Canonical copy in repo:** `.cursor/rules/openclaw-fork-guide.mdc` (installed from orama-system).

## Install

From **orama-system** root:

```bash
export PERISCOPE_REPO="$OPENCLAW_HOME/periscope"   # or another checkout path
bash scripts/periscope/install-cursor-rules.sh
bash scripts/periscope/recreate-ordered-prs-onto-merged.sh   # deps/docs PRs → merged
```

### ECC bundle mirror (optional sidecar)

Periscope owns its ECC artifacts (`.agents/skills/periscope/SKILL.md`,
`.claude/skills/periscope/SKILL.md`, instincts YAML). orama-system does not
install them — it only verifies mirror integrity when a clone is present:

```bash
export PERISCOPE_REPO="$OPENCLAW_HOME/periscope"   # or another checkout path
bash scripts/periscope/verify-ecc-skill-mirror.sh
```

Canonical sidecar skill: `bin/orama-system/skills/periscope-ecc/SKILL.md` (v1 probe;
v2 orbiting satellite — periscope remains ECC SSoT).

### ECC PR replay (path-scoped)

When `merged` already contains an ECC bundle (e.g. PR #10) and an open PR still
carries pre-merge commits, replay **only the harmonized path delta** onto fresh
`origin/merged` — never merge the stale branch wholesale. See
`bin/orama-system/skills/git-history-surgery/references/path-scoped-pr-replay-reference-card.md`.

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
| [`docs/plans/2026-05-24-periscope-l4-integration-plan.md`](../plans/2026-05-24-periscope-l4-integration-plan.md) | L4 mission, PT-adapter boundary, revalidation (2026-07-28) |
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
