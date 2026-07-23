# ALL AGENTS — CRG platform endpoints + orama skills update

**Fan-out:** coord-026  
**Status:** OPERATOR RULE — read before next CRG/MCP work  
**From:** win-cursor @ primary Win orchestrator  
**Date:** 2026-07-23

## Audience

| Lane | Action |
|------|--------|
| **win-coder** | Re-run `sync-cursor-mcp.sh` on Windows; confirm `.cursor/mcp.json` CRG → `:1234` |
| **win-autoresearcher** | Ack only — no CRG config change unless using code-review-graph MCP |
| **win-cursor / Hermes** | Post-ECC Windows installs: validate CRG in doctor smoke checks |
| **mac-orchestrator** | **No change** — keep Ollama `:11434`; ack when read |
| **mac-researcher** | Ack only |
| **RTX 5080 / sibling Win** | Same as win-coder — LM Studio `:1234`, not `:11434` |

## Platform rule (SSoT)

| Platform | `CRG_OPENAI_BASE_URL` | Backend |
|----------|----------------------|---------|
| **macOS / Linux** | `http://localhost:11434/v1` | Ollama (`bge-m3`) |
| **Windows (all)** | `http://localhost:1234/v1` | LM Studio |

`:11434` is **Ollama-only (Mac/Linux)**. Every Windows host uses **LM Studio `:1234`**.

Canonical doc:
`bin/orama-system/skills/code-review/references/crg-platform-endpoints.md`

## What landed (orama skills + scripts)

- **New SSoT:** `code-review/references/crg-platform-endpoints.md`
- **Updated skills:** code-review, hermes-harness, windows-hermes-setup, windows-onboarding-config, platform-affinity-routing, cross-harness-protocol, cursor-agent, mcp-install, first-run-setup (windows-node-onboarding), ecc-doctor
- **Scripts:** `openclaw-env.sh` (`_crg_openai_base_url`), `sync-cursor-mcp.sh` (patches URL at sync), `crg-embed-mode` (platform-aware)
- **Review F3:** RESOLVED in `win-code-review-main-push-6.md`

*Note: changes may be local until next push — pull `orama-system` main when available.*

## Windows action (all Win lanes)

```powershell
cd $env:ORAMA_SYSTEM_PATH
bash bin/orama-system/scripts/sync-cursor-mcp.sh --profile readonly
```

Reload MCP in Cursor Settings. Verify:

```powershell
# Expect localhost:1234 in .cursor/mcp.json → code-review-graph.env
Invoke-RestMethod http://localhost:1234/v1/models | ConvertTo-Json -Depth 1
```

## macOS action

**No endpoint change.** Confirm Ollama warm:

```bash
curl -s http://localhost:11434/api/tags | grep -q bge-m3
```

## Supersedes

- `win-rtx5080-crg-endpoint-correction.md` (coord-025 errata) — absorbed into SSoT above

## GossipBus pointer

`coord-026` — CRG platform skills broadcast. Inbox: `win-2026-07-23-crg-platform-skills-broadcast.md`
