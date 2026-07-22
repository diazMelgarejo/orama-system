# Appendix: Legacy file disposition

> Extracted from `mcp-orchestration/SKILL.md` during the 2026-07-22
> skill-trimming pass — historical/rarely-needed, kept for reference.

The following files are superseded by the canonical `SKILL.md`:

| Legacy path | New status |
| ------------- | ------------ |
| `OpenClaw/MCP_ORCHESTRATION_SKILL.md` | Redirect stub — points here |
| `OpenClaw/MCP_ORCHESTRATION_SKILL_v2.md` | Redirect stub — points here |
| `OpenClaw/MCP-INSTALL-PLAN.md` | Reference companion — kept for installation procedure |
| `~/.claude/skills/mcp-orchestration/SKILL.md` | User-level mirror — keep in sync via `install -m 0644 bin/orama-system/mcp-orchestration/SKILL.md ~/.claude/skills/mcp-orchestration/SKILL.md` (run from repo root after edits). For installing the MCP stack itself, see [`../../mcp-install/SKILL.md`](../../mcp-install/SKILL.md). |

Update all references to point at `orama-system/bin/orama-system/mcp-orchestration/SKILL.md`.
