# FAQ

> Extracted from `fable5-tier-based-routing/SKILL.md` during the 2026-07-22
> skill-trimming pass.

**Q: Can I force Tier 1 or Tier 2 via escalation_tier parameter?**
A: No. Tiers 0–2 are PROBE-ONLY (internal logic). Passing `escalation_tier=1` or `escalation_tier=2`
raises `FrugalityPolicyError: cannot escalate to tier N; tiers 0-2 require probe match`. Only Tiers 3–6
are reachable via escalation_tier + escalation_reason.

**Q: What if Tier 1 (Ollama) is down?**
A: Probing returns None, code falls through to Tier 2. If Tier 2 also fails,
escalate to Tier 3+ with `escalation_reason="tier_2_unavailable"`.

**Q: Do I need escalation_reason for Tiers 0–2?**
A: No. Escalation_reason is REQUIRED only when escalation_tier >= 3. Omitting it for Tier 3+
raises `FrugalityPolicyError: escalation_reason is required when tier >= 3`.

**Q: Why raise exceptions instead of auto-escalate on cost gate?**
A: Silent escalation = silent cost overrun. Explicit exceptions (via `CostGuard.can_spend()`)
force the caller to acknowledge cost impact and decide: retry with approval, queue for later,
or fail gracefully.

**Q: What is the daily budget and how do I change it?**
A: Default: $25.00/day (CostGuard.ALERT_RATIO = 0.80 at 80% spend). Change via:
```python
guard = CostGuard()
guard.set_budget(50.0)  # New daily budget
```
Budget auto-resets every 24h based on last_reset timestamp.

**Q: What happens if Tier 6 (last resort) fails?**
A: No fallback. Tier 6 failure is FATAL. Caller must raise SystemExit or equivalent:
```python
except TimeoutError:
    raise SystemExit("CRITICAL: Tier 6 (last resort) timeout. No fallback.")
```

**Q: Can I skip the cost guard?**
A: The cost guard is built into resolve_route() when escalating to Tier 3+.
You MUST call `guard.can_spend()` before escalation. There is no way to bypass it
without modifying orchestrator/cost_guard.py.

**Q: Do local tiers (1–2) have timeouts?**
A: Tier 1–2 are local and typically fast (<3s). Timeouts are enforced by the caller
via Monitor until-loop or run_in_background pattern (never `timeout N && cmd`).
Recommended: 10s timeout for all tiers as a consistent safety margin.

**Q: How do I audit cost escalations?**
A: Always log the escalation event with route.escalation_reason. Example:
```python
audit_log = {
    "timestamp": time.time(),
    "escalation_reason": route.escalation_reason,
    "tier": route.tier,
    "backend": route.backend,
    "est_cost_usd": route.est_cost_usd,
}
```
