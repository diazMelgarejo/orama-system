# PR #166 and PR #169 — Git Surgery, Recovery, Reanchor, and Replay Analysis

Date: 2026-07-17  
Repository: `diazMelgarejo/orama-system`  
Method: `/oramasys-method` — AFRP Type C, Expert, Mode 2  
Status: analysis and next moves only; no branch rewrite or merge performed

## Executive decision

**Do not merge or conventionally rebase either preservation PR.**

Both branches diverged from the same obsolete merge base and now contain hundreds of commits that overlap heavily with work already absorbed into current `main` through later PRs and repository reorganizations. A whole-branch rebase would replay superseded history, reintroduce deleted layouts, and manufacture conflicts that do not represent current product intent.

Use this recovery pattern instead:

1. retain the original head as an immutable safety/audit ref;
2. classify commits and trees against current `main` using tree-twins and `git cherry`;
3. create a fresh recovery branch from current `main`;
4. replay only unique, still-valid intent in small thematic batches;
5. verify every batch before opening a replacement PR;
6. close the preservation PR as superseded only after all accepted work is accounted for.

## Ground truth

Current comparison target:

- current `main`: `81e24e24b99eefb4a2748b53c4cce65bf498b575`
- shared merge base for both preservation branches: `ffe76f41959f1363052d8e948ee68e2604c86a85`

| PR | Head | Ahead of main | Behind main | Changed files | Classification |
|---|---|---:|---:|---:|---|
| #169 | `539cc92314e9fdd7460ba6dc214289d2d3f6618e` | 196 | 773 | 472 | salvageable experiment; selective replay |
| #166 | `13f14d03a3537511f6b847026e4c7432d5f5ac99` | 330 | 773 | 645 | historical security/TDD quarry; likely mostly superseded |

Both PRs are currently non-mergeable. CodeRabbit skipped #169 because the review set exceeded its 150-file limit, selecting 469 files. This is a scope/topology failure, not a request for more conflict resolution inside the same PR.

## Why rebase is the wrong operation

A normal rebase assumes the branch represents a coherent sequence of commits that should be replayed onto the new base. That assumption is false here:

- both branches contain large portions of old repository history;
- many changes have content-equivalent descendants on current `main` under newer paths;
- both branches delete or replace canonical skill trees that current `main` intentionally retains;
- generated wrappers, memory files, lockfiles, docs, and implementation changes are interleaved;
- the branches include merge commits for work later landed through other PRs;
- their file counts exceed practical human and automated review limits.

Rebasing 196 or 330 commits would turn already-solved history into artificial conflicts and could regress canonical structure.

## Required safety setup

Before any surgery, create immutable safety refs:

```bash
git fetch origin --prune

git branch safety/pr169-original-20260717 origin/experiment/pt-orama-self-reflection
git push origin safety/pr169-original-20260717

git branch safety/pr166-original-20260717 origin/cursor/security-hardening-pre-v2-c4ae
git push origin safety/pr166-original-20260717
```

Do not force-push the preservation branches during analysis.

## Shared Phase 0 — tree-twin and uniqueness inventory

Run from a fresh checkout of current `main`:

```bash
git fetch origin --prune

git log --oneline --reverse \
  ffe76f41959f1363052d8e948ee68e2604c86a85..origin/experiment/pt-orama-self-reflection \
  > /tmp/pr169-commits.txt

git log --oneline --reverse \
  ffe76f41959f1363052d8e948ee68e2604c86a85..origin/cursor/security-hardening-pre-v2-c4ae \
  > /tmp/pr166-commits.txt

git cherry -v origin/main origin/experiment/pt-orama-self-reflection \
  > /tmp/pr169-cherry.txt

git cherry -v origin/main origin/cursor/security-hardening-pre-v2-c4ae \
  > /tmp/pr166-cherry.txt

bash scripts/git/reanchor_scan.sh . origin/main all
```

For every `+` commit from `git cherry`, also test whether its resulting tree already exists on `main`:

```bash
branch_commit=<sha>
tree=$(git show -s --format=%T "$branch_commit")
git log origin/main --format='%H %T' | awk -v t="$tree" '$2 == t {print $1}'
```

Classification:

- matching tree on main → **absorbed/tree-twin**, do not replay;
- no tree match but identical scoped patch → **superseded equivalent**, document and skip;
- unique patch, valid current path, current behavior still needed → **replay candidate**;
- old path or architecture removed from main → **archive-only** unless intent can be reimplemented against the current API;
- generated memory/wrapper/lockfile churn → regenerate from current tooling, never cherry-pick blindly.

---

# PR #169 — `experiment/pt-orama-self-reflection`

## Assessment

PR #169 is the better salvage candidate, but only its recent thematic tail should be considered. The 196-commit graph is not a unit.

The branch's latest visible sequence has a coherent Hermes/ECC/OpenClaw theme:

1. inventory Hermes ECC fork surfaces;
2. extract Hermes council gates;
3. add ECC cross-harness authoring reference;
4. record AGY quota readiness diagnostics;
5. harmonize council orchestration and non-clobber installer behavior;
6. add tests;
7. address CodeRabbit findings and audit wrapper skills;
8. restore sequential procedure numbering.

This tail may contain still-valid intent. The rest of the branch includes broad historical repository state, generated wrapper trees, removed canonical directories, lockfile replacement, and old skill-layout transitions. Those must not be replayed wholesale.

## Recovery decision

**Selective replay onto a fresh branch from current `main`. No rebase.**

Proposed branch:

```text
recovery/pr169-hermes-ecc-selective-replay
```

Create it only after the uniqueness inventory:

```bash
git switch main
git pull --ff-only origin main
git switch -c recovery/pr169-hermes-ecc-selective-replay
```

## Replay order

Replay by intent, not necessarily by original SHA order:

### Batch A — documentation provenance

Candidate intent:

- Hermes ECC fork inventory;
- council review gates;
- ECC cross-harness authoring;
- partner/AGY readiness diagnostics.

Method:

- compare each source document with current canonical Hermes and Skillify references;
- add or synthesize missing sections into current paths;
- do not restore stale duplicate wrapper trees;
- preserve current contribution standards and repository-standard pointers.

### Batch B — installer behavior

Candidate intent:

- non-clobber Hermes thin-skill installation;
- deterministic wrapper generation;
- preservation of operator-authored files.

Method:

- port behavior into the current installer API rather than cherry-picking old path assumptions;
- require idempotency tests;
- generated wrappers must be regenerated from the current canonical source;
- never delete a current canonical skill because the old branch used a different layout.

### Batch C — focused tests and CodeRabbit remediation

Candidate intent:

- tests for installer non-clobber behavior;
- wrapper audit coverage;
- sequential procedure numbering validation.

Method:

- replay tests only after current implementation has been synthesized;
- update fixtures to current paths;
- run the test through the real install/wrapper path, not only isolated mocks.

## Explicit exclusions

Do not replay from #169 without separate approval:

- `.agent/memory/**` snapshots;
- `.claude/lessons/LESSONS.md` replacement;
- mass-generated `.agents/skills/**` or `.claude/skills/**` wrappers;
- deletion of current AFRP/CIDF/orama-system skill trees;
- old `package-lock.json` → `pnpm-lock.yaml` transition as part of this recovery;
- old CI, hooks, attribution, or security policy files already superseded on current `main`;
- empty/zero-change rename artifacts reported by the large compare.

## Verification gate

```bash
python3 scripts/review/repo_hygiene.py .
python3 scripts/review/check_orama_skills.py --mode baseline
python3 -m pytest tests/test_check_orama_skills.py -q

# Add targeted Hermes/OpenClaw tests selected by the replayed files.
# Run installer tests through the actual non-clobber path.
```

Replacement PR requirement:

- fewer than 100 changed files, preferably fewer than 30;
- one coherent Hermes/ECC objective;
- original PR #169 linked as provenance;
- every original tail commit marked replayed, superseded, or rejected in a disposition table.

---

# PR #166 — `cursor/security-hardening-pre-v2-c4ae`

## Assessment

PR #166 is primarily a historical integration quarry, not an active feature branch. Its 330 commits combine:

- old security-hardening work;
- Git hooks and attribution changes;
- TDD/Vitest frontend setup;
- Hermes and OpenClaw additions;
- skill-layout migrations;
- line-ending normalization;
- lockfile migration;
- generated wrapper trees;
- broad documentation and repository restructuring.

The compare output contains many files with zero effective changes and many removals of canonical skill trees that current `main` intentionally retains. This is strong evidence of content absorption plus path/history drift.

## Recovery decision

**Do not rebase. Do not replay the whole branch. Treat it as archive-first and prove any residual value commit-by-commit.**

Proposed branch, only if unique work is found:

```text
recovery/pr166-residual-security-tdd
```

## Candidate residual buckets

### Bucket 1 — frontend TDD/Vitest

Recent branch commits mention:

- Vitest frontend gate;
- 17 documented Vitest guarantees;
- test-count documentation corrections;
- `web/vitest.config.ts` and related frontend tests.

Before replaying anything:

1. inspect current `main` for equivalent Vitest config and the 17 guarantees;
2. run current frontend tests;
3. classify each branch commit with `git cherry` and tree-twins;
4. port only genuinely absent guarantees.

Do not replay lockfiles independently from the package-manager policy on current `main`.

### Bucket 2 — line endings and Git turf

Recent branch commits mention `.gitattributes` and CRLF normalization.

Before replaying:

- compare current `.gitattributes` and platform-specific file rules;
- verify `git check-attr` for `.cmd`, `.ps1`, `.sh`, and lockfiles;
- replay only missing policy, then renormalize only the explicitly governed files;
- avoid repository-wide renormalization in the same commit.

### Bucket 3 — security and review remediation

Most security, review, and contribution standards have newer descendants on current `main`, including post-review micro-remediation and contribution standards. Default classification is **superseded** unless a specific invariant is absent and has a current regression test.

### Bucket 4 — git-history-surgery references

The branch contains early versions of reanchor/history-surgery references. Current `main` has newer method-level guidance. Compare content semantically; extract only unique operational examples, not obsolete copies of the skill.

## Default disposition

Unless Phase 0 proves unique current value:

- mark #166 **archive-only / superseded**;
- retain `safety/pr166-original-20260717`;
- close the preservation PR with a disposition summary;
- do not create a replacement PR merely to make the branch mergeable.

## Verification gate for any residual replay

```bash
python3 scripts/review/repo_hygiene.py .
python3 scripts/review/check_orama_skills.py --mode baseline

cd web
pnpm install --frozen-lockfile
pnpm test
pnpm build
```

Run Git guard and line-ending checks only for the affected bucket.

---

# Recommended execution sequence

1. **Freeze safety refs** for both original heads.
2. **Inventory #166 first**, because it is likely mostly superseded and can probably be closed without a replacement PR.
3. **Inventory #169's last eight thematic commits** and current Hermes/ECC paths.
4. Create `recovery/pr169-hermes-ecc-selective-replay` from current `main` only if unique intent remains.
5. Replay in three small commits: docs provenance, installer behavior, tests/remediation.
6. Run focused and repository-wide validation.
7. Open a replacement PR linked to #169.
8. Append disposition tables to #166 and #169; do not replace their preserved summaries.
9. Close the original preservation PRs as superseded only after accepted work is accounted for.

## Disposition table template

```markdown
| Original commit | Intent | Tree twin on main? | Current equivalent | Decision | Replacement commit |
|---|---|---:|---|---|---|
| `<sha>` | `<intent>` | yes/no | `<path/PR>` | replay/superseded/archive/reject | `<sha or n/a>` |
```

## Hard boundaries

- No whole-branch `git rebase` for either PR.
- No force-push until a safety ref exists and the replacement tree is verified.
- No `--ours` or `--theirs` whole-file conflict resolution.
- No restoration of obsolete generated wrapper trees.
- No hand-merging rendered memory files.
- No lockfile replay without the matching manifest and package-manager policy.
- No merge of either preservation PR merely because conflicts were made resolvable.

## Final recommendation

- **PR #169:** salvage the coherent Hermes/ECC tail through selective replay onto fresh `main`; preserve the original as audit history.
- **PR #166:** default to superseded/archive-only; create a residual recovery PR only for narrowly proven missing TDD, line-ending, or security invariants.

The correct operation for both is **recovery by classification and replay**, not rebase.