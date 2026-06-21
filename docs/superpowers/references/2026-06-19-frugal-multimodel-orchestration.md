# Frugal Multi-Model Orchestration — Reference

> Pattern: run external model panels directly from the orchestrator's Bash subprocess.  
> Never wrap them in Claude `agent()` calls.

## Why this matters

Claude's `agent()` calls are all billed to the same Anthropic spend cap. When the
cap is hit, every `agent()` call fails before the prompt even reaches the external
model — including calls to Codex, ollama, AGY, and OpenRouter. The models never
execute; the shell subprocesses never launch. The fix: call external models
directly from the orchestrator's Bash. The orchestrator (Opus-4.8 or Sonnet-4.6)
handles synthesis; external calls go via `subprocess`, `curl`, or direct CLI tools.

```
WRONG  (all lanes die when Anthropic cap hits):
  orchestrator:agent() → Claude:agent("use codex") → codex exec …
  orchestrator:agent() → Claude:agent("use ollama") → ollama http call …

RIGHT  (only Claude's orchestrator tokens count against the cap):
  orchestrator:Bash → codex exec … (direct subprocess)
  orchestrator:Bash → curl http://ollama … (direct http)
  orchestrator:Bash → agy -p "/goal …" (direct CLI)
```

## Canonical implementation

`$TMPDIR/cox_panel.py` (created 2026-06-19) is the reference implementation.
Copy it to `scripts/panels/` when you want a permanent version.

Key structural decisions from that run:

| Decision | Value |
|----------|-------|
| Execution model | `concurrent.futures.ThreadPoolExecutor`, one thread per lane |
| Timeout per lane | codex 260s, agy 260s, ollama 240s, openrouter 180s, gemini 220s |
| Output isolation | Each lane writes `$TMPDIR/cox_<lane>.out` — no shared state |
| HTTP calls | `subprocess.run(["curl", ...])` NOT `urllib.request` (avoids macOS SSL CA issue) |
| Secrets | Read from `os.environ`, never printed, never copied into files |
| Failure mode | Fail-open: a lane returning `(lane, False, 0)` is skipped during synthesis |

## Adopted features from the frugal `.mjs` workflow

The `.mjs` at `docs/superpowers/plans/2026-06-19-codex-openclaw-agent-frugal-multimodel-workflow.mjs`
had several design features worth keeping:

- **Probe-first gate**: check that a lane is reachable before sending the full prompt
- **`unavailableReport()`**: log why a lane was skipped (not silently dropped)
- **`cost_tier` field**: tag findings by which tier model surfaced them
- **`support[]` corroboration**: track which lanes agree on a finding
- **Free OpenRouter model default**: `nvidia/nemotron-3-super-120b-a12b:free`
- **AgentRouter ≠ OpenRouter**: these are separate; never fake one through the other
- **`ORAMASYS_OFFLINE=1` guard**: for CI/local-only runs
- **`gtimeout`**: macOS has no `timeout`; use `gtimeout <s>` for bounded subprocess calls
- **`normalizeKey()` dedup**: severity-promote duplicate findings across lanes
- **`workflowPaths()` via env vars**: no hardcoded paths in tracked scripts

## What the `.mjs` got wrong (and `cox_panel.py` fixed)

Both the `.mjs` and the initial ultracode workflow wrapped every external model
call inside a Claude `agent()` call:

```javascript
// .mjs (flawed — all these die on spend cap)
const codexResult = await agent("run codex exec ...", { model: "sonnet" })
const ollamaResult = await agent("call ollama ...", { model: "sonnet" })
```

The fix in `cox_panel.py`: Python threads, direct `subprocess.run` and `curl`.
No Claude agent wrappers. The orchestrator calls `python3 $TMPDIR/cox_panel.py`
from a single Bash tool call; it reads the results from `$TMPDIR/cox_*.out`.

## MCP orchestration adaptation

For workflows that use the Workflow tool (`agent()` calls):

```javascript
// Pattern: orchestrator calls a single Bash lane that runs the external panel
phase('ExternalPanel')
const panelScript = await agent(
  "Generate $TMPDIR/panel_<run>.py based on the digest and run it. " +
  "Return the content of each $TMPDIR/panel_<lane>.out file.",
  { label: "panel-runner", phase: "ExternalPanel" }
)
// Only ONE Claude agent call for the whole panel — the synthesis step.
// All external model calls happen inside the Python script via subprocess.
```

This keeps the Workflow budget usage to one `agent()` call for synthesis while
all the actual external-model traffic happens outside Claude's billing.

## Gemini CLI lane: DEAD (2026-06-19)

Google deprecated "Gemini Code Assist for individuals" — the `gemini` CLI free
tier is gone. Any call to `gemini -p "..."` returns `IneligibleTierError`.

**Replacement**: Use `agy` (Antigravity, v1.0.8) for Gemini-family inference:

```bash
agy -p "/goal <task>" --dangerously-skip-permissions
```

`agy models` shows available models including Gemini 3.5 Flash, 3.1 Pro, etc.
`orchestration-dispatch.md` priority 3 should say "agy only" not "agy / gemini".

## Lane availability summary (as of 2026-06-19)

| Lane | Status | Notes |
|------|--------|-------|
| codex | OK | `codex exec <digest> -C <repo> -s read-only` |
| agy | OK | v1.0.8, `--dangerously-skip-permissions` for unattended |
| ollama | OK | `qwen3-coder:480b-cloud` or `qwen3.5:9b-nvfp4` |
| openrouter | OK (fix SSL) | Use `curl` not `urllib.request`; key via `$OPENROUTER_API_KEY` |
| gemini CLI | DEAD | `IneligibleTierError` — use `agy` instead |
| OmniRoute | Quarantined | Disabled 2026-06-14; backup at `~/claude-config-backups/` |
| AgentRouter | Offline | No env; not routed through OpenRouter |

## OpenRouter SSL fix (Python `urllib.request` on macOS)

Python's `urllib.request` can't verify OpenRouter's cert using macOS system CAs.
Replace with `curl` in the panel script:

```python
def openrouter():
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        open(OUT("openrouter"), "w").write("[openrouter: no key]")
        return ("openrouter", False, 0)
    try:
        payload = json.dumps({
            "model": "deepseek/deepseek-chat-v3.1:free",
            "messages": [{"role": "user", "content": DIGEST}],
            "max_tokens": 1200, "temperature": 0.3
        })
        r = subprocess.run(
            ["curl", "-s", "--max-time", "180",
             "-H", "Content-Type: application/json",
             "-H", f"Authorization: Bearer {key}",
             "-d", payload,
             "https://openrouter.ai/api/v1/chat/completions"],
            capture_output=True, text=True, timeout=190
        )
        data = json.loads(r.stdout)
        text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        open(OUT("openrouter"), "w").write(text or json.dumps(data)[:2000])
        return ("openrouter", bool((text or "").strip()), len(text or ""))
    except Exception as e:
        open(OUT("openrouter"), "w").write(f"[openrouter ERROR: {e}]")
        return ("openrouter", False, 0)
```

## Spike answers: openclaw.json provider schema (2026-06-19)

These answer PT-MM1 and PT-MM2 from the multi-model panel.

### PT-MM1 RESOLVED: Backend identity IS exposed

The OpenClaw gateway model identifier uses `<provider-key>/<model-id>` format
throughout `~/.openclaw/openclaw.json`. Every model reference includes the
provider prefix:

- `"ollama/qwen3.5:9b-nvfp4"` → Ollama backend
- `"lmstudio-win/qwen3.5-27b-..."` → Win LM Studio backend
- `"google/gemini-3.1-pro-preview"` → Gemini backend

Stage 4 verify can parse the model string from the completion response. If the
model prefix matches the Codex provider key (e.g., `"codex/"`), Codex is active.
If it starts with `"ollama/"`, Ollama was used instead. This is a reliable
parseable signal — no gateway modification needed.

Additionally, `diagnostics.otel.traces: true` is live, so OTEL spans provide a
second signal path if needed.

### PT-MM2 RESOLVED: Fallback provider schema is proven

The OpenAI-compatible provider schema (used by `lmstudio-mac`, `lmstudio-win`,
`gemini-main`, `gemini-fallback`) is:

```json
"<provider-key>": {
  "api": "openai-completions",
  "apiKey": "${env:SOME_ENV_VAR}",
  "baseUrl": "http://localhost:<port>/v1",
  "models": [
    {
      "id": "<model-id>",
      "name": "<display name>",
      "contextWindow": <int>,
      "maxTokens": <int>,
      "cost": { "input": 0, "output": 0 }
    }
  ]
}
```

To add Codex as Stage 3 fallback:

```json
"models": {
  "providers": {
    "codex": {
      "api": "openai-completions",
      "apiKey": "${env:OPENAI_API_KEY}",
      "baseUrl": "http://localhost:${CODEX_APP_SERVER_PORT}/v1",
      "models": [
        {
          "id": "gpt-5.5",
          "name": "Codex GPT-5.5",
          "contextWindow": 200000,
          "maxTokens": 65536,
          "cost": { "input": 0, "output": 0 }
        }
      ]
    }
  }
}
```

Then set in the agent entry: `"model": { "primary": "codex/gpt-5.5" }`.

**Stage 3 IS viable.** The schema is real and working for 5 other providers.
The only unknown is the Codex app-server's actual localhost port — discoverable
via `gstack-codex-probe` or by checking the app-server process.

### openclaw CLI status (2026-06-19)

The `openclaw` CLI binary is broken: `MODULE_NOT_FOUND` for
`~/.local/openclaw/openclaw.mjs`. The gateway and config files still work.
This means Stage 0 probe must check the CLI separately from the gateway:

- `openclaw --version` → BROKEN (module not found)
- `~/.openclaw/openclaw.json` → exists and readable
- Gateway port 18789 → check with `curl -s http://localhost:18789/` (token required)
- OTEL traces → `diagnostics.otel.enabled: true` in config

Stage 0 should treat "openclaw CLI absent/broken" as a non-fatal probe miss that
routes to Stage 2 (idempotent install) rather than a fatal error.
