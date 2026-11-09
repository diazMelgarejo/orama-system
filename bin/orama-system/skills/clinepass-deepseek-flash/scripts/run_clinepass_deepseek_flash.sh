#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: run_clinepass_deepseek_flash.sh [--cwd PATH] [--timeout SECONDS] [--plan|--act] PROMPT

Dispatch Cline non-interactively with:
  model:     cline-pass/deepseek-v4.1-flash-1017
  provider:  cline-pass
  reasoning: medium
  output:    JSON lines

Set CLINE_BIN to an absolute executable path if cline is not on PATH. The
installed CLI must support explicit provider selection and --thinking.

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

cline_bin="${CLINE_BIN:-cline}"
if ! command -v "$cline_bin" >/dev/null 2>&1; then
  echo "cline CLI not found on PATH" >&2
  exit 127
fi

if ! help_text="$("$cline_bin" --help 2>&1)"; then
  echo "cannot inspect cline CLI help" >&2
  exit 1
fi
if ! grep -q -- '--provider' <<<"$help_text" || ! grep -q -- '--thinking' <<<"$help_text" || ! grep -qw -- 'medium' <<<"$help_text"; then
  echo "cline CLI lacks explicit provider or medium thinking support" >&2
  exit 1
fi

auto_args=()
if grep -q -- '--auto-approve-all' <<<"$help_text"; then
  auto_args=(--auto-approve-all)
elif grep -q -- '--auto-approve ' <<<"$help_text"; then
  auto_args=(--auto-approve true)
else
  echo "cline CLI lacks a supported auto-approval flag" >&2
  exit 1
fi

cmd=("$cline_bin" --json)
[[ -z "$mode" ]] || cmd+=("$mode")
cmd+=("${auto_args[@]}")
cmd+=(-P cline-pass -m cline-pass/deepseek-v4.1-flash-1017 --thinking medium -c "$cwd" -t "$timeout")
cmd+=("$*")

exec "${cmd[@]}"
