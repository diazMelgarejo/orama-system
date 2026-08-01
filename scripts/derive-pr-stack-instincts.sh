#!/usr/bin/env bash
# derive-pr-stack-instincts.sh — document + scaffold session instincts from PR stack lessons.
#
# Usage:
#   scripts/derive-pr-stack-instincts.sh --check
#   scripts/derive-pr-stack-instincts.sh --list
#
# Full derivation pipeline (manual curation required — ECC homunculus quality gate):
#   1. Incident closes → append lesson to .agent/memory/semantic/lessons.jsonl
#   2. Working doc in .agent/memory/working/<TOPIC>.md with evidence + PR refs
#   3. Curate 2-4 instincts in .claude/homunculus/instincts/inherited/<stack>-<date>.yaml
#      (follow alphaclaw-cron-ci / guard-sync-pr251 template — trigger, confidence, action, evidence)
#   4. /instinct-import <yaml> --dry-run then --force (Claude Code + instinct-cli.py)
#   5. /instinct-status — verify triggers loaded
#   6. /ecc-sync post-merge — commit instinct YAML to main in both repos if cross-repo
#
# Automated inputs (read-only helpers):
#   - lesson IDs from lessons.jsonl (grep related PR)
#   - PR_BODY_ANTI_CLOBBER_ENFORCEMENT_PLAN.md incident ledger
#   - scripts/git/remind-pr-body-append-only.sh (mechanical hook reference)
#
# Do NOT bulk-generate from repo-analysis alone — everything-claude-code learning-curation
# instinct: prefer small accurate set over duplicated auto-dumps.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTINCT_DIR="$REPO_ROOT/.claude/homunculus/instincts/inherited"

list_session_instincts() {
  find "$INSTINCT_DIR" -maxdepth 1 -name '*-20*.yaml' -o -name 'guard-sync-*.yaml' 2>/dev/null | sort
}

case "${1:-}" in
  --list)
    echo "Session-derived instinct YAML files:"
    list_session_instincts || echo "  (none)"
    ;;
  --check)
    echo "== PR stack instinct derivation checklist =="
    echo "  [ ] Lesson appended to lessons.jsonl with evidence_ids"
    echo "  [ ] Working doc in .agent/memory/working/"
    echo "  [ ] Session YAML in .claude/homunculus/instincts/inherited/"
    echo "  [ ] /instinct-import --dry-run reviewed"
    echo "  [ ] remind/hook wired if instinct references mechanical gate"
    echo "  [ ] PR body updated via append-pr-body.sh (not delta update_pr)"
    missing=0
    for f in \
      "$INSTINCT_DIR/guard-sync-pr251-2026-08-01.yaml" \
      "$REPO_ROOT/../Perpetua-Tools/.claude/homunculus/instincts/inherited/guard-sync-pr314-2026-08-01.yaml"; do
      if [[ -f "$f" ]]; then
        echo "  OK  $f"
      else
        echo "  MISS $f"
        missing=1
      fi
    done
    exit "$missing"
    ;;
  -h|--help|"")
    sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
    ;;
  *)
    echo "error: unknown argument: $1" >&2
    exit 1
    ;;
esac
