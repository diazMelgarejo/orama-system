---
name: cline-openclaw-agent
description: Create or reconcile the dedicated OpenClaw Cline sub-agent at `~/.openclaw/agents/cline-agent` and wire the Cline CLI (v3.x) as an agentic coding backend via exec, ACP, and MCP bridges. Use when installing, repairing, delegating to, or validating the explicit `cline-agent` without changing the Main Agent, global default routing, or the existing `codex-agent`/`coder` agents. Covers all Cline CLI modes — act, plan, TUI, zen/hub, ACP, JSON one-shot, worktree, kanban, hooks, schedule, history, plugin, skill, connect, doctor, auth, config.
---

# Cline OpenClaw Agent

Maintain one explicit Cline-backed coding sub-agent. It is never the default
route. The Main Agent (or any allowlisted parent) delegates coding tasks to it;
the agent either reasons with its own OpenClaw model or shells out / bridges to
the `cline` CLI for agentic tool loops.

## Architectural Note (read first)

Unlike `codex-agent` — which binds `codex/gpt-5.5` as a **native OpenClaw model
provider** because `codex serve` exposes an OpenAI-compatible app-server —
**Cline does not expose an OpenAI completions endpoint.** The Cline hub daemon
(`ws://127.0.0.1:25463/hub`) speaks Cline's own protocol, and `cline --acp`
speaks ACP, not OpenAI completions. The actual upstream API
(`https://api.cline.bot/api/v1/chat/completions`) is OpenAI-compatible but is
fronted by a short-lived WorkOS OAuth token that only the Cline CLI can refresh.

Therefore `cline-agent` is **not** a model-provider binding. It is an OpenClaw
agent that:

1. Uses an OpenClaw-routable model that **mirrors Cline's GLM-5.2** —
   `openrouter/z-ai/glm-5.2` (1M context, reasoning-capable; same `zai/glm-5.2`
   upstream that `cline-pass/glm-5.2` reaches via `api.cline.bot`).
2. Delegates agentic execution to the `cline` CLI through three bridges:
   **exec** (one-shot shell-out), **ACP** (`openclaw acp client --server cline
   --server-args --acp`), and **MCP** (`openclaw mcp serve` → `cline mcp
   install`).

See [references/cline-backend-binding.md](references/cline-backend-binding.md)
for the full contract and the reasoning behind each decision.

## Canonical State

| Field | Required value |
| --- | --- |
| Agent id | `cline-agent` |
| Workspace | `~/.openclaw/agents/cline-agent` |
| Agent state directory | `~/.openclaw/agents/cline-agent/agent` |
| Model | `openrouter/z-ai/glm-5.2` (mirrors Cline's `cline-pass/glm-5.2`) |
| Thinking | `medium` by default; `high`/`xhigh` only when requested |
| Tool profile | `coding` |
| Delegation allowlist | `agents.defaults.subagents.allowAgents` contains `cline-agent` |
| Channel routing | None; invoke explicitly or delegate through the allowlist |
| Cline CLI | `cline` v3.x on PATH (resolved via `command -v cline`) |
| Cline provider | `cline-pass` with model `cline-pass/glm-5.2` (or `cline` with `zai/glm-5.2`) |

Use the current OpenClaw shape, not legacy fields:

```json
{
  "id": "cline-agent",
  "name": "cline-agent",
  "workspace": "~/.openclaw/agents/cline-agent",
  "agentDir": "~/.openclaw/agents/cline-agent/agent",
  "model": "openrouter/z-ai/glm-5.2",
  "thinkingDefault": "medium",
  "tools": {"profile": "coding"}
}
```

The parent allowlist is a separate managed field:

```json
{
  "agents": {
    "defaults": {
      "subagents": {"allowAgents": ["cline-agent"]}
    }
  }
}
```

Preserve every other existing allowlisted agent (e.g. `codex-agent`). Do not use
`agents.bindings.*.allowAgents`.

## Procedure

Run the binder from the skill directory:

```bash
bash scripts/bind_cline_backend.sh --effort medium
```

The binder must:

1. Resolve the running OpenClaw CLI through the repository resolver.
2. Verify the `cline` CLI is installed (`command -v cline`); report `needs_cline`
   without modifying config if absent.
3. Create the agent with `openclaw agents add` only when its id is absent.
4. Refuse an existing `cline-agent` whose workspace differs from the canonical path.
5. Reconcile only `model`, `thinkingDefault`, `tools.profile`, `agentDir`, and the
   preserved delegation allowlist (union-merge `cline-agent` into `allowAgents`).
6. Create or update only OramaClaw marker regions in `CLINE.md`, `IDENTITY.md`,
   `AGENTS.md`, and `TOOLS.md`; create `SECURITY.md` only when missing.
7. Restart the gateway only after agent configuration changed, validate the
   config, and report `ok`.

Use `--dry-run` to preview. The normal rerun must make no configuration or
workspace write when state already matches.

## Workspace Template

```bash
python scripts/generate_cline_openclaw_profile.py \
  --workspace ~/.openclaw/agents/cline-agent \
  --effort medium
```

| Flag | Default | Effect |
| --- | --- | --- |
| `--workspace PATH` | `~/.openclaw/agents/cline-agent` | Target workspace directory |
| `--effort medium\|high\|xhigh` | `medium` | Sets `thinkingDefault` in the `IDENTITY.md` marker |
| `--dry-run` | off | Reports which files would change without writing |

### Bridge 1 — Exec one-shot (simplest, works now)

```bash
cline "refactor lib/foo.js to add a cache" \
  --json --auto-approve true \
  -c /path/to/repo \
  --thinking medium \
  -P cline-pass -m cline-pass/glm-5.2 \
  --timeout 600 --retries 3
```

Resume: `cline --id <session-id> "continue" --json`. See
[references/exec-one-shot.md](references/exec-one-shot.md).

### Bridge 2 — ACP (structured, streaming)

```bash
openclaw acp client \
  --server cline --server-args --acp \
  --cwd /path/to/repo \
  --session agent:cline-agent:main
```

See [references/acp-bridge.md](references/acp-bridge.md).

### Bridge 3 — MCP (tool-level)

```bash
openclaw mcp serve        # expose OpenClaw channels over MCP stdio
cline mcp install openclaw -- npx -y openclaw mcp serve
```

See [references/mcp-bridge.md](references/mcp-bridge.md).

## Boundaries

- Do not modify `agents.defaults.model`, the Main Agent, `codex-agent`, `coder`,
  or gateway/LaunchAgent settings.
- Do not add a channel binding or a custom Cline endpoint to `models.providers`
  (Cline's `api.cline.bot` is not a stable OpenAI-compatible provider for
  OpenClaw — its token expires in ~12 min and only the Cline CLI can refresh it).
- Do not enable `acp.enabled` globally without a registered ACP runtime backend
  plugin; use the one-shot `openclaw acp client --server cline` bridge instead.
- Do not delete bootstrap files, workspace memory, sessions, or
  operator-authored content.
- Do not record secrets in generated files, logs, or binding records.

## Verification

```bash
openclaw config validate
openclaw agents list
openclaw models status --agent cline-agent
command -v cline && cline version
```

The target is configured only when the resolved default is
`openrouter/z-ai/glm-5.2` and `cline-agent` is in the allowlist. It is
executable only when the `cline` CLI is on PATH and the OpenRouter provider is
authenticated (or Cline Credits are funded for `cline-pass` exec calls).

## Related

- [Cline backend binding contract](references/cline-backend-binding.md)
- [Cline CLI reference (all commands/flags)](references/cline-cli-reference.md)
- [Modes matrix (exhaustive)](references/modes-matrix.md)
- [ACP bridge](references/acp-bridge.md)
- [MCP bridge](references/mcp-bridge.md)
- [Exec one-shot](references/exec-one-shot.md)
- [Hub daemon](references/hub-daemon.md)
- [Provider auth](references/provider-auth.md)
- [Codex OpenClaw Agent (sibling skill)](../codex-openclaw-agent/SKILL.md)
- [OpenClaw new-agent skill](../openclaw-new-agent/SKILL.md)
