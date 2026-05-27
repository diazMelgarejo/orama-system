#!/usr/bin/env bash
# Check out the AlphaClaw *contribution* branch (never commit feature work on main).
set -euo pipefail

OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/openclaw-v1}"
AC_ROOT="${ALPHACLAW_INSTALL_DIR:-$OPENCLAW_HOME/AlphaClaw}"
UPSTREAM_BRANCH="${ALPHACLAW_UPSTREAM_BRANCH:-main}"
CONTRIB_BRANCH="${ALPHACLAW_CONTRIB_BRANCH:-feature/MacOS-post-install}"

if [[ ! -d "$AC_ROOT/.git" ]]; then
  echo "ERROR: AlphaClaw not cloned at $AC_ROOT" >&2
  exit 1
fi

cd "$AC_ROOT"
git fetch origin "$UPSTREAM_BRANCH" 2>/dev/null || true

if git show-ref --verify --quiet "refs/remotes/origin/${CONTRIB_BRANCH}"; then
  git checkout -B "$CONTRIB_BRANCH" "origin/${CONTRIB_BRANCH}"
elif git show-ref --verify --quiet "refs/heads/${CONTRIB_BRANCH}"; then
  git checkout "$CONTRIB_BRANCH"
else
  git checkout "$UPSTREAM_BRANCH" 2>/dev/null || git checkout -B "$UPSTREAM_BRANCH" "origin/${UPSTREAM_BRANCH}"
  git checkout -B "$CONTRIB_BRANCH"
fi

echo "OK: AlphaClaw on contrib branch ${CONTRIB_BRANCH} (upstream tracking: origin/${UPSTREAM_BRANCH})"

# After checkout, realign onto current upstream mirror if main moved.
if [[ -x "$(dirname "$0")/alphaclaw-realign-contrib-branches.sh" ]]; then
  ALPHACLAW_INSTALL_DIR="$AC_ROOT" ALPHACLAW_CONTRIB_BRANCHES="$contrib" \
    bash "$(dirname "$0")/alphaclaw-realign-contrib-branches.sh" || true
fi
