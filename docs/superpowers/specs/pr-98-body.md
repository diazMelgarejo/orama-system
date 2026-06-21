## Summary

Adds a named OpenClaw sub-agent (`codex-agent`) backed by OpenAI Codex CLI + GPT-5.5, an oramaclaw orbit plugin scaffold for AlphaClaw/OpenClaw lifecycle management, and migrates all Gemini persona dispatch to AGY's `invoke_agent()` convention. **No default routing is touched.**

---

## Preserved invariants

| Setting | Value |
|---|---|
| `agents.defaults.model.primary` | `ollama/qwen3.5:9b-nvfp4` (LaunchAgent — unchanged) |
| `main` agent | `lmstudio-mac/qwen3.5-9b-mlx` (unchanged) |
| `coder` agent | `lmstudio-win/qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2` (unchanged) |
| LaunchAgent plist | not touched |

The binding script enforces these via a snapshot → post-mutation invariant check and rolls back `openclaw.json` if any of the three are mutated.

---

## What's in this PR (25 commits, 74 files, +7748 / -1162)

### 1. `codex-agent` sub-agent — explicit GPT-5.5 path via Codex CLI

Invoked only via `openclaw run codex-agent`. Never becomes the default.

**New files:**
```
bin/orama-system/skills/codex-openclaw-agent/
  SKILL.md                                    canonical skill + routing guard
  references/codex-backend-binding.md         5-stage resolver ladder (a→e)
  scripts/bind_codex_backend.sh               idempotent binder; flock; atomic writes; rollback on verify fail
  scripts/generate_codex_openclaw_profile.py  marker-region reconciler (oramaclaw:generated:start/end)
.agents/skills/codex-openclaw-agent/SKILL.md  thin wrapper (byte-identical pair)
.claude/skills/codex-openclaw-agent/SKILL.md  thin wrapper (byte-identical pair)
```

**Resolver ladder:**
- **(a) Probe** — read-only: CLI present, auth structure in `~/.codex/config.toml`, plugin presence, live HTTP health ping on port 61234; stale state-file guard
- **(b) Primary** — native OpenClaw Codex plugin: `openclaw plugins install/allow/enable openai` + `openclaw agents add` with canonical workspace
- **(c) Idempotent install** — installs plugin if absent, retries (b)
- **(d) Fallback** — registers codex app-server as `openai-completions` provider directly in `openclaw.json`; `apiKey` as `${CODEX_API_KEY_REF}` env-var reference (never literal)
- **(e) Verify** — `openclaw run codex-agent --task "reply with exactly: CODEX_BACKEND_OK"`; rolls back and fails loudly if ollama answered

**Binder refactored in `dce98e6`:** replaced custom app-server path with native OpenClaw Codex provider; `generate_codex_openclaw_profile.py` is now an idempotent marker-region reconciler; `bind_codex_backend.sh` drops `--force` and stale app-server detection, adds plugin allowlist preservation.

**Resolved findings:** PT-MM1 (backend identity is `<provider>/<model>`-parseable), PT-MM2 (OpenAI-compat provider schema proven across 5 live providers), PT-MM5 (POSIX `mkdir` lock fallback for macOS).

**Usage:**
```bash
bash bin/orama-system/skills/codex-openclaw-agent/scripts/bind_codex_backend.sh
bash bin/orama-system/skills/codex-openclaw-agent/scripts/bind_codex_backend.sh --dry-run
openclaw run codex-agent --task "your task here"
```

---

### 2. AGY persona migration — `invoke_agent(name, prompt)`

`gemini -p "…"` is dead as of 2026-06-19 (`IneligibleTierError` — Google deprecated Code Assist for individuals). All Gemini-persona dispatch now goes through `invoke_agent()`.

**New files:**
```
agy-gemini.md                  command guide for agy (was referenced throughout, never existed)
scripts/agy/invoke_agent.sh    tool-level dispatcher — source and call
```

**Three named personas:**

| Persona | Model | Timeout | Role |
|---|---|---|---|
| `codebase_investigator` | Gemini 3.1 Pro (High) | 260 s | Deep analysis / architecture map / security audit / blast-radius |
| `generalist` | Gemini 3.5 Flash (Med) | 200 s | High-volume refactor / lint / doc-drift / PR lenses 2–5 |
| `cli_help` | agy `--print` (default) | 60 s | CLI flag lookup / error decode / one-shot answer |

**Dispatch convention:** never call bare `agy -p` in scripts — always `invoke_agent <persona> <prompt>`. Includes built-in probe guard (`AGY_READY` stdout check), `gtimeout` enforcement, and fail-open degradation to next lane.

**Files updated:** `orchestration-dispatch.md` (agy § replaced), `mcp-orchestration/SKILL.md` (successor note rewritten), `multi-channel-steelman.md` (gemini probe line commented DEAD).

---

### 3. oramaclaw orbit plugin scaffold

D22 design doc + control plane v1 implementation plan for `oramaclaw` — an orbit plugin for the AlphaClaw/OpenClaw lifecycle. Tracked as `docs/v2/40-*`.

---

### 4. OpenClaw CLI resolver substrate

- `scripts/openclaw/resolve-openclaw.sh` — 4-candidate canonical resolver (prefers launchd gateway install, blacklists stale `~/.alphaclaw` orphan, verifies `--version` before returning)
- `bin/orama-system/scripts/lib/openclaw-env.sh` — three helpers: `openclaw_resolver_path()`, `resolve_openclaw_cli()`, `openclaw_cmd()`
- `scripts/setup_macos.py` — idempotent `step_openclaw_cli_wrapper()` (rewrites `~/.local/bin/openclaw` to resolver wrapper on every `start.sh`)

---

### 5. Test coverage added

```
tests/conftest.py
tests/fixtures/oramaclaw-native-codex-agent.json
tests/fixtures/oramaclaw-cooperative-drift.json
tests/fixtures/oramaclaw-security-topology.json
tests/fixtures/oramaclaw-stale-gateway.json
tests/test_ensure_rag_mcp.py
```

---

## Security

- Auth referenced by `~/.codex/config.toml` path only — no keys in any generated file
- `apiKey` in provider block uses `${CODEX_API_KEY_REF}` env-var resolved by OpenClaw runtime
- All paths use `~` / `${HOME}` — `/Users/` literals blocked by `repo_hygiene.py`
- `SECURITY.md` for `codex-agent` is an operator-owned scaffold (sandbox + approval policies)
- `invoke_agent` probe guard prevents dispatch to an unready or quota-exhausted agy instance
- No fallback to ollama/lmstudio — `codex-agent` fails loudly if Codex is unavailable
