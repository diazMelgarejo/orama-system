# 27 — Git Governance: One Source of Truth, Zero Fragmentation (org-wide)

> **Status:** active doctrine (2026-06-05). Companion: [`11-idempotency-and-guard-patterns.md`](11-idempotency-and-guard-patterns.md),
> [`23-security-preconditions.md`](23-security-preconditions.md). Skill: [git-reanchor](https://github.com/diazMelgarejo/orama-system/blob/main/bin/orama-system/skills/git-reanchor/SKILL.md).
> Lesson that motivated this: [`docs/LESSONS.md` § 2026-06-05](../LESSONS.md).

## Why

Two recurring, expensive failure classes — both caused by **per-repo copies of git logic
drifting out of sync**:

1. **History-rewrite misjudgment.** After a `main` rewrite (expunge / squash-rebundle /
   force-push), `ahead/behind`, `rev-list --count`, and `merge-base` are SHA-graph proxies and
   are *meaningless* — yet agents keep reaching for them and declaring branches healthy or
   orphaned wrongly (orama PR#70 "600 behind"; PT re-scan 2026-06-05). The only correct test is
   the **tree-twin** (`%T` match).
2. **Attribution-guard drift.** PT's `audit_attribution.sh` / `check_commit_message.sh` /
   `check_identity.sh` were stale forks of orama's canonical guards. Under
   `GIT_AUDIT_STRICT=1` (the `pre-push` mode), PT rejected mainstream-AI co-authors
   (`coderabbitai`, `dependabot`, `anthropic.com`) that orama already allowed — blocking valid
   pushes. The sync tool itself silently **omitted two of the four guard files**.

Fragmentation is the root cause in both. This doc makes the rule org-wide and enforceable so
future `oramasys/*` repos inherit identical behavior from day one.

## The invariant

**There is exactly one canonical copy of every git-governance script, and it lives in
`orama-system/scripts/git/`. Every other repo carries a byte-identical copy, never a fork and
never a thin wrapper.**

Canonical set (all synced, all byte-identical across repos):

| Script | Role |
|--------|------|
| `banned_attribution_lib.sh` | shared matcher for VERBOTEN / banned co-authors |
| `audit_attribution.sh` | range + strict-history attribution audit (pre-push gate) |
| `check_commit_message.sh` | commit-msg allowlist (mainstream AI authors/co-authors) |
| `check_identity.sh` | Cursor-scoped author/committer identity check |
| `daily-attribution-guard.sh` | session/cron sweep — **self-contained**, derives `REPO_ROOT` |
| `neutralize-cursor-coauthor-hook.sh`, `expunge-all-workspace-repos.sh`, `verify-git-guards.sh` | deps of the daily guard |
| `reanchor_scan.sh` | tree-twin branch-state detector (history-rewrite safety) |

## Rules (apply to every agent: Claude, Codex, Cursor, CodeRabbit, Greptile, future)

1. **Never hand-edit a guard in a downstream repo.** Edit orama's canonical copy, then
   `bash scripts/git/sync-attribution-guard-scripts.sh <target-repo>`.
2. **No thin wrappers** for `daily-attribution-guard.sh`. A wrapper hardcodes a path and, run
   against its own target, execs itself (infinite recursion). The full impl is self-contained.
3. **Mainstream AI models / autonomous agents are allowed** as author and `Co-authored-by`.
   The only hard ban is the VERBOTEN pattern in the gitignored private lib.
4. **Branch judgment uses tree-twins, never graph proxies** across a rewritten `main`
   (`reanchor_scan.sh` + `git cherry`). "N behind + byte-identical content" must HALT you.
5. **Mirror forks are out of scope** for re-anchor: periscope `main`/`agentsview` and
   AlphaClaw `main` are pure upstream mirrors, never rewritten by us.

## Onboarding a new `oramasys/*` repo (zero-drift checklist)

```bash
# from orama-system root, for each new repo checkout:
bash scripts/git/sync-attribution-guard-scripts.sh <new-repo-path>   # copies ALL guards
bash <new-repo-path>/scripts/git/install-local-hooks.sh              # wires .githooks
bash <new-repo-path>/scripts/git/verify-git-guards.sh                # asserts parity
```

Add the same two CLAUDE.md/AGENTS.md sections every repo carries: **History-rewrite & branch
re-anchor** and **Attribution guards: single source of truth**. Both reference orama by GitHub
URL so the canonical source is unambiguous.

## Enforcement roadmap (so drift is caught, not just discouraged)

- **CI parity check (next):** a job that fails if any repo's guard script differs from orama's
  canonical copy (hash compare). Turns "don't hand-edit" from convention into a gate.
- **Sync completeness test:** assert `sync-attribution-guard-scripts.sh`'s copy list covers
  every file in the canonical set (the omission of `check_commit_message.sh` /
  `check_identity.sh` is exactly what this would have caught).
- **Bootstrap hook:** new-repo bootstrap calls the onboarding checklist automatically.

## Paths

Relative in-repo links + GitHub URLs only — never absolute workstation paths (CI
`scripts/review/repo_hygiene.py`; CIDF LINT-006). See [`08-git-hygiene`](../wiki/08-git-hygiene-and-branching.md).
