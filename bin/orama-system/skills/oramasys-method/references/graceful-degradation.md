# Graceful degradation & fallback ladders

Unified doctrine for **oramasys-method** (search + reasoning) and **perpetua-model-selection**
(inference + orchestration). Aligns with PT fail-closed gateways vs discovery-tool graceful
degrade (`lesson_b5d28f5d6e08`).

**Rule:** Stop at the **first tier that answers**. State the fallback in one line when
escalating. Never parallel-fire expensive tiers.

---

## Ladder A — Context & search (oramasys-method)

From `search-frugality.md`:

```text
gbrain → CRG → Grep (exact) → Brave → Perplexity → Grok
```

| Step | When | On miss / error |
|------|------|-----------------|
| gbrain | Semantic intent, past decisions | → CRG or harness-local search |
| CRG | Multi-file blast radius | → gbrain code-def → Grep |
| Grep | Known exact string / regex | → next tier only if still blocked |
| Brave | External facts, docs | → Perplexity (ask operator first) |
| Perplexity / Grok | Paid last resort | Document why local tiers failed |

**Heavy reasoning:** `mcp-oramasys` when exposed → else `POST /oramasys` :8001 → else inline
Mode 1/2 in current harness.

**Harness unavailable tier:** Briefly name the missing tool; use cheapest local equivalent
(file Read on confirmed paths, targeted Grep) before web/paid.

---

## Ladder B — Model & inference (perpetua-model-selection)

### B1 — Host-local primary (hardware affinity, fail-closed)

| Host | Primary | Validated fallbacks (same host) |
|------|---------|----------------------------------|
| Mac | Ollama warm / MLX 9B | glm-5.1:cloud probe → MLX 9B |
| Win | LM Studio 27B `:1234` | qwen3-coder:14b → gemma-4-26b → Ollama critic |

**Never** cross-list MLX on Win or 27B CUDA paths on Mac.

### B2 — Cloud budget (hard cutoff → local)

```text
Privacy-critical → always local (skip cloud)
Budget exhausted / offline → qwen3-30b-critic (Win) or Mac local stack
Strategic / realtime cloud triggers → Perplexity only if budget guard allows
```

On exceed: `fallback_on_exceed` in SKILL.md — **no silent cloud retry**.

### B3 — Orchestration state

```text
Redis (multi-instance v1.1+) → .state/agents.json + .state/budget.json (MVP)
PT hardware policy API → cache YAML (DR only, CRITICAL warning)
```

### B4 — Autoresearch GPU preflight (coord-003 spike)

```text
AUTORESEARCH_PREFLIGHT_MODE=auto:
  GPU_BOX host local? → http-local (git + GET /v1/models)
  else → SSH legacy (Mac → Win remote)
Force: http-local | ssh
```

SSH paths (`deploy_train_py`, `run_experiment_on_gpu`) remain until next cycle.

---

## Ladder C — LAN co-orchestration (Mac ↔ Win)

| Capability | Primary | Degraded |
|------------|---------|----------|
| Work handoff | `lan_peer_assign.py` file inbox | Fan-out `partial` — local OK, peer retry later |
| Live signal | ws-peer WebSocket | SSE+POST (`lan_peer_channel.py`) |
| Win inbox UI | `/peer-inbox` (`platform/windows/`) | `/co-orchestration/windows` → 307 redirect |
| Mac inbox UI | `/co-orchestration/macos` | `/co-orchestration` (Mac role only) |
| Remote agent exec | **Not supported** | Each host runs PATH agents locally |
| Subagent parallel | Task / harness subagents | Direct parent execution on usage limit |

**Probe gate:** `probe_lan_peer.py` green before fan-out GO. `portal-health` PASS alone does
not prove `/api/peer-file` or `/` dashboard (restart after pull).

---

## Ladder D — Portal & control plane

```text
Loopback HTML shell → token injected in page (no Bearer on GET /, /peer-inbox, /co-orchestration/*)
LAN API → Authorization required (joint PT + orama tokens)
Peer inbox mirror → local list; remote via HTTP to peer :8002/api/peer-inbox
Markdown preview → server-side render (Win); marked.js CDN (Mac co-orchestration)
```

On peer fetch failure: return structured `{ok: false, error}` — UI shows err panel, 15s refresh.

---

## Ladder E — Subagent & spawn (frugality under load)

```text
Mode 3 parallel subagents (orchestrator fan-out)
  → single subagent Task
  → parent inline execution (document blocker)
  → file inbox drop for peer host to pick up
```

Branch policy: `subagent/<role>/<topic>` for mutations; coordination stays on `main` via inbox.

---

## Anti-patterns

| Violation | Why |
|-----------|-----|
| Parallel gbrain + Brave + Perplexity | Frugality burn |
| Silent cloud when budget exceeded | Violates BUDGET_GUARD |
| SSH preflight on local Win GPU host | 90s timeout blocks co-orchestration |
| Remote cursor-agent / Hermes RPC over LAN | Not implemented — use file drops |
| Fail-open on hardware affinity | Use explicit error + local fallback list |

---

## Verification triggers

- After pull: restart `start.ps1 --lan-peer` / `start.sh --lan-peer` before probing `/` or peer-file
- Win autoresearch: `preflight()` shows `preflight_mode=http-local` when on GPU host
- Search task: can you cite which ladder step answered without skipping local tiers?
