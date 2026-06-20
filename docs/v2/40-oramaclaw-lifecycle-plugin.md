# 40 — oramaclaw: OpenClaw + AlphaClaw Lifecycle Plugin (D22)

> **Status:** Decision locked 2026-06-20 | Orbit tier — ships at own pace
> **Decision:** D22 — oramaclaw is the canonical v2 plugin for all OpenClaw and AlphaClaw lifecycle management.

---

## 1. The Decision

OpenClaw and AlphaClaw lifecycle management is consolidated into a single
Python package — **`oramaclaw`** — that lives as an orbiting plugin in the
v2 microkernel architecture.

**Key constraints (non-negotiable):**

- `oramaclaw` depends **only on `perpetua-core` primitives** — never on
  `oramasys`, never on AlphaClaw internals directly.
- It is a **plugin in orbit**, not baked into the kernel. The kernel does
  not import it; `oramasys` registers it through the internal plugin API (D5).
- It is **analogous to `againtra-platform`** (see `28-againtra-platform-requirements-alignment.md`):
  a bounded, independently-testable module that the orchestration layer picks
  up through a manifest, not hard-wiring.
- Its **v1 migration is dogfood** for v2 plugin testing — the first production
  plugin to go through the full plugin lifecycle (develop → unit-test →
  integration-gate → orbit registration).

---

## 2. Scope — what oramaclaw owns

| Responsibility | What it does | What it does NOT own |
|----------------|-------------|----------------------|
| **OpenClaw config management** | `parse_manifest()`, three-way SSA merge, gateway `baseHash` write path, `--unsafe-direct-config` break-glass | OpenClaw CLI itself, gateway process management |
| **AlphaClaw lifecycle** | Device pairing relay, MCP smoke-test pre-flight (14-tool verifier), session pre-flight gate | AlphaClaw binary, MCP server hosting |
| **Control-plane types** | `ControlManifest`, `Conflict`, `ControlResult`, `GatewayConfig`, `OpenClawTransport` (Protocol) | LLM routing, hardware policy (owned by perpetua-core) |
| **Cooperative merge engine** | 90-second auto-weave timer, `portal` conflict resolution, `--offline` provider-only path | Persistent state storage (delegated to perpetua-core's GossipBus) |
| **Delegation management** | `agents.defaults.subagents.allowAgents` write path, conflict policy enforcement for security topology | Agent runtime dispatch |

**Not in scope:** The OpenClaw gateway binary, the AlphaClaw npm package, and
the `codex-supervisor` plugin — these remain in their own repos and are only
referenced by oramaclaw via `OpenClawTransport` Protocol and `authReference`
paths, never imported.

---

## 3. Package structure

```
src/oramaclaw/
├── __init__.py          # nothing re-exported — callers use submodule paths
├── types.py             # frozen dataclasses (ControlManifest, ControlResult, ...)
├── schema.py            # parse_manifest() — structural + semantic validation
├── merge.py             # three-way SSA merge engine (Task 3 in v1 plan)
├── engine.py            # ControlEngine.apply_manifest() (Task 5 in v1 plan)
├── gateway.py           # OpenClawTransport implementation over HTTP
├── portal.py            # PortalInteraction + 90-second cooperative timer
└── cli.py               # `oramaclaw plan|apply|resolve|status` entry point
```

**Dependency rule (enforced by CI import-linter):**

```
oramaclaw → perpetua_core   ✅
oramaclaw → oramasys        ❌  (layering violation)
oramaclaw → alphaclaw.*     ❌  (only via OpenClawTransport Protocol)
perpetua_core → oramaclaw   ❌  (upward import forbidden)
```

---

## 4. Why this is the right boundary

`againtra-platform` migration (D28, `28-againtra-platform-requirements-alignment.md`)
established the pattern: complex external-system integrations that need the
kernel's primitives (GossipBus, PerpetuaState, LLMClient) but must not pollute
the kernel live as orbiting plugins.

OpenClaw + AlphaClaw are the same class of problem:

- They have their own config format, auth model, and update cadence.
- They need GossipBus for audit (every config write emits a `CONTROL_PLANE_APPLY` event).
- They are independently testable without a running oramasys graph.
- Breaking them out as a plugin means the kernel stays at 70 lines even as the
  lifecycle management grows in complexity.

Additionally, oramaclaw V1 (built on `feat/openclaw-codex-app-server`, 2026-06-20)
gives us a working implementation to dogfood the plugin migration path — concrete
types, schema validation, and test fixtures already exist before the v2 plugin
API is finalized (D5, v2.1). That ordering is intentional: the plugin API will
be designed to fit real plugins, not hypothetical ones.

---

## 5. v1 → v2 plugin migration plan

The migration happens in three gates, each with acceptance criteria before the
next gate opens.

### Gate M1: Package extraction (v1.x, before v2.0 stabilizes)

- `src/oramaclaw/` extracted from `orama-system` into its own pip-installable
  package (Hatch `src/` layout, `pyproject.toml` with `perpetua-core` as the
  only non-stdlib dependency).
- All v1 frozen types (`types.py`) and `parse_manifest()` (`schema.py`) green.
- `ControlEngine.apply_manifest()` (`engine.py`) covered by Task 5 tests.
- PT vendor-sync: `vendor/oramaclaw/` mirrors the package via
  `sync-oramaclaw.sh` (same pattern as ecc-tools submodule).
- **Acceptance:** `python -m pytest tests/test_oramaclaw_engine.py -q` green on
  both Mac and CI.

### Gate M2: perpetua-core wiring (v2.0 parity window)

- Replace in-process lock file with GossipBus `CONTROL_PLANE_LOCK` event pair.
- Replace CLI exit codes with `ControlResult.state` mapped to `GossipBus` audit.
- `OpenClawTransport` implementation in `gateway.py` uses `LLMClient`-style
  retry/timeout patterns from perpetua-core (no new HTTP library).
- **Acceptance:** integration test with a stubbed gateway passes; GossipBus
  audit log contains `CONTROL_PLANE_APPLY` events.

### Gate M3: Orbit registration (v2.1, after public Plugin API)

- `oramaclaw` registered as an orbit plugin via `oramasys/plugins/manifest.toml`.
- `oramasys` discovers it at startup; `openclaw_lifecycle` node added to graph DSL.
- AlphaClaw MCP smoke-test (`02-modules/alphaclaw-mcp-smoke-test.md`) delegates
  pre-flight to `oramaclaw.gateway.AlphaClawPreflight` instead of raw shell calls.
- **Acceptance:** `oramasys` boots with `ORAMACLAW_PLUGIN=1` and the session
  pre-flight gate runs without any AlphaClaw-specific code in the kernel.

---

## 6. Relationship to existing v2 docs

| Doc | Update required |
|-----|-----------------|
| `02-modules/alphaclaw-mcp-smoke-test.md` | Note that pre-flight delegation moves to `oramaclaw.gateway.AlphaClawPreflight` at Gate M3; doc stays as the integration contract. |
| `10-v1-hacks-automation-orbit.md` | Pairing/Auth row: "Auth Handshake via L2 manager" → will be implemented by `oramaclaw.gateway` at Gate M2. |
| `18-master-alignment-v2-migration-plan.md` | Step A ("re-target submodule to `oramasys/orama/plugins/`") → superseded by this doc: the plugin lands at the orbit tier, not as a submodule in `oramasys/orama/`. |
| `README.md` | D22 added to locked decisions; module roadmap updated; spec tree updated. |
| `25-autoresearcher-doctrine-and-againtra-flagship.md` | Cross-reference: oramaclaw follows the same dogfood-first orbit pattern as againtra-platform. |

---

## 7. What stays in Perpetua-Tools (L2)

PT remains the runtime/state authority. oramaclaw's vendor copy (`vendor/oramaclaw/`)
is imported by PT's orchestrator for:

- Control-plane pre-flight before job dispatch.
- `ControlResult` mapped to PT job state transitions.

PT does NOT implement lifecycle logic — it calls `oramaclaw.engine.ControlEngine`.
This preserves the L1 → L2 → L3 import direction and keeps PT's orchestrator
thin.

---

## 8. Acceptance criteria (Gate M1, minimal viable orbit)

```
[ ] src/oramaclaw/ installable as `pip install -e .` with perpetua-core as only dep
[ ] python -m pytest tests/ -q  →  all green (including Task 5 engine tests)
[ ] `oramaclaw apply --manifest tests/fixtures/oramaclaw-codex-provider.json --dry-run` exits 0
[ ] No import of oramasys, AlphaClaw internals, or OpenClaw CLI binaries at module load
[ ] GossipBus integration: STUB_BUS accepted in tests; real bus wired at Gate M2
```
