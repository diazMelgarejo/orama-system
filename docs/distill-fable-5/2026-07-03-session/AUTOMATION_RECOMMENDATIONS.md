# Automation Recommendations — AutoResearcher pair (2026-07-03)

Prioritized, grounded in what exists (pulse cron, ClinePass fallback, LM Link
watcher, thin-wrapper skills). Each entry: what · where · trigger · payoff.

1. **MCP stdout-purity gate** — extend `scripts/security/check_endpoint_policy_contract.py`
   pattern with a sibling check: every MCP server script referenced by
   `.mcp.json`/Desktop config must route non-JSON output to stderr (static grep
   for `print(`/`console.log` before serve-loop). Trigger: CI + pre-commit.
   Payoff: the "Unexpected token" class never returns.
2. **LM Link as dispatch gate** — pulse cron step 0 becomes
   `python3 scripts/lm_link_watch.py --status` (or PT `scripts/lm_link_status.py`);
   dispatch only when `mode=linked`. Trigger: existing `mac-orchestrator-pulse`
   cron. Payoff: no wasted 401/timeout dispatch attempts; token-free probing.
3. **SessionEnd distill scaffold** — a Stop-hook that creates
   `docs/distill-fable-5/<date>-session/` with LESSONS.md stub when the session
   touched a frontier model. Trigger: Claude Code Stop hook. Payoff: farming
   becomes automatic instead of remembered.
4. **Gossip consumer in portal** — portal (`:8002`) renders
   `~/.openclaw/state/lan_peer/inbox/gossip-*.json` as a link-health widget.
   Trigger: existing portal poll. Payoff: humans see link state without CLI.
5. **Win watcher autostart** — add `scripts/lm_link_watch.ps1` to `start.ps1`
   (background job) so the Win side of the link is persistent too. Trigger:
   Win `start.ps1 --lan-peer`. Payoff: bidirectional link without manual step.
6. **Limit-aware delegation ladder in Workflow scripts** — orchestration
   workflows should catch subagent session-limit failures and re-dispatch the
   same prompts to local LM Studio/Ollama via `openclaw agent`/curl instead of
   dying. Trigger: workflow error handler. Payoff: two sessions in a row lost
   all 5-of-5 and 2-of-2 subagents to limits; local fallback keeps throughput.
7. **Distill index auto-link** — pre-commit hook appends new
   `docs/distill-fable-5/*-session/` folders to the README pilot table.
   Trigger: pre-commit. Payoff: index never rots.
