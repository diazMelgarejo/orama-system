# Semantic Lessons Pointer

Canonical lessons live in `docs/LESSONS.md`. This file exists so Antigravity can
find the memory surface without duplicating the lesson log.

Before acting, read:

- `docs/LESSONS.md`
- `docs/wiki/README.md`
- `bin/orama-system/skills/hermes-harness/SKILL.md` for Hermes/ECC work
- `bin/orama-system/skills/mcp-orchestration/SKILL.md` for AGY/Gemini/Codex dispatch
- `bin/orama-system/skills/git-history-surgery/SKILL.md` for branch repair or history work

Add durable new lessons to `docs/LESSONS.md`, then update canonical skills only
when the lesson is repeated or operationally important.

## 2026-07-10T11:01:06+00:00 - Cline Instance Map (2026-07-08 Session)

**Lesson ID:** `lesson_d05c151e5302` | Salience: 7.0 | Confidence: 0.95

| # | PID | Process | Caller | Role |
|---|---|---|---|---|
| 1 | 51483 | node cline | zsh (terminal) | CLI launcher |
| 2 | 51484 | .cline main | PID 51483 | Active session (66.8% CPU, 619MB) |
| 3 | 44584 | .cline --cline-hub-daemon | PID 51484 (auto) | Hub daemon ws://127.0.0.1:25463/hub |
| 4 | 71165 | cline_mcp_server.mjs | Claude Code 0a13d9d5 | MCP stdio bridge |

Process tree: zsh -> node cline -> .cline -> .cline --cline-hub-daemon; claude --resume -> cline_mcp_server.mjs
cline-agent allowlisted in openclaw.json but NOT dispatched via gateway. All running ~2h.
