# 36 — ClawRouter Scoring Pattern: Dynamic Thresholding at the `resolve_backend` Seam

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

PT currently does static routing — candidates are declared in `config/routing.yml`
as **role-keyed lists** (not model strings; each entry is a role/platform token that
`worker_registry.resolve_backend` resolves to a real backend at dispatch time).
`_dispatch` calls `worker_registry.resolve_backend` at `supervisor.py:573` to
determine the winning backend; `model_registry.route_task` is an **HTTP-only**
path (`fastapi_app.py:502/536`) and is **never** called on the dispatch path.
An `_endpoint_online` probe already exists in the dispatch path — the scorer must
not duplicate it.

The v2 distillation plan (Group B, item [4]) says: emulate ClawRouter's
**15-dimension weighted scoring** — inside PT (L2), never a ClawRouter installation.

### Two routing surfaces (important — not one)

| Surface | Call path | Who calls it |
|---------|-----------|-------------|
| `worker_registry.resolve_backend` (`supervisor.py:573`) | Runtime dispatch path | `_dispatch` (every job) |
| `model_registry.route_task` (`model_registry.py:173`) | HTTP `/orchestrate` path | `fastapi_app.py:502/536` only |

**The scorer plugs into the runtime dispatch surface only** — it re-orders the
candidate set produced by `worker_registry.resolve_backend` before `_dispatch` picks
the winner. `model_registry.route_task` is not involved and must not be modified.

---

## 2. Decision (D19)

**What to build:** A `score_candidates(route_key, available_models, context)` function
in a new `model_scoring.py` module (or as an extension of `worker_registry.py`) that
re-orders the candidates produced by `worker_registry.resolve_backend` according to
weighted multi-dimensional scoring. Scores are deterministic given the same inputs
(no randomness). Lives entirely in PT (L2), wired into `_dispatch` at the
`resolve_backend` seam (`supervisor.py:573`).

**What it is NOT:**
- Not a ClawRouter installation or fork.
- Not a separate service.
- Not a change to `config/routing.yml` format — the config feeds the scorer as
  candidate declarations (role lists), not as final routing decisions.
- Not a change to the `_dispatch` seam signature (`supervisor.py:534`).
- Not wired into `model_registry.route_task` — that is the HTTP-only surface.
- Not wired at `_prepare_spec_for_inference:722` — that function runs **after** the
  backend is already selected, so wiring there would be inert.

---

## 3. Scoring dimensions (v2 subset — not all 15)

Start with the dimensions that are already measurable locally:

| Dimension | Source | Weight (default) |
|-----------|--------|-----------------|
| `hardware_affinity` | `config/model_hardware_policy.yml` + `src/utils/hardware_policy.py` (`HardwareAffinityError`) | 0.35 |
| `availability` | `ModelTarget.online` flag (single source; do not also read `last_discovery.json` as a third source) | 0.25 |
| `capability_tier` | `routing.yml` role tags | 0.20 |
| `cost_tier` | D20 `CostGuard.gate()` budget headroom — **deferred until D20 is approved**; set weight to 0.0 until then | 0.15 |
| `latency_estimate` | D18 trace annotations — **planned; no trace data exists today** | 0.05 |

Weights must sum to 1.0. They are configurable in `config/routing.yml` under
a new `scoring_weights` key (optional; defaults shown above apply when absent).

The `cost_tier` dimension is explicitly deferred: its weight is 0.0 (and the
dimension is a no-op) until D20 (`CostGuard.gate()`) is approved. Activating
`cost_tier` before D20 risks fail-open behavior (§5).

---

## 4. Integration point

```python
# model_scoring.py (or worker_registry.py extension) — new public function
def score_candidates(
    route_key: str,
    available_models: list[str],
    context: dict,          # budget_remaining, hardware_state, trace_ctx
) -> list[tuple[str, float]]:
    """Return models ranked by score, highest first. Empty list = no viable candidate."""
```

Wired at `supervisor.py:_dispatch` immediately **before** `worker_registry.resolve_backend`
is called (`:573`), so the scorer re-orders the candidate list that `resolve_backend`
consumes. The `_dispatch` seam signature is unchanged; `resolve_backend` receives
a pre-scored candidate ordering.

`_prepare_spec_for_inference` (`supervisor.py:722`) is a 4-param `@staticmethod`
(`spec, backend, *, affinity_platform`) that runs **after** the backend is already
fixed — wiring the scorer there would be inert. `check_affinity` is already invoked
at `supervisor.py:753` inside this function; the scorer must not duplicate it.

---

## 5. Fail-safe contract

If `score_candidates` raises or returns empty:
- Log the failure with exception type and `route_key` only — **never log raw spec/prompt content**.
- Fall back to the **local-tier default** from `routing.yml` for that route key (never to a cloud-tier model). The fallback MUST NOT select a cloud-escalation model (e.g. `claude-fable-5`) — that would make a scorer failure silently cost-escalating. If the static `routing.yml` default for the route key is a cloud model, the fallback becomes REJECT (do not dispatch).
- Never block dispatch entirely due to scorer failure when a safe local fallback exists — scorer is advisory when local fallbacks are available.

---

## 6. Alternatives rejected

| Alternative | Why rejected |
|-------------|-------------|
| Import ClawRouter | External dep; violates "emulation not importation" |
| 15 dimensions immediately | Latency estimates require trace data not yet collected; start with 5 measurable dimensions |
| Move scoring to orama (L3) | Routing is runtime state — belongs in PT (L2) per architecture |
| Change `_dispatch` signature | Breaks the decorator contract from D17; scorer plugs in upstream of `resolve_backend` |
| Wire at `_prepare_spec_for_inference:722` | Backend already fixed at that point — wiring there is inert |
| Wire at `model_registry.route_task` | HTTP-only path; never called by `_dispatch` |

---

## 7. Consequences

**Positive:**
- Routing adapts to live hardware state (Win down → Mac Ollama scores higher automatically).
- Cost awareness built into routing, not bolted on after (once D20 lands).
- Incrementally extensible — add dimensions as trace data accumulates.

**Negative / constraints:**
- Default weights are opinionated; wrong weights can degrade routing quality.
- Latency and cost dimensions are stubs until D18/D20 land.
- Adds complexity upstream of `resolve_backend` — must remain unit-testable in isolation.

---

## 8. Open questions

- **Q1:** Should `scoring_weights` be hot-reloadable from `routing.yml` without restart?
  Recommend: yes, via `watchdog` (already in PT deps) in v2.1; static load in v2.
- **Q2:** Should score history be persisted? Recommend: no — scores are ephemeral;
  only trace annotations (D18) persist for distillation input.

---

## 9. Locked decision

**D19 — ClawRouter scoring is a weighted multi-dimensional scorer wired at the `resolve_backend` seam (`_dispatch:573`), PT-only (2026-06-17)**

PT emulates ClawRouter's weighted scoring as `score_candidates()` wired at
`supervisor.py:573` (upstream of `worker_registry.resolve_backend`). 5 dimensions
initially; `cost_tier` weight = 0.0 until D20 approved. Fail-safe: falls back to
local-tier routing.yml default on scorer failure — never to a cloud-tier model.
Gate doc: this file.

---

## 10. Cross-references

- D17: `30-multi-llm-router-caching-batching-decorator.md` (decorator wraps `_dispatch`; scorer plugs in upstream at `resolve_backend:573`, before the decorator's cache check)
- D20: `37-manifest-cost-tiering-pattern.md` (`cost_tier` dimension deferred until D20 approved; activating before D20 risks fail-open cloud escalation)
- D18: `35-langfuse-trace-tree-pattern.md` (`latency_estimate` dimension deferred until D18 trace data available)
- `Perpetua-Tools/orchestrator/supervisor.py:573` — wiring seam (`_dispatch`, before `resolve_backend`)
- `Perpetua-Tools/orchestrator/worker_registry.py:106` — `resolve_backend` (runtime dispatch; scorer re-orders its candidate input)
- `Perpetua-Tools/config/routing.yml` — scoring_weights config key; role-keyed candidate lists (not model strings)
- `Perpetua-Tools/config/model_hardware_policy.yml` — policy data file read by `hardware_policy.py:load_policy()` (input to `hardware_affinity` dimension)
- `docs/distill-fable-5/implementation-plan.md` — Group B [4]
