# gemini-mcp-tool and ai-cli-mcp — Install & Reference

> Extracted from `mcp-orchestration/SKILL.md` §4–§5 during the 2026-07-22
> skill-trimming pass. Decision-time routing rules stay in `SKILL.md` §2;
> this file is install/setup detail, read on demand.

## gemini-mcp-tool

Repository: `jamubc/gemini-mcp-tool`

### Purpose

Bridges Gemini CLI into Claude Code or other MCP clients. Used **only for Gemini-Analyzer use-cases** per `SKILL.md` §2 Rule 2.

### Claude Code setup

Register server `gemini-cli` in Claude Code MCP settings with command `npx` and
args `-y gemini-mcp-tool@<PINNED_VERSION>` (never bare `@latest` — pin after review).

Verify: `/mcp` → expect `gemini-cli active`

### Claude Desktop setup

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "gemini-cli": {
      "command": "npx",
      "args": ["-y", "gemini-mcp-tool@<PINNED_VERSION>"]
    }
  }
}
```

Restart Claude Desktop.

### Reader Protocol (Gemini-Analyzer mode)

1. Mark the call as Gemini-Analyzer (explicit user intent)
2. Ask Gemini a NARROW reading question with structured output
3. Ask Claude to verify the evidence
4. Let Claude decide

Good:

```text
Ask Gemini to identify stale architecture claims in @README.md and @docs/. Return file, claim, contradiction, confidence.
```

Bad:

```text
Ask Gemini to fix the repo.
```

### Model selection

| Model | Use |
| --- | --- |
| Gemini Pro | architecture, whole-repo reading, security review, visual diff |
| Gemini Flash | quick review, smaller files, routine docs |

### Windows / Parallels note

Use official `gemini-mcp-tool` first. A package like `gemini-mcp-tool-windows-fixed` is a local workaround only.

---

## ai-cli-mcp

Repository: `mkXultra/ai-cli-mcp`

### Purpose

Runs AI CLI tools as background worker processes with PID tracking, result retrieval, waiting, killing, cleanup.

### Critical first run

Run once:

```bash
claude --dangerously-skip-permissions
codex login
gemini auth login
```

### Claude Code setup

Add server `ai-cli` in Claude Code MCP settings using JSON config:

```json
{"name":"ai-cli","command":"npx","args":["-y","ai-cli-mcp@<PINNED_VERSION>"]}
```

### Generic MCP config

```json
{
  "mcpServers": {
    "ai-cli-mcp": {
      "command": "npx",
      "args": ["-y", "ai-cli-mcp@<PINNED_VERSION>"],
      "env": {
        "MCP_CLAUDE_DEBUG": "false"
      }
    }
  }
}
```

### Core tools

| Tool | Purpose |
| --- | --- |
| `run` | Launch a background AI CLI process |
| `wait` | Wait for one or more PIDs |
| `peek` | Watch short live output from a running worker |
| `get_result` | Fetch result for one worker |
| `list_processes` | List tracked workers |
| `kill_process` | Stop a stuck worker |

### Worker safety

- Use absolute `workFolder`
- Avoid destructive actions
- Do not allow background agents to commit
- Require explicit user confirmation for writes, deletes, deploys, account changes
- Kill runaway PIDs
- Archive useful results into `learnings.md` only after review
