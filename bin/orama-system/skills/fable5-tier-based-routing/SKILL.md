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

**⚠️ WIRING GAP (found 2026-07-22, see `references/deployment-validation.md`
bottom):** `resolve_route()` has zero real callers in `orchestrator/` today —
`ModelRegistry.route_task()` and `src/perpetua_tools/orchestrator.py` both do
their own separate routing. Documentation of a built-but-unwired system, not
enforced production behavior, until that gap closes.

## Load First (reference detail — read on demand, not every invocation)

- [`references/deployment-validation.md`](references/deployment-validation.md) — production status, verification, CI/CD, version/consensus
- [`references/failure-modes.md`](references/failure-modes.md) — symptom → cause → fix
- [`references/faq.md`](references/faq.md) — escalation, cost gate, timeouts
- [`examples/good/tier-progression.md`](examples/good/tier-progression.md) — golden-path tier-progression example

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
| 3 | free_remote | $0.001/token (flat) | HuggingFace free tier | Escalation only; requires escalation_reason |
| 4 | free_proprietary | $0.001/token (flat) | Free proprietary (e.g., Claude free tier) | Escalation only; cost-gated |
| 5 | paid | $0.001/token (flat) | OpenRouter (paid models) | Escalation only; explicit cost approval |
| 6 | last_resort | $0.001/token (flat) | Grok (extreme fallback) | Last resort; fail-closed after |

**Note on cost rate:** `_escalation_route()` (frugality_router.py line 175) uses
a single flat formula for every escalation tier — `est_cost_usd = 0.001 * max(est_tokens, 1)`.
There is **no per-tier rate differentiation** in the current code (tier 5/6 are
not more expensive per-token than tier 3/4 despite backend naming implying
otherwise). At $0.001/token this is $1.00 per 1K tokens, not $0.001 per 1K
tokens — do not confuse the two when estimating cost.

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

`_probe_tier_1()` calls `resolve_backend_for_spec(registry, ...)`, which needs a
real `BackendRegistry` populated with an **online** backend — passing
`registry={}` (or omitting `registry` entirely, which defaults to `None`)
short-circuits `_probe_tier_1` back to `None` (or raises `AttributeError` from
`registry.online()` if the object isn't a real `BackendRegistry`), so the probe
never reaches tier 1 and the example raises `FrugalityPolicyError` when it
falls through to `resolve_route`'s implicit tier-3 escalation with no
`escalation_reason` set. Populate the registry via `autodetect()` (or hand-roll
one with a known-online `Backend`) before calling `resolve_route`:

```python
import asyncio
from orchestrator.frugality_router import ToolCallSpec, resolve_route
from perpetua.discovery.registry import BackendRegistry

async def get_registry() -> BackendRegistry:
    registry = BackendRegistry()
    await registry.autodetect()  # probes ollama-local / lmstudio-mac / lmstudio-win
    return registry

registry = asyncio.run(get_registry())

spec = ToolCallSpec(
    task_type="reasoning",
    model_hint="qwen3.5:9b-nvfp4",
    est_tokens=100,
)
route = resolve_route(spec, registry=registry)  # ← registry required; no escalation_tier param
# Returns: ResolvedRoute(tier=1, backend="ollama-local", model="qwen3.5:9b-nvfp4", est_cost_usd=0.0)
# Live-tested 2026-07-04: tier=1, backend=ollama-local, model=qwen3.5:9b-nvfp4, cost=$0.0000
# If registry has no online local backend, PolicyUnavailable is caught internally
# and the probe falls through to tier 2/3.
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
**Cost:** $0.001/token, flat (`0.001 * max(est_tokens, 1)`) — $1.00 per 1K tokens
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
#                        est_cost_usd=1.0, escalation_reason="tier_1_timeout")
# Cost check: est_tokens (1000) × 0.001 = $1.00
```

### Tier 4: Proprietary Free (Free Proprietary APIs)

**Backend:** free_proprietary
**Cost:** $0.001/token, flat (`0.001 * max(est_tokens, 1)`) — $1.00 per 1K tokens
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
#                        est_cost_usd=2.0, escalation_reason="tier_2_unavailable")
# Cost check: est_tokens (2000) × 0.001 = $2.00
```

### Tier 5: Paid (OpenRouter & Paid Services)

**Backend:** openrouter
**Endpoint:** OpenRouter (routing service for paid models)
**Cost:** $0.001/token, flat (`0.001 * max(est_tokens, 1)`) — $1.00 per 1K tokens
(same flat formula as tiers 3–4; the "varies by model" framing does not apply
to the current `_escalation_route()` implementation)
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
#                        est_cost_usd=3.0, escalation_reason="tier_4_rate_limited")
# Cost check: est_tokens (3000) × 0.001 = $3.00
```

### Tier 6: Last Resort (Grok / Emergency)

**Backend:** grok
**Cost:** $0.001/token, flat (`0.001 * max(est_tokens, 1)`) — $1.00 per 1K tokens
(same flat formula as tiers 3–5; the "most expensive" framing does not apply
to the current `_escalation_route()` implementation)
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
#                        est_cost_usd=5.0, escalation_reason="tier_5_unavailable")
# Cost check: est_tokens (5000) × 0.001 = $5.00

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

Same invariant as the bash pattern above, for callers already in a Python
process: [`references/python-timeout-pattern.md`](references/python-timeout-pattern.md).

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

---

## Further Reading

Golden-path example, deployment validation, CI/CD, failure modes, and FAQ
moved to `references/`/`examples/` (2026-07-22 trim) — see "Load First" above.
