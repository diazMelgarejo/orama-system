# Vite frontend TDD gate — evidence report

> Task: implement `docs/TDD.md` minimum acceptance gate for `web/` (RC-1 gap).
> Method: oramasys-method Stage 4 (RED → GREEN → verify).

## Guarantees

| # | What is guaranteed | Test file | Result |
|---|--------------------|-----------|--------|
| 1 | `apiFetch` parses JSON on success | `src/api/client.test.ts` | PASS |
| 2 | `apiFetch` throws `ApiError` on HTTP error | `src/api/client.test.ts` | PASS |
| 3 | Display state falls back to mock when fetch is undefined | `src/features/command-center/commandCenterState.test.ts` | PASS |
| 4 | Jobs fall back to mock seed when jobs section missing | `src/features/command-center/commandCenterState.test.ts` | PASS |
| 5 | Empty-string job id does not enable artifact polling | `src/features/command-center/commandCenterState.test.ts` | PASS |
| 6 | Routing hides Win LM Studio row when offline | `src/features/routing/RoutingView.test.tsx` | PASS |
| 7 | App smoke: renders nav + mock fallback banner on API error | `src/App.test.tsx` | PASS |
| 8 | Composer nav: swarm composer page without command-dashboard runs table | `src/features/command-center/CommandCenter.test.tsx` | PASS |
| 9 | Runs nav: runs table without swarm composer panel | `src/features/command-center/CommandCenter.test.tsx` | PASS |
| 10 | Artifacts nav: artifacts panel without swarm composer panel | `src/features/command-center/CommandCenter.test.tsx` | PASS |

## Validation commands

```bash
cd web && pnpm install && pnpm test
bash scripts/git/install-local-hooks.sh   # wires commit-msg → check_tdd_commit.sh
```

Output (2026-06-27): 5 files, 16 tests, all PASS.

## Toolchain

- Vitest 3.x + jsdom
- `@testing-library/react` + `@testing-library/jest-dom`
- `vitest.config.ts`, `src/test/setup.ts`
- CI: `orama-system/.github/workflows/ci.yml` job `web-test`
- Commit-msg gate: `scripts/git/check_tdd_commit.sh` (`tdd-skip:` escape hatch per `docs/TDD.md`)
- **Bash 3.2:** macOS lacks `mapfile`; hook uses `while read` — [`bash-32-git-script-portability.md`](../../bin/orama-system/skills/git-history-surgery/references/bash-32-git-script-portability.md)

## Progress status (2026-06-27 triage)

### Where things stand

**On `origin/main`:** the Vitest/TDD gate is **not landed**. `web/package.json` has no `test` script or Vitest deps, CI has no `web-test` job, and `docs/TDD.md` on main still describes the RC-1 gap (zero `*.test.ts*` in `web/src/`).

**On open branches** ([PR #117](https://github.com/diazMelgarejo/orama-system/pull/117) `feat/vitest-tdd-gate-scratch`, [PR #118](https://github.com/diazMelgarejo/orama-system/pull/118) `feat/dev-recalib-cursor-agent`): most of the RC-1 minimum is implemented but unmerged.

| Item | Branch status | On `main`? |
|------|---------------|------------|
| Vitest 3 + jsdom + RTL + `pnpm test` | Done | No |
| `web-test` CI job | Done | No |
| 16 tests / 5 files (this evidence report) | Done | No |
| Nav smokes (`composer`, `runs`, `artifacts`) | Done (`CommandCenter.test.tsx`) | No |
| `scripts/git/check_tdd_commit.sh` | Done (commit-msg hook) | No |
| `commandCenterState.ts` / `routingState.ts` extractions + wired into components | Done (#118; scratch may lag) | No |
| `docs/testing-anti-patterns.md`, `tdd-gate.md`, this `.tdd.md` | Done | No |
| `docs/TDD.md` “gate closed” section | On branch only | Main still says “gap” |
| oramasys-method Stage 4 TDD refs | On branch | Partial on main |

The largest remaining step is **merge**, not greenfield implementation.

### RC-1 minimum — branch status (2026-06-27)

| Item | Status |
|------|--------|
| One test per top-level page/route | Done — `command` (App + state), `routing`, `composer` / `runs` / `artifacts` (nav smokes) |
| `CommandCenter.test.tsx` | Done — nav smokes (fallback logic remains in `commandCenterState.test.ts`) |
| `client.ts:26` dead ternary | Fixed; covered by `client.test.ts` |
| `check_tdd_commit.sh` | Done — `.githooks/commit-msg` |

`CommandCenter` pages: `command`, `composer`, `runs`, `routing`, `artifacts` (`settings` / `docs` are footer nav placeholders).

### Incremental backlog (post-merge)

| Item | Notes |
|------|--------|
| E2E / Playwright | **Deferred until after #118 lands on `main`** |
| PT pointer layer | `docs/TDD.md` pointer + ADR-004 — [Perpetua-Tools PR #163](https://github.com/diazMelgarejo/Perpetua-Tools/pull/163) |

### PR housekeeping

1. **Land [PR #118](https://github.com/diazMelgarejo/orama-system/pull/118)** (Vitest + turf + docs) as the integration PR; fold or close [#117](https://github.com/diazMelgarejo/orama-system/pull/117) if redundant.
2. **Coordinate with [PR #116](https://github.com/diazMelgarejo/orama-system/pull/116)** (Windows CRLF turf) — overlaps `platform/windows/gstack-brain-sync.cmd` with #118.
3. **After merge:** `cd web && pnpm install && pnpm test` on `main`; confirm `web-test` green in CI; delete stale `wip/vitest-scratch` / `feat/vitest-tdd-gate-scratch` locals.

### Recommended next steps (ordered)

1. Merge #118 (after #116 or coordinated) → toolchain + CI + 16 tests on `main`.
2. Close or fold #117 if superseded.
3. **After merge:** Playwright E2E spike (out of RC-1 minimum).

**Summary:** RC-1 gate complete on branch; `main` still unmerged. Playwright deferred post-merge.

## Known gaps (incremental)

- E2E / Playwright — deferred until Vitest gate is merged to `main` (see post-merge backlog above)
