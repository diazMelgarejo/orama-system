# Codex Backend Binding Doctrine

**Skill:** `codex-openclaw-agent`
**Purpose:** Define the runtime contract that proves an OpenClaw agent is
Codex-backed, not merely Codex-profiled.

This document is binding guidance for `scripts/bind_codex_backend.sh`, the
profile generator, and the thin skill orchestrator. It is a peer substrate to
`hermes-harness`: reusable, probe-first, idempotent, and safe to re-run.

## Non-Negotiable Invariants

- Do not change `agents.defaults.model.primary`.
- Do not change the existing `main` or `coder` primary models.
- Do not edit the OpenClaw LaunchAgent plist.
- Do not copy API keys, OAuth material, bearer tokens, or raw auth files into
  generated docs, refs, logs, prompts, or config patches.
- Do not hand-edit `openclaw.json`; use `openclaw config patch --file`.
- Do not run `stow --no-folding -t "$OPENCLAW_HOME" .` from an arbitrary cwd.
- Do not declare success until runtime backend identity resolves to Codex.

## OpenClaw Invocation

All OpenClaw CLI calls must go through the repo resolver:

```bash
scripts/openclaw/resolve-openclaw.sh <openclaw-args...>
```

Never call a bare `openclaw` binary from this substrate. The resolver avoids
stale pnpm shims and prefers the install that actually runs the gateway.

## Resolution Ladder

| Stage | Action | Mutates? |
| --- | --- | --- |
| 0 Probe | Gather evidence only: Codex CLI, auth reference, app-server endpoint, plugin state, existing agent/provider config. | No |
| 1 Primary | Bind through the real native plugin, `codex-supervisor`, when it is enabled and the gateway has loaded it. | Yes |
| 2 Install | If `codex-supervisor` is present but disabled, enable it with `openclaw config patch`; if absent but installable, install and re-probe. | Yes |
| 3 Fallback | Register the discovered Codex app-server as an OpenAI-compatible provider with provider key `codex`. | Yes |
| 4 Verify | Run a harmless task and assert resolved backend identity is Codex/GPT-5.5, not Ollama. | Session only |
| 5 Record | Write a redacted `refs/codex-backend-binding.json` for the generator. | Yes |

The resolver is opportunistic: prefer the first path that passes probe and
verify. Fallback is a first-class path, not an exceptional degraded mode.

## Stage 0 Probe Rules

Probe output must be JSON on stdout and diagnostics on stderr. It must not
mutate files.

Required checks:

- `codex --version` succeeds.
- Auth reference exists through at least one accepted surface:
  `CODEX_API_KEY`, `OPENAI_API_KEY`, `~/.codex/auth.json`, or a structurally
  valid `~/.codex/config.toml`. Values are never printed.
- App-server endpoint is discovered from
  `~/.codex/cache/codex_apps_server_info/*.json`.
- `GET <endpoint>/v1/models` returns `200`, `401`, or `403`.
- `.app-server-state-reconciled-v1` is treated only as a stale-prone hint.
- `codex-supervisor` state is read through the OpenClaw resolver.
- Existing `openclaw.json` state is inspected through `openclaw config` or a
  dry-run patch target, not modified.

## Provider Strings

- Native path: use the provider key reported by `codex-supervisor` probe.
- Fallback path: provider key `codex`, model id `gpt-5.5`, provider string
  `codex/gpt-5.5`.

If the runtime resolves to `ollama/*`, verification must fail.

## Reasoning Effort

Default effort is `medium` for cost and latency control. `high` and `xhigh`
are explicit operator opt-ins and must only be written when passed through the
skill, binder, or profile generator arguments.

## OpenAI-Compatible Fallback Shape

The fallback provider patch must use this schema:

```json
{
  "models": {
    "providers": {
      "codex": {
        "api": "openai-completions",
        "apiKey": "${env:OPENAI_API_KEY}",
        "baseUrl": "http://127.0.0.1:<port>/v1",
        "models": [
          {
            "id": "gpt-5.5",
            "name": "Codex GPT-5.5",
            "contextWindow": 200000,
            "maxTokens": 65536,
            "cost": {"input": 0, "output": 0}
          }
        ]
      }
    }
  }
}
```

Write this with `openclaw config patch --file <patch.json>`. The endpoint port
comes from the live Codex server-info canary unless the operator explicitly
passes an override.

## Mutation Boundaries

Use a per-`openclaw-home` lock before any write.

Allowed writes:

- OpenClaw config patch for the target provider and target agent only.
- Target agent runtime scaffolds under
  `$OPENCLAW_HOME/.openclaw/agents/<agent_id>/` when needed.
- Redacted binding record under the target agent `refs/` directory.
- Generated profile sections owned by the profile generator.

Disallowed writes:

- Global defaults, `main`, or `coder` routing.
- LaunchAgent plist.
- Literal secrets.
- Whole-file replacement of operator-authored directive files unless the
  operator explicitly passes a force flag.

## Verification Gate

Verification must prove runtime identity, not just file shape.

PASS requires all of:

1. A harmless task returns the expected canary text.
2. The resolved model string is `codex/gpt-5.5` or the verified
   `codex-supervisor` provider key plus `/gpt-5.5`.
3. The resolved provider prefix is not `ollama`.
4. The binding record captures expected vs actual provider/model.

OTEL traces are a secondary signal. They strengthen evidence but do not replace
the resolved model-prefix check.

## Binding Record Contract

`refs/codex-backend-binding.json` must be redacted and repo-safe:

```json
{
  "schema_version": "1",
  "winning_path": "plugin|idempotent-install|fallback",
  "provider_key": "codex",
  "provider_string": "codex/gpt-5.5",
  "model": "gpt-5.5",
  "effort": "medium",
  "auth_source_ref": "~/.codex/auth.json",
  "endpoint_ref": "http://127.0.0.1:<port>/v1",
  "verification": {
    "status": "pass",
    "expected": "codex/gpt-5.5",
    "actual": "codex/gpt-5.5",
    "method": "model-prefix"
  },
  "timestamp": "2026-06-19T00:00:00Z",
  "binder_version": "1.0.0",
  "agent_id": "codex-agent"
}
```

Use references only. Do not serialize raw server-info files or auth payloads.

## Failure Output

Every failure must print:

- Stage that failed.
- Expected provider/model and actual provider/model when known.
- Redacted auth source reference.
- Endpoint reference.
- Whether files were modified.
- One safe recovery command.

Preferred recovery commands:

- `codex login`
- `codex --version`
- `codex-openclaw-agent --agent-id <id> --prefer compat --refresh`
- `codex-openclaw-agent --agent-id <id> --bind-only --verify`

## Test Requirements

- Unit-test probe JSON and endpoint canary behavior.
- Unit-test auth reference detection for env keys and `~/.codex/auth.json`.
- Unit-test fallback provider patch shape.
- Unit-test that no binder path stows arbitrary cwd.
- Unit-test that generated records contain no workstation paths or secrets.
- End-to-end smoke must fail if runtime identity resolves to Ollama.
