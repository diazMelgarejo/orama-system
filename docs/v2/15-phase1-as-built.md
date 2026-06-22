# 15 — v2 Alpha As-Built Notes (2026-05-01)

> Records what the canonical `oramasys/*` repos shipped in their v2.0-alpha.1 build.
> All three repos were pushed to GitHub on 2026-05-01 and remain 0 ahead/0 behind remote.
> Status: **reference doc** — no code changes implied here.

---

## What shipped (2026-05-01)

### `oramasys/perpetua-core` — kernel

**Commit:** `2f717f5` "feat: perpetua-core v2.0 alpha — 70-line kernel + plugin system (32/32 tests)"
**Tests:** 32 passing (Python 3.11+)
**Remote:** `github.com/oramasys/perpetua-core`

| Module | File | Notes |
|--------|------|-------|
| State | `perpetua_core/state.py` | `BaseModel`, `scratchpad: dict[str,Any]`, `HardwareTier`/`TaskType`/`OptHint` literals, `merge()` via `model_copy()` |
| LLM client | `perpetua_core/llm.py` | Async OpenAI-compatible; `LLM_BASE_URL` env var |
| Hardware policy | `perpetua_core/policy.py` | `HardwarePolicyResolver`, `HardwareAffinityError` |
| Gossip bus | `perpetua_core/gossip.py` | `aiosqlite` (async, 47 lines) |
| Graph engine | `perpetua_core/graph/engine.py` | **65 lines**, START/END sentinels, duck-typed HITL via `Interrupt` exception |
| Plugin: checkpointer | `perpetua_core/graph/plugins/checkpointer.py` | SQLite state snapshots |
| Plugin: interrupts | `perpetua_core/graph/plugins/interrupts.py` | `Interrupt` + `aresume()` |
| Plugin: streaming | `perpetua_core/graph/plugins/streaming.py` | `AsyncGenerator` token + state streaming |
| Plugin: structured_output | `perpetua_core/graph/plugins/structured_output.py` | Force LLM → Pydantic v2 shapes |
| Plugin: subgraphs | `perpetua_core/graph/plugins/subgraphs.py` | Nested `MiniGraph` as node |
| Plugin: tool | `perpetua_core/graph/plugins/tool.py` | `@tool` decorator, auto-schema from type hints |

**Key design confirmations vs. spec:**
- `PerpetuaState` is `BaseModel` (not dataclass) ✅ matches `01-kernel-spec.md`
- `scratchpad: dict[str, Any]` ✅ matches `01-kernel-spec.md`
- `optimize_for: OptHint = "quality"` is ON `PerpetuaState` (matches Grok synthesis, D8)
- `target_tier`, `task_type`, `model_hint` fields present (Grok additions, not in original spec)
- Engine is 65 lines — matches D8 revision ("~70-line kernel + plugins")
- All 6 Tier-3 features ship as plugins (not inline in engine)
- `aiosqlite` used throughout — no sync SQLite

**Open gaps (Phase 2 work):**
- `MiniGraph.max_steps` safety guard not implemented (OQ12 — still open)
- No `perpetua_core/message.py` typed Message wrapper — messages are plain `dict` (OQ17 — still open)

---

### `oramasys/oramasys` — methodology + FastAPI layer

**Commit:** `d123420` "feat: oramasys v2.0 alpha — FastAPI glass-window + hardware-routed graph (4/4 tests)"
**Tests:** 4 passing
**Remote:** `github.com/oramasys/oramasys`

| Module | File | Notes |
|--------|------|-------|
| Graph | `orama/graph/perpetua_graph.py` | 3-node: route → dispatch → respond; hardware affinity gate in `route_node` |
| API server | `orama/api/server.py` | FastAPI `/run` + `/health`, handlers ≤ 10 lines ✅ |
| API contracts | `orama/api/contracts.py` | `RunRequest` → `PerpetuaState`, `RunResponse` from state |

**Open gaps (Phase 3 work):**
- `dispatch_node` is a placeholder (echo-only) — not wired to `LLMClient` (OQ15 partial, Phase 3)
- No `TaskPlan` / `OramaToPTBridge` migration from v1 yet (OQ15 — still open)

---

### `oramasys/agate` — hardware policy specification

**Commits:** `755e1de` / `f1d5a57`
**Remote:** `github.com/oramasys/agate`

| Module | File | Notes |
|--------|------|-------|
| JSON Schema | `schemas/model_hardware_policy.schema.json` | Hardware policy schema v1 |
| Examples | `examples/` | Example policy YAMLs |
| GGUF RFC | `docs/gguf-hardware-affinity-rfc.md` | Community RFC for `system_requirements` in GGUF |

**Open gaps (future work):**
- Bridge adapter (OramaToPTBridge → agate) not yet implemented (OQ15)
- IDE API surface not yet in agate (future scope from D5 / agate vision)

---

## OQs resolved by this build

| OQ | Resolution | Date |
|----|------------|------|
| OQ4 — GitHub org `oramasys` | **Resolved:** org exists at `github.com/oramasys`; all 3 v2 repos live there | 2026-05-01 |
| OQ7 — Python version | **Resolved:** canonical uses Python 3.11+; `requires-python = ">=3.11"` in all 3 pyproject.toml files | 2026-05-01 |
| OQ8 — `optimize_for` field name | **Resolved:** `optimize_for: OptHint = "quality"` is on `PerpetuaState` directly (matches Grok synthesis and policy routing key structure) | 2026-05-01 |
| OQ11 — GossipBus async | **Resolved:** `aiosqlite` used from day one; no sync sqlite3 in the codebase | 2026-05-01 |
| (was OQ13) — PerpetuaState dataclass vs BaseModel | **Resolved:** `BaseModel` with `ConfigDict` in canonical | 2026-05-01 |
| (was OQ14) — `perpetua-core` org transfer | **Resolved:** canonical was always under `oramasys` org | 2026-05-01 |
| (was OQ16) — engine.py size and integration | **Resolved:** 65-line pure engine + `graph/plugins/` — D8 revision is implemented | 2026-05-01 |

---

---

## Hardware Policy Enshrinement (2026-05-17/18) — v1 RC-1 post-ship

> This section documents decisions made **after** the 2026-05-01 alpha build —
> during the RC-1 policy audit of `diazMelgarejo/Perpetua-Tools`. They are
> captured here because they define the **required policy surface** that v2 /
> agate must have correct from day one. See `17-hardware-policy-enforcement.md`
> for the full reference.

### Key decisions locked (D14, D15)

| Decision | Summary |
|----------|---------|
| D14 | LM Studio Mac = **MIRROR ONLY**. `_MIRROR_BACKENDS` frozenset + `windows_only:` in `model_hardware_policy.yml` + `_TIER_HOSTS["mac"] = {"ollama-local"}` only. Dispatching a `windows_only:` model to the mirror = proxy back to Win = double-barrel GPU = OOM. Fail closed. |
| D15 | `orchestrator/agent_launcher.py` → `orchestrator/backend_resolver.py`. Pure policy function separated from 859-line operational CLI. No ambiguity between the two. |

### v1 test count update

| Repo | Tests (2026-05-01) | Tests (2026-05-18) | New |
|------|--------------------|--------------------|-----|
| `diazMelgarejo/Perpetua-Tools` | 33 | 36 | 3 mirror/resolver tests |
| `oramasys/perpetua-core` | 32 | 38 (est.) | 6 mirror-exclusion tests |
| `oramasys/oramasys` | 4 | 4 | — |

### `model_hardware_policy.yml` hard enforcement

Before (wrong — framed as "performance routing"):
```yaml
shared:
  - qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2  # was here — WRONG
```

After (hard enforcement):
```yaml
windows_only:
  - qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2  # RTX 3080 GGUF only
  - gemma-4-26b-a4b-it                                  # RTX 3080 GGUF only
```

### `devices.yml` corrections

| Field | Before | After |
|-------|--------|-------|
| `win-rtx3080.lan_ip` | `""` (empty) | `"192.168.254.103"` |
| `mac-studio.default_backend` | `"mlx"` | `"ollama"` |
| `mac-studio.secondary_backend` | present | removed (contradicted mirror policy) |
| `shared-ollama.lan_ip` | `"192.168.254.103"` (wrong — was Win IP) | `""` |

### agate design constraint from D14

agate must distinguish three affinity levels:

| Verdict | Meaning | v1 mechanism |
|---------|---------|--------------|
| `NEVER` | Hardware damage risk (OOM, double-barrel GPU) | `windows_only:` + `_MIRROR_BACKENDS` |
| `PREFER` | Best fit; other tiers are fallback | `shared:` with sort-order priority |
| `ALLOW` | Works but not optimal | `shared:` at secondary sort position |

The agate JSON Schema must surface `NEVER` explicitly — it cannot be inferred
from list membership. A tool consuming the schema needs to parse `NEVER` as a
hard block, not a soft preference.

---

## Note on `diazMelgarejo/perpetua-core` (divergent build)

A divergent build (`9cb153a`, 2026-05-14) was accidentally created at the wrong local path
and pushed to `diazMelgarejo/perpetua-core`. It is SUPERSEDED by this canonical build.
See `docs/wiki/10-wrong-repo-build-what-not-to-do.md` for the full post-mortem.

No further work goes to `diazMelgarejo/perpetua-core`.

---

## Salvage Translation RC-1 (2026-05-17) — v2 kernel completion

> Ports 6 assets from the divergent wrong-repo into canonical `oramasys/perpetua-core`.
> All 16 tasks completed same-day. Branch `feat/salvage-plugins-rc1` is local-only,
> pending Mac+Win hardware review before push to perpetua-core `main`.
> **Spec:** [`docs/superpowers/specs/2026-05-17-salvage-translation-design.md`](../superpowers/specs/2026-05-17-salvage-translation-design.md)
> **Plan:** [`docs/superpowers/plans/2026-05-17-salvage-translation-v1-discovery.md`](../superpowers/plans/2026-05-17-salvage-translation-v1-discovery.md)
> **PROGRESS.md:** [`github.com/oramasys/perpetua-core/blob/feat/salvage-plugins-rc1/PROGRESS.md`](https://github.com/oramasys/perpetua-core/blob/feat/salvage-plugins-rc1/PROGRESS.md)

**Commit:** `56f2a6d` "feat: salvage translation RC-1 — 16 tasks, 62 tests, mirror safety (v2-planning)"
**Branch:** `feat/salvage-plugins-rc1` (local-only — push gate: Mac+Win hardware review)
**Tests after RC-1:** 56 passing in `perpetua-core` (32 baseline + 24 new)

### New modules shipped in RC-1

| Module | File | Lines | Notes |
|--------|------|------:|-------|
| Discovery: backend | `perpetua_core/discovery/backend.py` | 38 | `Backend` dataclass, tier/task fields |
| Discovery: probe | `perpetua_core/discovery/probe.py` | 29 | async `health_probe()` |
| Discovery: registry | `perpetua_core/discovery/registry.py` | 60 | autodetect + `register_by_ip` |
| Discovery: selector | `perpetua_core/discovery/selector.py` | 67 | tier+task routing, `_MIRROR_BACKENDS` safety |
| Discovery: errors | `perpetua_core/discovery/errors.py` | 6 | typed error hierarchy |
| Typed message wrapper | `perpetua_core/message.py` | 43 | **OQ17 RESOLVED** — `Message` typed wrapper, replaces plain `dict` |
| Plugin: tool_node | `perpetua_core/graph/plugins/tool_node.py` | 55 | async subprocess `ToolNode` |
| Plugin: routing | `perpetua_core/graph/plugins/routing.py` | 24 | `LabelRouter` (callable in `add_edge`) |
| Plugin: validator | `perpetua_core/graph/plugins/validator.py` | 38 | pre/post gate `Validated` |
| Plugin: interrupt_guard | `perpetua_core/graph/plugins/interrupt_guard.py` | 27 | `resume_policy` (shipped separate, not merged) |
| Plugin: parallel | `perpetua_core/graph/plugins/parallel.py` | 31 | `parallel_dispatch` fan-out via `Send` |

### Engine changes in RC-1

| Change | Detail |
|--------|--------|
| `max_steps` cycle guard | `test_engine_max_steps.py` — prevents infinite loops (OQ12 **RESOLVED**) |
| `set_entry()` method | selects graph entry node; returns `self` for chaining |
| `compile()` method | returns `CompiledGraph`; lazy-compile guard; frozen after compile |
| `nodes_visited: list[str]` | added to `PerpetuaState` (RC-1 state-field decision) |
| `retry_count: int` | added to `PerpetuaState` (RC-1 state-field decision) |
| Engine size | **102 lines** (up from 65 — compile path added; still within spirit of D8) |

### OQs resolved by RC-1

| OQ | Resolution | Date |
|----|------------|------|
| OQ12 — `max_steps` safety guard | **Resolved:** `engine.ainvoke` raises `RuntimeError` after `max_steps`; `tests/graph/test_engine_max_steps.py` | 2026-05-17 |
| OQ17 — typed `Message` wrapper | **Resolved:** `perpetua_core/message.py` ships `Message(BaseModel)` with role/content/metadata; `tests/test_message.py` | 2026-05-17 |
| OQ19 — selector mirror exclusion | **Resolved:** `selector.py` derives `_MIRROR_BACKENDS` from config; `_TIER_HOSTS["mac"]` enforces mirror-only; `test_discovery_selector.py` covers 12 cases | 2026-05-17 |

### Phase 2 status after RC-1

| Item | Status |
|------|--------|
| `GraphPlugin` protocol + 6 original plugins | ✅ Done (2f717f5) |
| `max_steps` cycle guard | ✅ Done (RC-1) |
| `perpetua_core/message.py` typed wrapper | ✅ Done (RC-1) |
| `set_entry` + `compile` engine methods | ✅ Done (RC-1) |
| Salvaged plugins: tool_node, routing, validator, interrupt_guard, parallel | ✅ Done (RC-1) |
| Discovery layer (v1 → v2 verbatim port) | ✅ Done (RC-1) |
| Sentinel Node (SWARM misalignment monitoring) | ⏳ Not yet — Phase 2 remainder |

**Phase 2 is effectively complete** modulo the Sentinel Node. Phase 3 (Orchestration & API
Layer) is unblocked once the hardware review gate clears and RC-1 lands on `perpetua-core` main.

### Test breakdown after RC-1

| Suite | Count | Location |
|-------|------:|----------|
| Baseline (2f717f5 — Phase 1) | 32 | `tests/test_*.py` (top-level) |
| Engine: compile + max_steps | 2 | `tests/graph/test_engine_*.py` |
| Plugin: interrupt_guard | 4 | `tests/graph/plugins/test_interrupt_guard.py` |
| Plugin: parallel | 6 | `tests/graph/plugins/test_parallel.py` |
| Plugin: routing | 5 | `tests/graph/plugins/test_routing.py` |
| Plugin: tool_node | 4 | `tests/graph/plugins/test_tool_node.py` |
| Plugin: validator | 5 | `tests/graph/plugins/test_validator.py` |
| Property tests (Hypothesis) | 4 | `tests/property/test_engine_invariants.py` |
| **Total** | **56** | all green |

Cross-repo total (all three repos, three generations): **73 tests green** (perpetua-core 56 + oramasys 5 + Perpetua-Tools 12).

### Push gate

All branches are **local-only** until user end-to-end review on:
- Mac: Ollama `localhost:11434` (`qwen3.5:9b-nvfp4`, `qwen3-coder:480b-cloud`)
- Win: LM Studio `192.168.254.103:1234` (`qwen3.5-27b-claude-4.6-opus-reasoning-distilled-v2`)

After review + push: tag canonical `v0.2.0-alpha` (or per user versioning preference).

### Memory

Inspection findings and push-gate status recorded in Perpetua-Tools agent memory:
- [`Perpetua-Tools/.agent/memory/working/WORKSPACE.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/.agent/memory/working/WORKSPACE.md) — current task state
- [`Perpetua-Tools/.agent/memory/semantic/DECISIONS.md`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/.agent/memory/semantic/DECISIONS.md) — architectural decision record
- [`Perpetua-Tools/.agent/memory/episodic/AGENT_LEARNINGS.jsonl`](https://github.com/diazMelgarejo/Perpetua-Tools/blob/main/.agent/memory/episodic/AGENT_LEARNINGS.jsonl) — raw experience log
