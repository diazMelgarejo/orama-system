# Stacked PR Naming — Git Reference Card

> **OSSF-1 atomic card.** Thin skill: [`../stacked-pr-naming/SKILL.md`](../../stacked-pr-naming/SKILL.md).
> Load when opening, retitling, rebasing, or stacking PRs so merge order is
> obvious in GitHub and `PR(N+1)` is always based on `PR(N)`.

## Purpose

Minimize stack conflicts by encoding **base, order, and total width** in the
branch name and PR title. Reviewers merge **top-down** (`00` first).

Security stacking (`SECURITY.md` / `docs/SECURITY-POLICY.md`) is the same
doctrine with a **severity-ordered** topic prefix. This card is the **naming
format**; those docs remain the **priority order** for security work.

## Integration base by repo

| Repo | Integration base (`stack/00` parent) | Not an agent PR base |
|------|--------------------------------------|----------------------|
| `orama-system`, `Perpetua-Tools` | `main` | — |
| `diazMelgarejo/periscope` | `merged` | `main` (upstream mirror), `agentsview` (grandmother lineage) |
| AlphaClaw fork | `feature/MacOS-post-install` | `main` (upstream mirror), `pr-4-macos` |

Periscope lineage (do not invert):

```text
kenn-io/agentsview:main
  → latentsignal-org/periscope
    → diazMelgarejo/periscope:merged   ← working / PR target
```

`merged` absorbs later grandmother updates from `agentsview`; **all other
fork PRs stack onto `merged`**, not onto `main` or `agentsview`.

## Formats (always apply)

### Branch

```text
stack/NN-short-topic
```

- `NN` is zero-padded (`00`, `01`, …).
- `short-topic` is lowercase hyphenated.
- Standalone (non-stacked) work still uses dated names
  `yyyy-mm-dd-NNN-brief-summary` — see
  [`docs/wiki/08-git-hygiene-and-branching.md`](../../../../../docs/wiki/08-git-hygiene-and-branching.md).
  **Stacked work uses `stack/NN-…`**, not a dated name.

### PR title

```text
[NN/TT → <integration-base>] <type>: <summary>
```

- `NN` is this PR’s index (same as the branch).
- `TT` is the stack width (total PRs in this stack).
- `<integration-base>` is the **repo integration branch** (`main` / `merged` /
  `feature/MacOS-post-install`), even when GitHub `base` for `NN>00` is the
  previous stack branch.

### PR body (first lines)

```text
Stack: NN/TT
Integration base: <integration-base>
GitHub base: <integration-base | stack/(NN-1)-…>
Depends on: <none | stack/MM-…>
```

## Base chain (conflict-minimizing)

```text
<integration-base>
  └─ stack/00-…     → PR title [0/TT → base]   GitHub base = integration-base
      └─ stack/01-… → PR title [1/TT → base]   GitHub base = stack/00-…
          └─ stack/02-… → …                    GitHub base = stack/01-…
```

Rules:

1. `PR0` (`stack/00`) branches from current `origin/<integration-base>`.
2. `PR(N+1)` is **rebased on `PR(N)`’s branch** before opening.
3. Merge **strictly** `00` → `01` → … → `TT-1`.
4. One logical fix per PR. Shared tests live on the earliest PR that needs them.
5. Wrong-base open PRs (for example periscope Dependabot targeting `main`)
   close as superseded; replay unique patches onto the stack.
6. Ask before rewriting an existing remote branch (lease + operator approval).

## Worked example (periscope)

```text
merged
  └─ stack/00-sync-agentsview-into-merged
      └─ stack/01-deps-cargo-tauri
          └─ stack/02-deps-npm-svelte-postcss
              └─ stack/03-docs-cursor-cloud-agents
```

Titles:

```text
[0/4 → merged] sync: absorb agentsview lineage
[1/4 → merged] build(deps): cargo / tauri bump
[2/4 → merged] build(deps): svelte + postcss (targeted)
[3/4 → merged] docs: Cursor Cloud + lineage policy
```

Order `00` first so later PRs rebase onto the absorbed grandmother lineage,
not onto a stale `merged` tip.

## Skills that load this card

| Skill | Why |
|-------|-----|
| [`stacked-pr-naming/SKILL.md`](../../stacked-pr-naming/SKILL.md) | Canonical OSSF-1 entry |
| [`git-history-surgery/SKILL.md`](../SKILL.md) | Stacked-family rebase after sibling merge (Decision 14) |
| [`git-pending-push-guard/SKILL.md`](../../git-pending-push-guard/SKILL.md) | Do not push a stack step with pending `*_HEAD` |
| [`using-git-worktrees/SKILL.md`](../../using-git-worktrees/SKILL.md) | Board jobs / parallel agents cut from the **stack parent**, not a random tip |
| [`cursor-pr-body/SKILL.md`](../../cursor-pr-body/SKILL.md) | Titles/stack lines; body still comment-only unless operator grant |
| [`oramasys-method/SKILL.md`](../../oramasys-method/SKILL.md) | Integrative merge of stacked conflicts |
| [`fable5-git-rebase-safety/SKILL.md`](../../fable5-git-rebase-safety/SKILL.md) | Tree-twin vs “behind” after a stack rebase |
| [`code-review/SKILL.md`](../../code-review/SKILL.md) | Review stacked PRs in merge order |
| [`cursor-agent/SKILL.md`](../../cursor-agent/SKILL.md) | Fan-out must not open duplicate PRs against the integration base |
| [`security/SKILL.md`](../../security/SKILL.md) | Security stacks use this naming + `SECURITY.md` priority |
| [`path-scoped-pr-replay-reference-card.md`](path-scoped-pr-replay-reference-card.md) | Replay unique paths onto the **current stack parent** |

## Policy docs (do not fork the format)

- [`SECURITY.md`](../../../../../SECURITY.md) § Security PR stacking
- [`docs/SECURITY-POLICY.md`](../../../../../docs/SECURITY-POLICY.md) (same stacking rule)
- [`docs/wiki/08-git-hygiene-and-branching.md`](../../../../../docs/wiki/08-git-hygiene-and-branching.md)
- [`docs/reference/periscope-cursor-repo-rules.md`](../../../../../docs/reference/periscope-cursor-repo-rules.md)
- [`oramasys-method/references/integrative-merge.md`](../../oramasys-method/references/integrative-merge.md)
