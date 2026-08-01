# PR Body Anti-Clobber — Incident Ledger & Enforcement Doctrine

> **Role:** canonical incident record + enforcement ladder for append-only PR bodies.
> **Do not duplicate** — link from `cursor-pr-body` skill, `post-review-micro-remediation`,
> and `.agent/memory/working/PR_BODY_ANTI_CLOBBER_ENFORCEMENT_PLAN.md`.
> **Origin:** formalized from session findings 2026-08-01 (PT #314 repeat clobber).

---

## Layer 0 — Comment only (Cursor agents, top prohibition)

**Default:** agents **never** mutate an existing PR description. Progress updates go to
**comments** (`ManagePullRequest post_comment`, `gh pr comment`).

Hooks block `update_pr` with `body=`, `gh pr edit`, and `append-pr-body.sh` unless the
human created `~/.cursor/pr-body-human-override-ack` (or repo-local ack file) **and**
set `CURSOR_PR_BODY_HUMAN_OVERRIDE_ACK=1` in the current session.

Cursor rule: `.cursor/rules/pr-body-comment-only.mdc` (alwaysApply, listed before append-only).

---

## The failure mode

**PR body was replaced, not appended.** A delta-only `ManagePullRequest update_pr` or
`gh pr edit --body` call erased the original `## Summary` and any CodeRabbit release
notes. This is **always wrong** when an open PR already has a Summary.

### Documented incidents

| Date | PR(s) | Caught by | Recovery |
| --- | --- | --- | --- |
| 2026-06-27 | PT #154 | Human | Integrative restore → `lesson_3b13ab0a45d4` |
| 2026-07-27 | orama #222 | Human | Restored Summary + Follow-ups → `lesson_6fff093ccb00` |
| 2026-07-29 | PT #298, orama #239 | Human | `lesson_4a38f0e95fcf` |
| 2026-08-01 | PT #314 | Human (again) | Integrative restore + enforcement rollout |
| 2026-08-01 | PT #319 | Human | Delta-only `update_pr` clobber; integrative restore + Cursor hooks Layer 7 |

**Documented:** 6 PRs / 5 incidents. User-estimated silent rate ~5× → **~20–25 total**
if most turn-end `update_pr` calls go unreviewed.

### Why agents keep forgetting

| Factor | Effect |
| --- | --- |
| Cloud turn-end rule | "Update PR before summary" → one `update_pr` feels correct |
| `update_pr` ergonomics | One parameter vs READ → backup → merge → write |
| Lessons ≠ hooks | Rules in memory don't block the write at push time |
| Selective recall | Append-only reflexive for LESSONS, not PR bodies |

---

## Enforcement ladder (all layers active)

### Layer 1 — Before any PR body write

```text
READ  → gh pr view <N> --json body
BACKUP → .git/pr-body-backups/<slug>-pr<N>-<ts>.md
MERGE  → original ## Summary + chronological ## Follow-up blocks
WRITE  → append-pr-body.sh OR gh pr edit --body-file merged.md (full body only)
```

**NEVER:** `ManagePullRequest update_pr` with `body=` containing only the latest delta.

### Layer 2 — After commit, before push

```bash
bash scripts/git/remind-pr-body-append-only.sh
```

### Layer 3 — Audited publisher (strict by default)

`publish-clean-branch.sh` sets `PR_BODY_GUARD_STRICT=1` and calls the remind script
before `git push --force-with-lease`. Override only when PR body was not touched:

```bash
PR_BODY_UPDATE_ACK=1 bash scripts/git/publish-clean-branch.sh <branch> main origin
```

### Layer 4 — Cursor rule (alwaysApply)

`.cursor/rules/append-only-pr-body.mdc` — synced to PT/AlphaClaw via guard sync.

### Layer 5 — Cloud agent checklist

At end of every turn with code changes on a PR branch:

1. Touched PR body? → prove backup exists under `.git/pr-body-backups/`.
2. Used `update_pr`? → verify body still contains `## Summary`.
3. Clobbered? → recover before reporting done (`lesson_6fff093ccb00`).

### Layer 6 — CI gate

`scripts/git/verify-pr-body-not-clobbered.sh` — fails if open PR body lacks `## Summary`.
Workflow: `.github/workflows/pr-body-guard.yml`.

### Layer 7 — Cursor runtime hooks (Cursor agents only)

Installed via `scripts/cursor/install-user-git-environment.sh` into `~/.cursor/hooks.json`:

| Hook event | Script | Behavior |
| ---------- | ------ | -------- |
| `beforeSubmitPrompt` | `before-submit-pr-body-reminder.sh` | Injects Layer 0 reminder when prompt mentions PR bodies |
| `preToolUse` (`ManagePullRequest`) | `before-mcp-pr-body-guard.sh` | **Deny** `update_pr` with `body=`; allow `post_comment` |
| `beforeMCPExecution` | same | Backup on PR read |
| `beforeShellExecution` | `before-shell-pr-body-guard.sh` | **Deny** `gh pr edit`, `append-pr-body.sh`; allow `gh pr comment` |

Core logic: `scripts/cursor/hooks/pr-body-guard-core.py`

Human override only: `CURSOR_PR_BODY_HUMAN_OVERRIDE_ACK=1` — then Layers 1–6 (append-only) apply.

Hookify: `.claude/hookify.pr-body-comment-only.local.md`

---

## Correct write path

```bash
bash scripts/cursor/append-pr-body.sh <owner/repo> <N> \
  --title "Follow-up: <short title>" \
  --file follow-up.md
```

## Agent recall anchors

- `lesson_3b13ab0a45d4` — append-only PR descriptions
- `lesson_4a38f0e95fcf` — `update_pr` replaces entire body
- `lesson_6fff093ccb00` — recovery procedure
- `lesson_a8f3c2e91d04` — mechanical enforcement plan
- `bin/orama-system/skills/cursor-pr-body/SKILL.md`
- `scripts/git/remind-pr-body-append-only.sh`

## Success criteria

- Zero delta-only `update_pr` body writes on PRs with existing Summary.
- Every PR body update has a matching `.git/pr-body-backups/*` artifact.
- User stops catching clobber incidents manually.
