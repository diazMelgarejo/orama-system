# Bash 3.2 portability for `scripts/git/` hooks

> Applies to all git skills (`git-history-surgery`, `using-git-worktrees`,
> `icloud-escape-move`) and TDD commit enforcement (`oramasys-method` → `tdd-gate.md`).

## Root cause

macOS ships **bash 3.2** as `/bin/bash`. It does **not** include `mapfile` / `readarray`
(bash 4+). Hook scripts invoked from `.githooks/` run under that shell unless the
user explicitly uses a newer bash.

## `check_tdd_commit.sh` fix (2026-06-27)

`scripts/git/check_tdd_commit.sh` originally used `mapfile` to read staged paths.
On macOS that failed with `mapfile: command not found` (exit 127).

**Fix:** replace `mapfile` with a bash 3.2–safe loop:

```bash
staged=()
while IFS= read -r line; do
  staged+=("$line")
done < <(git diff --cached --name-only --diff-filter=ACMRT 2>/dev/null || true)
```

Regression coverage: `tests/test_check_tdd_commit.py`.

## Authoring rule for new `scripts/git/*.sh`

- Prefer `while IFS= read -r` over `mapfile` / `readarray`.
- Avoid associative arrays (`declare -A`) unless the script pins `#!/usr/bin/env bash`
  and documents a minimum version, or uses `#!/bin/sh` POSIX patterns.
- Run `bash -n scripts/git/<script>.sh` and pytest hook tests before commit.
- Install hooks once per clone: `bash scripts/git/install-local-hooks.sh`
  (wires `commit-msg` → `check_tdd_commit.sh` for the web TDD gate).

## Cross-references

| Topic | Location |
|-------|----------|
| TDD commit gate policy | `docs/TDD.md`, `oramasys-method/references/tdd-gate.md` |
| Evidence report | `docs/testing/2026-06-26-vite-frontend-tdd-gate.tdd.md` |
| Hook installer | `scripts/git/install-local-hooks.sh` |
| Git hygiene wiki | `docs/wiki/08-git-hygiene-and-branching.md` |
