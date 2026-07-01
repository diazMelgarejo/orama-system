#!/usr/bin/env bash
# Reconcile the canonical Cline-backed OpenClaw agent. Safe to re-run.
# Mirrors bind_codex_backend.sh but for cline-agent (agent-level binding, not
# a native model-provider binding — see references/cline-backend-binding.md).

set -euo pipefail

EFFORT="medium"
DRY_RUN=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --effort)
      EFFORT="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

case "$EFFORT" in
  medium|high|xhigh) ;;
  *)
    echo "Invalid --effort '$EFFORT' (expected medium, high, or xhigh)" >&2
    exit 2
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORAMA_ROOT="$(cd "$SCRIPT_DIR/../../../../../" && pwd)"
RESOLVER="$ORAMA_ROOT/scripts/openclaw/resolve-openclaw.sh"
OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME}"
CONFIG_PATH="$OPENCLAW_HOME/.openclaw/openclaw.json"
WORKSPACE="$OPENCLAW_HOME/.openclaw/agents/cline-agent"
AGENT_DIR="$WORKSPACE/agent"
GENERATOR="$SCRIPT_DIR/generate_cline_openclaw_profile.py"
MODEL="openrouter/z-ai/glm-5.2"

log() { printf '[cline-bind] %s\n' "$*" >&2; }
fail() { log "FAIL: $*"; exit 1; }

if [[ ! -x "$RESOLVER" ]]; then
  fail "OpenClaw resolver is missing: $RESOLVER"
fi
if ! command -v jq >/dev/null 2>&1; then
  fail "jq is required"
fi
if [[ ! -f "$CONFIG_PATH" ]]; then
  fail "OpenClaw configuration is missing: $CONFIG_PATH"
fi

# Cline CLI check — report needs_cline without modifying config if absent.
if ! command -v cline >/dev/null 2>&1; then
  printf '%s\n' '{"status":"needs_cline","agent_id":"cline-agent","backend":"openrouter/z-ai/glm-5.2","follow_up":"install cline CLI: npm install -g cline"}'
  exit 0
fi

oc() { "$RESOLVER" "$@"; }

agent_index() {
  jq -r '(.agents.list // []) | map(.id) | index("cline-agent") // empty' "$CONFIG_PATH"
}

current_index="$(agent_index)"
restart_required=false

if [[ -z "$current_index" ]]; then
  if [[ "$DRY_RUN" == true ]]; then
    log "DRY-RUN: would create cline-agent with openclaw agents add"
  else
    log "creating cline-agent"
    oc agents add cline-agent \
      --workspace "$WORKSPACE" \
      --agent-dir "$AGENT_DIR" \
      --model "$MODEL" \
      --non-interactive >/dev/null
    restart_required=true
    current_index="$(agent_index)"
  fi
fi

if [[ "$DRY_RUN" == false ]]; then
  existing_ws="$(jq -r --argjson i "$current_index" '.agents.list[$i].workspace // ""' "$CONFIG_PATH")"
  if [[ -n "$existing_ws" && "$existing_ws" != "$WORKSPACE" ]]; then
    fail "existing cline-agent has workspace '$existing_ws' (expected '$WORKSPACE'); refusing to change it"
  fi
fi

config_changed=false
if [[ "$DRY_RUN" == false ]]; then
  desired_allow_agents="$(jq -c '
    (.agents.defaults.subagents.allowAgents // [])
    | if index("cline-agent") then . else . + ["cline-agent"] end
  ' "$CONFIG_PATH")"

  needs_agent_update="$(jq -e --argjson index "$current_index" --arg effort "$EFFORT" --arg agent_dir "$AGENT_DIR" --arg model "$MODEL" '
    .agents.list[$index] as $agent
    | (($agent.model | if type == "object" then .primary else . end) != $model)
      or ($agent.thinkingDefault != $effort)
      or ($agent.tools.profile != "coding")
      or ($agent.agentDir != $agent_dir)
  ' "$CONFIG_PATH" >/dev/null && echo true || echo false)"
  needs_delegation_update="$(jq -e --argjson desired "$desired_allow_agents" '
    (.agents.defaults.subagents.allowAgents // []) != $desired
  ' "$CONFIG_PATH" >/dev/null && echo true || echo false)"

  if [[ "$needs_agent_update" == true || "$needs_delegation_update" == true ]]; then
    patch="$(jq -nc \
      --arg index "$current_index" \
      --arg effort "$EFFORT" \
      --arg agent_dir "$AGENT_DIR" \
      --arg model "$MODEL" \
      --argjson allow_agents "$desired_allow_agents" \
      '[
        {path: ("agents.list[" + $index + "].model"), value: $model},
        {path: ("agents.list[" + $index + "].thinkingDefault"), value: $effort},
        {path: ("agents.list[" + $index + "].tools.profile"), value: "coding"},
        {path: ("agents.list[" + $index + "].agentDir"), value: $agent_dir},
        {path: ("agents.list[" + $index + "].name"), value: "cline-agent"},
        {path: "agents.defaults.subagents.allowAgents", value: $allow_agents}
      ]')"
    log "updating only Cline-managed agent fields and delegation allowlist"
    oc config set --batch-json "$patch" >/dev/null
    config_changed=true
  else
    log "agent schema and delegation are already converged"
    config_changed=false
  fi
else
  log "DRY-RUN: would reconcile model, thinkingDefault, tools.profile, agentDir, name, and allowAgents"
  config_changed=false
fi

generator_args=(--workspace "$WORKSPACE" --effort "$EFFORT")
if [[ "$DRY_RUN" == true ]]; then
  generator_args+=(--dry-run)
fi
python3 "$GENERATOR" "${generator_args[@]}" >/dev/null

if [[ "$DRY_RUN" == true ]]; then
  printf '%s\n' '{"status":"dry-run","agent_id":"cline-agent","backend":"openrouter/z-ai/glm-5.2","binding_path":"agent-level"}'
  exit 0
fi

oc config validate >/dev/null

if [[ "$config_changed" == true ]]; then
  restart_required=true
fi

if [[ "$restart_required" == true ]]; then
  log "restarting the gateway after agent configuration changed"
  oc gateway restart >/dev/null
fi

status="$(oc models status --agent cline-agent --json 2>/dev/null || echo '{}')"
if jq -e '.auth.missingProvidersInUse | index("openrouter") != null' <<<"$status" >/dev/null 2>&1; then
  printf '%s\n' '{"status":"needs_auth","agent_id":"cline-agent","backend":"openrouter/z-ai/glm-5.2","binding_path":"agent-level","follow_up":"set OPENROUTER_API_KEY env and restart gateway"}'
  exit 0
fi

printf '%s\n' '{"status":"ok","agent_id":"cline-agent","backend":"openrouter/z-ai/glm-5.2","binding_path":"agent-level","cline_cli":"'"$(command -v cline)"'"}'
