#!/usr/bin/env bash
# gstack-safe-upgrade.sh — snapshot + upgrade + recover, so a gstack upgrade
# never silently drops local uniqueness the way a naive `git reset --hard
# origin/main` (the upstream gstack-upgrade skill's default git-install path)
# would.
#
# Two distinct kinds of local uniqueness, both covered:
#   1. Registered fork patches (patches/*.patch) — already recoverable via
#      apply-fork-patches.sh. This script still re-runs it as the last step.
#   2. Everything ELSE: uncommitted working-tree diffs (e.g. model-overlay
#      content baked into SKILL.md files by a prior `./setup` run) and any
#      commits on a local branch that touch files no registered patch covers
#      (e.g. fix/1802-staging-ownership-guard's own commits, before or
#      alongside their extraction into a registered patch). Found 2026-07-12:
#      `git stash` was the ONLY thing standing between a set of uncommitted
#      "## Brain Context Load" additions and permanent loss — one `stash
#      drop` away, tracked nowhere.
#
# Workflow:
#   gstack-safe-upgrade.sh snapshot   # ALWAYS run this before any upgrade
#   gstack-safe-upgrade.sh upgrade    # fetch + merge + ./setup + reapply patches + restore snapshot
#   gstack-safe-upgrade.sh verify     # confirm nothing was silently dropped
#   gstack-safe-upgrade.sh status     # what's currently unregistered / at risk
set -uo pipefail

GSTACK_ROOT="${GSTACK_ROOT:-$HOME/.claude/skills/gstack}"
PATCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCHES_DIR="$PATCH_ROOT/patches"
SNAPSHOT_DIR="${GSTACK_SNAPSHOT_DIR:-$HOME/.gstack/upgrade-snapshots}"
LATEST_LINK="$SNAPSHOT_DIR/latest"

die() { echo "gstack-safe-upgrade: $*" >&2; exit 1; }
log() { echo "[gstack-safe-upgrade] $*"; }

[ -d "$GSTACK_ROOT/.git" ] || die "no git checkout at $GSTACK_ROOT"

_registered_patch_files() {
  # Union of every file path any registered patch touches, one per line.
  [ -d "$PATCHES_DIR" ] || return 0
  grep -h '^--- a/\|^+++ b/' "$PATCHES_DIR"/*.patch 2>/dev/null \
    | sed -E 's/^(---|\+\+\+) [ab]\///' | sort -u
}

# Files touched by commits on this branch that origin/main doesn't have —
# the "unregistered branch commit" risk class.
_local_only_commit_files() {
  cd "$GSTACK_ROOT"
  git fetch origin --quiet 2>/dev/null || true
  git diff --name-only origin/main...HEAD 2>/dev/null | sort -u
}

cmd_status() {
  cd "$GSTACK_ROOT"
  local branch head registered local_files unregistered
  branch="$(git rev-parse --abbrev-ref HEAD)"
  head="$(git rev-parse --short HEAD)"
  echo "gstack checkout: $branch @ $head"

  echo ""
  echo "Uncommitted working-tree diff:"
  local dirty_files
  dirty_files="$(git diff --name-only HEAD 2>/dev/null)"
  if [ -z "$dirty_files" ]; then
    echo "  (clean)"
  else
    printf '%s\n' "$dirty_files" | sed 's/^/  M /'
    echo "  ^ NOT git-committed, NOT a registered fork patch. A raw"
    echo "    'git reset --hard' or 'git checkout .' loses this permanently."
  fi

  echo ""
  echo "Commits on this branch not in origin/main:"
  local_files="$(_local_only_commit_files)"
  if [ -z "$local_files" ]; then
    echo "  (none — branch matches origin/main)"
  else
    git log --oneline origin/main..HEAD 2>/dev/null | sed 's/^/  /'
    registered="$(_registered_patch_files)"
    unregistered="$(comm -23 <(printf '%s\n' "$local_files") <(printf '%s\n' "$registered"))"
    if [ -n "$unregistered" ]; then
      echo "  UNREGISTERED files touched by local-only commits (no fork-patches/ entry covers them):"
      printf '%s\n' "$unregistered" | sed 's/^/    /'
      echo "  Register these via fork-patches/README.md before the next upgrade,"
      echo "  or they will not survive a fast-forward/reset-based upgrade path."
    else
      echo "  All touched files are covered by a registered fork patch."
    fi
  fi
}

cmd_snapshot() {
  cd "$GSTACK_ROOT"
  mkdir -p "$SNAPSHOT_DIR"
  local ts snap_dir
  ts="$(date -u +%Y%m%dT%H%M%SZ)"
  snap_dir="$SNAPSHOT_DIR/$ts"
  mkdir -p "$snap_dir"

  git rev-parse --abbrev-ref HEAD > "$snap_dir/branch.txt"
  git rev-parse HEAD > "$snap_dir/head-sha.txt"
  git diff HEAD > "$snap_dir/worktree.patch" 2>/dev/null || true
  git diff --name-only HEAD > "$snap_dir/worktree-files.txt" 2>/dev/null || true
  git log --oneline origin/main..HEAD > "$snap_dir/local-commits.txt" 2>/dev/null || true
  _local_only_commit_files > "$snap_dir/local-commit-files.txt"

  ln -sfn "$snap_dir" "$LATEST_LINK"
  log "snapshot written to $snap_dir"
  cmd_status
}

cmd_upgrade() {
  [ -L "$LATEST_LINK" ] || die "no snapshot found — run 'snapshot' first (never upgrade blind)"
  cd "$GSTACK_ROOT"

  local had_dirty=0
  if [ -n "$(git status --porcelain)" ]; then
    had_dirty=1
    log "stashing working-tree dirt..."
    git stash push -m "gstack-safe-upgrade $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  fi

  log "fetching origin..."
  git fetch origin

  log "merging origin/main (--no-edit)..."
  if ! git merge origin/main --no-edit; then
    echo ""
    echo "MERGE CONFLICT — resolve manually, then re-run:"
    echo "  cd $GSTACK_ROOT"
    echo "  # for each conflicted file, prefer upstream when it's a strict"
    echo "  # superset (adds features on top of a patch):"
    echo "  git checkout --theirs <file> && git add <file>"
    echo "  git commit --no-edit"
    echo "  bash $PATCH_ROOT/gstack-safe-upgrade.sh finish"
    exit 1
  fi

  cmd_finish "$had_dirty"
}

cmd_finish() {
  local had_dirty="${1:-1}"
  cd "$GSTACK_ROOT"

  log "regenerating skill files (./setup)..."
  ./setup

  log "re-applying registered fork patches..."
  bash "$PATCH_ROOT/apply-fork-patches.sh" || log "WARN: fork-patch apply reported issues — review above"

  if [ "$had_dirty" = "1" ]; then
    log "restoring pre-upgrade working-tree diff..."
    if ! git stash pop; then
      echo ""
      echo "WARN: stash pop hit conflicts. Your pre-upgrade working-tree diff is"
      echo "still safe in 'git stash list' — resolve manually, do not drop the stash."
    fi
  fi

  cat VERSION 2>/dev/null | sed 's/^/[gstack-safe-upgrade] now at v/'
  cmd_verify
}

cmd_verify() {
  [ -L "$LATEST_LINK" ] || die "no snapshot found — cannot verify against nothing"
  cd "$GSTACK_ROOT"
  local snap_files pre_local_files post_local_files missing

  echo ""
  echo "=== verify: comparing against $(readlink "$LATEST_LINK") ==="

  snap_files="$(cat "$LATEST_LINK/worktree-files.txt" 2>/dev/null || true)"
  if [ -n "$snap_files" ]; then
    local current_dirty
    current_dirty="$(git diff --name-only HEAD 2>/dev/null; git stash show --name-only 2>/dev/null || true)"
    missing="$(comm -23 <(printf '%s\n' "$snap_files" | sort -u) <(printf '%s\n' "$current_dirty" | sort -u))"
    if [ -n "$missing" ]; then
      echo "POSSIBLE LOSS — these files had uncommitted local diffs before the"
      echo "upgrade and do not appear restored now (check 'git stash list' before"
      echo "assuming data loss — they may just be committed/merged cleanly):"
      printf '%s\n' "$missing" | sed 's/^/  /'
    else
      echo "OK: all pre-upgrade working-tree diffs accounted for."
    fi
  else
    echo "OK: no pre-upgrade working-tree diff existed."
  fi

  pre_local_files="$(cat "$LATEST_LINK/local-commit-files.txt" 2>/dev/null || true)"
  if [ -n "$pre_local_files" ]; then
    post_local_files="$(_local_only_commit_files)"
    missing="$(comm -23 <(printf '%s\n' "$pre_local_files" | sort -u) <(printf '%s\n' "$post_local_files" | sort -u))"
    if [ -n "$missing" ]; then
      echo ""
      echo "These files were touched by pre-upgrade local-only commits and are"
      echo "no longer part of any local-only diff vs origin/main (expected if"
      echo "upstream merged them; concerning if not):"
      printf '%s\n' "$missing" | sed 's/^/  /'
    fi
  fi
  echo "=== end verify ==="
}

case "${1:-help}" in
  snapshot) cmd_snapshot ;;
  upgrade) cmd_upgrade ;;
  finish) cmd_finish "${2:-1}" ;;
  verify) cmd_verify ;;
  status) cmd_status ;;
  *) grep -E '^#( |$)' "$0" | sed 's/^# \{0,1\}//' ;;
esac
