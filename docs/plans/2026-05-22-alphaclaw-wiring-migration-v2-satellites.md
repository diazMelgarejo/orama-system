# AlphaClaw Wiring Audit + Migration + v2.1 Satellite Plan

> Created: 2026-05-22 | Branch: unknown (cross-repo plan)
> Repos: AlphaClaw (L1) · Perpetua-Tools (L2) · orama-system (L3)
> Source docs: UNIFIED-ABSORPTION-PLAN · docs/v2/01-kernel-spec · docs/v2/02-modules · docs/v2/10-v1-hacks-automation-orbit

---

## § 0 — Research Summary (from GBrain + Code-Review-Graph)

### Touch-Point Map — How all three repos wire AlphaClaw today

```
orama-system (L3 — stateless orchestration)
  start.sh ─────────────────────────────────────── delegates to PT alphaclaw_manager.py
  orchestrator/orama_bridge.py ─────────────────── HTTP → ultrathink endpoint
  bin/mcp_servers/openclaw_mcp_server.py ────────── MCP → OpenClaw (NOT AlphaClaw direct)
  scripts/discover.py ──────────────────────────── path discovery for AlphaClaw + PT roots

Perpetua-Tools (L2 — runtime/state authority)
  orchestrator/alphaclaw_manager.py ───────────────── bootstrap_alphaclaw(mac_ip, win_ip) → AlphaClawState
  orchestrator/openclaw_skill_resolver.py ─────────── resolve_skill(...) → SkillEnvelope
  orchestrator/orama_mcp_client.py ────────────────── MCP client for orama queries
  packages/alphaclaw-adapter/src/index.js v0.9.9.8 ── HTTP+CLI adapter (CORRECT arch, no internal requires)
  packages/alphaclaw-mcp/src/index.ts v0.1.0 ─────── TypeScript MCP server (wraps adapter) — 6 tools
  packages/local-agents/src/client.js ─────────────── Ollama + LM Studio client
  packages/local-agents/src/orchestrator.js ───────── Claude-as-planner pattern
  packages/mcpb-agents/ ───────────────────────────── lmstudio-agent.mcpb, ollama-agent.mcpb
  packages/agentic-stack/ ─────────────────────────── submodule

AlphaClaw (L1 — infra, should NOT contain L2/L3 logic)
  lib/mcp/alphaclaw-mcp.js v0.9.9.7 ──────────────── 11-tool MCP server (WRONG repo — migrate to PT)
  lib/agents/local-agent-client.js ───────────────── Ollama+LM Studio client (DUPLICATE of PT packages/local-agents)
  lib/agents/orchestrator.js ─────────────────────── Claude-as-planner (DUPLICATE of PT packages/local-agents/src/orchestrator.js)
```

### Gap Analysis

**AlphaClaw `lib/mcp/alphaclaw-mcp.js` has 11 tools; PT `packages/alphaclaw-mcp` has only 6.**

Missing tools in PT TypeScript version:
| Tool | Status |
|------|--------|
| `alphaclaw_read_config` | MISSING in PT |
| `alphaclaw_list_providers` | MISSING in PT |
| `alphaclaw_tail_logs` | MISSING in PT |
| `alphaclaw_check_env` | MISSING in PT |
| `alphaclaw_build_ui` | MISSING in PT |
| `alphaclaw_run_tests` | MISSING in PT |
| `local_agent_list_models` | MISSING in PT |
| `local_agent_propose_edit` | MISSING in PT |

Present in both (parity confirmed):
- `alphaclaw_status`, `alphaclaw_health` (renamed), `alphaclaw_watchdog_logs` (new in TS), `local_agent_health`, `local_agent_ask_about_code`

**AlphaClaw `lib/agents/` duplicates `packages/local-agents/src/`** — need cross-check then remove from AlphaClaw.

### Pending Plans Across All 3 Repos

| Plan | Repo | Status |
|------|------|--------|
| UNIFIED-ABSORPTION-PLAN §3-7 (shared types, verifier gate, hardware policy) | orama+PT | Partial |
| Migration Plan 3: move lib/mcp → PT packages/alphaclaw-mcp (complete tool parity) | AlphaClaw+PT | Incomplete — 8 tools missing |
| Migration Plan 4: local agents cleanup after PT packages/local-agents verified | AlphaClaw | Incomplete |
| docs/v2/10: V1 hacks → Orbit satellites | orama | Stub |
| docs/v2/02-modules: all 7 module stubs | perpetua-core | All stubs |
| salvage-translation-v1-discovery plan | orama | Pending Phase 2 |
| gbrain+CRG embedding Phase 2+3 | orama | Pending upstream PR |

---

## § 1 — Goal 1: Wiring Correctness Verification

**Task 1.1** — Verify `start.sh` delegates fully to PT, zero routing logic in shell
- `grep -n "alphaclaw" orama-system/start.sh` should show delegate calls only
- No direct `node AlphaClaw/...` invocations

**Task 1.2** — Verify PT `alphaclaw_manager.py` bootstrap path is live (not stale)
- `bootstrap_alphaclaw(mac_ip, win_ip)` must call `discover.py` result, not hardcoded IPs
- Validate: `orama_bridge.py` → PT API → `alphaclaw_manager.py` → HTTP call to AlphaClaw

**Task 1.3** — Verify orama never calls AlphaClaw directly
- `grep -r "AlphaClaw" orama-system/ --include="*.py"` must return zero runtime call sites
- Allowed: doc references, path string in `discover.py`

**Task 1.4** — Verify PT `packages/alphaclaw-adapter` is used by `alphaclaw_manager.py`
- Currently `alphaclaw_manager.py` is Python, adapter is JS/Node — bridge may be CLI-based
- Confirm: how does Python PT call JS adapter? (CLI subprocess? Or is there a Python adapter too?)

**Task 1.5** — Verify `.mcp.json` registers PT's `packages/alphaclaw-mcp` (TypeScript), NOT AlphaClaw's `lib/mcp/alphaclaw-mcp.js`
- If both are registered, there's a duplicate MCP server — remove AlphaClaw's

---

## § 2 — Goal 2: AlphaClaw Feature Migration to Perpetua-Tools

### Phase A: Complete alphaclaw-mcp tool parity (8 missing tools)

**Task 2A.1** — In `packages/alphaclaw-mcp/src/index.ts`, add the 8 missing tools calling the HTTP adapter:

```typescript
// Tools to add (calling adapter methods via fetch to AlphaClaw HTTP API):
alphaclaw_read_config     // GET /api/config or equivalent
alphaclaw_list_providers  // GET /api/providers
alphaclaw_tail_logs       // GET /api/logs?tail=N
alphaclaw_check_env       // GET /api/env or POST /api/env/check
alphaclaw_build_ui        // POST /api/build
alphaclaw_run_tests       // POST /api/test
local_agent_list_models   // GET from Ollama + LM Studio backends
local_agent_propose_edit  // POST to local model with diff-proposal prompt
```

Each tool must call through `@diazmelgarejo/alphaclaw-adapter` — NEVER direct HTTP to AlphaClaw bypassing the adapter.

**Task 2A.2** — Update `packages/alphaclaw-adapter/src/index.js` to expose the backing HTTP methods if missing:
- `readConfig()`, `listProviders()`, `tailLogs(n)`, `checkEnv()`, `buildUi()`, `runTests()`
- For local_agent_list_models: call Ollama `/api/tags` + LM Studio `/v1/models`
- For local_agent_propose_edit: call Ollama/LM Studio completions with unified-diff prompt

**Task 2A.3** — Update version to `0.2.0` in `packages/alphaclaw-mcp/package.json`

**Task 2A.4** — Add Vitest tests for all 8 new tools in `packages/alphaclaw-mcp/tests/`

### Phase B: Verify and clean up lib/agents duplication

**Task 2B.1** — Diff `AlphaClaw/lib/agents/local-agent-client.js` vs `PT/packages/local-agents/src/client.js`
- If PT version is complete superset: delete AlphaClaw's copy, remove from .mcp.json if registered
- If AlphaClaw has features PT lacks: cherry-pick to PT first, then delete

**Task 2B.2** — Diff `AlphaClaw/lib/agents/orchestrator.js` vs `PT/packages/local-agents/src/orchestrator.js`
- Same approach: complete superset in PT → delete AlphaClaw's copy

**Task 2B.3** — After deletion: update AlphaClaw's `.mcp.json` to point to PT's packages only

### Phase C: Remove AlphaClaw lib/mcp after parity confirmed

**Task 2C.1** — After Task 2A is complete and verified (all 11 tools in PT's TypeScript version):
- Remove `AlphaClaw/lib/mcp/alphaclaw-mcp.js` from feature/MacOS-post-install branch
- Remove corresponding entries from AlphaClaw's `.mcp.json` if present
- Add note in AlphaClaw's CHANGELOG.md: "alphaclaw-mcp moved to Perpetua-Tools packages/alphaclaw-mcp"

**Task 2C.2** — Commit sequence (UNIFIED-ABSORPTION-PLAN §8: lockstep commits):
1. PT: add 8 tools + tests + version bump → `feat(alphaclaw-mcp): complete 11-tool parity`
2. AlphaClaw: remove lib/mcp + lib/agents → `chore: remove mcp+agents moved to Perpetua-Tools`
3. orama: update LESSONS.md with migration complete note

### Phase D: Verify UNIFIED-ABSORPTION-PLAN implementation status

**Task 2D.1** — Check §3 shared types in `orchestrator/contracts.py`:
- All 5 types must exist: `OrchestrationSession`, `TaskEnvelope`, `WorkerAssignment`, `WorkerResult`, `VerificationResult`
- All use `@field_validator` (Pydantic V2)

**Task 2D.2** — Check §4 vocabulary normalization (grep acceptance criteria):
```bash
grep -r "Coordinator" . --include="*.py" --include="*.json"  # → 0
grep -r "deviceaffinity" . --include="*.py"  # → 0
grep -r "qwen3-coder" . --include="*.py"  # → 0
```

**Task 2D.3** — Check §5 hardware policy: `utils/hardware_policy.py` must call `check_affinity()` before spawn

**Task 2D.4** — Check `AlphaClawManager.validate_routing_affinity()` exists in `alphaclaw_manager.py`

---

## § 3 — Goal 3: v2.1 Satellite Architecture (autoplan for docs/v2)

### Current v2 state

**MiniGraph kernel** (`perpetua-core/graph/engine.py`) — ~70 lines, blocking for v2.0:
- `PerpetuaState` (Pydantic v2): session_id, messages, scratchpad, status, error, routing hints
- `LLMClient` (async OpenAI-compat)
- `HardwarePolicyResolver` + `HardwareAffinityError`
- `GossipBus` (SQLite event log)
- Cold kernel = zero optional deps

**v2.0 non-blocking module stubs** (all in `docs/v2/02-modules/`, all status: Stub):
1. Multi-agent network
2. MCP-Optional transport
3. Redis coordination
4. Self-improve evaluator (v2.5)
5. RAG + memory
6. Lessons + SKILL.md tooling
7. Public Plugin API (v2.1)

**v2 "Orbit" / Satellite strategy** (`docs/v2/10-v1-hacks-automation-orbit.md`):
- Satellites run in parallel asyncio loop, emit to GossipBus only, kernel reads bus
- Kernel has veto power (PORT_COLLISION, NODE_VERSION_MISMATCH → refuse to start)
- All V1 manual hacks → automated Orbit satellites

### AlphaClaw features that map to v2.1 satellites

The following AlphaClaw features are in the *right conceptual shape* to become satellite plugins orbiting the MiniGraph kernel in v2.1:

| AlphaClaw Feature | v2.1 Satellite Module | Plugin Location | GossipBus Event |
|-------------------|-----------------------|-----------------|-----------------|
| `lib/server/watchdog.js` | **Watchdog Satellite** | `perpetua_core/satellites/watchdog.py` | `GATEWAY_HEALTH`, `GATEWAY_CRASHED` |
| `lib/server/system-cron.js` | **Scheduler Satellite** | `perpetua_core/satellites/scheduler.py` | `CRON_TICK`, `CRON_MISSED` |
| `lib/setup/` (env.template, setup UI) | **Env Bootstrap Satellite** | `perpetua_core/satellites/env_bootstrap.py` | `ENV_READY`, `ENV_MISSING_REQUIRED` |
| `lib/server/channels/` (Telegram, Discord, webhooks) | **Channel Satellite** | `perpetua_core/satellites/channels.py` | `CHANNEL_MESSAGE`, `CHANNEL_DOWN` |
| `lib/agents/` (local model routing) | **Agent Router Satellite** | `perpetua_core/satellites/agent_router.py` | `MODEL_AVAILABLE`, `MODEL_DOWN` |
| `lib/mcp/alphaclaw-mcp.js` (mgmt surface) | **OpenClaw MCP Satellite** | PT `packages/alphaclaw-mcp` (already there) | (via adapter, not GossipBus) |
| `lib/server/routes/` (management REST API) | **REST API Satellite** (maps to v2.1 Public Plugin API) | `perpetua_core/api/` | (HTTP surface, not GossipBus) |

### V1-hack-to-satellite mapping (`docs/v2/10` §1)

| V1 Hack | Satellite | v2.1 Task |
|---------|-----------|-----------|
| Manual path `sed` in setup_macos.py | Sentinel Node (path expansion via `Path.home()`) | `Task 3.1` |
| Manual `find . -name "*.pyc" -delete` | GC Worker (background bytecode GC) | `Task 3.2` |
| Manual `lsof -ti:PORT | xargs kill` | Port Manager (orchestrator-level port leasing) | `Task 3.3` |
| Hardcoded Node.js shebangs | Env Validator (kills if Node < 22) | `Task 3.4` |
| Redundant `discover.py` + `start.sh` IP logic | Gossip Hub (network_autoconfig.py → GossipBus) | `Task 3.5` |
| Manual `openclaw devices approve` | Auth Handshake Satellite (automated via L2 manager) | `Task 3.6` |
| Manual symlink creation | Link Watcher (5-state guard from `11-idempotency-patterns.md`) | `Task 3.7` |

### v2.1 Module implementation plan

**Milestone: v2.0 (kernel only, currently blocking)**
- MiniGraph engine.py (~70 lines) ← already specced
- PerpetuaState, LLMClient, HardwarePolicyResolver, GossipBus ← already specced
- All Tier-3 features as plugins: checkpointer, interrupts, subgraphs, tool, streaming, structured output

**Milestone: v2.1 (satellite modules + public API)**

Task 3A — Implement the 7 Orbit satellites listed above, each as a MiniGraph subgraph exposed via `as_node()`:
```python
# Pattern (same for all satellites):
from perpetua_core.graph.subgraphs import as_node
from perpetua_core.graph.engine import MiniGraph

watchdog_sg = as_node(build_watchdog_subgraph())
app_graph = MiniGraph()
app_graph.add_node("watchdog", watchdog_sg)
```

Task 3B — Implement `docs/v2/02-modules/multi-agent-network.md` (stub → code)
- Each worker type as a MiniGraph node
- Parallel group execution via `WorkerAssignment.parallel_group`
- Depth=0 enforced at kernel level

Task 3C — Implement `docs/v2/02-modules/mcp-optional-transport.md` (stub → code)
- MCP as optional transport layer over existing HTTP surface
- Kernel unchanged; satellite handles MCP session lifecycle

Task 3D — Implement `docs/v2/02-modules/rag-and-memory.md` (stub → code)
- LanceDB + bge-m3 for RAG/session memory (decided 2026-05-15: `orama-system CLAUDE.md §8`)
- Coexists with gbrain (pgvector); LanceDB = orama job/decision history

Task 3E — Implement `docs/v2/02-modules/plugin-api-public.md` (v2.1 promotion steps)
- `/v1/run`, `/v1/route`, `/v1/policy`, `/v1/health`
- `X-API-Version` header on every route
- OpenAPI spec published to `oramasys/agate/`
- Bump to `oramasys` v2.1.0

Task 3F — Port OpenClaw primitives identified above as v2.1 satellite plugins
- Each satellite: `perpetua_core/satellites/<name>.py`
- Interface: emit to GossipBus, kernel reads, optional veto
- Tests: `tests/test_satellite_<name>.py`

---

## § 4 — Build Order (Cross-Repo Lockstep)

```
Phase 1 (Verification — no code changes):
  1.1 Verify start.sh wiring
  1.2 Verify alphaclaw_manager.py bootstrap path
  1.3 Verify zero direct orama→AlphaClaw calls
  1.4 Verify Python→JS adapter bridge mechanism
  1.5 Verify .mcp.json registration

Phase 2 (Migration — PT + AlphaClaw):
  2A.1-4 Complete alphaclaw-mcp 11-tool parity
  2B.1-3 Verify + clean lib/agents duplication
  2C.1-2 Remove AlphaClaw lib/mcp after parity
  2D.1-4 Verify UNIFIED-ABSORPTION-PLAN compliance

Phase 3 (v2.1 planning — perpetua-core + orama-system docs):
  3A    Implement 7 Orbit satellites
  3B    Multi-agent network module
  3C    MCP-Optional transport module
  3D    RAG + memory (LanceDB)
  3E    Public Plugin API v2.1
  3F    Port AlphaClaw features as satellite plugins
```

---

## Acceptance Criteria

**Goal 1 complete when:**
- `grep -r "alphaclaw_manager\|AlphaClawManager" orama-system/ --include="*.py"` shows ZERO direct instantiation (only delegation)
- `grep -rn "node.*AlphaClaw/lib\|require.*AlphaClaw" orama-system/ Perpetua-Tools/` returns 0
- `.mcp.json` registers PT `packages/alphaclaw-mcp` only

**Goal 2 complete when:**
- `packages/alphaclaw-mcp` has all 11 tools, all tests green
- `AlphaClaw/lib/mcp/` and `AlphaClaw/lib/agents/` are deleted
- UNIFIED-ABSORPTION-PLAN grep acceptance criteria return 0
- AlphaClaw CI (`feature/MacOS-post-install`) remains green after cleanup

**Goal 3 complete when:**
- `docs/v2/02-modules/` README shows all modules as "In Progress" not "Stub"
- `perpetua_core/satellites/` has at least Watchdog + Agent Router implemented
- `docs/v2/10-v1-hacks-automation-orbit.md` §1 table updated with implementation status
- Public Plugin API has OpenAPI spec draft

---

## GSTACK REVIEW REPORT
<!-- Placeholder — to be filled by /autoplan review pipeline -->
