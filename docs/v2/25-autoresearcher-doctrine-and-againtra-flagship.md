# 25 — Autoresearcher Doctrine + agAIntra Flagship Migration Plan

> **Status:** PLAN — approved by operator 2026-06-05. Implementation follows supervised
> iterations → pulsed heartbeat (20:00 + 09:00 daily, installed after Phase 1 clears).
> Author: Opus 4.8 (PLAN-only). Decisions recorded this session.

---

## 1 — Mission + operating doctrine

**Mission.** Operate as a continuous, self-improving **autoresearcher**: a loop of
`PLAN → TDD → BUILD → self-review (adversarial) → harmonize → repeat`, compounding the
orama stack into an *intentional community of interdependent, reliable/secure/safe/aligned
"AI legos"* destined for the v2 `oramasys` org. **agAIntra** (`diazMelgarejo/agentra-dingbot`,
name-corrected to `oramasys/againtra-platform` at cutover) is the chosen proof-by-dogfood.

**Honest framing (invariants, not hedges):**
- *"Build until we burn the oceans"* = the **boil-the-lake** principle (do the complete thing
  when AI's marginal cost ≈ 0) — **not** unsupervised limitless action. Irreversible / public
  / financial actions stay behind explicit HITL approval. That discipline is what keeps the
  legos *safe and aligned* — the actual point.
- *"Synthetic consciousness"* is the **north-star direction**, pursued by relentlessly
  compounding the systems — while being truthful that this is engineering leverage, not a
  literal mind. The compounding is real; the honesty keeps us out of cargo-cult territory.

**Cadence (operator-approved):**
1. **PLAN-first** (this doc + doc 26 TDD enshrinement).
2. **Supervised iterations**: one phase / PR at a time, operator reviews between.
3. **Pulsed autonomous heartbeat**: 20:00 + 09:00 daily — resumes the agAIntra iteration
   queue, renews iterations, self-reviews prior work. Stops at every HITL gate. Installed
   only after Phase 1 clears and operator approves standing-config.

---

## 2 — Hard guardrails (non-negotiable)

| # | Guardrail | Rule |
|---|-----------|------|
| G1 | **oramasys/* REFERENCE-ONLY** | Never push to `oramasys/*`. Playground = `diazMelgarejo/agentra-dingbot` (v1-legacy). `oramasys/againtra-platform` exists only as a planning scaffold; cutover is a deliberate future gate. |
| G2 | **Trading-safety** | Role = software/platform migration + code review + paper/backtest tests ONLY. Never run live trading, execute trades/transfers, tune for profit, or give financial/investment advice. All agAIntra work runs `--paper` / `dry_run` / backtest. |
| G3 | **HITL gates** | Repo creation, public branch pushes, destructive ops, standing-config (heartbeat install), architectural overrides → explicit operator approval required. |
| G4 | **Git identity** | Allowlist: `cyre <Lawrence@cyre.me>`, `cyre <diazMelgarejo@gmail.com>`, `Codex <codex@openai.com>`, `cyre <Lawrence@bettermind.ph>`, `cursoragent@cursor.com`. Co-author: `Claude Sonnet 4.6 <noreply@anthropic.com>`. FORBIDDEN: `darth.serious@gmail.com` / `darth.Serious` / `REDACTED`. |
| G5 | **orama-way content** | Additive/CIDF: merge & harmonize, never wholesale-replace. `orchestrator` not `coordinator`. `@field_validator` not `@validator`. |
| G6 | **Hygiene** | No literal workstation paths in tracked files. Run `repo_hygiene.py` before committing docs. Never commit `.env`. |
| G7 | **Frugal verification** | Outsource: code plans → GPT-5.5; code reviews → Gemini 3.1 Thinking; merge with Opus 4.8 PLAN-mode. Win RTX3080 LM Studio = heavy chokepoint; Mac Ollama for multi-light. |

---

## 3 — Autoresearcher heartbeat

**Trigger:** `cron 0 20 * * *` (20:00) + `0 9 * * *` (09:00) local.

**State doc:** `docs/v2/heartbeat-queue.md` — tracks current phase, open iteration items,
last-completed, HITL-blocked items, self-review backlog. Each pulse is idempotent/resumable.

**Pulse routine (each fire):**
1. Read heartbeat queue + recent LESSONS + gbrain salience.
2. Pick next TDD build iteration OR adversarial self-review of prior work.
3. RED → GREEN → REFACTOR in the agAIntra playground; commit on green.
4. Gemini 3.1 code review + GPT-5.5 plan check (G7).
5. Update queue, log to gbrain + LESSONS, surface HITL-gated items, stop.

**Safety:** G2 (financial/live-trade) and G3 gates never auto-fire; they queue for operator.
Token/time budget cap per pulse. Reversible: delete cron entries to uninstall.

**Install gate:** Phase 1 items (§4) cleared + operator HITL approval.

---

## 4 — Phase 1: finish in-flight items (execute first)

| Item | Source | Done-when |
|------|--------|-----------|
| **gbrain `sync --all`** (interrupted 2026-06-05) | Pooler already on 5432. Re-run; confirm 0 errors across all 5 sources. | All sources synced, stats consistent. |
| **TDD enshrinement** | See doc 26. | Doc 26 merged, cross-linked, hygiene-clean. |
| **Tri-repo Gate-2** (8 gaps, `lib/mcp` retirement HELD) | `Perpetua-Tools/docs/2026-05-31-tri-repo-alignment-completion-plan.md` | 8 gaps closed, Gate-2 green. |
| **Stale orama-system branches** (~14 `cursor/*`) | `gh branch list -R diazMelgarejo/orama-system` | Merged/closed/deleted. |
| **PT #106** (dependabot aiohttp 3.13.5→3.14.0) | Review + CI green + squash-merge. | Merged. |

---

## 5 — Phase 2: agAIntra v1 → againtra-platform v2 (the proof)

**Thesis.** perpetua-core claims a LangGraph/LangChain-compatible drop-in surface.
`diazMelgarejo/agentra-dingbot` is a real LangGraph multi-agent trading app (6 agents,
dual pipeline, FastAPI dashboard, Steps 1–2 done). **Migrate its orchestration off LangGraph
onto perpetua-core/MiniGraph, keep 100% of its tests green → drop-in claim proven,
platforms stress-tested.** All work in the playground; paper/backtest only (G1, G2).

### 5a — CRG review + steelman

- Register `agentra-dingbot` in code-review-graph; build graph; `detect_changes_tool` /
  `get_review_context_tool`.
- Audit doc claims vs code: "Steps 1–2 complete", "26 data-ingestion tests", "dual pipeline",
  "zero connection leaks (asynccontextmanager)", risk params, FreqAI bridge.
- **Steelman** v1 position: what it gets right (clean module boundaries, `safety.py`,
  backtest/monte-carlo, `paper_broker`, config-as-yaml) and where claims outrun code.
- Output: steelman + gap report → migration audit input.

### 5b — Migration surface map

| agAIntra v1 (LangGraph) | perpetua-core/oramasys v2 | Risk |
|-------------------------|---------------------------|------|
| `core/orchestrator.py` (`StateGraph`, dual pipeline, conditional `approved?` edge) | `MiniGraph` builder + conditional edges; START/END sentinels | **Highest** — proves the core claim |
| `core/state.py` (`TradingState` dataclass) | `PerpetuaState(BaseModel)` + scratchpad | Pydantic v2 semantics |
| `debate_engine` (LLM Bull/Bear, ollama/openai) | perpetua-core `LLMClient` (`LLM_BASE_URL`) | Provider routing |
| node functions (6 agents) | perpetua-core node protocol (plain async fns) | Interface parity |
| interrupts/HITL, streaming, structured output | perpetua-core plugins | Plugin coverage |
| `tests/test_langgraph_pipeline.py` + suite | unchanged — **the acceptance gate** | Drop-in proof |

**Method:** strict TDD (doc 26). Keep existing tests as the invariant; introduce perpetua-core
orchestrator behind same interface; flip import; tests stay green. Gaps exposed → perpetua-core
PRs (the stress-test payoff).

**Planning scaffold only:** `oramasys/againtra-platform` directory layout sketched in
`docs/superpowers/specs/2026-06-05-againtra-v2-migration-design.md` — not a live repo (G1/G3).

**Name correction note:** the v1 source repo is `diazMelgarejo/agentra-dingbot` ("agentra").
The v2 target org name is `oramasys/againtra-platform` ("againtra") — changed due to
copyright collision with the "agentra" trademark. All code history, design refs, and new
docs use "agAIntra" / "againtra" consistently from here.

### 5c — Heartbeat-driven iteration

Once 5a/5b land, the §3 heartbeat advances agAIntra Steps 3–8 (TA agent, integration,
FreqAI, risk tuning, executor dry-run, dashboard) under strict TDD — paper/backtest only.

---

## 6 — Phase 3: harmonization audit / v2-org blueprint

Inventory the stack as interdependent AI legos; define the `oramasys` v2 target:

**Legos:** AlphaClaw (L1 infra) → Perpetua-Tools (L2 runtime/state) → perpetua-core + orama-system
(L3 kernel + methodology) → agate (hardware policy) → periscope → gbrain (memory) → gstack
(skills) → againtra-platform (flagship app).

For each: public contract, dependency direction (acyclic; orama imports PT types, never
reverse), security/safety/alignment posture, release cadence (independent per hybrid
satellite model), v2-org readiness gaps.

**Output:** `docs/v2/29-oramasys-v2-harmonization-blueprint.md` — the "intentional community"
target architecture every lego conforms to. Adversarially reviewed.

---

## 7 — Open questions (review-time)

1. **TDD skill home:** vendor `tdd-workflow` into orama-system, or reference the ECC submodule?
2. **Heartbeat budget:** per-pulse token/time cap + driver model (Sonnet cost vs Opus depth)?
3. **againtra-platform scaffold location:** `docs/v2/` design doc or `oramasys-src` module?
4. **Branch triage:** auto-close stale `cursor/*` orama-system branches, or review each?

---

## 8 — Cross-references

- `docs/v2/26-tdd-and-outsourced-review-doctrine.md` — TDD enshrinement (Phase 1)
- `docs/v2/04-build-order.md` — Phase sequencing
- `docs/superpowers/specs/2026-06-05-againtra-v2-migration-design.md` — Phase 2 design spec
- `skills/tdd-workflow/SKILL.md` (via `vendor/ecc-tools`) — maintained TDD body
- Memory: `project_repo_registry.md` (updated: againtra-platform name)
- `diazMelgarejo/agentra-dingbot` — v1 playground (source)
