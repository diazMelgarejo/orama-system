---
name: codex-mcp-debugging
description: >-
  Use when debugging Codex CLI MCP config.toml errors — invalid transport, GitHub MCP,
  bearer_token_env_var confusion, stdio vs HTTP transport, Exa wrapper setup, or
  codex mcp list failures. Activates when MCP transport shape or auth field family is wrong.
version: "1.0"
layer: "agent-local"
compatibility: claude-code, codex, gemini, hermes
agent_compatibility:
  - Claude
  - Codex
  - Gemini
  - Hermes
allowed-tools: bash, file-operations
triggers:
  - codex mcp
  - invalid transport
  - config.toml mcp
  - github mcp codex
  - exa mcp wrapper
---

# Codex MCP Debugging

## Purpose

Diagnose Codex CLI MCP `config.toml` transport and auth field mismatches before editing servers.

## When to Use

- `codex mcp list` fails with `invalid transport` or schema errors
- GitHub MCP shows bearer-token fields on a stdio subprocess
- Exa or custom wrappers need stdio verification on OpenClaw machines

Use this before editing `~/.codex/config.toml` MCP blocks.

## Core Rule

Classify transport before touching auth.

- stdio server: local process; requires `command`, optional `args`, and env under
  `[mcp_servers.<name>.env]`.
- HTTP server: remote URL; requires `url`; `bearer_token_env_var` belongs here.

If the error says `invalid transport`, assume schema mismatch first, not missing credentials.

## GitHub MCP Pattern

For the local npm GitHub MCP server, use stdio:

```toml
[mcp_servers.github]
transport = "stdio"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]

[mcp_servers.github.env]
GITHUB_PERSONAL_ACCESS_TOKEN = "${CODEX_GITHUB_PERSONAL_ACCESS_TOKEN}"
```

The shell should export `CODEX_GITHUB_PERSONAL_ACCESS_TOKEN`, preferably from `~/.zshenv` for
non-interactive shells.

GitHub also documents a remote Streamable HTTP Codex setup at `https://api.githubcopilot.com/mcp/`.
For that remote transport, `bearer_token_env_var` is valid. Do not mix the two shapes.

## Exa MCP Pattern

For OpenClaw machines, Exa is intentionally configured as a stdio wrapper, not the bare remote URL.
The wrapper resolves `EXA_API_KEY` from OpenClaw config or macOS Keychain and multiplexes Claude,
orama-system, Perpetua-Tools, and Codex through one local daemon.

Preferred setup:

```sh
codex mcp remove exa 2>/dev/null || true
codex mcp add exa -- bash -c 'exec "$HOME/code/OpenClaw/orama-system/scripts/exa/exa-mcp-wrapper.sh"'
codex mcp get exa
codex mcp list
```

Expected `codex mcp get exa` shape:

```text
transport: stdio
command: bash
args: -c exec "$HOME/code/OpenClaw/orama-system/scripts/exa/exa-mcp-wrapper.sh"
```

Smoke-test the wrapper itself when debugging:

```sh
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"codex-smoke","version":"0"}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | "$HOME/code/OpenClaw/orama-system/scripts/exa/exa-mcp-wrapper.sh"
```

Success exposes `web_search_exa` and `web_fetch_exa`. A current Codex session may need restart before
newly added MCP tools appear in the tool surface.

## Antipattern

Do not apply this as the whole fix:

```toml
[mcp_servers.github]
bearer_token_env_var = "CODEX_GITHUB_PERSONAL_ACCESS_TOKEN"
```

That treats the local npm GitHub server as HTTP bearer-token config, but this GitHub server is a
stdio subprocess.

## Verification

Run:

```sh
codex mcp list
```

Success criteria:

- Config loads without `invalid transport`.
- `github` shows command `npx` and args containing `@modelcontextprotocol/server-github`.
- Env shows `GITHUB_PERSONAL_ACCESS_TOKEN=*****`.
- `Auth: Unsupported` is acceptable for stdio; it means Codex OAuth is not being used.

## Reasoning Checklist

1. Read the actual config block before editing.
2. Compare fields against the transport schema.
3. Move credentials into the correct field family for that transport.
4. Validate with the Codex parser and launcher, not by visual inspection.
5. Preserve secrets; never paste token values into notes, logs, or skills.

## Failure Lesson To Reuse

If a user says Claude fixed a Codex MCP issue that Codex could not, treat that as a signal to run a
transport/schema postmortem. The specific failure was reading a GitHub warning as "missing PAT env
var" when the real blocker was an invalid MCP transport shape.

Good response pattern:

- Acknowledge the wrong mental model directly.
- Search/check docs for transport-specific fields.
- Mention the remote GitHub HTTP exception where `bearer_token_env_var` is valid.
- Save the pattern and antipattern.
- Re-run `codex mcp get github` or `codex mcp list` before declaring success.

## References

- [`../openclaw-skills/references/openrouter-defaults.md`](../openclaw-skills/references/openrouter-defaults.md) - model routing source of truth
- [`../openclaw-skills/references/universal-skill-protocol.md`](../openclaw-skills/references/universal-skill-protocol.md) - invocation envelope standard
- [`../openclaw-skills/references/pt-orama-weave.md`](../openclaw-skills/references/pt-orama-weave.md) - how PT + orama-system cooperate

## Boundaries

### Always Do

- Classify transport (stdio vs HTTP) before touching auth fields.
- Validate with `codex mcp list` and `codex mcp get <name>` after edits.
- Preserve secrets; reference env var names only, never token values.

### Ask First

- Switching GitHub MCP from stdio npm server to remote HTTP Copilot endpoint.
- Adding new MCP servers that duplicate existing OpenClaw wrapper coverage.

### Never Do

- Apply `bearer_token_env_var` to stdio subprocess servers.
- Paste PATs, API keys, or bearer tokens into skills, logs, or commit messages.
- Declare success without re-running the Codex MCP parser.
