# Lessons — 2026-07-03 session (Fable-5 orchestrator)

1. **MCP stdio servers demand stdout purity.** `openclaw mcp serve` printed
   Doctor-warning box-art to stdout → every MCP client saw `Unexpected token '│'`.
   `doctor --fix` cannot clear persistent migration notices, so the durable fix
   is a `grep --line-buffered '^{'` wrapper, registered canonically in
   `bin/orama-system/skills/openclaw-skills/scripts/`. Full trace: DEBUG_TRACE.md.

2. **MCP scope duplicates mask fixes.** The broken raw-binary registration
   survived in the workspace `.mcp.json` (project scope) after the user-scope
   fix; `claude mcp list` warned about split endpoints. Always sweep all three
   scopes (user / project / Desktop config) when repairing a server.

3. **Session-limit failures are bursty — design for 0-of-N delegation.** Second
   consecutive run where every Sonnet subagent died instantly on a session
   limit. The ladder (inline main-loop + local models) shipped the identical
   scope both times. Orchestration plans must treat "no Claude subagents" as a
   normal operating mode, not an exception.

4. **One shared state file beats two listeners.** The LM Link watcher writes
   `~/.openclaw/state/lm_link.json` once; orama (canonical watcher) and
   Perpetua (thin `scripts/lm_link_status.py`, exit-code gate) both consume it.
   No RPC, no duplicated probing, works while either repo's services are down —
   the same pattern as `last_discovery.json`, now applied to link health.

5. **Gossip payloads stay PII-free by construction.** Heartbeats carry model
   ids + queue depth only — the redaction rule enforced at the schema level,
   not by post-hoc filtering.
