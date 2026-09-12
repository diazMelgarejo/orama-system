#!/usr/bin/env bash
# Run the PT five-stage harness through one repository-owned entry point.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
# shellcheck source=resolve_perp_harness.sh
source "${repo_root}/bin/orama-system/skills/hermes-harness/scripts/resolve_perp_harness.sh"

task="$*"
if [[ -z "$task" ]]; then
  echo "Usage: /hermes-orama <task description>" >&2
  exit 1
fi

perp_script="$(resolve_perp_harness_script)"
echo "🧠 L-PT: Orama 5-stage pipeline (PT hermes_harness, not delegate_task): $task"
exec python3 "$perp_script" "$task"
