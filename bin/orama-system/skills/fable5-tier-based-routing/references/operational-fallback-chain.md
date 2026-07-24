# Operational Fallback Chain (LLM-Council 4-tier) vs. Code Routing Tiers

Added 2026-07-19 (LLM-Council Task 3). Reconciles two legitimate tier vocabularies that coexist in this stack — do not "fix" one to match the other.

## Two different things called "tiers"

| Vocabulary | Where it lives | What it orders |
|---|---|---|
| **Routing tiers** (SKILL.md Tiers 1-4) | `Perpetua-Tools/orchestrator/frugality_router.py` (code-grounded) | Cost/privacy escalation for TOOL-CALL routing: Local OSS → Local Index (gbrain/CRG) → Remote Free (HF) → Proprietary Free |
| **Operational fallback chain** (this file) | LLM-Council consensus (7/7 agents, 2026-07-04, PT `lesson_6741dab9176f`) | Which INFERENCE BACKEND an orchestration session tries next when one is down/exhausted |

## The operational chain (mandatory order)

```text
Tier 1: Local (Ollama qwen3.5:9b-nvfp4, localhost:11434)
        10s timeout, always try first.
Tier 2: Windows GPU (LM Studio)
        Endpoint from discovery (last_discovery.json → endpoints.win),
        NEVER hardcoded. SKIP entirely if offline — don't burn the timeout.
Tier 3: Regional (GLM-5.2 BigModel, open.bigmodel.cn) — cost-gated.
Tier 4: Cloud (Sonnet 5 Medium) — last resort ONLY. No further fallback:
        when Tier 4 fails, surface the outage; do not retry-storm.
```

## Invariants (identical to SKILL.md's; restated because violations recur)

- HARD 10s timeout per tier via a **killable background call**.
- **NEVER `timeout N && cmd`** — it breaks SIGTERM delivery (see
  `references/python-timeout-pattern.md` for the correct pattern).
- Cost gate **raises on deny** — never a silent reroute to a paid tier.
- Track `escalation_reason` on every tier elevation.
- Escalation triggers: "endpoint timeout" → next tier; "tier unavailable"
  → skip to next; "cost budget exceeded" → raise (not reroute).

## Fact-check against code (2026-07-19 — honest status, not aspiration)

Verified by grep against PT `orchestrator/`:

- `_enforce_tier_policy()` — **EXISTS** (`frugality_router.py:94`, called at
  174/242/251). This is the routing-tier gate.
- `TIER_PROBE_TIMEOUT_S = 10.0` — **DOES NOT EXIST** anywhere in
  `orchestrator/`. The task brief asserting it is stale/aspirational. The
  10s ceiling is doctrine (this file + PT lessons), not yet a named code
  constant. If unified later, add the constant in ONE place and cite it
  here — do not invent it in docs first.
- `cost_guard` import in `frugality_router.py` — **NOT PRESENT** (it
  imports `backend_resolver`). Cost gating doctrine currently lives at the
  policy layer, not as a frugality_router import.

Re-verify: `grep -rn "TIER_PROBE_TIMEOUT" "$REPO_ROOT/../Perpetua-Tools/orchestrator/"`

AUDIT: 2026-07-19 fable5-tier-based-routing upgrade (reference add) — LLM-Council
Task 3; grounded against frugality_router.py; two brief-asserted facts found
absent in code and recorded as absent rather than fabricated.
