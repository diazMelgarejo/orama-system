# Cline Backend Binding Contract

<!-- wandb-inference-working-config -->
## W&B inference

`invalid model ID` from the Cline CLI is stale provider metadata, not a
bad model id. `tokenSource` must be `manual` (or Cline's `oauth` or
`migration`) and `updatedAt` must be UTC with millisecond precision and a
trailing `Z`. Repair a shared entry with
`bin/orama-system/scripts/cline-provider-profiles/switch_cline_provider.py`.
When two routes run side by side, use
`bin/orama-system/skills/cline-wandb/scripts/launch_cline_wandb.py`.
Use the OpenAI client and Weave only if that error remains after the
metadata is current. Do not send a CoreWeave team/project string.
Shell-source the operator W&B env file before reading
`DEEPSEEK_V4_FLASH_WANDB`.

> **Update 2026-11-10 (verified on CLI 3.0.74 by the Windows and Mac hosts; Cline benchmark finding).** The CLI is now
> 3.0.74. There is no `task` subcommand: the prompt is a bare positional argument. Cline's own default is act mode with
> tool auto-approval ON, so review or unattended runs should pass `--plan --auto-approve false` unless the operator
> authorises act mode. An npm install on Windows ships `cline.cmd`: never pass a prompt through a cmd shim; launch node
> with the package entry script. The text below is the 3.0.34 record and is kept as history.
>
> **Live working code:** `scripts/cline_autoresearcher.py` (`_cline_argv`, `_cline_launcher`, `dispatch_cline`,
> `dispatch_autoresearcher`) and `scripts/autoresearcher_lock.py` (`BackendLock`); the Windows watcher autostart is
> the AutoResearcher block in `platform/windows/start.ps1`.

## Purpose

Define the idempotent OpenClaw configuration contract for `cline-agent`. This
reference applies to the binder, profile generator, and OramaClaw manifest
migration. It reflects the OpenClaw schema installed on 2026-06-30 and the
Cline CLI v3.0.34.

## Why `cline-agent` Is Not a Model-Provider Binding

`codex-agent` binds `codex/gpt-5.5` as a native OpenClaw model because `codex
serve` exposes an OpenAI-compatible app-server on localhost. Cline has no
equivalent:

- The **Cline hub** (`ws://127.0.0.1:25463/hub`, started by `cline --zen` or
  `cline hub`) speaks Cline's proprietary WebSocket protocol — `GET /v1/models`
  and `GET /` both return `404 Not found`. It is not an OpenAI completions
  endpoint.
- `cline --acp` speaks **ACP** (Agent Client Protocol), not OpenAI completions.
- The real upstream API is `https://api.cline.bot/api/v1/chat/completions`
  (OpenAI-compatible, model `zai/glm-5.3-flash`), but it is fronted by a **WorkOS
  OAuth token** (`workos:eyJ...`) with `expiresAt` ~12 minutes out and a
  `refreshToken` that only the Cline CLI's auth loop knows how to rotate.
  OpenClaw has no WorkOS refresh loop, so a hardcoded token would die within
  minutes and OpenClaw would start getting `401`s.

Therefore the binding is **agent-level**, not provider-level. The `cline-agent`
uses an OpenClaw-routable model that mirrors Cline's glm-5.3-flash and delegates
agentic execution to the `cline` CLI via exec / ACP / MCP.

## Managed Surface

```json
{
  "id": "cline-agent",
  "name": "cline-agent",
  "workspace": "~/.openclaw/agents/cline-agent",
  "agentDir": "~/.openclaw/agents/cline-agent/agent",
    "model": "openrouter/free",
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

## Model Choice Rationale

The `cline-agent` uses `openrouter/free` (free auto-router) as its lightweight
agent model — **not** the primary coding path. The **default coding execution**
is the `cline` CLI via `cline-pass/glm-5.3-flash` (Cline Credits through
`api.cline.bot`).

**ClinePass is the better default for coding** because:

1. **No rate limits** — OpenRouter free is limited to 50 req/day, 20 RPM; ClinePass
   has no such restriction
2. **1M context** — full glm-5.3-flash capability with reasoning + tool loops
3. **Dedicated billing** — Cline Credits are separate from OpenRouter credits
4. **Auto-refreshing auth** — the Cline CLI refreshes its WorkOS token automatically

The OpenRouter free auto-router (`openrouter/free`) is used only for:

- Lightweight routing/triage (deciding whether to delegate to cline)
- Quick questions that don't need tool loops
- Fallback when Cline Credits are exhausted

If the operator specifically wants OpenClaw to route through `api.cline.bot`
directly (without the `cline` CLI), they need a static Cline API key or a local
token-refresh proxy — the WorkOS token expires in ~12 min and only the Cline CLI
can refresh it.

## ACP

The OpenClaw `acp` config block (`acp.enabled`, `acp.backend`,
`acp.allowedAgents`) requires `acp.backend` to match a **registered ACP runtime
plugin backend** (e.g. `acpx`). Cline's `--acp` mode makes Cline an ACP
**server**, not a backend plugin. Therefore:

- Do **not** enable `acp.enabled` globally or set `acp.backend` to `cline`.
- Use the one-shot bridge: `openclaw acp client --server cline --server-args
  --acp --cwd <repo>`. This spawns `cline --acp` as a stdio ACP server and
  bridges it into an OpenClaw session without requiring the global ACP gate.

## MCP

Cline is an MCP **client** (`cline mcp install|add`), not an MCP server. There
is no `cline mcp serve` command. Therefore:

- Do **not** add a `cline` entry to `mcp.servers` in OpenClaw config.
- The working direction is: `openclaw mcp serve` (exposes OpenClaw channels
  over MCP stdio) → register server `openclaw` in Cline with launch command
  `openclaw mcp serve` via the MCP client UI (resolved local binary; review
  OpenClaw version before enabling).

## Idempotent Reconciliation

1. Resolve the active OpenClaw executable through
   `scripts/openclaw/resolve-openclaw.sh`.
2. Verify `cline` CLI is installed (`command -v cline`); report `needs_cline`
   without modifying config if absent.
3. Read the existing agent by id.
4. If absent, call `openclaw agents add` with the canonical workspace, state
   directory, and model.
5. If present with another workspace, stop without changing it.
6. Compare and update only the managed agent fields and the union-preserved
   allowlist. Union-merge `cline-agent` into `allowAgents`, preserving every
   existing value.
7. Run the profile generator. It owns only paired `oramaclaw:generated` marker
   regions and creates `SECURITY.md` only when absent.
8. Run `openclaw config validate`; restart the gateway only when agent config
   changed.
9. Report `ok` when the resolved default is `openrouter/free` and
   `cline-agent` is in the allowlist.

Rerunning with unchanged input must neither modify `openclaw.json` nor rewrite
workspace files.

## Security And Verification

- Keep OAuth profiles, bearer headers, API keys, cookies, and credential-store
  files outside the workspace and generated records. The WorkOS token in
  `~/.cline/data/settings/providers.json` must never be copied into OpenClaw
  config or workspace files.
- Do not change the Main Agent, global default routing, `codex-agent`, `coder`,
  channel bindings, or LaunchAgent configuration.
- The Cline agent's configured state requires
  `resolvedDefault == "openrouter/free"`. `openclaw config validate`
  checks configuration syntax, not this policy; the post-restart
  `openclaw models status --agent cline-agent` identity check is separate.
- Cline Credits (`https://app.cline.bot/credits`) fund `cline-pass` exec calls;
  OpenRouter credits fund the OpenClaw agent's own model calls. Both must be
  funded for full operation.
