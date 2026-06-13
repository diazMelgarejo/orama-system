# OmniRoute Lazy-Sidecar (Optional Parallel Dispatch)

> **NEVER install. NEVER require. NEVER fail if absent.**
> OmniRoute is a local HTTP MCP server (port 20128) that fans tasks to free
> OpenRouter/AgentRouter models in parallel. When present it enhances throughput;
> when absent the workflow continues unchanged. It is installed independently and
> managed by the user — no setup script should touch it.
>
> Offloaded from `bin/orama-system/SKILL.md` for progressive disclosure.

## Probe (run once at session start, silent on any failure)

The bearer token is read from the environment — never hardcode it (a literal token in
a tracked file is a committed secret). Export `OMNIROUTE_TOKEN` in `.env` (gitignored).

```bash
_OR_URL="http://127.0.0.1:20128/api/mcp/stream"
_OR_TOK="${OMNIROUTE_TOKEN:-}"   # injected from env/.env; never hardcode a token here
_OMNIROUTE="unavailable"
if [ -n "$_OR_TOK" ] && curl -sf --max-time 2 "$_OR_URL" -H "Authorization: Bearer $_OR_TOK" >/dev/null 2>&1; then
  _OMNIROUTE="running"
elif command -v omniroute >/dev/null 2>&1; then
  omniroute serve --daemon --no-open >/dev/null 2>&1
  sleep 1
  if [ -n "$_OR_TOK" ] && curl -sf --max-time 2 "$_OR_URL" -H "Authorization: Bearer $_OR_TOK" >/dev/null 2>&1; then
    _OMNIROUTE="started"
  fi
fi
echo "OMNIROUTE: $_OMNIROUTE"
```

## Workflow rule

| `OMNIROUTE` value | Action |
|-------------------|--------|
| `running` or `started` | Route suitable subtasks through OmniRoute: review passes, draft generation, parallel A/B model comparisons. OmniRoute tools appear in Claude Code as MCP tools — use them for fan-out. |
| `unavailable` | Continue with standard stack (code-review-graph → gbrain → Gemini → ai-cli). Do NOT warn the user. Do NOT suggest installation. |

## Never

- Install or upgrade OmniRoute inside any setup script or `start.sh`
- Fail, warn, or degrade visibly when OmniRoute is absent
- Block on OmniRoute being rate-limited or unreliable
- Retry more than once per session if start fails
