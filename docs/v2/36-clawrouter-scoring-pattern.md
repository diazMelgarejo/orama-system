# 36 — ClawRouter Scoring Pattern: Dynamic Thresholding in `model_registry.py`

> **Canonical home:** `orama-system/docs/v2/36-clawrouter-scoring-pattern.md`
> **Status:** Proposed — approve before any implementation
> **Locks decision:** D19

---

## 1. Context

ClawRouter is a routing framework that scores model candidates across multiple
weighted dimensions before dispatching. The core contribution is a **multi-dimensional
weighted scoring function**: each candidate model receives a score per dimension
(latency, capability, cost, hardware affinity, availability), weights are applied,
and the highest-scoring available candidate wins.

`model_registry.py` in PT currently does static threshold routing — routes are
declared in `config/routing.yml` as fixed model strings per route type. There is
no dynamic scoring, no fallback weighting, and no runtime adaptation when the
preferred model is unavailable or overloaded.

The v2 distillation plan (Group B, item [4]) says: emulate ClawRouter's
**15-dimension weighted scoring** as an extension of `model_registry.py` dynamic
thresholding — inside PT (L2), never a ClawRouter installation.

---

## 2. Decision (D19)

**What to build:** A `score_candidates(route_key, available_models, context)` function
inside `model_registry.py` that replaces static string lookup with weighted multi-
dimensional scoring. Scores are deterministic given the same inputs (no randomness).
Lives entirely in PT (L2), called by the existing dispatch path in `supervisor.py`.

**What it is NOT:**
- Not a ClawRouter installation or fork.
- Not a separate service.
- Not a change to `config/routing.yml` format — the config feeds the scorer as
  candidate declarations, not as final routing decisions.
- Not a change to the `_dispatch` seam signature (`supervisor.py:534`).

---

## 3. Scoring dimensions (v2 subset — not all 15)

Start with the dimensions that are already measurable locally:

| Dimension | Source | Weight (default) |
|-----------|--------|-----------------|
| `hardware_affinity` | `hardware_policy.yml` + `HardwareAffinityError` | 0.35 |
| `availability` | last_discovery.json `reachable` flag | 0.25 |
| `capability_tier` | `routing.yml` capability tags | 0.20 |
| `cost_tier` | `cost_guard.py` budget headroom | 0.15 |
| `latency_estimate` | rolling average from `capture_lesson.py` traces (v2.1) | 0.05 |

Weights must sum to 1.0. They are configurable in `config/routing.yml` under
a new `scoring_weights` key (optional; defaults shown above apply when absent).

---

## 4. Integration point

```python
# model_registry.py — new public function
def score_candidates(
    route_key: str,
    available_models: list[str],
    context: dict,          # budget_remaining, hardware_state, trace_ctx
) -> list[tuple[str, float]]:
    """Return models ranked by score, highest first. Empty list = no viable candidate."""
```

Called at `supervisor.py:_prepare_spec_for_inference` (`:722`) instead of direct
`routing.yml` lookup. Falls back to static routing if scorer returns empty list.

---

## 5. Fail-closed contract

If `score_candidates` raises or returns empty:
- Log the failure with full context.
- Fall back to the static `routing.yml` winner for that route key.
- Never block dispatch entirely due to scorer failure — scorer is advisory, not gating.

---

## 6. Alternatives rejected

| Alternative | Why rejected |
|-------------|-------------|
| Import ClawRouter | External dep; violates "emulation not importation" |
| 15 dimensions immediately | Latency estimates require trace data not yet collected; start with 5 measurable dimensions |
| Move scoring to orama (L3) | Routing is runtime state — belongs in PT (L2) per architecture |
| Change `_dispatch` signature | Breaks the decorator contract from D17; scorer plugs in upstream |

---

## 7. Consequences

**Positive:**
- Routing adapts to live hardware state (Win down → Mac Ollama scores higher automatically).
- Cost awareness built into routing, not bolted on after.
- Incrementally extensible — add dimensions as trace data accumulates.

**Negative / constraints:**
- Default weights are opinionated; wrong weights can degrade routing quality.
- Latency dimension is a stub until trace data is collected (v2.1).
- Adds complexity to `model_registry.py` — must remain unit-testable in isolation.

---

## 8. Open questions

- **Q1:** Should `scoring_weights` be hot-reloadable from `routing.yml` without restart?
  Recommend: yes, via `watchdog` (already in PT deps) in v2.1; static load in v2.
- **Q2:** Should score history be persisted? Recommend: no — scores are ephemeral;
  only trace annotations (D18) persist for distillation input.

---

## 9. Locked decision

**D19 — ClawRouter scoring is a weighted multi-dimensional scorer inside `model_registry.py`, PT-only (2026-06-17)**

PT emulates ClawRouter's weighted scoring as `score_candidates()` in `model_registry.py`.
5 dimensions initially (hardware_affinity, availability, capability_tier, cost_tier,
latency_estimate). Configurable weights in `routing.yml`. Fail-closed: falls back to
static routing on scorer failure. Gate doc: this file.

---

## 10. Cross-references

- D17: `30-multi-llm-router-caching-batching-decorator.md` (decorator wraps `_dispatch`; scorer plugs in upstream at `_prepare_spec_for_inference`)
- D20: `37-manifest-cost-tiering-pattern.md` (cost_tier dimension feeds from Manifest cost guard extension)
- `Perpetua-Tools/orchestrator/model_registry.py` — implementation target
- `Perpetua-Tools/config/routing.yml` — scoring_weights config key
- `docs/distill-fable-5/implementation-plan.md` — Group B [4]
