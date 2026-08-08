#!/usr/bin/env bash
# Restore branches accidentally deleted during post-rewrite cherry-reanchor.
#
# Uses local refs/heads/<branch> as source when origin/<branch> is missing.
# Never deletes remotes on failure.
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

export DELETE_ON_CHERRY_CONFLICT=0
export SKIP_EMPTY_CHERRY=1
export ALLOW_LOCAL_SOURCE=1

exec bash "$SCRIPT_DIR/cherry-reanchor-branches.sh" "$REPO" "$@"
