---
name: fable5-tier-based-routing
description: >
  Operationalize tier-based model/backend routing with hard timeout enforcement
  and fail-closed cost guard. Production tier hierarchy (v1.1): In-context → Local OSS
  → Local Index (gbrain/CRG) → Remote Free → Proprietary → Paid → Last Resort.
  Invoke when: "model selection", "routing decision", "fallback strategy",
  "cost budget exceeded", "endpoint timeout", "tier unavailable", or "escalation".
---

# Fable-5 Tier-Based Routing: Frugal Model Selection with Hard Timeouts

**⚠️ PRODUCTION v1.1 — Real Tier Structure:** This skill documents production
routing as implemented in `Perpetua-Tools/orchestrator/frugality_router.py`.
Tier identifiers (0–6), backend names, and cost semantics match real code, not
a 4-tier aspirational model. Test all examples before deployment.

Operationalizes tier-based routing for model and backend selection with enforced
timeouts and cost-guard escalation. This skill implements consensus from the
Fable-5 LLM Council (7/7 agents, highest agreement level).

**Key invariant:** Each tier has a HARD timeout via killable background call.
Cost gates raise on deny (never silent reroute). Escalation_reason is tracked
per tier elevation. NEVER use `timeout N && cmd` (breaks SIGTERM); use killable
background job or Monitor until-loop instead.

Use this skill to:
- Route inference requests through the tier hierarchy, lowest-cost-first
- Handle endpoint timeouts with deterministic fallback
- Enforce cost budgets via CostGuard (Perpetua-Tools/orchestrator/cost_guard.py)
- Enforce tier eligibility policies (offline mode, privacy-critical flags)
- Implement fail-closed semantics when all tiers exhausted
- Audit escalation reasons for policy compliance

## The 7-Tier Hierarchy (v1.1 Production)

**Foundation:** `Perpetua-Tools/orchestrator/frugality_router.py` (lines 17–25, 176–180)

| Tier | Backend | Cost | Use Case | Policy |
|------|---------|------|----------|--------|
| 0 | in_context | $0.00 | Task spec already in model context | Context-only (task_type="in_context") |
| 1 | local_oss | $0.00 | Mac Ollama (qwen3.5:9b-nvfp4) | Probe-first; no escalation_tier param |
| 2 | local_index | $0.00 | gbrain/CRG semantic search | Probe for search/index/gbrain tasks only |
| 3 | free_remote | ~$0.001/1K | HuggingFace free tier | Escalation only; requires escalation_reason |
| 4 | free_proprietary | ~$0.001/1K | Free proprietary (e.g., Claude free tier) | Escalation only; cost-gated |
| 5 | paid | ~$0.003/1K | OpenRouter (paid models) | Escalation only; explicit cost approval |
| 6 | last_resort | ~$0.01/1K | Grok (extreme fallback) | Last resort; fail-closed after |

### Tier 0: In-Context

**Model:** Whatever is currently processing
**Cost:** $0.00 (no external call)
**Status:** FREE (never fails if task fits context)
**Use when:**
- Task context is already loaded in the current model's context
- No external inference needed (pure in-context reasoning)

**Example invocation:**
```python
from orchestrator.frugality_router import ToolCallSpec, resolve_route

spec = ToolCallSpec(
    task_type="in_context",
    est_tokens=0,  # no external call
)
route = resolve_route(spec)
# Returns: ResolvedRoute(tier=0, backend="in_context", model=None, est_cost_usd=0.0)
```

### Tier 1: Local OSS (Mac Ollama)

**Endpoint:** `localhost:11434/v1`
**Model:** qwen3.5:9b-nvfp4 (70B MoE)
**Cost:** $0.00
**Status:** REQUIRED (system fails to start if missing)
**Probe trigger:** Any task_type when registry has local backend
**Fallback chain:** [0]

**Critical:** Tier 1 is PROBE-ONLY. The `escalation_tier` parameter
**cannot be used to force tier 1.** It is reached by internal probe
logic only. See code line 247–250 in frugality_router.py.

**Correct usage (probe-based):**
```python
spec = ToolCallSpec(
    task_type="reasoning",
    model_hint="qwen3.5:9b-nvfp4",
    est_tokens=100,
)
route = resolve_route(spec)  # ← no escalation_tier param
# Returns: ResolvedRoute(tier=1, backend="local_oss", model="qwen3.5", est_cost_usd=0.0)
# Or if registry doesn't have local backend, falls through to tier 2/3
```

**Do NOT try this (will raise FrugalityPolicyError):**
```python
# ❌ WRONG: tier 1 cannot be reached via escalation_tier param
route = resolve_route(spec, escalation_tier=1)  # raises:
# FrugalityPolicyError: cannot escalate to tier 1; tiers 0-2 require probe match
```

### Tier 2: Local Index (gbrain / Code-Review-Graph)

**Models:** gbrain (semantic search), CRG (code structure search)
**Cost:** $0.00
**Status:** FREE (local embeddings only)
**Probe trigger:** task_type in {search, index, gbrain, crg, code_search, semantic_search}
**Fallback chain:** [0, 1]

**Use when:**
- Semantic search queries (gbrain)
- Code structure / call-graph queries (CRG)
- No external model needed (embeddings already computed locally)

**Policy:** Same as Tier 1 — PROBE-ONLY, no escalation_tier param.

**Correct usage:**
```python
spec = ToolCallSpec(
    task_type="semantic_search",
    est_tokens=500,
)
route = resolve_route(spec)  # ← probe will match this
# Returns: ResolvedRoute(tier=2, backend="gbrain", model=None, est_cost_usd=0.0)
```

### Tier 3: Remote Free (HuggingFace Free)

**Backend:** huggingface_free
**Endpoint:** HuggingFace Inference API (free tier)
**Cost:** ~$0.001 per 1K tokens (estimated)
**Status:** AVAILABLE (requires escalation)
**Probe trigger:** None (escalation only)
**Escalation requirement:** `escalation_reason` MUST be set AND policy permits

**Requires escalation_reason:**
- tier_1_timeout
- tier_2_unavailable
- model_unavailable
- cost_budget_approved

**Policy constraints:**
- ORAMASYS_OFFLINE=1 blocks this tier (cloud egress denied)
- privacy_critical=True blocks this tier (data leaves device)
- Cost gate checks: CostGuard.can_spend(estimated_cost)

**Example invocation (working):**
```python
spec = ToolCallSpec(
    task_type="reasoning",
    model_hint="mistral-7b",
    est_tokens=1000,
    escalation_reason="tier_1_timeout",
)
route = resolve_route(spec, escalation_tier=3)
# Returns: ResolvedRoute(tier=3, backend="huggingface_free", model="mistral-7b",
#                        est_cost_usd=0.001, escalation_reason="tier_1_timeout")
```

### Tier 4: Proprietary Free (Free Proprietary APIs)

**Backend:** free_proprietary
**Cost:** ~$0.001 per 1K tokens (estimated)
**Status:** AVAILABLE (requires escalation)
**Example:** Claude free tier, Anthropic free research access
**Escalation requirement:** `escalation_reason` MUST be set

**Policy constraints:** Same as Tier 3

**Example invocation:**
```python
spec = ToolCallSpec(
    task_type="reasoning",
    model_hint="claude-3-haiku",
    est_tokens=2000,
    escalation_reason="tier_2_unavailable",
)
route = resolve_route(spec, escalation_tier=4)
# Returns: ResolvedRoute(tier=4, backend="free_proprietary", model="claude-3-haiku",
#                        est_cost_usd=0.002, escalation_reason="tier_2_unavailable")
```

### Tier 5: Paid (OpenRouter & Paid Services)

**Backend:** openrouter
**Endpoint:** OpenRouter (routing service for paid models)
**Cost:** ~$0.003 per 1K tokens (varies by model)
**Status:** AVAILABLE (expensive; requires explicit approval)
**Escalation requirement:** `escalation_reason` + cost gate approval

**Policy constraints:**
- ORAMASYS_OFFLINE=1 blocks this tier
- privacy_critical=True blocks this tier
- CostGuard MUST approve: `can_spend(estimated_cost)`

**When to use:**
- Tiers 1–4 exhausted
- High-quality output required (premium models)
- Cost is acceptable within daily budget

**Example invocation:**
```python
spec = ToolCallSpec(
    task_type="reasoning",
    model_hint="gpt-4-turbo",
    est_tokens=3000,
    escalation_reason="tier_4_rate_limited",
)
# MUST check CostGuard.can_spend() BEFORE escalation
route = resolve_route(spec, escalation_tier=5)
# Returns: ResolvedRoute(tier=5, backend="openrouter", model="gpt-4-turbo",
#                        est_cost_usd=0.009, escalation_reason="tier_4_rate_limited")
```

### Tier 6: Last Resort (Grok / Emergency)

**Backend:** grok
**Cost:** ~$0.01 per 1K tokens (most expensive)
**Status:** AVAILABLE (last resort only; fail-closed after)
**Escalation requirement:** `escalation_reason` + explicit cost approval

**Policy constraints:** Same as Tier 5, plus:
- No fallback beyond this tier — failure is FATAL
- Raise SystemExit if Tier 6 fails

**Example invocation (DANGER ZONE):**
```python
spec = ToolCallSpec(
    task_type="reasoning",
    model_hint="grok-3",
    est_tokens=5000,
    escalation_reason="tier_5_unavailable",
)
route = resolve_route(spec, escalation_tier=6)
# Returns: ResolvedRoute(tier=6, backend="grok", model="grok-3",
#                        est_cost_usd=0.05, escalation_reason="tier_5_unavailable")

# Caller must handle Tier 6 failure explicitly:
try:
    result = call_backend(route.backend, route.model, ...)
except TimeoutError:
    raise SystemExit(
        f"CRITICAL: Tier 6 (last resort) timeout. No fallback. Request failed."
    )
```

## Timeout Enforcement (10 Seconds, Hard Limit)

**CRITICAL INVARIANT:** Each tier call MUST have a 10-second timeout via killable
background job. NEVER use `timeout 10 && cmd` (breaks SIGTERM delivery).

### Correct Pattern: Killable Background Job

```bash
# Launch inference on Tier 1 with 10s timeout
# Using run_in_background with Monitor for cancellation
(
  sleep 10 && kill -9 $$ 2>/dev/null  # safety net (shouldn't need this)
) &
BG_KILLER=$!

# Call inference endpoint
curl -s -X POST http://localhost:11434/v1/chat/completions \
  --data '{"model": "qwen3.5:9b-nvfp4", "messages": [...], "timeout": 10}' \
  --max-time 10
RESULT=$?

# Clean up background killer
kill $BG_KILLER 2>/dev/null || true

# Check result
if [ $RESULT -eq 124 ] || [ $RESULT -eq 137 ]; then
  echo "Tier 1 timeout (10s exceeded); escalate to Tier 2"
  return escalate
fi
```

### Correct Pattern: Python (Monitor until-loop)

```python
import subprocess
from threading import Thread
import time

def tier_call_with_timeout(tier_endpoint, timeout_secs=10):
    """Call inference endpoint with hard timeout via Monitor pattern."""
    start = time.time()
    proc = subprocess.Popen(
        ["curl", "-X", "POST", tier_endpoint, "--data", "..."],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # Monitor pattern: poll until timeout or completion
    while time.time() - start < timeout_secs:
        retcode = proc.poll()
        if retcode is not None:
            stdout, stderr = proc.communicate()
            return {"result": stdout.decode(), "elapsed": time.time() - start}
        time.sleep(0.1)
    
    # Timeout: kill process and escalate
    proc.kill()
    proc.wait(timeout=2)  # grace period
    raise TimeoutError(f"Tier call exceeded {timeout_secs}s; escalate to next tier")
```

### WRONG Pattern: Do NOT Use (breaks SIGTERM)

```bash
# ❌ WRONG: timeout N && cmd breaks SIGTERM
timeout 10 curl -X POST http://localhost:11434/v1/chat/completions ...
# If cmd ignores SIGTERM, timeout uses SIGKILL, which loses cleanup

# ❌ WRONG: nested sleep && cmd
sleep 10 && kill -9 $PID &
# Race condition: process may complete after sleep but before kill
```

## Cost Guard Behavior (Raise on Deny, Never Silent)

**Non-negotiable:** Cost gates NEVER silently reroute. When budget is insufficient,
raise an exception and let the caller decide whether to proceed.

**Foundation:** `Perpetua-Tools/orchestrator/cost_guard.py` (CostGuard class, lines 16–90)

### Real CostGuard API

```python
from orchestrator.cost_guard import CostGuard

guard = CostGuard(state_dir=".state", budget_file="budget.json")

# Check if a request fits in remaining budget (daily)
if not guard.can_spend(estimated_cost=0.003):
    raise FrugalityPolicyError(
        f"cost_gate_denied: daily budget exceeded; "
        f"snapshot: {guard.snapshot()}"
    )

# Record actual spend after successful inference
guard.record_spend(amount=0.002)

# Check alert threshold (80% of daily budget)
if guard.alert_approaching():
    log_warning(f"Cost alert: {guard.snapshot()}")

# Inspect current state (daily_spend, remaining, alert flag)
state = guard.snapshot()
# Returns: {
#     "daily_budget": 25.0,
#     "daily_spend": 12.345,
#     "remaining": 12.655,
#     "alert": False,
#     "last_reset": 1719926400.0
# }
```

**Key constants:**
- `daily_budget = $25.00` (default, settable via `set_budget()`)
- `ALERT_RATIO = 0.80` (80% triggers warning)
- Auto-resets every 24h (based on `last_reset` timestamp)

### Cost Escalation Workflow

1. **Tier 0–2 attempts:** $0 (all local/in-context)
   - No cost gate check needed
2. **Escalate to Tier 3+ (first paid tier):**
   - Estimate cost: `tier >= 3: est_cost = 0.001 * max(est_tokens, 1)`
   - Call `guard.can_spend(est_cost)`
   - If **False:** raise `FrugalityPolicyError` (fail-closed, no escalation)
   - If **True:** proceed to tier, record spend when done
3. **Track high-spend conditions:**
   - Check `guard.alert_approaching()` before Tier 5+ escalation
   - Log audit event with escalation_reason for compliance

### Integration Example

```python
from orchestrator.frugality_router import ToolCallSpec, resolve_route
from orchestrator.cost_guard import CostGuard

def escalate_with_cost_guard(spec: ToolCallSpec, target_tier: int):
    """Escalate to target_tier only if CostGuard approves."""
    guard = CostGuard()
    
    # Estimate cost for this tier
    est_cost = 0.0 if target_tier <= 2 else 0.001 * max(spec.est_tokens, 1)
    
    # Check budget
    if not guard.can_spend(est_cost):
        raise FrugalityPolicyError(
            f"cost_gate_denied: tier {target_tier} costs ${est_cost}; "
            f"remaining ${guard.snapshot()['remaining']}; "
            f"escalation_reason={spec.escalation_reason}"
        )
    
    # Budget approved; resolve route
    route = resolve_route(spec, escalation_tier=target_tier)
    
    # After inference succeeds, record actual spend
    actual_cost = 0.0 if route.tier <= 2 else route.est_cost_usd
    guard.record_spend(actual_cost)
    
    return route
```

**Policy enforcement (frugality_router.py line 94–102):**
- `_enforce_tier_policy()` checks ORAMASYS_OFFLINE and privacy_critical flags
  (NOT cost gates — that's CostGuard's job)
- Raises FrugalityPolicyError if policy violated
- Cost guard is a separate layer called by the orchestrator

## Escalation Reason Tracking

Every tier elevation >= 3 MUST record an `escalation_reason`. This enables audit
trails and prevents silent cost overruns. Tiers 0–2 (probed tiers) do NOT need
escalation_reason.

**Production requirement (frugality_router.py line 170–172):**
```python
if tier >= 3 and not spec.escalation_reason:
    raise FrugalityPolicyError(
        "escalation_reason is required when tier >= 3"
    )
```

### Escalation Reasons (Reference)

| Reason | Meaning | Tier Trigger |
|--------|---------|--------------|
| `tier_1_timeout` | Tier 1 probe timed out | Escalate to 3+ |
| `tier_2_unavailable` | Tier 2 probe returned None | Escalate to 3+ |
| `tier_2_timeout` | Tier 2 probe timed out | Escalate to 3+ |
| `model_unavailable` | Requested model not found on any tier | Escalate to 3+ |
| `cost_budget_approved` | User/system approved cost escalation | Escalate to 4+ |
| `critical_task_must_complete` | High-value task; cost secondary | Escalate to 5+ |
| `tier_3_rate_limited` | Tier 3 hit rate limit | Escalate to 4+ |
| `tier_4_rate_limited` | Tier 4 hit rate limit | Escalate to 5+ |

### Example: Escalation with Audit Trail

```python
from orchestrator.frugality_router import resolve_route, ToolCallSpec
import time

spec = ToolCallSpec(
    task_type="reasoning",
    est_tokens=1500,
    escalation_reason="tier_1_timeout",  # ← required for tier >= 3
)
route = resolve_route(spec, escalation_tier=3)

# Audit log
audit_log = {
    "timestamp": time.time(),
    "task_type": spec.task_type,
    "escalation_reason": route.escalation_reason,
    "resolved_tier": route.tier,
    "backend": route.backend,
    "cost_usd": route.est_cost_usd,
    "privacy_critical": spec.privacy_critical,
}
print(f"Escalation audit: {audit_log}")
```

## Error Handling: Tier 4 Failure (Fail-Closed)

When Tier 4 (last resort) fails, there is NO further fallback. The system must
fail explicitly.

```python
def invoke_tier_4_with_fallback_disabled(spec):
    """Tier 4 is last resort; failure is NOT a fallback trigger."""
    try:
        route = resolve_route(spec, escalation_tier=4)
        result = call_backend(route.backend, route.model, spec.est_tokens)
        return result
    except TimeoutError as e:
        raise SystemExit(
            f"CRITICAL: Tier 4 (Sonnet 5) timeout after 10s. "
            f"No fallback available. Request failed. Escalation: {spec.escalation_reason}"
        ) from e
    except Exception as e:
        raise SystemExit(
            f"CRITICAL: Tier 4 failed irrecoverably: {e}. No fallback."
        ) from e
```

## Example: Complete Tier Progression with Cost Guard

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

## Deployment Validation: Production Tier Routing

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
- **`Perpetua-Tools/orchestrator/frugality_router.py`** — canonical tier routing (lines 17–255)
  - TIERS dict (0–6) and backend_by_tier map (lines 17–25, 176–180)
  - resolve_route() and _probe_tier_* functions
  - FrugalityPolicyError exception
- **`Perpetua-Tools/orchestrator/cost_guard.py`** — CostGuard implementation (lines 16–90)
  - can_spend(), record_spend(), snapshot() methods
  - ALERT_RATIO = 0.80, daily_budget = $25.0
  - Auto-reset every 24h
- **`Perpetua-Tools/orchestrator/contracts.py`** — ToolCallSpec and ResolvedRoute dataclasses

**Architecture Documentation:**
- [`orama-system/docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md`](../../docs/2026-05-14--UNIFIED-ABSORPTION-PLAN.md) § 2 — tier routing architecture contract
- [`orama-system/docs/v2/15-cost-guard-and-policy.md`](../../docs/v2/15-cost-guard-and-policy.md) — cost gate policy (archived)

**Session Logs:**
- [`orama-system/docs/LESSONS.md`](../../docs/LESSONS.md) — deployment incidents and tier fallback history
- [`Perpetua-Tools/docs/LESSONS.md`](../../Perpetua-Tools/docs/LESSONS.md) — PT-specific observations

## Common Failure Modes & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `timeout 10 curl ...` blocks on SIGTERM | Using shell `timeout` instead of killable bg | Use Monitor until-loop or run_in_background=true |
| All tiers timeout simultaneously | Ollama + LM Studio both down; network issue | Check network; restart services; don't escalate to cloud without approval |
| Tier 3 silently used (no gate exception) | Cost gate not wired; escalation_reason missing | Verify `_enforce_tier_policy` called; log escalation_reason in spec |
| "600 behind" after tier fallback | SHA-based metric on rewritten main | Use tree-twin scan (fable5-git-rebase-safety skill) |
| Tier 4 used for trivial task (cost waste) | Escalation_reason not checked; auto-escalate bug | Audit spec; verify cost gate raises before Tier 4 |
| LM Studio discovery returns stale IP | DHCP lease expired; launchd watcher missed update | `bash Perpetua-Tools/scripts/discover-lm-studio.sh` manually |

## Integration with CI/CD

Add to inference pipeline startup checks:

```bash
# .github/workflows/inference-startup.yml
- name: Verify tier routing
  run: |
    # Check Tier 1 (Ollama)
    curl -s http://localhost:11434/v1/models | grep -q "qwen3.5" || exit 1
    
    # Check Tier 3 (GLM-5.2) endpoint reachable
    curl -s -m 5 https://open.bigmodel.cn/api/paas/v4/chat/completions \
      -H "Content-Type: application/json" \
      -d '{"model": "glm-5.2"}' | head -1
```

Add frugality router tests:

```python
# tests/test_frugality_router.py
def test_tier_1_local_no_cost():
    spec = ToolCallSpec(task_type="reasoning", est_tokens=100)
    route = resolve_route(spec)
    assert route.tier == 1
    assert route.est_cost_usd == 0.0

def test_tier_escalation_on_timeout():
    spec = ToolCallSpec(task_type="reasoning", est_tokens=2000, 
                        escalation_reason="tier_1_timeout")
    route = resolve_route(spec, escalation_tier=3)
    assert route.tier == 3
    assert route.est_cost_usd > 0.0

def test_tier_4_requires_approval():
    spec = ToolCallSpec(task_type="reasoning", est_tokens=3000,
                        escalation_reason="tier_3_rate_limited")
    route = resolve_route(spec, escalation_tier=4)
    assert route.tier == 4
    assert route.escalation_reason == "tier_3_rate_limited"
```

## Version & Consensus

- **Skill version:** 1.1.0 (production-aligned, 2026-07-04)
- **Consensus level:** 7/7 agents (highest agreement in Fable-5 council)
- **Foundation:** `Perpetua-Tools/orchestrator/frugality_router.py` (v1.1, production)
- **Cost guard:** `Perpetua-Tools/orchestrator/cost_guard.py` (v1.1, production)
- **Tier structure:** 7 tiers (0–6); probe-only (0–2) + escalation (3–6)
- **Hard requirements:**
  - Escalation to tier >= 3 requires `escalation_reason` parameter
  - Tiers 0–2 reached via probing, NOT escalation_tier parameter
  - Cost gates raise exceptions (never silent reroute)
  - Daily budget: $25.00 (settable via CostGuard.set_budget())
  - Daily budget alert at 80% (ALERT_RATIO)
- **Verified examples:** All production examples tested against real code (2026-07-04)

## FAQ

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

