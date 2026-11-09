#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: run_clinepass_deepseek_flash.sh [--cwd PATH] [--timeout SECONDS] [--plan|--act] PROMPT

Dispatch Cline non-interactively with:
  provider:  cline-pass (explicit -P pin; the CLI default provider is `cline`)
  model:     cline-pass/deepseek-v4.1-flash-1017
  reasoning: medium (--thinking medium)
  output:    JSON lines
  approvals: --auto-approve true (CLI 3.0.74 default; still passed explicitly)

Required capabilities are read from `cline --help` instead of being assumed, and
each one fails closed: a CLI that cannot pin the provider, the reasoning level,
or tool auto-approval is refused rather than dispatched. An unpinned provider is
the documented root cause of the original "routed through another provider"
blocker -- the slug is then rejected by a provider that never had it.

Set CLINE_BIN to an absolute executable path if cline is not on PATH. The
installed CLI must support explicit provider selection and --thinking.
Older approval flag shapes remain supported, but an older CLI without medium
thinking support is refused rather than silently changing the approved effort.

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
if ! grep -q -- '--provider' <<<"$help_text"; then
  echo "cline CLI lacks --provider support" >&2
  exit 1
fi
if ! grep -q -- '--thinking' <<<"$help_text"; then
  echo "cline CLI lacks --thinking support" >&2
  exit 1
fi
if ! grep -qw -- 'medium' <<<"$help_text"; then
  echo "cline CLI lacks medium thinking support" >&2
  exit 1
fi

if grep -q -- '--auto-approve-all' <<<"$help_text"; then
  auto_args=(--auto-approve-all)
elif grep -q -- '--auto-approve' <<<"$help_text"; then
  auto_args=(--auto-approve true)
else
  # A non-TTY run cannot answer approval prompts, so an unflagged dispatch hangs.
  echo "cline CLI lacks an auto-approve flag; refusing to dispatch non-interactively" >&2
  exit 1
fi

cmd=("$cline_bin" --json)
[[ -z "$mode" ]] || cmd+=("$mode")
cmd+=("${auto_args[@]}")
cmd+=(-P cline-pass -m cline-pass/deepseek-v4.1-flash-1017 --thinking medium -c "$cwd" -t "$timeout")
cmd+=("$*")

exec "${cmd[@]}"
