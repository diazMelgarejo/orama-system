#!/usr/bin/env bash
# 2026-07-22-branch-cleanup-verified-superseded.sh
#
# Deletes local branches + worktrees in orama-system and Perpetua-Tools that
# were verified this session as fully superseded (squash-merged into main,
# or trivially obsolete). Verification method: git-history-surgery tree-twin
# scan (scripts/git/reanchor_scan.sh) + git diff main..<branch> --stat +
# git log main --grep for the absorbing squash-merge commit. See:
#   orama-system/references/tiered-model-implementation-navigator.md
#   orama-system/docs/plans/2026-07-22-frugality-privacy-reconciliation-and-navigator-closeout.md
#
# List hand-trimmed by user on 2026-07-22 (dropped: G7-Async-notifications,
# pr194, coordination-consolidation-part2-20260719, pr204-clean, pr260-work,
# pr263-reanchor-20260719 — left for separate/manual handling).
#
# Safe to re-run: uses -D only on branches confirmed superseded, --force only
# on worktrees confirmed superseded; skips anything already gone.
#
# Usage: bash 2026-07-22-branch-cleanup-verified-superseded.sh [--dry-run]

set -euo pipefail

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

ORAMA_DIR="$HOME/code/OpenClaw/orama-system"
PT_DIR="$HOME/code/OpenClaw/perplexity-api/Perpetua-Tools"

run() {
  if [ "$DRY_RUN" = "1" ]; then
    echo "[dry-run] $*"
  else
    "$@" || echo "  (skipped/already gone: $*)"
  fi
}

echo "== orama-system: branches =="
cd "$ORAMA_DIR"
ORAMA_BRANCHES=(
  2026-06-26--dev-recalib-cursor-agent
  2026-07-19-001-clinebot-idempotent-install
  __diag3
  __diag4
  cursor/security-hardening-pre-v2-c4ae
  cursor/security-pr3-planning-f559
  cursor/security-pr3-swarm-approval-f559
  experiment/pt-orama-self-reflection
  feat/dev-recalib-cursor-agent
  feat/launcher-cli-parity-20260715
  platform/macos-portal
  pr-146-attribution-import
  pr-149-tmp
  safety/pr183-pre-graph-reanchor-20260715
  integrate/pr183-launcher-harmonization-20260715
  skillify-pr2-glm52-remediation
  skillify-pr2-low-risk-skills
)
for b in "${ORAMA_BRANCHES[@]}"; do
  run git branch -D "$b"
done

echo "== orama-system: worktrees =="
run git worktree remove /private/tmp/orama-launcher-cli-parity-20260715 --force
run git worktree remove /private/tmp/orama-pr183-launcher-harmonization-20260715 --force

echo "== Perpetua-Tools: branches =="
cd "$PT_DIR"
PT_BRANCHES=(
  memory-and-eventtype-splice-20260719
  memory/2026-07-19-lessons-pr190-winpeers
  pr-211
  pr-211-lessons-salvage
  pr258-work
  replace/pr258-clean-snapshot-20260718
  rescue/pt-uncommitted-2026-06-30
  safety/pr215-pre-reanchor-20260715
  salvage/state-transition-manager-06ce1309
  worktree-pr-203-stm-integration
)
for b in "${PT_BRANCHES[@]}"; do
  run git branch -D "$b"
done

echo "== Perpetua-Tools: worktrees =="
run git worktree remove /private/tmp/pt-coordination-part2-20260719 --force
run git worktree remove /private/tmp/pt-kimi-reanchor-review-20260715-001 --force
run git worktree remove /private/tmp/pt-part2-review-20260719 --force
run git worktree remove /private/tmp/pt-pr258-clean-snapshot-20260718 --force
run git worktree remove /private/tmp/pt-pr263-reanchor-20260719 --force
run git worktree remove "$PT_DIR/.claude/worktrees/pr-203-stm-integration" --force
run git worktree remove "$PT_DIR/.claude/worktrees/pt-pr258-fixes-20260718" --force

echo
echo "Done. Re-run with --dry-run first if you want to preview instead of execute."
