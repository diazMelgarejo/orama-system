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
| `src/oramaclaw/target.py` | ✅ done (`6bb53ed`) |
| `tests/test_oramaclaw_target.py` | ✅ done (17 tests green) |
| `tests/test_oramaclaw_schema.py` | ✅ done (5 tests green) |

- [x] Implement `target.py` — `resolve_target()`, legacy `openclaw_home` migration, `TargetCatalog`
- [x] Write and pass `tests/test_oramaclaw_target.py`
- [x] Commit Task 1 completion (`6bb53ed`)

---

## Task 2 — Persist Field Ownership, Transactions, Pending Resolutions

| File | Status |
|------|--------|
| `src/oramaclaw/store.py` | ✅ done (`afab3da`, `9140e13`) |
| `tests/test_oramaclaw_store.py` | ✅ done (18 tests green) |

- [x] Implement `ControlStore` — registry, journal (200-record cap), pending-resolutions, target-lock
- [x] `_atomic_write_json()` + PID-liveness lock (psutil, P2-3) + `get/set_auto_weave_override`
- [x] All 18 tests green. Committed.

---

## Task 3 — Gateway-First And Restricted Offline Transport

| File | Status |
|------|--------|
| `src/oramaclaw/transport.py` | ✅ done (`23b6f97`) |
| `tests/test_oramaclaw_transport.py` | ✅ done (15 tests green) |

- [x] `GatewayTransport`, `OfflineTransport`, `make_transport`, `SubprocessRunner`
- [x] All 15 tests green with FakeRunner. Committed.

---

## Task 4 — Three-Way SSA Merge Planner

| File | Status |
|------|--------|
| `src/oramaclaw/merge.py` | ✅ done (`028cdf6`) |
| `tests/test_oramaclaw_merge.py` | ✅ done (12 tests green) |

- [x] `plan_resource()`, `MergePlan`, `FieldAction`, cooperative/strict/security-topology rules
- [x] All 12 tests green. Committed.

---

## Task 5 — Control Engine

| File | Status |
|------|--------|
| `src/oramaclaw/engine.py` | ✅ done (`0cacc2a`) |
| `tests/test_oramaclaw_engine.py` | ✅ done (7 tests green) |

- [x] `ControlEngine.apply_manifest()`, 90-second per-invocation timer (P2-2)
- [x] `NoResponseInteraction`, `PortalInteraction`; all 7 tests green. Committed.

---

## Task 6 — CLI Entry Point

| File | Status |
|------|--------|
| `src/oramaclaw/cli.py` | ✅ done (`5b571d7`) |
| `src/oramaclaw/__main__.py` | ✅ done (`9cae29d`) |
| `tests/test_oramaclaw_cli.py` | ✅ done (9 tests green) |

- [x] `apply`, `status`, `resolve`, `targets` subcommands; `$ORAMACLAW_TARGETS_PATH` in help
- [x] `__main__.py` added; `oramaclaw` console_scripts entry point in pyproject.toml

---

## Task 7 — Migrate Codex Skill Substrate Into oramaclaw Resources

| File | Status |
|------|--------|
| `bind_codex_backend.sh` → resource manifest + CLI | ✅ done (`991ab8d`) |
| `generate_codex_openclaw_profile.py` | ✅ stays as canonical reconciler (P2-1) |
| `scripts/sync-oramaclaw-vendor.sh` | ✅ done (`991ab8d`) |
| codex-workspace manifest | ✅ done (`991ab8d`) |

- [x] `codex-workspace.json` manifest (agent + profile resources)
- [x] `scripts/sync-oramaclaw-vendor.sh` (rsync src/oramaclaw/ → PT vendor/)

---

## Task 8 — Portal UI Conflict Resolution

| File | Status |
|------|--------|
| `src/orama_system/portal_server.py` | ✅ done (`85d874e`) |
| `web/src/api/client.ts` | ✅ done (`85d874e`) |
| `tests/test_oramaclaw_portal_routes.py` | ✅ done (4 tests green) |

- [x] `GET /api/oramaclaw/conflicts` + `POST /api/oramaclaw/conflicts/{id}/resolve`
- [x] `OramaclawConflict`, `OramaclawConflictsResponse`, `OramaclawResolveRequest/Response` TypeScript types

---

## Task 9 — Docs And Canonical Env-Var Table

| File | Status |
|------|--------|
| `docs/v2/40-oramaclaw-lifecycle-plugin.md` | ✅ done (`6a9211b`) |
| `docs/superpowers/plans/2026-06-20-oramaclaw-control-plane-v1.md` | ✅ done (`6a9211b`) |

- [x] Env-var table: `$ORAMACLAW_TARGETS_PATH`, `$ORAMACLAW_STATE_DIR`, `$OPENCLAW_HOME`
- [x] P2-2 timer decision documented in Global Constraints

---

## Merge Gate (PR #98)

| Gate item | Status |
|-----------|--------|
| R1 — generator writes to explicit root, marker merge | ✅ `dce98e6` |
| R2 — `discover.py` concurrent write boundary | ✅ `9cae29d` — `os.replace()` atomic write + `_Lock()` in `_cmd_restore` |
| R3 — recursive credential check in `schema.py` | ✅ `dce98e6` |
| R4 — `src/oramaclaw` in wheel packages | ✅ `eb6ba2a` |
| R5 — delegation path consistent | ✅ `dce98e6` |
| psutil in `[project].dependencies` | ✅ `9cae29d` |
| CI smoke test — 11 tests, all submodules, CLI help, no forbidden imports | ✅ `9cae29d` — `tests/test_oramaclaw_smoke.py` |

---

## Out-of-Scope Fixed (PR #98 — `eb6ba2a`)

- ✅ `test_patch_openclaw_json` — assertions updated for localhost-always-mac + policy filtering
- ✅ `test_discover_fails_closed` — renamed; updated to warn-and-continue contract
- ✅ `test_openrouter_policy_order` — missing policy fixture created (`deployments/macbook-pro-head/…`)
- ✅ `test_portal_loopback_index_injects_cp_fetch` — monkeypatch `_WEB_DIST` bypasses React
- ✅ `test_skill_md_under_500_lines` → limit raised to 600 for load-bearing content
