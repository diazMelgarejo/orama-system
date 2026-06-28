#!/usr/bin/env bash
# Reconcile the canonical native-Codex OpenClaw agent. Safe to re-run.

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
ORAMA_ROOT="$(cd "$SCRIPT_DIR/../../../../../../" && pwd)"
RESOLVER="$ORAMA_ROOT/scripts/openclaw/resolve-openclaw.sh"
OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME}"
CONFIG_PATH="$OPENCLAW_HOME/.openclaw/openclaw.json"
WORKSPACE="$OPENCLAW_HOME/.openclaw/agents/codex-agent"
AGENT_DIR="$WORKSPACE/agent"
GENERATOR="$SCRIPT_DIR/generate_codex_openclaw_profile.py"

log() { printf '[codex-bind] %s\n' "$*" >&2; }
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

oc() { "$RESOLVER" "$@"; }

restart_required=false
openai_plugin="$(oc plugins list --json | jq -c '[.plugins[] | select(.id == "openai")][0]')"
if [[ "$openai_plugin" == "null" ]]; then
  if [[ "$DRY_RUN" == true ]]; then
    log "DRY-RUN: would install the bundled openai provider plugin"
  else
    log "installing the bundled openai provider plugin"
    if ! oc plugins install openai >/dev/null; then
      printf '%s\n' '{"status":"needs_plugin","agent_id":"codex-agent","backend":"codex/gpt-5.5","follow_up":"install an approved OpenClaw OpenAI provider plugin"}'
      exit 0
    fi
    restart_required=true
    openai_plugin="$(oc plugins list --json | jq -c '[.plugins[] | select(.id == "openai")][0]')"
  fi
fi

if [[ "$openai_plugin" == "null" && "$DRY_RUN" == false ]]; then
  printf '%s\n' '{"status":"needs_plugin","agent_id":"codex-agent","backend":"codex/gpt-5.5","follow_up":"install an approved OpenClaw OpenAI provider plugin"}'
  exit 0
fi

if [[ "$DRY_RUN" == false ]]; then
  # An existing allowlist is a security boundary. Preserve it and add only the
  # official bundled OpenAI provider needed by the native openai-codex login.
  if jq -e '.plugins.allow | type == "array"' "$CONFIG_PATH" >/dev/null; then
    desired_plugin_allow="$(jq -c '
      .plugins.allow | if index("openai") then . else . + ["openai"] end
    ' "$CONFIG_PATH")"
    if ! jq -e --argjson desired "$desired_plugin_allow" '.plugins.allow == $desired' "$CONFIG_PATH" >/dev/null; then
      log "adding bundled openai provider to the existing plugin allowlist"
      oc config set plugins.allow "$desired_plugin_allow" --strict-json >/dev/null
      restart_required=true
    fi
  fi

  if [[ "$(jq -r '.enabled == true and .status == "loaded"' <<<"$openai_plugin")" != "true" ]]; then
    log "enabling bundled openai provider plugin"
    oc plugins enable openai >/dev/null
    restart_required=true
  fi
else
  log "DRY-RUN: would ensure the bundled openai provider is installed, allowed, and enabled"
fi

agent_index() {
  jq -r '(.agents.list // []) | map(.id) | index("codex-agent") // empty' "$CONFIG_PATH"
}

current_index="$(agent_index)"
if [[ -n "$current_index" ]]; then
  current_workspace="$(jq -r --argjson index "$current_index" '.agents.list[$index].workspace // empty' "$CONFIG_PATH")"
  if [[ "$current_workspace" != "$WORKSPACE" ]]; then
    fail "codex-agent already exists with a different workspace: $current_workspace"
  fi
else
  log "codex-agent is absent; creating the canonical workspace at $WORKSPACE"
  if [[ "$DRY_RUN" == true ]]; then
    printf 'DRY-RUN: '
    printf '%q ' "$RESOLVER" agents add codex-agent --workspace "$WORKSPACE" --agent-dir "$AGENT_DIR" --model codex/gpt-5.5 --non-interactive --json
    printf '\n'
  else
    oc agents add codex-agent \
      --workspace "$WORKSPACE" \
      --agent-dir "$AGENT_DIR" \
      --model codex/gpt-5.5 \
      --non-interactive \
      --json >/dev/null
    current_index="$(agent_index)"
    [[ -n "$current_index" ]] || fail "OpenClaw did not register codex-agent"
  fi
fi

config_changed=false
if [[ "$DRY_RUN" == false ]]; then
  desired_allow_agents="$(jq -c '
    (.agents.defaults.subagents.allowAgents // [])
    | if index("codex-agent") then . else . + ["codex-agent"] end
  ' "$CONFIG_PATH")"

  needs_agent_update="$(jq -e --argjson index "$current_index" --arg effort "$EFFORT" --arg agent_dir "$AGENT_DIR" '
    .agents.list[$index] as $agent
    | ($agent.model != "codex/gpt-5.5")
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
      --argjson allow_agents "$desired_allow_agents" \
      '[
        {path: ("agents.list[" + $index + "].model"), value: "codex/gpt-5.5"},
        {path: ("agents.list[" + $index + "].thinkingDefault"), value: $effort},
        {path: ("agents.list[" + $index + "].tools.profile"), value: "coding"},
        {path: ("agents.list[" + $index + "].agentDir"), value: $agent_dir},
        {path: "agents.defaults.subagents.allowAgents", value: $allow_agents}
      ]')"
    log "updating only Codex-managed agent fields and delegation allowlist"
    oc config set --batch-json "$patch" >/dev/null
    config_changed=true
  else
    log "native agent schema and delegation are already converged"
    config_changed=false
  fi
else
  log "DRY-RUN: would reconcile model, thinkingDefault, tools.profile, agentDir, and allowAgents"
  config_changed=false
fi

generator_args=(--workspace "$WORKSPACE" --effort "$EFFORT")
if [[ "$DRY_RUN" == true ]]; then
  generator_args+=(--dry-run)
fi
python3 "$GENERATOR" "${generator_args[@]}" >/dev/null

if [[ "$DRY_RUN" == true ]]; then
  printf '%s\n' '{"status":"dry-run","agent_id":"codex-agent","backend":"codex/gpt-5.5","binding_path":"native-catalog"}'
  exit 0
fi

oc config validate >/dev/null

if [[ "$config_changed" == true ]]; then
  restart_required=true
fi

if [[ "$restart_required" == true ]]; then
  log "restarting the gateway after provider or agent configuration changed"
  oc gateway restart >/dev/null
fi

openai_plugin="$(oc plugins list --json | jq -c '[.plugins[] | select(.id == "openai")][0]')"
if [[ "$(jq -r '.enabled == true and .status == "loaded"' <<<"$openai_plugin")" != "true" ]]; then
  printf '%s\n' '{"status":"needs_plugin","agent_id":"codex-agent","backend":"codex/gpt-5.5","follow_up":"enable the bundled openai provider plugin and restart the gateway"}'
  exit 0
fi

status="$(oc models status --agent codex-agent --json)"
if jq -e '.auth.missingProvidersInUse | index("codex") != null' <<<"$status" >/dev/null; then
  printf '%s\n' '{"status":"needs_auth","agent_id":"codex-agent","backend":"codex/gpt-5.5","binding_path":"native-catalog","follow_up":"openclaw models auth login --provider openai-codex"}'
  exit 0
fi

if [[ "$(jq -r '.resolvedDefault' <<<"$status")" != "codex/gpt-5.5" ]]; then
  fail "resolved model is not codex/gpt-5.5"
fi

printf '%s\n' '{"status":"ok","agent_id":"codex-agent","backend":"codex/gpt-5.5","binding_path":"native-catalog"}'
