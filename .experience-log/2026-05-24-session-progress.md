# 2026-05-24 — Session Progress (post-compaction)

> Resume-safe checkpoint. If a future session lands here cold, this file is the
> ground truth for "what changed and what remains."

## Completed this turn

### Worktree (`feat/worktree-doctrine`, PR #38)

| Commit | What |
|--------|------|
| `53a6cfa` | feat(hygiene): scan stale `.git` locks (D5) and macOS dedup dirs (D6) — `scripts/review/repo_hygiene.py` + 4 new tests in `tests/test_repo_hygiene.py` (15 total passing) |
| `d214ae8` | feat(skills): `bin/orama-system/skills/expunge-git/SKILL.md` (275 lines) + symlink `~/.claude/skills/expunge-git/SKILL.md` |
| `a811ea3` | docs(v2): rename `19-worktree-parallel-agents.md` → `22-worktree-parallel-agents.md` (collision-free); 6 reference patches |

### Canonical orama-system (`main`)

| Commit | What |
|--------|------|
| `fd2accd` | docs(v2): rename `18-rag-and-memory-design.md` → `20-`; `18-periscope-l4-glass.md` → `21-`; 9 reference patches + 9 OpenClaw-path scrubs in periscope plan |
| (pre-commit) | Removed 543 untracked macOS dedup files/dirs (D6) — all untracked, zero data loss |

### Skill registry

- **New skill:** `expunge-git` — complete history scrub procedure (15 steps incl. `git remote prune`, reflog expire, repack/prune, blob-level grep verification). Triggers: "expunge git history", "scrub commits", "remove leaked secret from git", etc.
- **Renamed reference target:** all SKILL.md / CLAUDE.md / spec doc references that pointed at `19-worktree-parallel-agents.md` now point at `22-worktree-parallel-agents.md` (or `20-` / `21-` for the two main-branch renames).

## Hygiene gate now catches

| ID | Rule | Severity |
|----|------|----------|
| D1 | bidi controls | ERROR |
| D5 | stale `.git/*.lock` | ERROR (new) |
| D6 | macOS `* 2/`, `* 3/` dirs | ERROR (new) |
| D9 | machine-specific OpenClaw paths | ERROR |
| — | `/Users/<name>/` personal paths | ERROR |
| — | banned legacy names | ERROR |

## Pending

| # | Task | Status |
|---|------|--------|
| 1 | PR #38 CI re-run on `a811ea3` | running (~3 min) |
| 2 | Merge PR #38 once green | blocked on #1 |
| 3 | Phase 1 as-built plan (`docs/v2/15-phase1-as-built.md` enrichment + 06/04/00/README edits in canonical) | not started — separate body of work |
| 4 | Save session learnings to gbrain (legacy task #15 from prior session) | not started |

## Numbering map (final state of docs/v2)

```
00-context-and-decisions.md
01-kernel-spec.md
02-modules/
03-safety-v2.5.md
04-build-order.md
05-feasibility-review.md
06-open-questions.md
07-agate-vision.md
08-technical-architecture-review.md
09-comparative-analysis-and-merging-plan.md
10-v1-hacks-automation-orbit.md
11-idempotency-and-guard-patterns.md
12-xai-model-migration-2026-05.md
13-local-model-catalog-strategy.md
14-supervisor-and-anthropic-patterns.md
15-phase1-as-built.md
16-web-app-orchestration-plan.md
17-hardware-policy-enforcement.md
18-master-alignment-v2-migration-plan.md     ← original 18 (2026-05-20)
19-gstack-optional-integration.md            ← original 19 (2026-05-21)
20-rag-and-memory-design.md                  ← renamed from 18- (was 2026-05-21)
21-periscope-l4-glass.md                     ← renamed from 18- (was 2026-05-24)
22-worktree-parallel-agents.md               ← renamed from 19- (lands via PR #38)
```

Next free slot: `23-`.

## Key lessons captured this session

1. **Expunge requires `git remote prune` + reflog expire + repack/prune.** Skipping any of these leaves the contaminated string discoverable in local refs or pack storage. Codified in `expunge-git` skill.
2. **macOS Finder dedup is silent.** 543 ghost files in canonical orama-system, all untracked, all invisible until you look. Hygiene scanner now catches them.
3. **Stale `.git/index.lock` happens.** Just hit it mid-commit on canonical. Bootstrap script already cleans these; hygiene scanner now flags them too.
4. **Doc numbering collisions multiply silently.** When 3 docs claim "18-", picking "19-" perpetuates the bug because "19-" was already taken. Always inspect the FULL directory before picking the next number.
