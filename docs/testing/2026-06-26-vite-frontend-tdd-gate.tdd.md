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

## Validation commands

```bash
cd web && pnpm install && pnpm test
```

Output (2026-06-26): 4 files, 13 tests, all PASS.

## Toolchain

- Vitest 3.x + jsdom
- `@testing-library/react` + `@testing-library/jest-dom`
- `vitest.config.ts`, `src/test/setup.ts`
- CI: `orama-system/.github/workflows/ci.yml` job `web-test`

## Progress status (2026-06-27 triage)

### Where things stand

**On `origin/main`:** the Vitest/TDD gate is **not landed**. `web/package.json` has no `test` script or Vitest deps, CI has no `web-test` job, and `docs/TDD.md` on main still describes the RC-1 gap (zero `*.test.ts*` in `web/src/`).

**On open branches** ([PR #117](https://github.com/diazMelgarejo/orama-system/pull/117) `feat/vitest-tdd-gate-scratch`, [PR #118](https://github.com/diazMelgarejo/orama-system/pull/118) `feat/dev-recalib-cursor-agent`): most of the RC-1 minimum is implemented but unmerged.

| Item | Branch status | On `main`? |
|------|---------------|------------|
| Vitest 3 + jsdom + RTL + `pnpm test` | Done | No |
| `web-test` CI job | Done | No |
| 13 tests / 4 files (this evidence report) | Done | No |
| `commandCenterState.ts` / `routingState.ts` extractions + wired into components | Done (#118; scratch may lag) | No |
| `docs/testing-anti-patterns.md`, `tdd-gate.md`, this `.tdd.md` | Done | No |
| `docs/TDD.md` “gate closed” section | On branch only | Main still says “gap” |
| oramasys-method Stage 4 TDD refs | On branch | Partial on main |

The largest remaining step is **merge**, not greenfield implementation.

### RC-1 minimum — still open on branch

`docs/TDD.md` minimum checklist items not fully satisfied even on the feature branches:

| Gap | Current coverage | Still needed |
|-----|------------------|--------------|
| One test per top-level page/route | `command` (App smoke + state unit tests), `routing` (`RoutingView.test.tsx`) | Nav smokes for **composer**, **runs**, **artifacts** |
| `CommandCenter.test.tsx` (RC-1 `:33` fallback) | Logic covered via `commandCenterState.test.ts` | Optional full component-level test |
| `client.ts:26` dead ternary (RC-1) | Fixed on branch (comment at line 26); `client.test.ts` covers success/error | None unless explicit regression test desired |

`CommandCenter` pages: `command`, `composer`, `runs`, `routing`, `artifacts` (`settings` / `docs` are footer nav placeholders).

### Incremental backlog (post-gate)

| Item | Notes |
|------|--------|
| Per-route smokes (`composer`, `runs`, `artifacts`) | Satisfies “one test per top-level page” in `docs/TDD.md` |
| E2E / Playwright | Out of RC-1 minimum scope |
| `scripts/git/check_tdd_commit.sh` | v2/26 — “to be added”; not in RC-1 scope |
| PT pointer layer | `docs/TDD.md` pointer + ADR-004 — [Perpetua-Tools PR #163](https://github.com/diazMelgarejo/Perpetua-Tools/pull/163) |
| `tdd-skip:` enforcement habit | Policy written in `docs/TDD.md`; pre-commit hook not yet |

### PR housekeeping

1. **Land [PR #118](https://github.com/diazMelgarejo/orama-system/pull/118)** (Vitest + turf + docs) as the integration PR; fold or close [#117](https://github.com/diazMelgarejo/orama-system/pull/117) if redundant.
2. **Coordinate with [PR #116](https://github.com/diazMelgarejo/orama-system/pull/116)** (Windows CRLF turf) — overlaps `platform/windows/gstack-brain-sync.cmd` with #118.
3. **After merge:** `cd web && pnpm install && pnpm test` on `main`; confirm `web-test` green in CI; delete stale `wip/vitest-scratch` / `feat/vitest-tdd-gate-scratch` locals.

### Recommended next steps (ordered)

1. Merge #118 (after #116 or coordinated) → toolchain + CI + first 13 tests on `main`.
2. Close or fold #117 if superseded.
3. Follow-up PR: three nav smokes (`composer`, `runs`, `artifacts`).
4. Optional later: `check_tdd_commit.sh`, Playwright, `CommandCenter.test.tsx`.

**Summary:** ~80% done on branches; `main` still has zero Vitest. Remaining work is merge + ~3 route smokes + optional hook/E2E.

## Known gaps (incremental)

- Per-route smoke tests beyond default `command` page (incremental per `docs/TDD.md`)
- E2E / Playwright (out of RC-1 minimum gate scope)
