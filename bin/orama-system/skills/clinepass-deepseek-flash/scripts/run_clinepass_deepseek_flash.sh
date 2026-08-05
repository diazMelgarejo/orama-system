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

Fixed 2026-08-05: earlier versions of this script invoked `cline task ...`.
There is no `task` subcommand on the real CLI (verified against v3.0.49) --
the prompt is a bare positional argument to `cline` itself. Every prior
invocation of this script failed with "Unknown command or unquoted prompt".
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
      # act is the CLI's default when --plan is absent; no flag to pass.
      mode=""
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

help_text="$(cline --help 2>&1 || true)"

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

cmd=(cline --json)
[[ -z "$mode" ]] || cmd+=("$mode")
cmd+=("${auto_args[@]}")
cmd+=("${reasoning_args[@]}")
cmd+=(-m cline-pass/deepseek-v4-flash -c "$cwd" -t "$timeout")
cmd+=("$*")

exec "${cmd[@]}"
