# distill-fable-5 — Frontier-Model Session Distillation

Per-session crystallization of frontier-model (Claude Fable 5) runs into durable,
local-model-compatible artifacts, per the Frontier-Model Integration Plan
(`~/code/oramasys/tools/` on the workstation; canonical copy pending absorption here).

Each dated subfolder is one frontier session: LESSONS, a delegation map, and
measured model-performance deltas. Artifacts must be self-contained,
low-dependency, and usable by local models (Ollama / LM Studio / MLX).

## Pilot run — 2026-07-02

- **Orchestrator:** Claude Fable 5 (Mac, max reasoning reserved for planning/synthesis)
- **Delegates:** Sonnet-5-medium subagents (rate-limited mid-run → rerouted to
  inline execution + local models), Win LM Studio 27B (coordination verdict), Mac tooling
- **Tracks & outcomes:**
  1. **CI remediation** — Endpoint Policy Peer Contract failing on every main push
     since `033737c`: workflow re-added without its checker script (partial merge
     restore). Restored from `7021c9c`, AGENTS.md guidance re-merged additively,
     actions bumped v5/v6. Run 28563937736 **GREEN**.
  2. **Security review** — the two failing-run hypotheses in the external Codex
     deliverable were both refuted by 3 minutes of local git archaeology; orama's
     `src/utils/endpoint_policy_core.py` ALREADY satisfies the full invariant
     (wrapped `urlparse().port`, `ipv4_mapped` unwrap, link-local block; fuzz
     tests present; 1019 tests green).
  3. **"Mirror drift" finding downgraded** — PT vs orama `endpoint_policy_core.py`
     are different-purpose modules sharing a filename, not drifted mirrors;
     `model_endpoint_url.py` drift is docstring-only.
  4. **Win coordination** — division of labor proposed to and ACCEPTED by the Win
     27B co-orchestrator via direct LM Studio call (zero frontier tokens);
     Win owns `packages/endpoint-policy/` authoring in PT (coord-023 card).
  5. **MacOS environment** — all green: gateway up, ollama idle, portal 8002 200,
     `orchestrator.sh` syntax-valid, cline fallback correctly dormant,
     solo-mode correctly engaged (Win portal unreachable across subnets).

## Folder contract

- `YYYY-MM-DD-pilot/LESSONS.md` — session lessons (append-only)
- `YYYY-MM-DD-pilot/DELEGATION_MAP.md` — reusable model-routing recipe
- `YYYY-MM-DD-pilot/MODELS_PERFORMANCE_DELTA.md` — measured deltas only; TODOs explicit
