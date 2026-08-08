#!/usr/bin/env bash
# Write user-level private attribution data (never commit to any public repo).
set -euo pipefail

HOME="${HOME:-/home/ubuntu}"
OPENCLAW_DIR="${HOME}/.cursor/openclaw"
LESSONS_DIR="${OPENCLAW_DIR}/private-lessons"
PATTERNS="${OPENCLAW_DIR}/banned-attribution-patterns"
GUIDE="${OPENCLAW_DIR}/banned-attribution-local.md"
LESSON="${LESSONS_DIR}/perpetua-tools-git-attribution.md"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$OPENCLAW_DIR" "$LESSONS_DIR"
chmod 700 "$OPENCLAW_DIR" "$LESSONS_DIR" 2>/dev/null || true

if [[ ! -s "$PATTERNS" ]]; then
  if ! bash "$SCRIPT_DIR/seed-banned-attribution-patterns.sh" "$PATTERNS" 2>/dev/null; then
    # No local-only registry available yet on this machine. Fall back to a
    # placeholder rather than hard-failing; re-run this script (or the seed
    # script directly) once a real registry exists to replace it.
    {
      echo "# Banned attribution tokens (one per line, case-insensitive substring match)"
      echo "REDACTED"
    } >"$PATTERNS"
    chmod 600 "$PATTERNS"
  fi
else
  printf 'OK: preserve existing %s\n' "$PATTERNS"
fi

cat >"$GUIDE" <<'GUIDE_EOF'
# Banned git attribution (user-level private — not in git)

Patterns: `~/.cursor/openclaw/banned-attribution-patterns`

Never copy tokens into tracked files, commit messages, or GitHub.

Primary author: cyre + configured owner emails, or Codex — not Cursor Agent as author.
GUIDE_EOF
chmod 600 "$GUIDE"

cat >"$LESSON" <<'LESSON_EOF'
# Private lesson — Perpetua-Tools git attribution (NEVER commit this file)

## Hard rule

Banned tokens live only in `~/.cursor/openclaw/banned-attribution-patterns`.
Perpetua-Tools syncs them into `.cursor/private/` (gitignored). They must never
appear in PT tracked files, commit messages, PR bodies, or LESSONS on GitHub.

## Banned identities (author, committer, Co-authored-by)

Read `~/.cursor/openclaw/banned-attribution-patterns` (one token per line). Never
repeat those strings in commits, PRs, or tracked docs.

Cursor Agent must not be primary git author. Cursor may inject false Co-authored-by
trailers — hooks strip them before commit.

## Agent mistakes to avoid

- Writing banned tokens into docs/LESSONS.md "so agents remember" — use this file only.
- Putting base64 or plaintext tokens in PT scripts on GitHub.
- Committing as Cursor Agent instead of cyre.
- Leaving refs/original/ after filter-branch.
- **Re-adding forbidden Co-authored-by after an expunge** — forces another full `main` + all-branch rewrite and force-push.

## Daily enforcement (every session)

```bash
bash /path/to/Perpetua-Tools/scripts/git/daily-attribution-guard.sh
bash /path/to/Perpetua-Tools/scripts/git/expunge-all-workspace-repos.sh   # when scan hits > 0
```

Log: `~/.cursor/openclaw/attribution-guard.log`

## Commands

```bash
bash scripts/cursor/install-user-git-environment.sh   # orama or PT
bash scripts/cursor/sync-private-attribution-from-home.sh
bash scripts/git/daily-attribution-guard.sh
bash scripts/git/scan-tracked-banned-tokens.sh
bash scripts/git/commit-clean.sh -m "message"
bash scripts/git/publish-clean-branch.sh <branch> main origin
```
LESSON_EOF
chmod 600 "$LESSON"

printf 'OK: %s\n' "$PATTERNS"
printf 'OK: %s\n' "$GUIDE"
printf 'OK: %s\n' "$LESSON"
