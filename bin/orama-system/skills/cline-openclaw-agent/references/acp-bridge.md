# ACP Bridge (OpenClaw ↔ Cline)

Agent Client Protocol (ACP) is the structured, streaming bridge between OpenClaw
and Cline. Both sides implement it: OpenClaw bundles `@agentclientprotocol/sdk`
and ships `openclaw acp`; Cline ships `cline --acp`.

## Direction 1 — OpenClaw drives Cline (OpenClaw = client, Cline = server)

```bash
openclaw acp client \
  --server cline \
  --server-args --acp \
  --cwd /path/to/repo \
  --session agent:cline-agent:main
```

This spawns `cline --acp` as a stdio ACP server and bridges it into an OpenClaw
session. Options:

| Flag | Description |
| --- | --- |
| `--server <command>` | ACP server command (default: `openclaw`; set to `cline`) |
| `--server-args <args...>` | Extra arguments for the ACP server (set to `--acp`) |
| `--cwd <dir>` | Working directory for the ACP session |
| `--session <key>` | Default session key (e.g. `agent:cline-agent:main`) |
| `--session-label <label>` | Default session label to resolve |
| `--reset-session` | Reset the session key before first use |
| `--require-existing` | Fail if the session key/label does not exist |
| `--provenance <mode>` | `off`, `meta`, or `meta+receipt` |
| `--no-prefix-cwd` | Do not prefix prompts with the working directory |
| `--server-verbose` | Enable verbose logging on the ACP server |
| `--token <token>` / `--token-file <path>` | Gateway token if required |
| `--password <pw>` / `--password-file <path>` | Gateway password if required |
| `--url <url>` | Gateway WebSocket URL (defaults to `gateway.remote.url`) |
| `-v, --verbose` | Verbose client logging to stderr |

## Direction 2 — Cline drives OpenClaw (Cline = client, OpenClaw = server)

```bash
# Terminal 1: expose OpenClaw as an ACP server on stdio
openclaw acp

# Terminal 2: point Cline at that server (via Cline's ACP client config)
cline --acp  # when configured to talk to the OpenClaw ACP server
```

`openclaw acp` (no subcommand) runs the ACP bridge backed by the Gateway. It
exposes OpenClaw as an ACP server that Cline can connect to as a client.

## Important: Do NOT enable `acp.enabled` globally

The `acp` config block (`acp.enabled`, `acp.backend`, `acp.allowedAgents`)
requires `acp.backend` to match a **registered ACP runtime plugin backend**
(e.g. `acpx`). Cline's `--acp` mode makes Cline an ACP **server**, not a
backend plugin. Setting `acp.backend: "cline"` or enabling `acp.enabled`
without a registered backend will break the gateway. Use the one-shot
`openclaw acp client --server cline` bridge instead — it does not require the
global ACP gate.

## One-shot bridge script

See [../scripts/acp_bridge.sh](../scripts/acp_bridge.sh) for a wrapper that
handles session keys, working directory, and provenance.

## Use cases

- **Streaming delegation**: OpenClaw's Main Agent delegates a coding task to
  `cline-agent` via ACP; Cline executes with tool loops; results stream back
  into the OpenClaw session with provenance receipts.
- **Editor integration**: `cline --acp` is designed for editor integration;
  OpenClaw can be that "editor" client, gaining structured access to Cline's
  tool-use events.
- **Multi-turn handoff**: use `--session agent:cline-agent:main` to keep a
  persistent ACP session across multiple OpenClaw turns; resume with
  `--require-existing` to avoid creating a duplicate.
