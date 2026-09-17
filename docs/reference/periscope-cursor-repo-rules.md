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

Use stacked naming (`stack/NN`, `[NN/TT → merged]`) from
[`bin/orama-system/skills/stacked-pr-naming/SKILL.md`](../../bin/orama-system/skills/stacked-pr-naming/SKILL.md).
`PR(N+1)` GitHub-bases on `PR(N)`, not all on `merged`.

| Step | Branch | Content |
|------|--------|---------|
| **0** | `stack/00-sync-agentsview-into-merged` | Absorb grandmother lineage into `merged` first |
| **1** | `stack/01-deps-cargo-tauri` | Cargo lock / tauri bump |
| **2** | `stack/02-deps-npm-svelte-postcss` | svelte + postcss only (not full old `deps/2` branch) |
| **3** | `stack/03-docs-cursor-cloud-agents` | `AGENTS.md` Cursor Cloud section (cherry-pick, not stale PR #4 branch) |

Legacy `onto-merged/NN-…` names are superseded. Commit and push Cursor rules on
**`merged`** (not `main`).

## What the rule encodes

Summarizes established doctrine from:

| Doc | Topic |
|-----|--------|
| [`docs/plans/2026-05-24-periscope-l4-integration-plan.md`](../plans/2026-05-24-periscope-l4-integration-plan.md) | L4 mission, PT-adapter boundary, design canon + epilogue (successor to retired doc 21) |
| [`docs/plans/2026-05-24-periscope-l4-integration-plan.md`](../plans/2026-05-24-periscope-l4-integration-plan.md) | Phase A/B work, file paths |
| [`scripts/periscope/rebuild-deps-prs-onto-merged.sh`](../../scripts/periscope/rebuild-deps-prs-onto-merged.sh) | Deps PRs target `merged` |

### Branch model

Lineage: `kenn-io/agentsview:main` → `latentsignal-org/periscope` →
`diazMelgarejo/periscope:merged`.

- **`agentsview`** — grandmother sourced from `kenn-io/agentsview:main`
- **`main`** — mirror of `latentsignal-org/periscope` only (not a PR target)
- **`merged`** — working/build branch combining both lines; **all fork PRs stack here**

### Cursor-only extras

VM Go version, CGO, frontend-before-tests, git identity, and salvage rules are in the
`.mdc` file so Cursor loads them automatically; they are **not** duplicated in `AGENTS.md`
(which stays agent-neutral).

## Related

- [Stacked PR naming](../../bin/orama-system/skills/stacked-pr-naming/SKILL.md)
  — `stack/NN` + `[NN/TT → merged]`
- [Cursor cloud attribution](../wiki/12-cursor-cloud-commit-attribution.md) — orama-system
- [PyPI packaging](periscope-pypi-packaging.md) — release-CI topic, not a Cursor-rules
  topic; linked here only as the other periscope reference doc in this directory
