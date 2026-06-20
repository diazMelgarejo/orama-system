# Oramaclaw v1 Plan — Punch List

**Source plan:** `docs/superpowers/plans/2026-06-20-oramaclaw-control-plane-v1.md`
**Reviewed:** 2026-06-20 via `/autoplan` (targeted punch-list mode)
**Branch:** `feat/openclaw-codex-app-server`

Issues ranked P1 (blocks implementation) → P2 (decision needed) → P3 (hygiene).
Fixes P1-1 and P1-4 applied in the same commit as this file.

---

## P1 — Blockers (implement fails without resolution)

### [P1-1] Task 6 Steps 3 & 4 are inverted — PT `pyproject.toml` modified before mirror exists
**Status: FIXED in this commit.**

Step 3 said "Add to *both* repository `pyproject.toml` files after generated source exists," then Step 4 created the vendor mirror. An implementing agent would touch `../perplexity-api/Perpetua-Tools/pyproject.toml` before `oramaclaw/` existed in that repo. Fixed by swapping Steps 3 and 4: vendor sync comes first, PT pyproject edit comes after.

---

### [P1-2] Missing test fixture: `tests/fixtures/oramaclaw-codex-provider.json`
**Status: FIXED — all 4 scenario fixtures created.**

`tests/fixtures/oramaclaw-codex-provider.json` (3-resource: provider + agent + delegation), `tests/fixtures/oramaclaw-stale-gateway.json`, `tests/fixtures/oramaclaw-cooperative-drift.json`, `tests/fixtures/oramaclaw-security-topology.json`. All use `__TMP__` target prefix; `parse_manifest()` handles them without resolving paths on disk.

---

### [P1-3] `tests/test_control_plane_auth.py` referenced in Task 8 Step 4 but never created
**Status: FIXED — file exists (pre-existing).**

`tests/test_control_plane_auth.py` exists in the repo (tests portal auth flow). The plan should reference it as an existing file, not a new one. No creation step needed.

---

### [P1-4] Seven result/error types have no code stubs
**Status: FIXED in this commit.**

`ControlManifest`, `Conflict`, `PendingResolution`, `ControlResult`, `GatewayConfig`, `GatewayApplyResult`, `StaleConfiguration`, `OfflineOperationNotAllowed` were named in interfaces/prose but only `ConfigTarget`, `ResourceKind`, `MergePolicy`, and `Resource` had code. An implementing agent would invent fields and diverge from contracts. Fixed by adding frozen dataclass stubs to Task 1 Step 3 and Task 3 Step 3.

---

### [P1-5] Test helpers `provider_manifest_with_medium_effort()` and `NoResponseInteraction()` undefined
**Status: FIXED — both defined in `tests/conftest.py`.**

`provider_manifest_with_medium_effort(tmp_path)` builds a `ControlManifest` for the codex-app-server provider with `effort=medium`; skips if oramaclaw not installed yet. `NoResponseInteraction.choose()` always returns `None` to simulate the 90-second portal timeout (auto-weave path).

---

### [P1-6] `schema.py` listed in Task 1 Files but no step implements it
**Status: FIXED — `src/oramaclaw/schema.py` implemented.**

`parse_manifest(path: Path) -> ControlManifest` validates: version==1, non-empty resources, unique kind:id keys, non-empty manager, valid policy enum, security_topology→conflict-only, no raw credentials in spec. Raises `ManifestValidationError(ValueError)` on any violation. No external dependency (inline schema dict). `__TMP__` prefix paths pass through unexpanded (for planning fixtures).

---

## P2 — Decisions needed

### [P2-1] `generate_codex_openclaw_profile.py` (269 lines, exists) absent from Task 7 migration scope
**Status: OPEN — decision needed.**

This script writes `CODEX.md`, `AGENTS.md`, `TOOLS.md` using source hashes. Task 7 says the Codex binder becomes a "manifest producer" and `CODEX.md` records only marker-delimited metadata — but the existing generator is not listed in Task 7 Files. If left unchanged it will produce content outside the `oramaclaw:generated` markers, conflicting with Task 5 Step 5's profile merge.

**Decision:** Migrate/retire the generator in Task 7, or document explicitly that it stays unchanged and why.

---

### [P2-2] 90-second cooperative timer scope ambiguous: per-resource or per-apply-invocation?
**Status: OPEN — decision needed.**

Global Constraints say "may auto-weave … after 90 seconds." Task 5 and Task 8 describe different timer contexts (blocking Terminal vs async Portal). `PortalInteraction` must know whether the timer runs once for all pending resources in one apply, or per-resource independently.

**Decision:** Specify timer scoping explicitly in Task 5 Step 4 rule 7.

---

### [P2-3] PID-existence check for lock stale detection has no platform note and no declared dependency
**Status: OPEN — decision needed.**

Task 2 Step 10 requires "A lock is broken only after its recorded PID is confirmed absent." On macOS, liveness check needs `os.kill(pid, 0)` plus start-time comparison (to avoid PID recycling). The start-time comparison requires either `psutil` or platform-specific code. `psutil` is not in the dependency list.

**Decision:** Add `psutil` to `pyproject.toml` or specify the platform-native approach explicitly.

---

### [P2-4] `src/oramaclaw/__init__.py` exports not specified
**Status: OPEN — decision needed.**

The file is listed but its public API surface is never described. All downstream callers (Task 7 migration, PT vendor tests) depend on what this exports.

**Decision:** Specify the public API in `__init__.py`, or state "nothing re-exported, use submodule paths."

---

### [P2-5] `$ORAMACLAW_TARGETS_PATH` env var not surfaced in CLI commands or setup steps
**Status: OPEN — needs addition to Task 6 Step 2 and Task 9 docs.**

The target catalog path is specified in Global Constraints but not documented in the CLI command list (Task 6) or the canonical docs (Task 9).

---

### [P2-6] Task 8 `web/src/api/client.ts` listed as a file to modify but no content specified
**Status: OPEN — needs TypeScript type block in Task 8.**

The task says modify the API client without showing which methods to add or the TS types for oramaclaw response shapes.

---

## P3 — Hygiene / consistency

### [P3-1] Broken Markdown table in Task 7 Step 1 — 4 header columns, 3 separator cells
**Status: FIXED.** Added the missing 4th `---` cell to the separator row.

### [P3-2] Delegation path abbreviated inconsistently in Task 7
**Status: FIXED.** Task 7 Steps 2 and 3 now use the full dotted path `agents.defaults.subagents.allowAgents` / `agents.list[].subagents.allowAgents` matching Global Constraints and Task 4.

### [P3-3] Hardcoded absolute paths in Task 4 Step 1 fixture (`/work/openclaw`)
**Status: FIXED.** Added note: "planning-only fixture — paths need not exist on disk; use `tmp_path` when the planner is invoked from pytest."

### [P3-4] No `pyproject.toml` stub or Python version constraint
**Status: FIXED.** Task 1 Step 5 now includes the Hatch `src/` layout `pyproject.toml` diff with `[tool.hatch.build.targets.wheel] packages = ["src/oramaclaw"]`.

---

## Codex review findings (2026-06-20)

Three issues surfaced by `codex review` on the branch. All fixed in the same batch as P3 hygiene:

- **[CR-1] P1 — `bind_codex_backend.sh:332`** used `agents.bindings.main.allowAgents` (rejected by new control plane). Fixed to `agents.defaults.subagents.allowAgents`.
- **[CR-2] P2 — `ControlResult.state` Literal** omitted `gateway_unavailable` (exit code 3). Added.
- **[CR-3] P1 — `bind_codex_backend.sh:352`** used bare `timeout` (not on stock macOS). Fixed to gtimeout→timeout→unwrapped fallback.

---

## Open items summary

| ID | Priority | Status |
|----|----------|--------|
| P1-1 | P1 | ✅ Fixed |
| P1-2 | P1 | ✅ Fixed (4 fixtures) |
| P1-3 | P1 | ✅ Fixed (pre-existing) |
| P1-4 | P1 | ✅ Fixed |
| P1-5 | P1 | ✅ Fixed (conftest.py) |
| P1-6 | P1 | ✅ Fixed (schema.py) |
| CR-1 | P1 | ✅ Fixed (codex review) |
| CR-3 | P1 | ✅ Fixed (codex review) |
| P2-1 | P2 | OPEN — decision |
| P2-2 | P2 | OPEN — decision |
| P2-3 | P2 | OPEN — decision |
| P2-4 | P2 | OPEN — decision |
| P2-5 | P2 | OPEN |
| P2-6 | P2 | OPEN |
| CR-2 | P2 | ✅ Fixed (codex review) |
| P3-1 | P3 | ✅ Fixed |
| P3-2 | P3 | ✅ Fixed |
| P3-3 | P3 | ✅ Fixed |
| P3-4 | P3 | ✅ Fixed |
