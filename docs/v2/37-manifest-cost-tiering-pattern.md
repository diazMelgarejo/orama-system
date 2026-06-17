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
1. A `gate(spec: JobSpec) -> None` method on `CostGuard` that **raises** `BudgetExceededError`
   or `EscalationDeniedError` when the spec's model tier exceeds remaining budget or
   requires escalation that has not been granted — fail-closed, never silently degrades.
2. A `classify_tier(model_id: str) -> CostTier` function that maps model IDs to tiers.
3. Per-tier budget ceilings in `config/models.yml` under a `cost_tiers` key.
4. **Extend `record_spend` to accept granular token/cost data (binding):** The existing
   `record_spend` (`:74`) is extended to `record_spend(model_id: str, tokens_in: int,
   tokens_out: int, cost_usd: float) -> None`. This is called by **D17's decorator** after
   every real (non-cached) `_inner` dispatch with the provider-reported values. D20 stores
   these per-model, per-request — enabling D19's `cost_tier` scoring and future spend dashboards.
   This is the **canonical home for token/cost data in PT (L2)** — orama (L3) never computes
   or stores these values directly.
5. A `usage_snapshot(model_id: str | None = None) -> dict` accessor that returns
   `{tokens_in, tokens_out, cost_usd, request_count}` for a model (or all models if None).
   This feeds D19's `cost_tier` dimension once D20 is approved.
6. **Call site:** `gate(spec)` is called inside **D17's decorator `__call__`** — it is the
   sole call site on the dispatch path. D20 defines the method contract; D17 is the wiring.
   D20 does **NOT** add a second wiring at `_run_worker:401` — doing so would cause double-
   counted spend and double-blocked budget.

**Exception naming:** Use `BudgetExceededError` (budget ceiling hit) and
`EscalationDeniedError` (cloud escalation not enabled). These match D17's pseudocode.
`CostBudgetExceeded` is deprecated — do not use it in new code.

**CostGuard singleton:** D20 extends the `CostGuard` instance constructed at
`fastapi_app.py:134`. The decorator receives this instance via injection (see D17 §5).
**Never construct a second `CostGuard` inside `_dispatch`, the decorator, or `_run_worker`.**

**What it is NOT:**
- Not a Manifest installation.
- Not a change to the HTTP middleware path (that remains as an independent guard).
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
  cloud_escalation: # GPT-5.5, Grok, OpenRouter fallbacks; ALSO the fallback tier for
                    # any model ID not matched by local/cloud_standard/cloud_frontier.
    models: ["gpt-5.5*", "grok*", "openrouter*"]
    per_request_ceiling_usd: 5.00
    weekly_envelope_usd: 10.00
    requires_explicit_escalation: true  # gate: env var ORAMA_CLOUD_ESCALATION_ENABLED=1 required
```

> **`cloud_escalation` default-deny mechanism:** The `requires_explicit_escalation: true` flag
> is checked by `gate()` against env var `ORAMA_CLOUD_ESCALATION_ENABLED`. The value MUST be
> the literal string `"1"` — no other truthy value is accepted. If the env var is absent or any
> other value, `gate()` raises `EscalationDeniedError` immediately. The `models:` list uses
> explicit patterns (not empty `[]`) so that known escalation models are correctly classified;
> any model ID **not matched by any tier's pattern** is classified as `cloud_escalation` by
> default (unknown = most-restrictive tier). This ensures new/unrecognized model IDs are
> blocked, not passed through.

---

## 4. Integration: call site is D17's decorator, not `_run_worker`

The sole dispatch-path call site for `gate(spec)` is **D17's decorator `__call__`**
(see D17 §2 pseudocode). D20 defines the method contract; D17 is the wiring.

```python
# perpetua/core/multi_llm_router.py — D17 decorator (call site for gate())
async def __call__(self, spec) -> dict:
    # cache read path (§3.5 read-path fail-closed) ...
    if self._is_cacheable(spec):
        ...
    # cost gate — D20 method, D17 call site
    self._cost_guard.gate(spec)    # raises BudgetExceededError / EscalationDeniedError
    result = await self._inner(spec)
    ...
```

`CostGuard` is currently HTTP-only (`fastapi_app.py:134`). D17's decorator is the
**first and only** place it is wired into the dispatch path. The HTTP middleware
remains as an independent guard; the decorator gate is additive and is the
**authoritative dispatch-path gate**. Do NOT add a second `gate()` call at
`_run_worker:401` — the decorator already sits above `_run_worker` and a second
call would double-count spend and double-block budget.

---

## 5. Fail-closed contract

| Scenario | Behaviour |
|----------|-----------|
| Model ID not in any tier pattern | `classify_tier` classifies as `cloud_escalation` (unknown = most-restrictive); `gate` raises `EscalationDeniedError` unless `ORAMA_CLOUD_ESCALATION_ENABLED=1` |
| Weekly envelope exhausted | `gate` raises `BudgetExceededError` with remaining budget in message (no raw prompt in message) |
| `requires_explicit_escalation=true` tier, `ORAMA_CLOUD_ESCALATION_ENABLED` absent or not `"1"` | `gate` raises `EscalationDeniedError` immediately, regardless of budget |
| `CostGuard` fails to load `config/models.yml` | `gate()` **catches the load error internally** and re-raises as `BudgetExceededError("config unavailable")`. This blocks ALL dispatches including local models (true fail-closed — if we can't read tiers, we can't safely allow any tier). To avoid blocking local work on config failures, the `local` tier pattern list may be hardcoded as a fallback constant in `cost_guard.py` itself. |
| Gossip payload built from spec | Any `_record_to_gossip` or similar method MUST redact `spec.prompt` and other PII **before** building the payload. Never include raw prompt content in any log line, event, or gossip message — this is the same requirement as D17 §3.6. |

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
- Unknown model IDs are classified as `cloud_escalation` (blocked by default) — config update needed to add new models to the correct tier.
- D18 trace artifacts in orama (`docs/distill-fable-5/traces/`) are **read-only methodology data** — they are NOT a budget ledger, NOT a spend record, and MUST NOT be read by D20 budget enforcement logic. Budget state lives exclusively in PT `CostGuard` (L2).

---

## 8. Open questions

- **Q1:** Should the `cloud_escalation` tier be blocked entirely (no models) or
  populated with a known-safe fallback? Recommend: empty by default, explicit opt-in.
- **Q2:** Keys via Keychain or `.env`? Canonical answer: Keychain primary, `.env`
  fallback for CI. Never committed to config files (existing policy).

---

## 9. Locked decision

**D20 — Manifest cost-tiering is a `gate(spec)` + extended `record_spend` on `CostGuard`, called by D17's decorator, fail-closed (2026-06-17)**

PT emulates Manifest's cost-tiering as `CostGuard.gate(spec)` raising `BudgetExceededError`
or `EscalationDeniedError` on deny. Tiers defined in `config/models.yml`; unknown models
default to `cloud_escalation` (blocked). Cloud escalation requires env var
`ORAMA_CLOUD_ESCALATION_ENABLED=1` (literal). Call site is D17's decorator `__call__` —
never `_run_worker:401`. CostGuard singleton from `fastapi_app.py:134`, injected via D17.
`record_spend(model_id, tokens_in, tokens_out, cost_usd)` extended for granular per-call
tracking; `usage_snapshot(model_id)` exposes per-model spend for D19 `cost_tier` scoring.
Token/cost data is **canonical in PT (L2)** — orama L3 never computes or stores it directly.
In-memory budget in v2; SQLite persistence in v2.1. Gate doc: this file.

---

## 10. Cross-references

- D17: `30-multi-llm-router-caching-batching-decorator.md` — `gate()` is **called inside D17's decorator `__call__`** (the sole dispatch-path call site); D20 defines the method; D17 is the wiring
- D19: `36-clawrouter-scoring-pattern.md` — `cost_tier` dimension deferred until D20 approved; `classify_tier()` will feed D19 once both ADRs are approved
- `Perpetua-Tools/orchestrator/cost_guard.py` — implementation target for `gate()`, `classify_tier()`, `BudgetExceededError`, `EscalationDeniedError`
- `Perpetua-Tools/fastapi_app.py:134` — `CostGuard` singleton construction site (inject, never reconstruct)
- `Perpetua-Tools/config/models.yml` — `cost_tiers` config key
- `docs/distill-fable-5/implementation-plan.md` — Group B [3]
