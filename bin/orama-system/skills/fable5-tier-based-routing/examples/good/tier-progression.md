# Golden Path: Complete Tier Progression with Cost Guard

> Extracted from `fable5-tier-based-routing/SKILL.md` during the 2026-07-22
> skill-trimming pass.

Scenario: User requests complex reasoning task (3000 tokens), cost-conscious.

**How to use the real API:**

```python
from orchestrator.frugality_router import ToolCallSpec, resolve_route
from orchestrator.cost_guard import CostGuard
import time

def route_reasoning_request(tokens=3000, privacy_critical=False):
    """Route request through tier hierarchy with cost tracking."""

    guard = CostGuard()
    spec = ToolCallSpec(
        task_type="reasoning",
        est_tokens=tokens,
        privacy_critical=privacy_critical,
    )

    # Try probed tiers first (0-2, always free)
    try:
        route = resolve_route(spec)  # No escalation_tier param!
        print(f"Probed tier {route.tier}: {route.backend} (free)")
        result = call_backend_with_timeout(route.backend, route.model, timeout_secs=10)
        print(f"Success on tier {route.tier}")
        return result
    except TimeoutError:
        print(f"Tier {route.tier} timed out; escalating...")
    except Exception as e:
        print(f"Tier probe failed: {e}; escalating...")

    # Probed tiers failed. Try escalation tiers (3+)
    escalation_tiers = [3, 4, 5, 6]
    for tier in escalation_tiers:
        try:
            reason = f"tier_{tier-1}_unavailable"

            # Check cost gate BEFORE escalation
            est_cost = 0.001 * max(tokens, 1)  # ~$0.001/1K
            if not guard.can_spend(est_cost):
                print(f"Cost gate denied for tier {tier}: "
                      f"${est_cost:.3f} exceeds remaining ${guard.snapshot()['remaining']:.3f}")
                if tier == escalation_tiers[-1]:
                    raise SystemExit("All tiers exhausted (cost + availability)")
                continue

            # Budget approved; escalate
            spec = ToolCallSpec(
                task_type="reasoning",
                est_tokens=tokens,
                privacy_critical=privacy_critical,
                escalation_reason=reason,
            )
            route = resolve_route(spec, escalation_tier=tier)
            print(f"Escalated to tier {route.tier} ({route.backend}); est_cost=${route.est_cost_usd:.3f}")

            # Call backend with 10s timeout
            result = call_backend_with_timeout(route.backend, route.model, timeout_secs=10)
            guard.record_spend(route.est_cost_usd)
            print(f"Success on tier {route.tier}")
            return result

        except TimeoutError:
            print(f"Tier {tier} timed out")
            if tier == escalation_tiers[-1]:
                raise SystemExit("CRITICAL: Tier 6 (last resort) timeout. No fallback.")
        except Exception as e:
            print(f"Tier {tier} failed: {e}")
            if tier == escalation_tiers[-1]:
                raise SystemExit(f"CRITICAL: Tier 6 failed irrecoverably: {e}")

# Call with tracking
try:
    result = route_reasoning_request(tokens=3000, privacy_critical=False)
except SystemExit as e:
    print(f"Fatal error: {e}")
```

**Key points in this example:**

1. First call `resolve_route(spec)` with NO escalation_tier — lets probing happen
2. If probes fail, loop through escalation_tiers = [3, 4, 5, 6]
3. **Before each escalation**, check `guard.can_spend(est_cost)`
4. If gate denies AND this is the last tier, FAIL LOUDLY (no more fallbacks)
5. Record actual spend after successful call: `guard.record_spend(route.est_cost_usd)`
6. Each escalation requires an escalation_reason (e.g., "tier_2_unavailable")
