# Universal Skill Protocol

This protocol defines how Claude, Hermes, Gemini, Codex, Cursor, WindSurf, Antigravity, OpenCode, and 8gent.dev discover, invoke, chain, and report OpenClaw skills. It is the cross-agent contract for `openclaw-skills`.

The protocol is intentionally transport-neutral. Agents may call skills through native skill tools, MCP, Perpetua-Tools, CLI wrappers, editor rules, or local automation, but every call must normalize to the same envelope and output shape.

## Scope

Applies to these skill IDs:

| Skill ID |
|----------|
| `openclaw-new-agent` |
| `openclaw-add-channel` |
| `openclaw-add-cron` |
| `openclaw-dream-setup` |
| `openclaw-add-script` |
| `openclaw-add-secret` |
| `openclaw-status` |
| `openclaw-restart` |
| `openclaw-stow` |

## Discovery

| Agent | Discovery Method | Required Behavior |
|-------|------------------|-------------------|
| Claude | Native Skill tool or `.claude/skills/` style scan | Load master `SKILL.md`, then load the selected subskill file before acting. |
| Hermes | Local skill registry, MCP, or Perpetua-Tools adapter | Resolve `skill_id` against `openclaw-skills/skills/{skill_id}/SKILL.md`. |
| Gemini | `gemini-mcp-tool` | Treat each skill as an MCP callable and pass the common envelope unchanged. |
| Codex | `ai-cli-mcp`, local filesystem, or configured skill loader | Read the selected skill file and execute only inside `openclaw_home`. |
| Cursor | `.cursor/rules/` mirror, symlink, or workspace rule | Rules must point to this protocol and call by canonical skill ID. |
| WindSurf | Workspace rules, MCP, or local adapter | Resolve the skill ID from this folder and preserve protocol fields. |
| Antigravity | Agent rule registry or MCP adapter | Dispatch to Perpetua-Tools or equivalent runner with explicit `openclaw_home`. |
| OpenCode | Local command registry, MCP, or rule adapter | Invoke the skill by ID and return the normalized result. |
| 8gent.dev | Agent registry, MCP, or Perpetua-Tools adapter | Use the envelope as the handoff format between agents. |

Agents that cannot execute markdown skills directly must delegate to Perpetua-Tools or another runner that can read the local skill file and perform the steps deterministically.

## Invocation Envelope

Every skill call must normalize to this JSON object:

```json
{
  "skill_id": "openclaw-add-channel",
  "args": {
    "platform": "telegram",
    "channel_name": "alerts"
  },
  "agent_id": "codex",
  "openclaw_home": "/absolute/path/to/openclaw-home"
}
```

Fields:

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `skill_id` | yes | string | One of the nine canonical skill IDs. |
| `args` | yes | object | Skill-specific arguments. Use `{}` when no arguments are needed. |
| `agent_id` | yes | string | Invoking agent or wrapper ID, such as `claude`, `codex`, or `gemini`. |
| `openclaw_home` | yes | string | Absolute path to the target OpenClaw home repository. |

Optional transport metadata may be carried beside these fields, but runners must not require it for deterministic execution.

## Argument Rules

1. `openclaw_home` must be absolute.
2. Skill arguments must be explicit. Do not rely on chat history for required values.
3. Secret values must never appear in the envelope. Secret skills must collect credentials through a secure prompt or platform secret store.
4. Names must be normalized according to the master naming table before file writes.
5. Missing required arguments should return `status: "needs_input"` with `follow_up_actions`.

Example `needs_input`:

```json
{
  "status": "needs_input",
  "files_modified": [],
  "follow_up_actions": [
    "Provide channel platform: telegram, slack, or whatsapp"
  ]
}
```

## Required Output Format

Every skill returns:

```json
{
  "status": "ok",
  "files_modified": [
    "openclaw.json",
    "openclaw-env.sh"
  ],
  "follow_up_actions": [
    "Run openclaw-restart"
  ]
}
```

Fields:

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `status` | yes | string | `ok`, `needs_input`, `error`, or `partial`. |
| `files_modified` | yes | array | Paths modified relative to `openclaw_home`. Empty for read-only checks. |
| `follow_up_actions` | yes | array | Human or agent actions that should happen next. Empty when done. |

Recommended optional fields:

| Field | Type | Description |
|-------|------|-------------|
| `skill_id` | string | Echo of the invoked skill ID. |
| `agent_id` | string | Echo of the invoking agent ID. |
| `openclaw_home` | string | Echo of the target home. |
| `checks` | array | Verification checks performed. |
| `warnings` | array | Non-fatal issues. |
| `error` | string | Concise error message when `status` is `error` or `partial`. |

Secret values must not appear in any output field.

## Status Semantics

| Status | Meaning |
|--------|---------|
| `ok` | Skill completed and verification passed or no verification was required. |
| `needs_input` | No unsafe change was made because required input is missing. |
| `partial` | Some work completed, but verification or a follow-up step failed. |
| `error` | Skill could not complete. Include `error` and safe follow-up actions. |

## Chaining Skills

Skills may call other skills only when the chain is part of the canonical procedure. The child call must preserve `agent_id` and `openclaw_home`, and must record child modifications in the parent result.

Common chains:

| Parent Skill | Child Skill | Reason |
|--------------|-------------|--------|
| `openclaw-add-channel` | `openclaw-add-secret` | Channel credentials must pass through the canonical secret pipeline. |
| `openclaw-add-channel` | `openclaw-restart` | Channel configuration requires gateway restart and connection verification. |
| `openclaw-add-cron` | `openclaw-stow` | Cron config changes must handle transient `jobs.json` before deployment. |
| `openclaw-dream-setup` | `openclaw-add-cron` | Dream routines require scheduled execution. |
| `openclaw-new-agent` | `openclaw-add-channel` | Optional channel setup for a new agent. |
| `openclaw-restart` | `openclaw-stow` | Restart must deploy config with the canonical stow behavior first. |

Example parent call:

```json
{
  "skill_id": "openclaw-add-channel",
  "args": {
    "platform": "slack",
    "channel_name": "ops"
  },
  "agent_id": "hermes",
  "openclaw_home": "/Users/example/openclaw-home"
}
```

Example internal child call:

```json
{
  "skill_id": "openclaw-add-secret",
  "args": {
    "secret_name": "slack-bot-token",
    "requested_by": "openclaw-add-channel"
  },
  "agent_id": "hermes",
  "openclaw_home": "/Users/example/openclaw-home"
}
```

The parent result should include all relative paths changed by the parent and child skills. It may include a `checks` array listing child skills invoked.

## Execution Boundaries

1. A skill may modify only files under `openclaw_home` and approved user-level OpenClaw runtime paths such as `~/.openclaw/cron/jobs.json` when the specific skill requires it.
2. A skill must not commit, push, or run git checkout unless a separate explicit human instruction allows it.
3. A skill must use `stow --no-folding` for stow operations.
4. A skill must run `openclaw-status` before mutating operations when the caller has not supplied a fresh status result.
5. A skill must run or request `openclaw-restart` after configuration changes.
6. A skill must avoid destructive operations unless the canonical procedure explicitly requires them, such as removing transient `jobs.json`.

## Audit Requirements

Each invocation should leave an auditable trail containing:

| Item | Requirement |
|------|-------------|
| Skill ID | Canonical ID from this protocol |
| Agent ID | Invoking agent or wrapper |
| Target home | Absolute `openclaw_home` |
| Files changed | Relative paths only |
| Verification | Status, restart, stow, or channel checks performed |
| Follow-up | Required next actions |

Do not include secrets in audit logs.

## Search Frugality Rule

**RULE: Never guess when information is scarce.**
Search in this order — stop at the first satisfying result:

1. `/sync-gbrain` + `gbrain query "<question>"` — local semantic memory, zero cost
2. `code-review-graph: semantic_search_nodes` — structural code context
3. Brave Search API — web facts, current state
4. Perplexity API (inline) — deep web synthesis
5. Grok API — last resort only

**NEVER:** parallel-fire all search tools. Use the cheapest first.
**ALWAYS:** `AskUserQuestion` for decisions — never auto-select between ambiguous options.

## Windows Coder Policy

**RULE: Every available Windows coder MUST be given work as soon as it is idle.**

Endpoint pool: `$WIN_CODER_ENDPOINTS` (default: `192.168.254.103:1234`)

Dispatch protocol:
1. Before routing any task to Mac-only paths, check if a Windows coder is free.
2. If free AND task is compatible (Python, Go, TypeScript, general coding):
   → dispatch to Windows coder FIRST.
3. If offline or no model loaded: skip silently, log WARN, do not fail.
4. As more Windows coders are added to `$WIN_CODER_ENDPOINTS`, they join the pool
   automatically — same rule applies to all.

**Never leave a Windows coder idle if pending compatible work exists.**
