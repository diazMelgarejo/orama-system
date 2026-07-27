# Common Failure Modes & Fixes

> Extracted from `fable5-tier-based-routing/SKILL.md` during the 2026-07-22
> skill-trimming pass.

| Error | Cause | Fix |
|-------|-------|-----|
| `timeout 10 curl ...` blocks on SIGTERM | Using shell `timeout` instead of killable bg | Use Monitor until-loop or run_in_background=true |
| All tiers timeout simultaneously | Ollama + LM Studio both down; network issue | Check network; restart services; don't escalate to cloud without approval |
| Tier 3 silently used (no gate exception) | Cost gate not wired; escalation_reason missing | Verify `_enforce_tier_policy` called; log escalation_reason in spec |
| "600 behind" after tier fallback | SHA-based metric on rewritten main | Use tree-twin scan (fable5-git-rebase-safety skill) |
| Tier 4 used for trivial task (cost waste) | Escalation_reason not checked; auto-escalate bug | Audit spec; verify cost gate raises before Tier 4 |
| LM Studio discovery returns stale IP | DHCP lease expired; launchd watcher missed update | Run `$PERPETUA_TOOLS_PATH/scripts/discover-lm-studio.sh` manually |
