# CRG Platform Endpoints — Reference

> **Role:** Single source of truth for `code-review-graph` embedding backend URLs.
> **Skill owner:** code-review
> **Last updated:** 2026-07-23

## Rule

CRG and gbrain share **bge-m3** (1024-dim) via an OpenAI-compatible embeddings shim.
The **host and port** depend on platform — not the model name.

| Platform | `CRG_OPENAI_BASE_URL` | Inference backend | Notes |
|----------|----------------------|-------------------|-------|
| **macOS** | `http://localhost:11434/v1` | Ollama (`ollama pull bge-m3`) | Default in committed stack templates |
| **Linux** | `http://localhost:11434/v1` | Ollama (same as macOS) | Same stack as macOS unless overridden |
| **Windows (all)** | `http://localhost:1234/v1` | LM Studio (`$LM_STUDIO_WIN_ENDPOINTS`) | Primary Windows path — **not** `:11434` |

`:11434` is **macOS/Linux (Ollama) only**. Every Windows host — including RTX 5080
workstations — uses LM Studio at `:1234` unless Ollama is explicitly installed and
running as a deliberate fallback.

## Where it is configured

| Surface | File / command | Platform detection |
|---------|----------------|-------------------|
| Cursor project MCP | `orama-system/.cursor/mcp.json` | `sync-cursor-mcp.sh` patches URL at sync time |
| OpenClaw / Claude Code | `OpenClaw/.mcp.json` | `crg-embed-mode gbrain` + `openclaw-env.sh` helpers |
| CLI one-shot embed | shell `export CRG_OPENAI_BASE_URL=…` | Set manually per table above |

Shared env block (all platforms):

```json
{
  "CRG_OPENAI_API_KEY": "ollama",
  "CRG_OPENAI_MODEL": "bge-m3",
  "CRG_OPENAI_DIMENSION": "1024",
  "CRG_ACCEPT_CLOUD_EGRESS": "1"
}
```

Only `CRG_OPENAI_BASE_URL` changes by platform.

## Windows override (after ECC or vendor MCP install)

ECC vendor drops ship the **macOS** template (`:11434`). On Windows, patch after install:

```powershell
# .cursor/mcp.json → mcpServers.code-review-graph environment block
"CRG_OPENAI_BASE_URL": "http://localhost:1234/v1"
```

Or re-run sync (idempotent, platform-aware):

```powershell
cd $env:ORAMA_SYSTEM_PATH
bash bin/orama-system/scripts/sync-cursor-mcp.sh --profile readonly
```

Reload MCP in **Cursor Settings → MCP** after any change.

## macOS — no change needed

Keep `CRG_OPENAI_BASE_URL` at `http://localhost:11434/v1`. Confirm Ollama is warm:

```bash
curl -s http://localhost:11434/api/tags | grep -q bge-m3
```

## Verification

```bash
# macOS / Linux
curl -s http://localhost:11434/v1/models | head

# Windows (PowerShell)
Invoke-RestMethod http://localhost:1234/v1/models | ConvertTo-Json -Depth 2
```

```bash
bash bin/orama-system/skills/code-review/scripts/crg-embed-mode status
# prints current CRG_OPENAI_BASE_URL from OpenClaw .mcp.json
```

## Related

- [`crg-embed-mode.md`](crg-embed-mode.md) — toggle gbrain vs local embed mode
- [`../../hermes-harness/references/ecc-doctor-and-cursor-smoke-checks.md`](../../hermes-harness/references/ecc-doctor-and-cursor-smoke-checks.md) — Windows post-install validation
- [`../../hermes-harness/references/windows-onboarding-config.md`](../../hermes-harness/references/windows-onboarding-config.md) — `LM_STUDIO_WIN_ENDPOINTS`
- [`../../mcp-install/references/cursor-mcp.md`](../../mcp-install/references/cursor-mcp.md) — sync script and merge rules
