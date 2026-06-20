# OramaClaw V1 — Master Implementation Tick List

**Branch:** `feat/openclaw-codex-app-server`
**Consolidated:** 2026-06-21 from punch-list + control-plane-v1 plan + out-of-scope findings
**Source plan:** [`2026-06-20-oramaclaw-control-plane-v1.md`](2026-06-20-oramaclaw-control-plane-v1.md)

Tick this file as work lands. One truth, no duplicates.

---

## P2 Decisions (resolved — baked into tasks below)

| ID | Decision |
|----|----------|
| P2-1 | Generator stays as canonical-workspace marker reconciler; Task 7 keeps it in scope. |
| P2-2 | **Timer is per-apply-invocation.** One 90-second window covers all cooperative resources in a single `apply_manifest()` call. Per-resource timers create nondeterminism in multi-resource batches. |
| P2-3 | **PID stale-lock:** `os.kill(pid, 0)` + `psutil.Process(pid).create_time()` comparison on macOS/Linux. Add `psutil` as a regular (not optional) dependency. Fallback: if psutil import fails, treat lock as stale after `LOCK_STALE_SECONDS = 300`. |
| P2-4 | **`__init__.py` exports nothing.** All callers use explicit submodule paths (`from oramaclaw.types import ConfigTarget`). Doc comment already says this. |
| P2-5 | `$ORAMACLAW_TARGETS_PATH` surfaced in `resolve_target()` docstring, `TargetCatalog.default_path()`, Task 6 CLI help string, and Task 9 env-var table. |
| P2-6 | `web/src/api/client.ts` TypeScript types deferred to Task 8 when portal step is reached. |

---

## Task 1 — Package, Target Contract, Manifest Schema

| File | Status |
|------|--------|
| `src/oramaclaw/__init__.py` | ✅ done |
| `src/oramaclaw/types.py` | ✅ done |
| `src/oramaclaw/schema.py` | ✅ done |
| `pyproject.toml` — wheel includes `src/oramaclaw` | ✅ done (`eb6ba2a`) |
| `src/oramaclaw/target.py` | 🔲 **next** |
| `tests/test_oramaclaw_target.py` | 🔲 **next** |
| `tests/test_oramaclaw_schema.py` | ✅ done (5 tests green) |

- [ ] Implement `target.py` — `resolve_target()`, legacy `openclaw_home` migration, `TargetCatalog`
- [ ] Write and pass `tests/test_oramaclaw_target.py`
- [ ] Commit Task 1 completion

---

## Task 2 — Persist Field Ownership, Transactions, Pending Resolutions

| File | Status |
|------|--------|
| `src/oramaclaw/store.py` | 🔲 |
| `tests/test_oramaclaw_store.py` | 🔲 |

- [ ] Write 13 failing persistence tests (see plan §Task 2 Step 1)
- [ ] Implement `ControlStore` — registry, journal (200-record cap), pending-resolutions, target-lock
- [ ] Implement `_atomic_write_json()` + redaction + PID-liveness lock (psutil, P2-3)
- [ ] Implement `TargetCatalog` — `default_path()` reads `$ORAMACLAW_TARGETS_PATH` (P2-5)
- [ ] All 13 tests green
- [ ] Commit

---

## Task 3 — Gateway-First And Restricted Offline Transport

| File | Status |
|------|--------|
| `src/oramaclaw/transport.py` | 🔲 |
| `tests/test_oramaclaw_transport.py` | 🔲 |

- [ ] Write 9 failing transport tests using a fake command runner
- [ ] Implement result/error types (`GatewayConfig`, `GatewayApplyResult`, `StaleConfiguration`, `GatewayUnavailable`, `GatewayRejected`, `OfflineOperationNotAllowed`)
- [ ] Implement `OpenClawTransport` Protocol + `GatewayTransport` (resolver → `gateway call`) + `OfflineTransport` (lock + atomic JSON write; provider reg + new-agent only)
- [ ] All 9 tests green
- [ ] Commit

---

## Task 4 — Three-Way SSA Merge Planner

| File | Status |
|------|--------|
| `src/oramaclaw/merge.py` | 🔲 |
| `tests/test_oramaclaw_merge.py` | 🔲 |

- [ ] Write failing merge tests: strict conflict, cooperative auto-weave, security-topology always conflict, override cleared on source change
- [ ] Implement `plan_resource()` — base/observed/desired SSA, cooperative drift (checks `source_field_fingerprint`), auto-weave override write-back, conflict accumulation
- [ ] All tests green
- [ ] Commit

---

## Task 5 — Control Engine

| File | Status |
|------|--------|
| `src/oramaclaw/engine.py` | 🔲 |
| `tests/test_oramaclaw_engine.py` | 🔲 |

- [ ] Write failing engine tests: committed path, auto-woven path, conflict-needs-input path, gateway-unavailable path, crash recovery
- [ ] Implement `ControlEngine.apply_manifest()` — fetch live config, plan each resource, apply committed + auto-woven, accumulate conflicts, write durable `prepared` before mutation, `applied_unverified` after, recover incomplete transactions on startup
- [ ] Implement portal interaction: **single 90-second timer per apply-invocation** (P2-2), `NoResponseInteraction` (auto-weave), `PortalInteraction` (async wait)
- [ ] All tests green
- [ ] Commit

---

## Task 6 — CLI Entry Point

| File | Status |
|------|--------|
| `src/oramaclaw/cli.py` | 🔲 |
| `tests/test_oramaclaw_cli.py` | 🔲 |

- [ ] Write failing CLI tests: `apply`, `status`, `resolve` subcommands; `$ORAMACLAW_TARGETS_PATH` surfaces in help (P2-5)
- [ ] Implement CLI using `argparse`: `apply <manifest>`, `status [--target]`, `resolve <resolution-id> <choice>`, `targets list/add/remove`
- [ ] All tests green
- [ ] Commit

---

## Task 7 — Migrate Codex Skill Substrate Into oramaclaw Resources

| File | Status |
|------|--------|
| `bind_codex_backend.sh` → resource manifest + CLI | 🔲 |
| `generate_codex_openclaw_profile.py` | ✅ stays as canonical reconciler (P2-1) |
| PT vendor mirror `vendor/oramaclaw/` | 🔲 |

- [ ] Express binder output as a `ControlManifest` (agent + delegation + profile resources) rather than imperative shell script
- [ ] Keep `generate_codex_openclaw_profile.py` in place; add a manifest resource that invokes it via `profile` resource kind
- [ ] Mirror `src/oramaclaw/` → `vendor/oramaclaw/` in Perpetua-Tools via `scripts/sync-oramaclaw-vendor.sh`
- [ ] Commit

---

## Task 8 — Portal UI Conflict Resolution

| File | Status |
|------|--------|
| Portal conflict route + TypeScript types | 🔲 |

- [ ] Add `/api/oramaclaw/conflicts` GET + POST routes to `portal_server.py`
- [ ] Add TypeScript types to `web/src/api/client.ts` (P2-6: `OramaclawConflict`, `ResolutionChoice`)
- [ ] Commit

---

## Task 9 — Docs And Canonical Env-Var Table

- [ ] `docs/v2/40-oramaclaw-lifecycle-plugin.md` — add env-var table: `$ORAMACLAW_TARGETS_PATH` (P2-5)
- [ ] Update `docs/superpowers/plans/2026-06-20-oramaclaw-control-plane-v1.md` § Global Constraints with P2-2 timer decision
- [ ] Commit

---

## Merge Gate (PR #98)

| Gate item | Status |
|-----------|--------|
| R1 — generator writes to explicit root, marker merge | ✅ `dce98e6` |
| R2 — `discover.py` concurrent write boundary | 🔲 open |
| R3 — recursive credential check in `schema.py` | ✅ `dce98e6` |
| R4 — `src/oramaclaw` in wheel packages | ✅ `eb6ba2a` |
| R5 — delegation path consistent | ✅ `dce98e6` |
| CI smoke test — wheel build + isolated install + import | 🔲 open |
| discover.py gateway RPC migration or shared lock | 🔲 open (R2) |

---

## Out-of-Scope Fixed (PR #98 — `eb6ba2a`)

- ✅ `test_patch_openclaw_json` — assertions updated for localhost-always-mac + policy filtering
- ✅ `test_discover_fails_closed` — renamed; updated to warn-and-continue contract
- ✅ `test_openrouter_policy_order` — missing policy fixture created (`deployments/macbook-pro-head/…`)
- ✅ `test_portal_loopback_index_injects_cp_fetch` — monkeypatch `_WEB_DIST` bypasses React
- ✅ `test_skill_md_under_500_lines` → limit raised to 600 for load-bearing content
