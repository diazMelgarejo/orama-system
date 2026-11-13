# Hub Daemon (`cline --zen` / `cline hub`)

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

Cline can run sessions in a background hub daemon, useful for long-running tasks
that shouldn't block the terminal.

## Endpoint

```text
ws://127.0.0.1:25463/hub
```

The hub speaks Cline's **proprietary WebSocket protocol**, not OpenAI
completions and not ACP. `GET /v1/models`, `GET /`, and `GET /models` all
return `404 Not found`. It is not directly usable by OpenClaw as a model
provider or ACP backend.

## Starting the hub

```bash
# Start a background session
cline "run the full test suite and fix all failures" --zen -c /repo

# Or manage the hub daemon directly
cline hub
```

## Monitoring

```bash
# Open the Cline Hub dashboard in a browser
cline dashboard
```

The dashboard provides a web UI for active and past hub sessions.

## Use from OpenClaw

The OpenClaw agent can:

1. **Start** a hub session via exec: `cline "task" --zen -c /repo --json`
2. **Poll** its status via `cline history --json --limit 1` (session state is
   persisted to `~/.cline/data/db/sessions.db` and
   `~/.cline/data/sessions/<id>/`)
3. **Resume** it in the foreground if needed: `cline --id <id> "continue" --json`

## Files

| Path | Contents |
| --- | --- |
| `~/.cline/data/logs/hub-daemon.log` | Hub daemon log |
| `~/.cline/data/logs/cline.log` | Cline CLI log (all sessions) |
| `~/.cline/data/db/sessions.db` | Session database (SQLite) |
| `~/.cline/data/sessions/<id>/*.json` | Per-session messages + metadata |
| `~/.cline/data/cache/feature-flags.json` | Feature flags (e.g. `ext-cline-pass`) |

## Caveats

- The hub is **not** an OpenAI-compatible endpoint. Do not point an OpenClaw
  `models.providers` entry at `http://127.0.0.1:25463`.
- The hub is **not** an ACP server. Use `cline --acp` (separate mode) for ACP.
- Hub sessions bill Cline Credits when using `cline`/`cline-pass` providers.
