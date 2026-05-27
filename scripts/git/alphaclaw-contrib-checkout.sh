#!/usr/bin/env bash
# Check out AlphaClaw contrib branch stacked on integration (never commit on main).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/openclaw-v1}"
AC_ROOT="${ALPHACLAW_INSTALL_DIR:-$OPENCLAW_HOME/AlphaClaw}"
UPSTREAM_BRANCH="${ALPHACLAW_UPSTREAM_BRANCH:-main}"
INTEGRATION_BRANCH="${ALPHACLAW_INTEGRATION_BRANCH:-feature/MacOS-post-install}"
CONTRIB_BRANCH="${ALPHACLAW_CONTRIB_BRANCH:-cursor/sync-attribution-guards-6421}"

if [[ ! -d "$AC_ROOT/.git" ]]; then
  echo "ERROR: AlphaClaw not cloned at $AC_ROOT" >&2
  exit 1
fi

bash "$SCRIPT_DIR/alphaclaw-sync-integration-with-main.sh"

cd "$AC_ROOT"
git fetch origin --prune 2>/dev/null || true

integration_sha="$(git rev-parse "$INTEGRATION_BRANCH")"

if git show-ref --verify --quiet "refs/heads/${CONTRIB_BRANCH}"; then
  git checkout "$CONTRIB_BRANCH"
else
  git checkout -B "$CONTRIB_BRANCH" "$integration_sha"
fi

mb_main="$(git merge-base "origin/${UPSTREAM_BRANCH}" HEAD)"
main_sha="$(git rev-parse "origin/${UPSTREAM_BRANCH}")"
if [[ "$mb_main" != "$main_sha" ]]; then
  echo "WARN: contrib branch merge-base with origin/${UPSTREAM_BRANCH} is not main tip" >&2
  echo "      run: ALPHACLAW_CONTRIB_BRANCHES=${CONTRIB_BRANCH} bash scripts/git/alphaclaw-realign-contrib-branches.sh" >&2
fi

git config --local user.name "cyre" 2>/dev/null || true
git config --local user.email "diazMelgarejo@gmail.com" 2>/dev/null || true

echo "OK: AlphaClaw on ${CONTRIB_BRANCH} (integration=${INTEGRATION_BRANCH}, upstream=origin/${UPSTREAM_BRANCH})"
