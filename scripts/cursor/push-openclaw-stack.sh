#!/usr/bin/env bash
# Push AlphaClaw branches in order and print gh PR commands (run when push access is available).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/openclaw-v1}"
AC_ROOT="${ALPHACLAW_INSTALL_DIR:-$OPENCLAW_HOME/AlphaClaw}"
UPSTREAM="${ALPHACLAW_UPSTREAM_BRANCH:-main}"
INTEGRATION="${ALPHACLAW_INTEGRATION_BRANCH:-feature/MacOS-post-install}"
CONTRIB="${ALPHACLAW_CONTRIB_BRANCH:-cursor/sync-attribution-guards-6421}"
ORAMA_BRANCH="${ORAMA_PUSH_BRANCH:-cursor/user-level-git-guards-6421}"

echo "=== orama-system ==="
if [[ -d "$REPO_ROOT/.git" ]]; then
  (
    cd "$REPO_ROOT"
    git push -u origin "$ORAMA_BRANCH" || true
    echo "PR: gh pr create --repo diazMelgarejo/orama-system --head $ORAMA_BRANCH --base main \\"
    echo "  --title 'feat(git): Cursor cloud guards + AlphaClaw fork branch policy' --draft"
  )
fi

echo ""
echo "=== AlphaClaw (run alphaclaw-align-all.sh first) ==="
if [[ ! -d "$AC_ROOT/.git" ]]; then
  echo "skip: $AC_ROOT not cloned"
  exit 0
fi

cd "$AC_ROOT"
bash "$REPO_ROOT/scripts/git/alphaclaw-align-all.sh"

echo ">>> push integration branch"
git push -u origin "$INTEGRATION" || {
  echo "FAILED: push $INTEGRATION — check credentials"
  exit 1
}

echo ">>> push contrib branch"
git push -u origin "$CONTRIB" || {
  echo "FAILED: push $CONTRIB"
  exit 1
}

cat <<EOF

=== Open PR (AlphaClaw) ===
# Integration (if not already open): merge upstream sync into macOS line
gh pr create --repo diazMelgarejo/AlphaClaw \\
  --head ${INTEGRATION} --base ${UPSTREAM} \\
  --title "merge(upstream): sync origin/main into ${INTEGRATION}" \\
  --body "Keeps fork integration branch based on upstream mirror main." \\
  --draft

# Attribution guards (target integration branch, NOT main)
gh pr create --repo diazMelgarejo/AlphaClaw \\
  --head ${CONTRIB} --base ${INTEGRATION} \\
  --title "feat(git): sync Cursor attribution guards from orama-system" \\
  --body "Git guard scripts + Cursor Cloud instructions. PR base is ${INTEGRATION}, not ${UPSTREAM}." \\
  --draft

EOF
