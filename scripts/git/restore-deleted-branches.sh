#!/usr/bin/env bash
# Restore branches accidentally deleted during post-rewrite cherry-reanchor.
#
# Tries cherry-reanchor first; on failure runs restore-branch-theirs (conflicts/submodules).
# Uses local refs/heads/<branch> when origin/<branch> is missing. Never deletes remotes.
#
# Usage:
#   restore-deleted-branches.sh [repo_path] branch [branch...]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${1:-.}"
shift || true

if [[ $# -eq 0 ]]; then
  echo "usage: $0 [repo_path] branch [branch...]" >&2
  exit 2
fi

# Survives checkout to origin/main during restore (script file may disappear from tree).
SELF="$(cd "$SCRIPT_DIR" && pwd)/restore-branch-theirs.sh"
[[ -x "$SELF" ]] || SELF="/tmp/restore-branch-theirs.sh"
if [[ ! -x "$SELF" ]] && [[ -x "$SCRIPT_DIR/restore-branch-theirs.sh" ]]; then
  cp "$SCRIPT_DIR/restore-branch-theirs.sh" "$SELF"
  chmod +x "$SELF"
fi

export DELETE_ON_CHERRY_CONFLICT=0
export SKIP_EMPTY_CHERRY=1
export ALLOW_LOCAL_SOURCE=1

failed=0
for branch in "$@"; do
  echo ">>> RESTORE $branch"
  if bash "$SCRIPT_DIR/cherry-reanchor-branches.sh" "$REPO" "$branch"; then
    continue
  fi
  echo "  cherry-reanchor failed — trying restore-branch-theirs" >&2
  if bash "$SELF" "$REPO" "$branch"; then
    continue
  fi
  failed=$((failed + 1))
done

exit $(( failed > 0 ? 1 : 0 ))
