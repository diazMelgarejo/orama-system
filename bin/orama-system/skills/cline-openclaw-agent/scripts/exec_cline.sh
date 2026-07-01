#!/usr/bin/env bash
# Safe non-interactive Cline one-shot exec wrapper.
# Usage: exec_cline.sh "task prompt" [--cwd <dir>] [--thinking <level>] [--provider <id>] [--model <id>] [--timeout <s>] [--plan]

set -euo pipefail

PROMPT=""
CWD=""
THINKING="medium"
PROVIDER="cline-pass"
MODEL="cline-pass/glm-5.2"
TIMEOUT="600"
PLAN=false
EXTRA=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cwd) CWD="${2:-}"; shift 2 ;;
    --thinking) THINKING="${2:-}"; shift 2 ;;
    --provider) PROVIDER="${2:-}"; shift 2 ;;
    --model) MODEL="${2:-}"; shift 2 ;;
    --timeout) TIMEOUT="${2:-}"; shift 2 ;;
    --plan) PLAN=true; shift ;;
    --) shift; EXTRA+=("$@"); break ;;
    -*) echo "Unknown flag: $1" >&2; exit 2 ;;
    *) PROMPT="$1"; shift ;;
  esac
done

[[ -z "$PROMPT" ]] && { echo "Usage: exec_cline.sh \"<prompt>\" [--cwd <dir>] [--thinking <level>] [--provider <id>] [--model <id>] [--timeout <s>] [--plan]" >&2; exit 2; }
command -v cline >/dev/null 2>&1 || { echo "cline CLI not found on PATH" >&2; exit 1; }

cmd=(cline "$PROMPT" --json --auto-approve true --thinking "$THINKING" -P "$PROVIDER" -m "$MODEL" --timeout "$TIMEOUT" --retries 3)
[[ -n "$CWD" ]] && cmd+=(-c "$CWD")
[[ "$PLAN" == true ]] && cmd+=(--plan)
[[ ${#EXTRA[@]} -gt 0 ]] && cmd+=("${EXTRA[@]}")

exec "${cmd[@]}"
