# Debug Trace — MCP "openclaw" Unexpected token (autoresearch:debug style)

**Date:** 2026-07-03 · **Orchestrator:** Fable 5 (inline; Sonnet delegates limit-blocked)

## SYMPTOM
Claude Desktop and Claude CLI both mark the `openclaw` MCP server failed with
repeated `Unexpected token` JSON parse errors.

## HYPOTHESIS
The server pollutes stdout: MCP stdio clients parse stdout as newline-delimited
JSON-RPC, so any non-JSON byte stream (banner, warning) breaks the parser.

## EXPERIMENT
Run the registered command directly, capture streams separately:
`openclaw mcp serve > out.txt 2> err.txt` (4s, then kill).
**Observed:** stdout begins with a box-art "Doctor warnings" banner
(`│ ◇ ├ └` characters) — `Unexpected token '│'` exactly. stderr empty.

## FALSIFY THE EASY FIX
`openclaw doctor --fix` updated the config, but the persistent migration
notice ("Left plugin install index in place because shared SQLite state has
conflicting plugin install metadata") STILL prints to stdout on the next
`mcp serve`. Config-repair alone is not a durable fix — any future warning
class re-breaks the stream.

## FIX (durable, canonical)
`bin/orama-system/skills/openclaw-skills/scripts/openclaw-mcp-stdio-clean.sh`
— wraps `openclaw mcp serve`, filtering stdout with `grep --line-buffered '^{'`
(JSON-RPC lines always start with `{`; banner lines never do). stdin and stderr
pass through untouched.

## VERIFICATION
1. Idle wrapper stdout = **0 bytes** (banner filtered, server waiting).
2. `initialize` handshake through the wrapper returns
   `serverInfo {"name":"openclaw","version":"2026.6.11"}` — protocol intact.
3. `claude mcp list` → `openclaw … ✓ Connected` (user scope, via wrapper).
4. Claude Desktop config repointed to the wrapper; stale project-scope
   registration (raw binary) removed from the workspace `.mcp.json`.

## GENERALIZED LESSON
Any CLI that hosts an MCP stdio server must guarantee **stdout purity** —
banners, doctor output, and config warnings belong on stderr. When you don't
control the binary, a line-filter wrapper is the defensive pattern; add a CI
grep that MCP server entry points never print non-JSON to stdout.
