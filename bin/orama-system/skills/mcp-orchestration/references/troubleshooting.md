# mcp-orchestration Troubleshooting

> Extracted from `mcp-orchestration/SKILL.md` §10 during the 2026-07-22
> skill-trimming pass.

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| MCP server missing | Not registered or client not restarted | Run `/mcp` and `claude mcp list` |
| Gemini tool fails | Gemini CLI not authenticated | `gemini auth login` |
| Wrong Gemini package | Old guide used wrong package | Use `@google/gemini-cli` |
| ai-cli worker hangs | First-run prompt not accepted | `claude --dangerously-skip-permissions` once |
| `claude -p` says `Not logged in` after login | OAuth callback or credential persistence failed in sandbox | `claude auth login --claudeai` outside sandbox; verify `auth status` and `claude -p` |
| Claude login says success but status is false | Login metadata was written without a usable token | Capture `--debug` log; rerun auth outside sandbox |
| Multiple Claude installs | PATH/native/global mismatch | Compare `which claude`, versions, exact binaries; use one binary everywhere |
| OpenRouter free-tier rate-limit hit | 50 req/day exceeded | Fall back to local ollama, or wait |
| OpenRouter model unavailable | Provider rate limit on that specific model | Use the fallback chain in §2 Rule 1 |
| JSON parse error | Debug logs pollute stdout | Set `MCP_CLAUDE_DEBUG=false` |
| ESM import error | Old Node version | Use Node.js 20+ |
| Agent runs forever | Worker stuck | `peek`, then `kill_process` |
| Too many tools | Tool overload | Enable tool search |
| OpenClaw cannot see server | Wrong config shape | Use `openclaw mcp set` or `mcp.servers` |

## Windows UTF-8 fix

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
```
