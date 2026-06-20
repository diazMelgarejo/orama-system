---
name: codex-openclaw-agent
description: Create or reconcile the dedicated OpenClaw Codex sub-agent at `~/.openclaw/agents/codex-agent` using the native `codex/gpt-5.5` catalog and the current OpenClaw agent schema. Use when installing, repairing, or validating the explicit `codex-agent` without changing the Main Agent, global default routing, or the existing `coder` agent.
---

# Codex OpenClaw Agent

Maintain one explicit coding sub-agent. It is never the default route.

## Canonical State

| Field | Required value |
| --- | --- |
| Agent id | `codex-agent` |
| Workspace | `~/.openclaw/agents/codex-agent` |
| Agent state directory | `~/.openclaw/agents/codex-agent/agent` |
| Model | `codex/gpt-5.5` |
| Thinking | `medium` by default; `high` and `xhigh` only when requested |
| Tool profile | `coding` |
| Delegation allowlist | `agents.defaults.subagents.allowAgents` contains `codex-agent` |
| Channel routing | None; invoke explicitly or delegate through the allowlist |

Use the current OpenClaw shape, not legacy fields:

```json
{
  "id": "codex-agent",
  "workspace": "~/.openclaw/agents/codex-agent",
  "agentDir": "~/.openclaw/agents/codex-agent/agent",
  "model": "codex/gpt-5.5",
  "thinkingDefault": "medium",
  "tools": {"profile": "coding"}
}
```

`model_reasoning_effort`, `model.reasoning_effort`,
`agents.bindings.*.allowAgents`, `codex serve`, and a custom localhost
`models.providers.codex` block are obsolete for this workflow.

## Native Provider And Auth

`codex/gpt-5.5` is selected from OpenClaw's native Codex model catalog. Do not
register it as a custom OpenAI-compatible provider and do not infer that the
`codex-supervisor` observation plugin is a model runtime.

The official bundled `openai` provider plugin must be loaded before the native
`openai-codex` login route exists. The binder installs the official bundled
plugin through `openclaw plugins install openai` when absent. An explicit
`plugins.allow` list blocks it unless it includes `openai`; the binder preserves
that list, appends only `openai`, enables the plugin, and restarts the gateway
only when installation or activation changed. It reports `needs_plugin` only
when the automated bundled-plugin installation fails.

The native provider then requires its own managed credential profile. Inspect with:

```bash
openclaw models status --agent codex-agent
```

If it reports `codex` as missing, stop after configuration and direct the
operator to run the interactive flow:

```bash
openclaw models auth login --provider openai-codex
```

Never copy or reclassify an existing OAuth token, API key, bearer header, or
credential-store file.

## Procedure

Run the binder from the skill directory:

```bash
bash scripts/bind_codex_backend.sh --effort medium
```

The binder must:

1. Resolve the running OpenClaw CLI through the repository resolver.
2. Create the agent with `openclaw agents add` only when its id is absent.
3. Refuse an existing `codex-agent` whose workspace differs from the canonical path.
4. Install, allow, and enable the bundled `openai` provider without widening an existing allowlist beyond that single id.
5. Reconcile only `model`, `thinkingDefault`, `tools.profile`, `agentDir`, and the preserved delegation allowlist.
6. Create or update only OramaClaw marker regions in `CODEX.md`, `IDENTITY.md`, `AGENTS.md`, and `TOOLS.md`; create `SECURITY.md` only when missing.
7. Restart the gateway only after a provider or agent configuration change, validate the config, and report `needs_auth` without rolling back correct configuration.

Use `--dry-run` to preview. The normal rerun must make no configuration or
workspace write when state already matches. Operator-authored content outside
the `<!-- oramaclaw:generated:* -->` region is never replaced.

## Workspace Template

The workspace template generator reconciles only the `<!-- oramaclaw:generated:start/end -->`
marker regions in the four managed files and scaffolds `SECURITY.md` when absent.
All operator-authored content outside those markers is preserved. Reruns with
unchanged state write nothing and exit `{"changed": [], "status": "ok"}`.

Run from the skill directory:

```bash
python scripts/generate_codex_openclaw_profile.py \
  --workspace ~/.openclaw/agents/codex-agent \
  --effort medium
```

Options:

| Flag | Default | Effect |
| --- | --- | --- |
| `--workspace PATH` | `~/.openclaw/agents/codex-agent` | Target workspace directory |
| `--effort medium\|high\|xhigh` | `medium` | Sets the `thinkingDefault` written into the `IDENTITY.md` marker region |
| `--dry-run` | off | Reports which files would change without writing |

Managed files and their marker content:

| File | Marker section | Scaffold-only |
| --- | --- | --- |
| `CODEX.md` | Model, workspace, and tool-profile summary | no |
| `IDENTITY.md` | Agent name, role, model, and thinking level | no |
| `AGENTS.md` | Operational rules for the Codex sub-agent | no |
| `TOOLS.md` | Tool-profile and credential-handling rules | no |
| `SECURITY.md` | Security contract (credentials, approval gates) | **yes — created only when absent** |

The binder (`bind_codex_backend.sh`) calls this generator as step 6 of its
reconciliation pass. Run the generator directly when you only need to refresh
workspace defaults without touching the OpenClaw config or restarting the gateway.

## Boundaries

- Do not modify `agents.defaults.model`, the Main Agent, `coder`, or gateway/LaunchAgent settings.
- Do not add a channel binding, a fallback model, a custom Codex endpoint, or an ACP runtime unless a separately installed and verified runtime requires it.
- Do not delete bootstrap files, workspace memory, sessions, or operator-authored content.
- Do not record secrets in generated files, logs, or binding records.

## Verification

```bash
openclaw config validate
openclaw agents list
openclaw models status --agent codex-agent
```

The target is configured only when the resolved default is `codex/gpt-5.5` and
the fallback list is empty. It is executable only when the native `codex`
provider is authenticated.

## Related

- [Native binding contract](references/codex-backend-binding.md)
- [OramaClaw control-plane plan](../../../../../docs/superpowers/plans/2026-06-20-oramaclaw-control-plane-v1.md)
- [OramaClaw plan punch list](../../../../../docs/superpowers/plans/2026-06-20-oramaclaw-plan-punch-list.md)
- [OpenClaw new-agent skill](../skills/openclaw-new-agent/SKILL.md)
