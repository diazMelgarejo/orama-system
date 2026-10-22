---
name: openclaw-new-agent
description: Create a fully wired OpenClaw agent with required directives, directories, and openclaw.json registration.
agent_compatibility: [Claude, Hermes, Gemini, Codex, Cursor, WindSurf, Antigravity, OpenCode, 8gent.dev]
model_routing: ollama-first-then-openrouter
version: "1.0"
layer: "1 — Operations (builds on Layer 0: v1/OpenRouter.md)"
upstream: https://github.com/rahulsub-be/cc-openclaw
upstream_license: MIT
extends: ../cc-openclaw/.claude/skills/openclaw-new-agent/SKILL.md
overlay_role: orama-normalized cross-harness extension
allowed-tools: bash, file-operations
triggers:
  - create a new openclaw agent
  - openclaw-new-agent
  - /openclaw-new-agent
  - add an openclaw agent
  - register a sub-agent in openclaw.json
  - scaffold openclaw agent directives
---

## Overlay Source

This Orama-normalized skill extends the upstream cc-openclaw skill at [`../cc-openclaw/.claude/skills/openclaw-new-agent/SKILL.md`](../cc-openclaw/.claude/skills/openclaw-new-agent/SKILL.md). Use the upstream file as the behavioral baseline and this file as the cross-harness overlay for Orama, Perpetua-Tools, Codex, Hermes, Gemini, and other agent runners.

## Purpose

Create a new OpenClaw agent consistently without configuration drift. Complete required files before registration, then explicitly authorize parent-child delegation when requested.

## When to Use

- Creating any new OpenClaw agent profile
- Splitting responsibilities into specialized sub-agents
- Standardizing agent scaffolding across contributors

## Inputs

- Required:
  - `agent_id` (lowercase, hyphens)
  - `display_name` (human-readable)
  - `mode` (`standalone` or `sub-agent`)
  - `openclaw_home` (absolute OpenClaw state and configuration root)
- Optional:
  - `model_primary` (defaults to `ollama/qwen3.5:9b-nvfp4`)
  - `channel` (`telegram|slack|whatsapp|none`)
- Required when `mode=sub-agent`:
  - `parent_agent_id` (existing parent agent ID)
  - `parent_delegation_approved` (explicit approval to add the child to the parent's `allowAgents` list)

## Procedure

**CLI flags rechecked 2026-10-22 against OpenClaw 2026.7.1-beta.5.** Do not
hand-edit `openclaw_home/openclaw.json`. The CLI owns registration and schema
validation. The procedure below scopes every command to the requested target
and completes directive files before registration. Run the blocks in the same Bash process. Serialize
configuration changes for the target installation; do not run concurrent
agent-creation or configuration writers against it.

1. Validate inputs and scope the target OpenClaw installation.

```bash
set -euo pipefail

: "${openclaw_home:?openclaw_home is required}"
case "$openclaw_home" in
  /*) ;;
  *) printf '%s\n' 'openclaw_home must be an absolute path' >&2; exit 2 ;;
esac
printf '%s' "$agent_id" | grep -Eq '^[a-z0-9]+(-[a-z0-9]+)*$'
case "$mode" in
  standalone|sub-agent) ;;
  *) printf '%s\n' 'mode must be standalone or sub-agent' >&2; exit 2 ;;
esac
if [ "$mode" = 'sub-agent' ]; then
  : "${parent_agent_id:?parent_agent_id is required for mode=sub-agent}"
  [ "${parent_delegation_approved:-}" = 'true' ] || {
    printf '%s\n' 'parent_delegation_approved=true is required for mode=sub-agent' >&2
    exit 2
  }
  printf '%s' "$parent_agent_id" | grep -Eq '^[a-z0-9]+(-[a-z0-9]+)*$'
fi

workspace="$openclaw_home/agents/$agent_id"
agent_dir="$workspace/agent"
oc() {
  OPENCLAW_HOME="$openclaw_home" \
  OPENCLAW_STATE_DIR="$openclaw_home" \
  OPENCLAW_CONFIG_PATH="$openclaw_home/openclaw.json" \
  openclaw "$@"
}

test ! -e "$workspace" || { printf '%s\n' "agent workspace already exists: $workspace" >&2; exit 2; }
agents_json="$(oc agents list --json)"
printf '%s' "$agents_json" | python3 -c '
import json, sys
agent_id = sys.argv[1]
agents = json.load(sys.stdin)
if not isinstance(agents, list):
    raise SystemExit("agents list did not return a JSON array")
if any(item.get("id") == agent_id for item in agents):
    raise SystemExit("agent is already registered: " + agent_id)
' "$agent_id"
```

2. For a sub-agent, validate the named parent and existing allow-list before
   creating anything. The explicit approval input is required because this
   expands that parent's delegation authority.

```bash
if [ "$mode" = 'sub-agent' ]; then
  oc config get agents.list --json | python3 -c '
import json, sys
parent_id = sys.argv[1]
parent = next((item for item in json.load(sys.stdin) if item.get("id") == parent_id), None)
if parent is None:
    raise SystemExit("parent agent is not registered: " + parent_id)
allow = parent.get("subagents", {}).get("allowAgents", [])
if not isinstance(allow, list) or not all(isinstance(item, str) for item in allow):
    raise SystemExit("parent allowAgents must be a list of agent IDs")
' "$parent_agent_id"
fi
```

3. Prepare the workspace without registering the agent.

```bash
mkdir -p "$agent_dir"
```

4. Write all six directive files from repository-approved templates:
   `SOUL.md`, `IDENTITY.md`, `USER.md`, `AGENTS.md`, `TOOLS.md`, and `SECURITY.md`.
   Fill `IDENTITY.md` with the supplied display name, role, model, invocation,
   and scope. Do not copy another agent's private files.
   Add this provenance rule to the generated `AGENTS.md`:

   ```markdown
   ## Coordination provenance
   Follow the gossip-bus author-actor takeover policy: preserve original
   authorship, identify the current actor and verification state, bound
   endorsements to evidence, and disclose a takeover before commit, push,
   completion, or promotion claims. Use supported GossipBus APIs only.
   ```

5. Validate the completed files, then register the prepared workspace.

```bash
for directive in SOUL.md IDENTITY.md USER.md AGENTS.md TOOLS.md SECURITY.md; do
  test -s "$workspace/$directive"
done
oc agents add "$agent_id" \
  --model "${model_primary:-ollama/qwen3.5:9b-nvfp4}" \
  --workspace "$workspace" \
  --agent-dir "$agent_dir" \
  --non-interactive --json
oc config validate
oc agents list --json | python3 -c '
import json, sys
agent_id = sys.argv[1]
raise SystemExit(0 if any(item.get("id") == agent_id for item in json.load(sys.stdin)) else 1)
' "$agent_id"
```

6. For `mode=sub-agent`, add the child to the parent's allow-list with a
   minimal CLI-validated patch. `openclaw agents bind` configures channel
   bindings; it does not grant parent-child delegation.

```bash
build_parent_allowlist_patch() {
  oc config get agents.list --json | python3 -c '
import json, sys
parent_id, child_id = sys.argv[1:3]
agents = json.load(sys.stdin)
for index, agent in enumerate(agents):
    if agent.get("id") == parent_id:
        allow = agent.get("subagents", {}).get("allowAgents", [])
        if not isinstance(allow, list) or not all(isinstance(item, str) for item in allow):
            raise SystemExit("parent allowAgents must be a list of agent IDs")
        desired = [*allow]
        if child_id not in desired:
            desired.append(child_id)
        print(json.dumps([{"path": f"agents.list[{index}].subagents.allowAgents", "value": desired}]))
        break
else:
    raise SystemExit("parent agent is not registered: " + parent_id)
' "$parent_agent_id" "$agent_id"
}

if [ "$mode" = 'sub-agent' ]; then
  delegation_patch="$(build_parent_allowlist_patch)"
  oc config set --batch-json "$delegation_patch"
fi
```

If registration or delegation fails, report an error and inspect the target's
configuration before retrying. The CLI may save registration before a later
step fails. Do not automatically delete the agent: `agents delete` may use a
gateway RPC whose target differs from the local configuration. A failed
delegation leaves a completed agent profile without confirmed parent access;
report that partial state instead of claiming successful sub-agent creation.

7. If a channel is requested, delegate to `openclaw-add-channel` only after
   registration completes.

```bash
if [ "${channel:-none}" != 'none' ]; then
  echo "Run: openclaw-add-channel for $channel and bind to $agent_id" >&2
fi
```

8. **Auth is per-agent, not per-provider.** A provider shown as `configured`
   in the model catalog does not prove that the new agent can use it. Each
   agent has an isolated auth store at
   `<openclaw_home>/agents/<id>/agent/openclaw-agent.sqlite`. Check the auth
   state with scoped commands before assuming the agent is ready. Interactive
   OAuth requires the operator's terminal or browser and cannot be completed
   headlessly.
## Output Contract

```json
{
  "status": "ok|error",
  "openclaw_home": "<absolute target>",
  "files_modified": ["openclaw.json", "agents/<agent_id>/SOUL.md", "agents/<agent_id>/IDENTITY.md", "agents/<agent_id>/USER.md", "agents/<agent_id>/AGENTS.md", "agents/<agent_id>/TOOLS.md", "agents/<agent_id>/SECURITY.md"],
  "follow_up_actions": ["optional-next-step"]
}
```

## Naming Enforcement

- `agent_id` must be lowercase and hyphenated: `^[a-z0-9]+(-[a-z0-9]+)*$`
- Sub-agent IDs must still follow the same format as standalone agents
- Keep file names exact: `SOUL.md`, `IDENTITY.md`, `USER.md`, `AGENTS.md`, `TOOLS.md`, `SECURITY.md`

## Gotchas

- Manual agent creation often misses one or more of the six directive files.
  `openclaw agents add` auto-creates SOUL/USER/AGENTS/TOOLS.md and a blank
  IDENTITY.md template — SECURITY.md and a filled-in IDENTITY.md still need
  writing by hand (verified 2026-07-11, see § Procedure above).
- Sub-agents without explicit parent `allowAgents` wiring will not be callable.
- Do not use `openclaw agents bind` for parent-child delegation. It configures
  channel routing, not `allowAgents`; use the validated CLI configuration patch
  in this procedure.
- **`openclaw agent --session-key agent:<id>:<key>` requires `<id>` to be a
  REAL, already-registered agent** — verified live: `--session-key
  agent:review:...` failed with `Agent "review" no longer exists in
  configuration` because no agent named "review" was ever created. To make
  a one-off ad-hoc model call without a persistent agent, borrow an
  EXISTING agent's session slot (e.g. `agent:main:<ephemeral-key>`) with
  `--model` as the override — but note its auth store may not have the
  target provider's credentials either (see next gotcha). For anything
  recurring, create a real persistent agent instead (§ Procedure) —
  ephemeral session-key borrowing is a one-shot workaround, not a pattern.
- **Auth-provider preference order, when a provider supports both web OAuth
  and an API key: ALWAYS prefer web/OAuth login
  (`openclaw models auth login --provider <id>`) over API-key auth.** An
  API key is backup/fallback only — never set one up preferentially or skip
  the interactive login step just because a key is available (user-stated
  policy, 2026-07-11, in the context of `google-antigravity`/Gemini access
  where a Gemini API key exists as a fallback path).

## Boundaries

### Always Do

- Validate `openclaw_home`, `agent_id`, `mode`, and any sub-agent parent inputs before any create step.
- Scope every OpenClaw command to the requested `openclaw_home`.
- Complete and validate the directive files before `openclaw agents add`, then validate configuration and confirm with `openclaw agents list`.
- Add the Coordination provenance directive to `AGENTS.md` before registration.

### Ask First

- Any provider login that needs the operator's own terminal or browser (`openclaw models auth login`).
- Adding a new agent to a parent's `allowAgents` list without explicit delegation approval.
- Overwriting an existing agent directory or an existing `openclaw.json` entry for the same `agent_id`.

### Never Do

- Hand-edit `<openclaw_home>/openclaw.json` for agent creation or delegation.
- Treat a provider shown as `configured` in the model catalog as proof that the new agent has credentials.
- Prefer an API key over web/OAuth login when both are available (the key is fallback only).
- Let a new agent inherit a parent agent's identity, authority or authorship.

## See Also

- `../openclaw-add-channel/SKILL.md`
- `../openclaw-restart/SKILL.md`
- `../openclaw-status/SKILL.md`

## References

- [`references/openrouter-defaults.md`](../../references/openrouter-defaults.md) — model routing source of truth
- [`references/universal-skill-protocol.md`](../../references/universal-skill-protocol.md) — invocation envelope standard
- [`references/pt-orama-weave.md`](../../references/pt-orama-weave.md) — how PT + orama-system cooperate
