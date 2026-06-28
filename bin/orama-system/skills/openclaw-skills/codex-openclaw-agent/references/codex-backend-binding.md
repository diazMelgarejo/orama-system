# Native Codex Binding Contract

## Purpose

Define the idempotent OpenClaw configuration contract for `codex-agent`.
This reference applies to the binder, profile generator, and OramaClaw
manifest migration. It reflects the OpenClaw schema installed on 2026-06-20.

## Managed Surface

```json
{
  "id": "codex-agent",
  "name": "codex-agent",
  "workspace": "~/.openclaw/agents/codex-agent",
  "agentDir": "~/.openclaw/agents/codex-agent/agent",
  "model": "codex/gpt-5.5",
  "thinkingDefault": "medium",
  "tools": {"profile": "coding"}
}
```

The parent allowlist is a separate managed field:

```json
{
  "agents": {
    "defaults": {
      "subagents": {"allowAgents": ["codex-agent"]}
    }
  }
}
```

Preserve every other existing allowlisted agent. Do not use
`agents.bindings.*.allowAgents`.

The equivalent OramaClaw delegation resource is:

```json
{
  "kind": "delegation",
  "id": "main-allows-codex-agent",
  "manager": "codex-binder",
  "policy": "conflict",
  "spec": {
    "path": "agents.defaults.subagents.allowAgents",
    "allow_agent": "codex-agent"
  },
  "managed_paths": ["/agents/defaults/subagents/allowAgents"]
}
```

## Native Model Route

The native Codex model reference is `codex/gpt-5.5`. It is not a custom
`models.providers.codex` configuration block. Do not create an app-server
endpoint, run `codex serve`, use `openai-completions`, or write a placeholder
token reference into configuration.

`codex-supervisor` is an optional observation plugin. Its presence does not
prove that a Codex model provider or ACP runtime is available.

The accepted credential route is OpenClaw's `openai-codex` flow. Configuration
may be complete while execution remains blocked by missing provider auth:

```bash
openclaw models status --agent codex-agent
openclaw models auth login --provider openai-codex
```

The login command is interactive and never belongs in unattended first-run
automation. Do not copy credentials from another agent's profile.

Before login, ensure the official bundled `openai` provider plugin is loaded.
When absent, run `openclaw plugins install openai`; that bare spec resolves to
the bundled plugin in supported OpenClaw releases. An explicit `plugins.allow`
list blocks it unless `openai` is included. Preserve all existing allowed plugin
ids, append only `openai`, enable the bundled plugin, restart the gateway, and
re-check its loaded state. Return `needs_plugin` only when that automated
bundled-plugin installation fails; do not fall back to a custom localhost
provider.

## Idempotent Reconciliation

1. Resolve the active OpenClaw executable through `scripts/openclaw/resolve-openclaw.sh`.
2. Install the official bundled `openai` provider when absent; return `needs_plugin` only if installation fails.
3. When an explicit plugin allowlist exists, append only `openai`; enable the plugin and mark the gateway for restart when needed.
4. Read the existing agent by id.
5. If absent, call `openclaw agents add` with the canonical workspace, state directory, and model.
6. If present with another workspace, stop without changing it.
7. Compare and update only the managed agent fields and the union-preserved allowlist. For the delegation resource, `spec.path` must equal `agents.defaults.subagents.allowAgents`; a mismatch is a conflict and reconciliation stops without writing. Union-merge the non-empty `spec.allow_agent` into that array, preserving every existing value. No other delegation `spec` fields are managed, interpreted, or rewritten.
8. Run the profile generator. It owns only paired `oramaclaw:generated` marker regions and creates `SECURITY.md` only when absent.
9. Run `openclaw config validate`; restart the gateway only when provider or agent config changed.
10. Report `needs_auth` when the model status lists `codex` as missing. Do not roll back a valid agent definition.

Rerunning with unchanged input must neither modify `openclaw.json` nor rewrite
workspace files.

## Security And Verification

- Keep OAuth profiles, bearer headers, API keys, cookies, and credential-store files outside the workspace and generated records.
- Do not change the Main Agent, global default routing, `coder`, channel bindings, or LaunchAgent configuration.
- The Codex agent's configured state requires `resolvedDefault == "codex/gpt-5.5"` and no fallback models. The binder enforces this by reconciling the agent's `model` to the scalar `codex/gpt-5.5`, which replaces any model object that could contain fallbacks. `openclaw config validate` checks configuration syntax, not this policy; the post-restart `openclaw models status --agent codex-agent` identity check is separate. An implementation that observes a non-empty Codex-agent fallback list after reconciliation must fail rather than report `ok`.
- The executable state additionally requires no missing `codex` provider in `openclaw models status --agent codex-agent`.

See the [control-plane plan](../../../../../docs/superpowers/plans/2026-06-20-oramaclaw-control-plane-v1.md) for the eventual Gateway-first manifest writer.
