#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: run_clinepass_deepseek_flash.sh [--cwd PATH] [--timeout SECONDS] [--plan|--act] PROMPT

Dispatch Cline non-interactively with:
  model:     cline-pass/deepseek-v4-flash
  reasoning: high
  output:    JSON lines

The script adapts to Cline CLI flag drift between --auto-approve-all and
--auto-approve true, and between --reasoning-effort high and --thinking high.
USAGE
}

cwd="/private/tmp"
timeout="300"
mode=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cwd)
      [[ $# -ge 2 ]] || { echo "missing value for --cwd" >&2; exit 2; }
      cwd="$2"
      shift 2
      ;;
    --timeout|-t)
      [[ $# -ge 2 ]] || { echo "missing value for --timeout" >&2; exit 2; }
      timeout="$2"
      shift 2
      ;;
    --plan|-p)
      mode="--plan"
      shift
      ;;
    --act|-a)
      mode="--act"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

[[ $# -gt 0 ]] || { echo "missing prompt" >&2; usage >&2; exit 2; }

if ! command -v cline >/dev/null 2>&1; then
  echo "cline CLI not found on PATH" >&2
  exit 127
fi

help_text="$(cline task --help 2>&1 || true)"

auto_args=()
if grep -q -- '--auto-approve-all' <<<"$help_text"; then
  auto_args=(--auto-approve-all)
elif grep -q -- '--auto-approve ' <<<"$help_text"; then
  auto_args=(--auto-approve true)
fi

reasoning_args=()
if grep -q -- '--reasoning-effort' <<<"$help_text"; then
  reasoning_args=(--reasoning-effort high)
elif grep -q -- '--thinking' <<<"$help_text"; then
  reasoning_args=(--thinking high)
fi

cmd=(cline task --json)
[[ -z "$mode" ]] || cmd+=("$mode")
cmd+=("${auto_args[@]}")
cmd+=("${reasoning_args[@]}")
cmd+=(-m cline-pass/deepseek-v4-flash -c "$cwd" -t "$timeout")
cmd+=("$*")

exec "${cmd[@]}"
