# Win coder — local code review of main push (6 commits)

**Assignee:** win  
**Topic:** code-review/main-push-2026-07-23  
**Fan-out:** coord-025  
**Priority:** P0 — read reference doc **before** reviewing diffs

## BLOCKING PREREQ (all agents)

Read **first** (do not skip):

| Doc | Location |
|-----|----------|
| Full reference | `win-rtx5080-windows-dev-reference.md` (ultrathink workspace root, sibling of `ultrathink-system/`) |
| Peer summary | `bin/orama-system/skills/hermes-harness/references/results/win-2026-07-23-rtx5080-dev-reference.md` |

Contains PATH/ECC/start.ps1 context needed to judge the 6 commits below.

## Scope — `origin/main` range

Review merged commits `2a9bbf7a..4e47341c` (6 commits):

| SHA | Subject |
|-----|---------|
| `2a9bbf7a` | fix: ensure partner CLI paths in start.ps1 |
| `67ddd1ce` | chore: gitignore Hermes runtime + Cursor steering state |
| `9faaf51e` | feat(hermes): absorb windows-hermes-setup |
| `a53d2708` | docs(hermes): Win RTX5080 peer drop |
| `4f52089f` | chore: gitignore local Cursor ECC skills and hooks |
| `4e47341c` | feat(cursor): ECC minimal profile install |

```powershell
cd $env:ORAMA_SYSTEM_PATH
git fetch origin
git log --oneline 03143156..4e47341c
git diff 03143156..4e47341c --stat
```

## Review focus

1. **start.ps1** — `ensure-partner-cli-paths.ps1` sourcing order and idempotency
2. **hermes-harness** — `windows-hermes-setup` canonical absorption + thin wrapper registry
3. **.gitignore** — `.hermes/`, `.cursor/state/`, `.cursor/skills/`, `.cursor/hooks/` exclusions correct
4. **.cursor/** ECC install — no machine-local paths in tracked files; `no-workstation-paths.mdc` preserved
5. **Hygiene** — repo_hygiene / LINT-006 compliance on new markdown
6. **Gaps** — anything still open in reference doc that these commits should have addressed

## Deliverable

`win-code-review-main-push-6.md` in `references/results/` with:

- Verdict per commit (PASS / concerns / blockers)
- Findings table (severity, file, recommendation)
- Test commands run + results
- Drop to Mac peer inbox when done

## Rules

- Branch: review on `main` at `4e47341c` (no feature branch unless fix required)
- Frugality B1: local pytest only; no cloud unless operator approves
- One coder job — complete before taking other queue work
