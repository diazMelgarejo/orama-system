#!/usr/bin/env bash
# beforeMCPExecution — block ManagePullRequest update_pr body writes (Cursor agents only).
# Cursor agents must use scripts/cursor/append-pr-body.sh (append-only).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=pr-body-backup-lib.sh
source "$SCRIPT_DIR/pr-body-backup-lib.sh"

input="$(cat)"
decision="ALLOW"

while IFS= read -r line; do
  case "$line" in
    BACKUP\|*)
      repo="${line#BACKUP|}"
      pr="${repo##*|}"
      repo="${repo%|*}"
      pr_body_backup_if_needed "$repo" "$pr" "mcp-preflight"
      ;;
    DENY)
      decision="DENY"
      ;;
  esac
done < <(python3 - "$input" <<'PY'
import json, os, sys

raw = sys.argv[1]
try:
    data = json.loads(raw) if raw.strip() else {}
except json.JSONDecodeError:
    print("ALLOW")
    sys.exit(0)

tool = str(data.get("tool_name") or data.get("toolName") or "")
tool_input = data.get("tool_input") or data.get("arguments") or data.get("input") or {}
if isinstance(tool_input, str):
    try:
        tool_input = json.loads(tool_input)
    except json.JSONDecodeError:
        tool_input = {}

action = str(tool_input.get("action") or "")
body = tool_input.get("body")
remote = str(tool_input.get("remote_url") or tool_input.get("remoteUrl") or "")
pr_number = tool_input.get("pr_number") or tool_input.get("prNumber") or tool_input.get("branch_name")

is_manage_pr = "managepullrequest" in tool.lower() or tool == "ManagePullRequest"
if not is_manage_pr:
    print("ALLOW")
    sys.exit(0)

if remote and pr_number and str(pr_number).isdigit():
    repo = remote.replace("https://github.com/", "").replace("http://github.com/", "").strip("/")
    if repo:
        print(f"BACKUP|{repo}|{pr_number}")

if action == "update_pr" and body:
    if os.environ.get("CURSOR_PR_BODY_FULL_MERGE_ACK") == "1":
        print("ALLOW")
        sys.exit(0)
    print("DENY")
    sys.exit(0)

print("ALLOW")
PY
)

if [[ "$decision" == "DENY" ]]; then
  cat <<'JSON'
{"permission":"deny","agentMessage":"BLOCKED: ManagePullRequest update_pr with body= replaces the entire PR description. Mandatory path: (1) gh pr view --json body, (2) backup to .git/pr-body-backups/, (3) merge append-only, (4) bash scripts/cursor/append-pr-body.sh <owner/repo> <N> --title \"Follow-up: ...\" --file follow-up.md. Never pass delta-only body=. Skill: bin/orama-system/skills/cursor-pr-body/SKILL.md","userMessage":"Cursor agent blocked from clobbering PR body. Use append-pr-body.sh."}
JSON
  exit 0
fi

printf '%s\n' '{"permission":"allow"}'
