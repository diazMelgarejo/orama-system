# Deployment Validation & CI/CD Integration

> Extracted from `fable5-tier-based-routing/SKILL.md` during the 2026-07-22
> skill-trimming pass.

## Production Tier Routing

Tier-based routing is live in production (Perpetua-Tools v0.9.9.9). This skill
documents the actual implementation, not aspirational design.

**Current deployment status (Fable-5 v1.1):**
- Tier 0–2: Always available (local, free)
- Tier 3–6: Available subject to policy + cost gate approval
- Production uses CostGuard with $25/day budget
- Fallback tested via integration tests in `tests/test_frugality_router.py`

**To verify your deployment:**

1. Check local tier probing:
```bash
# Verify Tier 1 (Ollama) is reachable
curl -s http://localhost:11434/v1/models | jq . | head

# Verify Tier 2 (gbrain/CRG) is indexed
gbrain query "frugality" 2>/dev/null || echo "gbrain not ready"
```

2. Check cost guard state:
```bash
# View current budget state
python3 << 'PYEOF'
from orchestrator.cost_guard import CostGuard
guard = CostGuard()
print("Daily budget state:", guard.snapshot())
PYEOF
```

3. Test escalation with real code:
```bash
# Run the integration test suite
pytest tests/test_frugality_router.py -v
```

**Expected behavior:**
- Tiers 0–2 probed and available (no cost)
- Tier 3+ only reachable via escalation_tier param + escalation_reason
- CostGuard blocks escalation when budget exceeded
- All timeouts enforced via background job (not `timeout N &&`)
- Escalation reasons logged for audit trail

## References

**Production Code (Perpetua-Tools):**
- **[`orchestrator/frugality_router.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/orchestrator/frugality_router.py)** — canonical tier routing (lines 17–255)
  - TIERS dict (0–6) and backend_by_tier map (lines 17–25, 176–180)
  - resolve_route() and _probe_tier_* functions
  - FrugalityPolicyError exception
- **[`orchestrator/cost_guard.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/orchestrator/cost_guard.py)** — CostGuard implementation (lines 16–90)
  - can_spend(), record_spend(), snapshot() methods
  - ALERT_RATIO = 0.80, daily_budget = $25.0
  - Auto-reset every 24h
- **[`orchestrator/contracts.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/orchestrator/contracts.py)** — ToolCallSpec and ResolvedRoute dataclasses

**Architecture Documentation:**
- [`orama-system/docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md`](../../../../docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md) § 2 — tier routing architecture contract
- [`orama-system/docs/v2/15-cost-guard-and-policy.md`](../../../../docs/v2/15-cost-guard-and-policy.md) — cost gate policy (archived)

**Session Logs:**
- [`orama-system/docs/LESSONS.md`](../../../../docs/LESSONS.md) — deployment incidents and tier fallback history
- [`docs/LESSONS.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/docs/LESSONS.md) — PT-specific observations

## Integration with CI/CD

Add to inference pipeline startup checks:

```bash
# .github/workflows/inference-startup.yml
- name: Verify tier routing
  run: |
    # Check Tier 1 (Ollama)
    curl -s http://localhost:11434/v1/models | grep -q "qwen3.5" || exit 1

    # Check Tier 3 (huggingface_free) endpoint reachable
    curl -s -m 5 https://api-inference.huggingface.co/status \
      -H "Content-Type: application/json" | head -1
```

Add frugality router tests:

```python
# tests/test_frugality_router.py (real tests — verified against Perpetua-Tools/tests/test_frugality_router.py)
class TestPrivacyCritical:
    def test_privacy_critical_prefers_local_tier_1(self, registry):
        route = resolve_route(
            ToolCallSpec(task_type="coding", privacy_critical=True),
            registry=registry,
        )
        assert route.tier == 1
        assert route.est_cost_usd == 0.0

    def test_privacy_critical_allows_tier_3_escalation(self):
        spec = ToolCallSpec(
            task_type="reasoning",
            privacy_critical=True,
            escalation_reason="hf free inference required",
        )
        route = resolve_route(spec, escalation_tier=3)
        assert route.tier == 3
        assert route.backend == "huggingface_free"

    def test_privacy_critical_forbids_tier_4_escalation(self):
        spec = ToolCallSpec(
            task_type="reasoning",
            privacy_critical=True,
            escalation_reason="needs brave search",
        )
        with pytest.raises(
            FrugalityPolicyError,
            match="privacy_critical=True forbids tier >= 4",
        ):
            resolve_route(spec, escalation_tier=4)
```

## Version & Consensus

- **Skill version:** 1.1.0 (production-aligned, 2026-07-04)
- **Consensus level:** 7/7 agents (highest agreement in Fable-5 council)
- **Foundation:** [`orchestrator/frugality_router.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/orchestrator/frugality_router.py) (v1.1, production)
- **Cost guard:** [`orchestrator/cost_guard.py`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/orchestrator/cost_guard.py) (v1.1, production)
- **Tier structure:** 7 tiers (0–6); probe-only (0–2) + escalation (3–6)
- **Hard requirements:**
  - Escalation to tier >= 3 requires `escalation_reason` parameter
  - Tiers 0–2 reached via probing, NOT escalation_tier parameter
  - Cost gates raise exceptions (never silent reroute)
  - Daily budget: $25.00 (settable via CostGuard.set_budget())
  - Daily budget alert at 80% (ALERT_RATIO)
- **Verified examples:** All production examples tested against real code (2026-07-04)

**IMPORTANT (2026-07-22 wiring-gap finding — see
`docs/plans/2026-07-22-p4-skill-trimming-p3-frugality-wiring.md`):** this
skill documents `frugality_router.py`'s design and API correctly, but as of
2026-07-22 `resolve_route()` has **zero real callers** anywhere in
`orchestrator/`. `ModelRegistry.route_task()` and
`src/perpetua_tools/orchestrator.py`'s `/orchestrate` endpoint both do their
own separate routing/privacy handling, neither of which calls into this
module. Treat this skill as accurate documentation of a built-but-unwired
system, not a description of what's enforced in production dispatch today.