---
name: kimi-agent
description: >-
  Install, configure, and operate the Kimi Code CLI (`kimi`) for fanning out
  light/parallel tasks alongside the main orchestration session, and for
  monitoring its background server and session logs. Cross-platform installer
  (Moonshot AI); this skill documents the macOS/Linux path verified live on
  2026-07-10 (darwin-arm64, v0.23.4). Windows path is unverified — probe with
  the install script's PowerShell equivalent before relying on it there.
version: 1.0.0
license: Apache 2.0
compatibility: darwin, linux, orama-system, openclaw, hermes-harness
parent_skill: orama-system
triggers:
  - kimi
  - kimi code
  - kimi-code
  - kimi cli
  - fan out to kimi
  - moonshot kimi
allowed-tools: bash, file-operations
---

# Kimi Code Agent Skill

## Disambiguation

**`kimi`** (`~/.kimi-code/bin/kimi`) is Moonshot AI's Kimi Code CLI — a
standalone agentic coding tool in the same category as `cursor-agent`,
`codex`, and `gemini-cli`: a fan-out worker the main session can dispatch
light/parallel tasks to, NOT an internal oramasys stage worker (does not
belong in `bin/config/agent_registry.json`, which is reserved for
SOUL-file-backed OpenClaw/oramasys agents bound to a gateway provider).

| Command | Binary | What it is |
|---------|--------|------------|
| `kimi` | `~/.kimi-code/bin/kimi` | Moonshot Kimi Code CLI — use this |
| `cursor-agent` | `~/.local/bin/cursor-agent` | Cursor's background agent — separate product, see `../cursor-agent/SKILL.md` |

## Install

### macOS / Linux (verified 2026-07-10, darwin-arm64, v0.23.4)

```bash
curl -fsSL https://code.kimi.com/kimi-code/install.sh | bash
# Installs to ~/.kimi-code/bin/kimi; appends PATH entry to ~/.zshrc (or ~/.bashrc)
# New shells pick it up automatically; in an existing shell:
export PATH="$HOME/.kimi-code/bin:$PATH"
```

Verify:

```bash
kimi --version    # e.g. 0.23.4
kimi doctor       # validates config.toml / tui.toml — SKIP is fine on first run
```

### Windows

**Unverified — no PowerShell installer confirmed live.** Before relying on
Kimi on Windows/Hermes, check `https://code.kimi.com/kimi-code/` for a
`.ps1` equivalent, or run the bash installer under Git Bash and manually
add `%USERPROFILE%\.kimi-code\bin` to PATH. Do not assume parity with
`cursor-agent`'s Windows path until confirmed.

## Canonical Install Locations (binary tracking)

**Tracked so any session can call the binary without re-discovering it —
mirrors the `cursor-agent` canonical-paths table.**

| Item | Path |
|------|------|
| Binary | `~/.kimi-code/bin/kimi` |
| Config | `~/.kimi-code/config.toml` (empty until `login`/`provider add`) |
| Device ID | `~/.kimi-code/device_id` (mode 600 — do not commit, do not log) |
| Diagnostic log | `~/.kimi-code/logs/kimi-code.log` (not rotated; `.1` files are) |
| PATH entry | Appended to `~/.zshrc` by the installer — idempotent, re-running the installer does not duplicate |
| Session data | Managed internally by `kimi`; export via `kimi export [sessionId]` |

Quick binary-location check for any agent/script before invoking Kimi:

```bash
command -v kimi >/dev/null 2>&1 || export PATH="$HOME/.kimi-code/bin:$PATH"
command -v kimi >/dev/null 2>&1 || { echo "kimi not installed — see kimi-agent/SKILL.md § Install"; exit 1; }
```

## Provider Setup (REQUIRED before fan-out — ASK FIRST, do not fabricate)

`kimi doctor` reports config as empty by default — **no LLM provider is wired
until one of these runs**, and this is a live credentials/config decision,
not something to auto-decide:

| Path | Command | Notes |
|------|---------|-------|
| Moonshot cloud (Kimi K2 family) | `kimi login` | Interactive device-code OAuth in browser — cannot be completed headlessly by an agent |
| models.dev catalog import (e.g. local LM Studio) | `kimi provider catalog add lmstudio --api-key <key>` | **Verified blocked without a key** even for a local/no-auth backend — confirm with the user whether to pass a placeholder or use the custom-registry path instead |
| Custom registry (point directly at a local OpenAI-compatible endpoint, e.g. Win LM Studio `:1234` or Mac Ollama `:11434`) | `kimi provider add <url-to-api.json> [--api-key <key>]` | Needs a hand-authored `api.json` — not yet created; this is the local-first-doctrine-aligned path (see orama-system `SKILL.md § Local API Fallback`) and should be scripted once the user picks a default |

**Do not run `kimi login` or fabricate an API key on the user's behalf.**
Surface this table and ask which provider to wire before any dispatch that
needs a live model.

## Key Options (from `kimi --help`, v0.23.4 — verified)

| Option | Purpose |
|--------|---------|
| `-p, --prompt <prompt>` | Headless single-turn — prints response to stdout (equivalent to `cursor-agent --print`) |
| `--output-format <fmt>` | `text` (default) or `stream-json` |
| `-m, --model <model>` | Override model alias (defaults to `default_model` in `config.toml`) |
| `-y, --yolo` | Auto-approve all actions (trusted/CI only) |
| `--auto` | Start in auto permission mode |
| `--plan` | Read-only planning mode |
| `-S, --session [id]` | Resume a session (interactive picker without an id) |
| `-c, --continue` | Continue the previous session for the working directory |
| `--add-dir <dir>` | Add an extra workspace directory (repeatable) |
| `--skills-dir <dir>` | Load skills from a custom dir instead of auto-discovery (repeatable) |

## Light Task Fanout Pattern

Same shape as the `cursor-agent` pattern — headless, backgrounded, `wait` to collect:

```bash
export PATH="$HOME/.kimi-code/bin:$PATH"

kimi -p "Add type annotations to scripts/discover.py; only functions, no variables" \
  --output-format text > /tmp/kimi-task-a.txt &

kimi -p "Rename all snake_case variables in tests/test_foo.py to camelCase" \
  --output-format text > /tmp/kimi-task-b.txt &

wait   # collect when done
```

**Division of labour (matches the cursor-agent table — Kimi slots into the
same "mechanical fan-out" tier, not the orchestrator tier):**

| Main session (orchestrator) | `kimi` (fan-out worker) |
|------------------------------|--------------------------|
| Architecture decisions | Mechanical file edits |
| CIDF write discipline | Grep-and-replace tasks |
| Cross-repo synthesis | Doc generation |
| Security & policy review | Test scaffolding |
| Final crystallisation | Format / lint fixes |

## Monitoring & Observability

Kimi ships its own local server + visualizer — this IS the "monitor/observe"
surface, distinct from LAN-peer gossip (that's `scripts/lm_link_watch.py`,
a different concern: cross-machine inference-link health, not a single CLI
agent's own liveness).

```bash
# Start the background server (REST + WebSocket + web UI), bearer-token
# auth printed at startup, binds 127.0.0.1 only unless --host is passed:
kimi server run
kimi server run --foreground --log-level info   # attached, for live debugging

# List currently connected clients (machine-readable):
kimi server ps --json

# Stop it:
kimi server kill

# Session visualizer in browser (per-session trace):
kimi vis [sessionId]

# Config sanity check (run before any dispatch):
kimi doctor

# Diagnostic log (not rotated; .1 files are):
tail -f ~/.kimi-code/logs/kimi-code.log
```

**Health-check one-liner** for a pulse cron / pre-dispatch gate:

```bash
command -v kimi >/dev/null 2>&1 && kimi doctor >/dev/null 2>&1 && echo "kimi: OK" || echo "kimi: NOT READY"
```

## Session Export

```bash
kimi export [sessionId] -o /path/to/archive.zip   # defaults to most recent session
# --no-include-global-log to exclude ~/.kimi-code/logs/kimi-code.log from the bundle
```

## Update

```bash
kimi upgrade   # alias: kimi update
```

## Commands Summary (v0.23.4, verified)

| Command | Purpose |
|---------|---------|
| `kimi login` | Authenticate via device-code OAuth (Moonshot cloud) |
| `kimi doctor` | Validate config files |
| `kimi provider add\|remove\|list\|catalog` | Manage LLM providers non-interactively |
| `kimi server run\|ps\|kill\|rotate-token` | Local REST+WS daemon — observability surface |
| `kimi web` | Open the Kimi web UI (starts daemon if needed) |
| `kimi vis [sessionId]` | Session visualizer in browser |
| `kimi export [sessionId]` | Export a session as a ZIP archive |
| `kimi migrate` | Migrate data from a legacy `kimi-cli` install |
| `kimi acp` | Run as an Agent Client Protocol server over stdio (MCP-adjacent — not yet wired into this stack's MCP registry; evaluate separately before use) |
| `kimi upgrade` \| `kimi update` | Upgrade to latest version |

## References

- Platform-affinity routing (canonical known-agents table, Kimi added as a
  fan-out row): [`../hermes-harness/references/platform-affinity-routing.md`](../hermes-harness/references/platform-affinity-routing.md)
- Sibling fan-out agent (fuller precedent for this skill's structure):
  [`../cursor-agent/SKILL.md`](../cursor-agent/SKILL.md)
- Local-first fallback doctrine: [`../../../SKILL.md § Local API Fallback`](../../../SKILL.md)
- orama-system Stage 4 dispatch pattern: [`../../../SKILL.md § MODE 2 Stage 4`](../../../SKILL.md)

## Open Items (do not silently resolve — surface to user)

1. **Provider not yet wired** — `kimi doctor` passes on empty config, but no
   model can actually run until `login` or a `provider add`/`catalog add`
   path is chosen (see § Provider Setup). Ask before picking one.
2. **Windows install path unverified** — do not claim Hermes/Win parity
   until a `.ps1` installer or Git-Bash fallback is actually tested there.
3. **`kimi acp` (Agent Client Protocol) not yet evaluated** for MCP-registry
   integration — flagged for a future session, out of scope for this pass.
