#!/usr/bin/env bash
# beforeShellExecution — block gh pr edit inline body; backup on gh pr view body reads.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=pr-body-backup-lib.sh
source "$SCRIPT_DIR/pr-body-backup-lib.sh"

input="$(cat)"

command_line="$(printf '%s' "$input" | python3 -c '
import json, sys
raw = sys.stdin.read()
try:
    data = json.loads(raw) if raw.strip() else {}
except json.JSONDecodeError:
    data = {}
print(data.get("command") or data.get("cmd") or "")
')"

[[ -n "$command_line" ]] || {
  printf '%s\n' '{"permission":"allow"}'
  exit 0
}

# Always allow the canonical append script.
if [[ "$command_line" == *append-pr-body.sh* ]]; then
  printf '%s\n' '{"permission":"allow"}'
  exit 0
fi

# Block inline gh pr edit --body (not --body-file).
if [[ "$command_line" =~ gh[[:space:]]+pr[[:space:]]+edit ]] && [[ "$command_line" == *"--body"* ]] && [[ "$command_line" != *"--body-file"* ]]; then
  if [[ "${CURSOR_PR_BODY_FULL_MERGE_ACK:-0}" == "1" ]]; then
    printf '%s\n' '{"permission":"allow"}'
    exit 0
  fi
  cat <<'JSON'
{"permission":"deny","agentMessage":"BLOCKED: gh pr edit --body replaces the entire PR description. Use: bash scripts/cursor/append-pr-body.sh <owner/repo> <N> --title \"Follow-up: ...\" --file follow-up.md OR gh pr edit --body-file with a full integrative merged body (after READ→BACKUP).","userMessage":"Cursor agent blocked from inline gh pr edit --body."}
JSON
  exit 0
fi

# READ preflight: backup when fetching PR body via gh pr view.
if [[ "$command_line" =~ gh[[:space:]]+pr[[:space:]]+view ]] && [[ "$command_line" == *body* ]]; then
  read -r repo pr <<<"$(printf '%s' "$command_line" | python3 -c '
import re, sys
cmd = sys.stdin.read()
repo = ""
pr = ""
m = re.search(r"--repo[[:space:]]+([^\s]+)", cmd)
if m:
    repo = m.group(1)
m = re.search(r"gh[[:space:]]+pr[[:space:]]+view[[:space:]]+([0-9]+)", cmd)
if m:
    pr = m.group(1)
if not repo:
    m = re.search(r"github\.com/([^/]+/[^/\s]+)", cmd)
    if m:
        repo = m.group(1)
print(repo, pr)
')"
  if [[ -n "$repo" && -n "$pr" ]]; then
    pr_body_backup_if_needed "$repo" "$pr" "shell-preflight"
  fi
fi

printf '%s\n' '{"permission":"allow"}'
