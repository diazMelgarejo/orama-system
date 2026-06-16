# 37 — Manifest Cost-Tiering Pattern: Escalation Rules in `cost_guard.py`

> **Canonical home:** `orama-system/docs/v2/37-manifest-cost-tiering-pattern.md`
> **Status:** Proposed — approve before any implementation
> **Locks decision:** D20

---

## 1. Context

Manifest is a routing/cost-control framework with a **cost-tiering model**: requests
are classified into tiers (cheap/medium/expensive), each tier has a per-request
budget ceiling and a weekly/monthly envelope, and promotion to a higher tier requires
explicit escalation logic. The cost guard blocks promotion by default (fail-closed).

`cost_guard.py` in PT is currently HTTP-only — it lives in `fastapi_app.py:134` as
a middleware and is never imported by `supervisor.py`. It enforces a global budget
envelope but has no per-request tier classification and no escalation rules for
frontier models (Fable 5, Opus 4.8, cloud fallbacks).

The v2 distillation plan (Group B, item [3]) says: emulate Manifest's
**cost-tiering model** as an extension of `cost_guard.py` escalation rules —
inside PT (L2), never a Manifest installation.

---

## 2. Decision (D20)

**What to build:**
1. A `gate(spec: JobSpec) -> None` method on `CostGuard` that **raises** `CostBudgetExceeded`
   when the spec's model tier exceeds remaining budget — fail-closed, never silently degrades.
2. A `classify_tier(model_id: str) -> CostTier` function that maps model IDs to tiers.
3. Per-tier budget ceilings in `config/models.yml` under a `cost_tiers` key.
4. Wire `CostGuard.gate(spec)` into `supervisor.py:_run_worker` (`:401`) before `_dispatch`.

**What it is NOT:**
- Not a Manifest installation.
- Not a change to the HTTP middleware path (that remains).
- Not a budget tracker with persistence (budgets reset on restart in v2; v2.1 adds
  SQLite persistence).
- Not "4x Fable budget" as a target — the multiplier is a hypothesis to measure,
  not a default ceiling.

---

## 3. Tier schema

```yaml
# config/models.yml — new cost_tiers section
cost_tiers:
  local:             # Ollama, LM Studio local models
    models: ["qwen3.5:*", "qwen3.5-9b-*", "gemma-4-*"]
    per_request_ceiling_usd: 0.00    # free
    weekly_envelope_usd: 0.00
  cloud_standard:   # Sonnet 4.6, Haiku 4.5
    models: ["claude-sonnet-4-6", "claude-haiku-4-5*"]
    per_request_ceiling_usd: 0.10
    weekly_envelope_usd: 5.00
  cloud_frontier:   # Fable 5, Opus 4.8
    models: ["claude-fable-5", "claude-opus-4-8"]
    per_request_ceiling_usd: 2.00
    weekly_envelope_usd: 20.00
  cloud_escalation: # GPT-5.5, Grok, OpenRouter fallbacks
    models: []       # empty by default — must be explicitly populated
    per_request_ceiling_usd: 5.00
    weekly_envelope_usd: 10.00
    requires_explicit_escalation: true  # fails closed if not set in env
```

---

## 4. Integration: `supervisor.py` call site

```python
# supervisor.py:_run_worker (~line 401, before _dispatch call)
try:
    self._cost_guard.gate(spec)           # raises CostBudgetExceeded on deny
except CostBudgetExceeded as e:
    logger.warning("cost gate blocked: %s", e)
    raise HardwareAffinityError(str(e))   # reuse existing error pathway for now
```

`CostGuard` is currently HTTP-only. This wires it into the supervisor for the first
time. The HTTP middleware remains; the supervisor gate is additive.

---

## 5. Fail-closed contract

| Scenario | Behaviour |
|----------|-----------|
| Model ID not in any tier | `classify_tier` raises `UnknownModelTier` → `gate` raises `CostBudgetExceeded` |
| Weekly envelope exhausted | `gate` raises `CostBudgetExceeded` with remaining budget in message |
| `requires_explicit_escalation=true` tier, not set in env | `gate` raises immediately, regardless of budget |
| `CostGuard` fails to load config | Treat as "all tiers exhausted" — block all non-local models |

---

## 6. Alternatives rejected

| Alternative | Why rejected |
|-------------|-------------|
| Import Manifest | External dep; violates "emulation not importation" |
| Persist budgets to Redis | Redis is not in PT's dep graph; SQLite in v2.1 |
| "4x Fable budget" as default ceiling | Unproven for this workload — measure first |
| Keep cost guard HTTP-only | Supervisor can bypass HTTP path on internal calls — supervisor gate is the safe seam |

---

## 7. Consequences

**Positive:**
- Frontier model spend is fail-closed by default — no accidental cloud escalation.
- Tier classification feeds `score_candidates` (D19) `cost_tier` dimension directly.
- Per-request and weekly envelopes visible in `cost_guard.log`.

**Negative / constraints:**
- In-memory budget resets on restart — multi-day budget tracking deferred to v2.1.
- `UnknownModelTier` for new model IDs blocks dispatch until config is updated.

---

## 8. Open questions

- **Q1:** Should the `cloud_escalation` tier be blocked entirely (no models) or
  populated with a known-safe fallback? Recommend: empty by default, explicit opt-in.
- **Q2:** Keys via Keychain or `.env`? Canonical answer: Keychain primary, `.env`
  fallback for CI. Never committed to config files (existing policy).

---

## 9. Locked decision

**D20 — Manifest cost-tiering is a `gate(spec)` method on `CostGuard`, wired into `supervisor.py:_run_worker`, fail-closed (2026-06-17)**

PT emulates Manifest's cost-tiering as `CostGuard.gate(spec)` raising `CostBudgetExceeded`
on deny. Tiers defined in `config/models.yml`. `cloud_escalation` tier empty by default.
Wired at `supervisor.py:_run_worker` before `_dispatch`. In-memory budget in v2;
SQLite persistence in v2.1. Gate doc: this file.

---

## 10. Cross-references

- D17: `30-multi-llm-router-caching-batching-decorator.md` (decorator consumes `gate()` result implicitly via spec pre-check)
- D19: `36-clawrouter-scoring-pattern.md` (cost_tier dimension sourced from tier classification)
- `Perpetua-Tools/orchestrator/supervisor.py:401` — `_run_worker` integration point
- `Perpetua-Tools/config/models.yml` — `cost_tiers` config key
- `Perpetua-Tools/fastapi_app.py:134` — existing HTTP-only `CostGuard` (preserved, not replaced)
- `docs/distill-fable-5/implementation-plan.md` — Group B [3]
