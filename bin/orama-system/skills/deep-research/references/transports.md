# Deep research: EXA and Firecrawl transports

The transport rules for the [deep-research skill](../SKILL.md). The tool contract there says which tools exist; this page says how each harness reaches them.

Both together give the best coverage. The two use different transports, and the
difference matters:

- **EXA (local stdio MCP).** Reach it through the shared wrapper
  `scripts/exa/exa-mcp-wrapper.sh`, which runs one `exa-mcp-daemon` behind a Unix
  socket so every concurrent agent shares a single authenticated process instead
  of each spawning its own `npx` child. Setup and key lookup order:
  [`docs/exa-integration.md`](../../../../../docs/exa-integration.md).
- **Firecrawl (remote `type: http` MCP).** Connect directly. There is no local
  process to daemonize, so the shared-daemon pattern does not apply.
- **Do not switch EXA from the local stdio server to a hosted endpoint without
  explicit authorization.** If a hosted connector is already attached to the
  session, using it changes no config, but say so in the methodology note.
- **Secrets.** Never put an API key in a tracked file (`.mcp.json`, provider or
  agent configs). Use a checked-in template with `${VAR}` placeholders, resolve
  from a `0600` secrets file or the Keychain at runtime, and keep any backup of
  the resolved config outside git. Never print a token value.

## Which harness uses which EXA transport

| Harness | Config | EXA transport |
| --- | --- | --- |
| Claude Code in this repo | `.mcp.json` | Local stdio through the shared wrapper |
| Cursor | `.cursor/mcp.json`, template `.cursor/mcp-configs/mcp-servers.json` | Local stdio through the shared wrapper |
| Codex CLI, global | `scripts/exa/setup-exa.sh` | Local stdio through the shared wrapper |
| Codex CLI, Perpetua-Tools project | Perpetua-Tools `.codex/config.toml` | **Hosted exception, pending an operator ruling:** pinned `mcp-remote` to `https://mcp.exa.ai/mcp` |
| Kimi | `bin/orama-system/config/kimi-mcp.stack.json` | **Hosted exception:** `mcp-remote` to `https://mcp.exa.ai/mcp` |
| Windsurf | `bin/orama-system/config/windsurf-mcp.stack.json` | **Hosted exception:** `mcp-remote` to `https://mcp.exa.ai/mcp` |

The Kimi and Windsurf stacks are merged into each harness's global config by `sync-kimi-mcp.sh` and `sync-windsurf-mcp.sh`. They run from no fixed repo folder, so the repo-relative wrapper cannot be assumed there. Those two stacks and the Perpetua-Tools Codex project config are the only exceptions to the hosted-endpoint rule above. Adding another one needs explicit authorization.

## Why Firecrawl is set up this way

EXA and Firecrawl look alike, but they are connected differently on purpose:

- **Different jobs.** EXA finds URLs and Firecrawl reads them. Keeping Firecrawl downstream means credits go on pages discovery chose, not on blind scrapes.
- **Different transports.** EXA is a local stdio server, so every registration would spawn its own `npx` child; the shared daemon collapses them into one authenticated process. Firecrawl is a remote `type: http` server with no local process, so there is nothing to daemonize and the wrapper does not apply (Perpetua-Tools `lesson_2c4124092607`). Harnesses that cannot speak `type: http` reach it through a pinned `mcp-remote`.
- **Tier 6, not tier 1.** Both spend paid credits over many calls, so the pair runs as one capped pass after tiers 1 to 5 did not answer.
- **`firecrawl_search` stays in the manifest.** It is not part of normal discovery. It is the one fallback for a session where EXA is not connected, labelled as degraded, so a Firecrawl-only session is not stranded.
- **The manifest lists every documented operation.** `allowed-tools` sandboxes the skill, so a documented tool missing from it would fail when called. `ask` and `docs-search` are CLI-only and have no MCP tool.

## Who owns what across the two repositories

orama-system owns the search order, this skill and the EXA runtime in `scripts/exa/`. Perpetua-Tools owns the memory of what was learned.

- Perpetua-Tools `.mcp.json` resolves to orama-system's wrapper at run time, so one implementation serves both.
- `exa-mcp-wrapper.sh`, `exa-mcp-daemon.py`, `setup-exa.sh` and `EXA-AGENT-PROMPT.md` in Perpetua-Tools are byte-identical mirrors. Edit them here, then copy them across. Never edit the mirror.
- Perpetua-Tools docs point at [the search policy](../../../references/search-and-code-exploration-policy.md) and do not restate the chain.
