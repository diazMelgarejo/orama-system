# alphaclaw-mcp-smoke-test — OpenClaw Session Opener / MCP Verifier

**Module:** `alphaclaw-mcp-smoke-test`
**Target version:** v2.1
**Status:** Spec — ready to implement
**Blocking:** No
**Source:** Perpetua-Tools `packages/alphaclaw-mcp` v0.9.16.9 (14 tools, canonical)
**Layer:** Perpetua-Tools L2 → orama-system L3 handshake boundary
**PR reference:** diazMelgarejo/Perpetua-Tools#27 (`2026-05-22-001-alphaclaw-mcp-gate2-14tools`)

---

## Purpose

This module is the **OpenClaw session opener and gateway verifier**. Every orama-system
session that touches AlphaClaw begins here. It smoke-tests all 14 tools in
`packages/alphaclaw-mcp` against a live AlphaClaw instance and returns a
structured readiness report — before any task is dispatched.

Two responsibilities:

1. **Smoke-test** — exercise every tool in `alphaclaw-mcp`, capture pass/fail +
   latency per tool, surface actionable errors.
2. **Session opener** — if the smoke-test passes the threshold, emit a
   `SessionReady` event that unblocks orama-system's dispatch queue. If it
   fails, the queue remains blocked and the report is surfaced to the operator
   (HITL gate).

This is not a health check. It is a **contract verifier** — it proves that the
MCP server's public interface matches the tool contract documented in
`docs/adapter-interface-contract.md` before any real work begins.

---

## Why v2.1 (not v2.0)

The v2.0 kernel is complete and non-kernel modules are non-blocking. This module
is v2.1 because:

- It depends on `alphaclaw-mcp` being stable (gate: PR #27 merged to main, Gate 2
  smoke-tested)
- It introduces the first `SessionReady` event into the kernel's event bus — that
  extension lands in v2.1 with the public Plugin API
- The `dispatch_node` timeout/retry policy it enforces is a v2.1 contract item

A stub is acceptable in v2.0; the full implementation is v2.1.

---

## Tool map (14 tools, execution order)

The smoke-test exercises tools in dependency order: no-auth first, file-based
second (offline-capable), process-spawning third, authenticated last.

### Group A — No-auth / gateway probe (fail-fast)

| # | Tool | What is verified | Threshold |
|---|------|-----------------|-----------|
| 1 | `alphaclaw_health` | Gateway process reachable, HTTP 200 | **Required** — if this fails, skip groups C+D |
| 2 | `alphaclaw_check_env` | `.env` exists, `SETUP_PASSWORD` set | **Required** — if missing, login will fail |
| 3 | `alphaclaw_tail_logs` (lines=5) | Log file accessible, returns `found:true` | Advisory |

### Group B — File-based / offline-capable

| # | Tool | What is verified | Threshold |
|---|------|-----------------|-----------|
| 4 | `alphaclaw_read_config` | `openclaw.json` parseable, no raw secrets in output | **Required** |
| 5 | `alphaclaw_list_providers` | `providers` field is an **array** (not numeric-keyed object) | **Required** — validates P2 array-redaction fix |

### Group C — Authenticated (requires Group A pass + login)

| # | Tool | What is verified | Threshold |
|---|------|-----------------|-----------|
| 6 | `alphaclaw_login` | Session cookie obtained | **Required** for group C+D |
| 7 | `alphaclaw_status` | Returns `running:true` with port | **Required** |
| 8 | `alphaclaw_watchdog_logs` (lines=10) | Returns structured watchdog data | Advisory |

### Group D — Process-spawning (run in AlphaClaw project root)

| # | Tool | What is verified | Threshold |
|---|------|-----------------|-----------|
| 9 | `alphaclaw_build_ui` | `exit_code:0`, no esbuild ARM64 errors | Advisory |
| 10 | `alphaclaw_run_tests` (suite=watchdog) | 14 watchdog tests green | Advisory |

### Group E — Local agent delegation

| # | Tool | What is verified | Threshold |
|---|------|-----------------|-----------|
| 11 | `local_agent_health` | At least one backend (Ollama OR LM Studio) reachable | Advisory |
| 12 | `local_agent_list_models` | Non-empty model list returned | Advisory |
| 13 | `local_agent_ask_about_code` (probe file + trivial question) | Response received, no error | Advisory |
| 14 | `local_agent_propose_edit` (probe file + trivial instruction) | Diff returned, marked review-only | Advisory |

**Required** = blocks `SessionReady`. **Advisory** = recorded in report, does not block.

---

## Output contract

```python
from dataclasses import dataclass, field
from typing import Literal

@dataclass
class ToolResult:
    name: str
    group: Literal["A", "B", "C", "D", "E"]
    passed: bool
    latency_ms: float
    error: str | None = None
    notes: str | None = None

@dataclass
class SmokeTestReport:
    session_id: str
    timestamp_utc: str
    alphaclaw_root: str
    gateway_url: str
    required_passed: int
    required_total: int
    advisory_passed: int
    advisory_total: int
    ready: bool  # True iff all Required tools passed
    tools: list[ToolResult] = field(default_factory=list)
    blocking_errors: list[str] = field(default_factory=list)
```

`SmokeTestReport.ready = True` emits `SessionReady` event.
`SmokeTestReport.ready = False` raises `AlphaClawNotReady(report)` — caught at
the orama-system dispatch layer, which surfaces to the HITL gate.

---

## Integration into orama-system dispatch

```
orama-system session start
  │
  ▼
alphaclaw_mcp_smoke_test.run()
  │
  ├── SmokeTestReport.ready = True  →  dispatch_node unblocked  →  task queue runs
  │
  └── SmokeTestReport.ready = False →  AlphaClawNotReady raised
                                        │
                                        ▼
                                    HITL gate (operator notified)
                                    blocking_errors surfaced
                                    session held until manual clear or retry
```

The `run()` call is injected into `orama_bridge.py` (PT→orama handshake) before the
first `dispatch_node` is entered. This is not a background check — it is a
**synchronous pre-flight gate**.

---

## Module structure (PT side, v2.1)

```
Perpetua-Tools/
└── packages/
    └── alphaclaw-mcp-smoke-test/          ← NEW package
        ├── package.json                   v0.9.16.9, ESM
        ├── src/
        │   ├── index.ts                   ← run() + SmokeTestReport export
        │   ├── groups.ts                  ← A/B/C/D/E group runners
        │   └── report.ts                  ← SmokeTestReport type + formatter
        └── scripts/
            └── smoke-test.ts              ← CLI entrypoint: npx alphaclaw-smoke-test
```

## Module structure (orama side, v2.1)

```
orama-system/
└── orchestrator/
    └── alphaclaw_smoke_gate.py            ← Python wrapper: calls Node smoke-test
                                              via subprocess, parses JSON report,
                                              raises AlphaClawNotReady if not ready
```

`alphaclaw_smoke_gate.py` is the canonical orama-system integration point. It calls
the TypeScript smoke-test as a subprocess (same CLI+subprocess pattern as
`alphaclaw_manager.py`), reads the JSON report on stdout, and raises or returns.

---

## CLI entrypoint (operator-facing)

```bash
# Run from Perpetua-Tools root — requires live AlphaClaw
SETUP_PASSWORD=<pass> npx alphaclaw-smoke-test

# JSON report to stdout (for pipe/CI)
SETUP_PASSWORD=<pass> npx alphaclaw-smoke-test --json

# Advisory-only mode (skip groups D+E for fast check)
SETUP_PASSWORD=<pass> npx alphaclaw-smoke-test --fast
```

Output (human-readable):
```
AlphaClaw MCP Smoke Test v0.9.16.9
===================================
Group A — Gateway probe
  ✅ alphaclaw_health        12ms
  ✅ alphaclaw_check_env      3ms
  ✅ alphaclaw_tail_logs      8ms
Group B — File-based
  ✅ alphaclaw_read_config    4ms
  ✅ alphaclaw_list_providers 4ms  (providers[] is array ✓)
Group C — Authenticated
  ✅ alphaclaw_login         45ms
  ✅ alphaclaw_status        18ms
  ✅ alphaclaw_watchdog_logs 22ms
Group D — Process-spawning
  ✅ alphaclaw_build_ui     3210ms
  ✅ alphaclaw_run_tests     890ms  Tests 14 passed
Group E — Local agents
  ✅ local_agent_health       95ms  ollama:ok lmstudio:ok
  ✅ local_agent_list_models 110ms  12 models
  ✅ local_agent_ask_about_code 2400ms
  ✅ local_agent_propose_edit  1900ms

Required: 5/5 passed   Advisory: 9/9 passed
SESSION READY ✓
```

---

## Gate 2 → v2.1 migration path

The existing Gate 1 smoke-test (`packages/alphaclaw-adapter/scripts/smoke-test.js`,
25 HTTP methods) tests the **adapter HTTP client**. This module tests the **MCP
server tool contract**. They are complementary, not overlapping.

Migration checklist (v2.1 gate):
- [ ] PR #27 merged to `feat/openclaw-skills-spawn-helper` → main
- [ ] `alphaclaw-mcp-smoke-test` package scaffolded in PT
- [ ] All 14 tools pass against a live AlphaClaw instance (SETUP_PASSWORD in .env)
- [ ] `alphaclaw_smoke_gate.py` integrated into `orama_bridge.py` pre-flight
- [ ] `SessionReady` event added to kernel event bus (v2.1 Plugin API gate)
- [ ] CI gate: `smoke-test --fast` runs on every PT PR (groups A+B only — no live instance needed)
- [ ] HITL accountability: `AlphaClawNotReady` surfaced to operator per `HUMAN-IN-LOOP-ACCOUNTABILITY.md`

---

## Design invariants (must not violate)

- Smoke-test NEVER writes to disk or mutates AlphaClaw state — read-only + advisory process calls only
- `local_agent_propose_edit` patch is returned but never applied — smoke-test validates the contract, not the content
- Subprocess pattern for Python→Node bridge (same as `alphaclaw_manager.py`) — no Python requiring Node internals
- Report JSON is written to stdout only — never to a file — to keep the caller in control
- Timeout per tool: 10s for HTTP tools, 30s for process-spawning, 15s for local agents
- Total run time cap: 120s (fast mode: 30s)

---

## Cross-references

| What | Where |
|------|-------|
| MCP server being tested | `packages/alphaclaw-mcp/src/index.ts` (Perpetua-Tools) |
| Adapter HTTP client | `packages/alphaclaw-adapter/src/index.js` (Perpetua-Tools) |
| Adapter HTTP smoke-test | `packages/alphaclaw-adapter/scripts/smoke-test.js` |
| AlphaClaw bridge (Python) | `orchestrator/alphaclaw_manager.py` (Perpetua-Tools) |
| orama handshake point | `orchestrator/orama_bridge.py` (orama-system) |
| HITL accountability | `docs/HUMAN-IN-LOOP-ACCOUNTABILITY.md` (orama-system) |
| MCP transport module | `docs/v2/02-modules/mcp-optional-transport.md` |
| Gate 2 migration log | `docs/MIGRATION.md` Gate 2 (Perpetua-Tools) |
| OpenClaw plan | `docs/plans/2026-05-22-alphaclaw-wiring-migration-v2-satellites.md` (Perpetua-Tools) |
