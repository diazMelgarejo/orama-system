# Vite frontend TDD gate — evidence report

> Task: implement `docs/TDD.md` minimum acceptance gate for `web/` (RC-1 gap).
> Method: oramasys-method Stage 4 (RED → GREEN → verify).

## Guarantees

> **Coverage:** 17 Vitest tests across 5 files — one row per test. File-level roll-up:
> `client.test.ts` (4) · `commandCenterState.test.ts` (7) · `RoutingView.test.tsx` (2) ·
> `App.test.tsx` (1) · `CommandCenter.test.tsx` (3).

| # | What is guaranteed | Test file | Result |
|---|--------------------|-----------|--------|
| 1 | `apiFetch` parses JSON on success | `src/api/client.test.ts` | PASS |
| 2 | `apiFetch` throws `ApiError` on HTTP error | `src/api/client.test.ts` | PASS |
| 3 | `apiFetch` uses GET by default when no options are supplied | `src/api/client.test.ts` | PASS |
| 4 | `apiFetch` serializes POST body as JSON string | `src/api/client.test.ts` | PASS |
| 5 | Display state falls back to mock when fetch is undefined | `src/features/command-center/commandCenterState.test.ts` | PASS |
| 6 | Display state uses live API state when data is present | `src/features/command-center/commandCenterState.test.ts` | PASS |
| 7 | Jobs fall back to mock seed when jobs section is absent (`data: null`) | `src/features/command-center/commandCenterState.test.ts` | PASS |
| 8 | Jobs preserve an explicit empty array from the API (not mock fallback) | `src/features/command-center/commandCenterState.test.ts` | PASS |
| 9 | Empty-string job id does not enable artifact polling | `src/features/command-center/commandCenterState.test.ts` | PASS |
| 10 | Latest job id resolves `job_id` when present | `src/features/command-center/commandCenterState.test.ts` | PASS |
| 11 | Latest job id falls back to `id` when `job_id` is absent | `src/features/command-center/commandCenterState.test.ts` | PASS |
| 12 | Routing shows Win LM Studio row when `lmstudio_win` is online | `src/features/routing/RoutingView.test.tsx` | PASS |
| 13 | Routing hides Win LM Studio row when `lmstudio_win` is offline | `src/features/routing/RoutingView.test.tsx` | PASS |
| 14 | App smoke: renders nav + mock fallback banner on API error | `src/App.test.tsx` | PASS |
| 15 | Composer nav: swarm composer page without command-dashboard runs table | `src/features/command-center/CommandCenter.test.tsx` | PASS |
| 16 | Runs nav: runs table without swarm composer panel | `src/features/command-center/CommandCenter.test.tsx` | PASS |
| 17 | Artifacts nav: artifacts panel without swarm composer panel | `src/features/command-center/CommandCenter.test.tsx` | PASS |

## Validation commands

```bash
cd web && pnpm install && pnpm test
bash scripts/git/install-local-hooks.sh   # wires commit-msg → check_tdd_commit.sh
```

Output (2026-06-27, branch `feat/dev-recalib-cursor-agent`): 5 files, **17 tests**, all PASS.

## Toolchain

- Vitest 3.x + jsdom
- `@testing-library/react` + `@testing-library/jest-dom`
- `vitest.config.ts`, `src/test/setup.ts`
- CI: `orama-system/.github/workflows/ci.yml` job `web-test`
- Commit-msg gate: `scripts/git/check_tdd_commit.sh` (`tdd-skip:` escape hatch per `docs/TDD.md`)
- **Bash 3.2:** macOS lacks `mapfile`; hook uses `while read` — [`bash-32-git-script-portability.md`](../../bin/orama-system/skills/git-history-surgery/references/bash-32-git-script-portability.md)

## Progress status

> **Snapshot (2026-06-27):** branch evidence captured on `feat/dev-recalib-cursor-agent`
> ([PR #118](https://github.com/diazMelgarejo/orama-system/pull/118)) during Stage 4 verify.
> This section records **pre-merge** gate status only — not the landed state on `main`.
> After merge, re-run the validation commands above on `main` and tick the post-merge
> checklist below.

### Pre-merge: branch evidence vs `main` (as of snapshot date)

| Item | Verified on branch (PR #118) | Landed on `main`? |
|------|------------------------------|-------------------|
| Vitest 3 + jsdom + RTL + `pnpm test` | Yes | No |
| `web-test` CI job | Yes (on PR CI) | No |
| 17 tests / 5 files (guarantees table above) | Yes | No |
| Nav smokes (`composer`, `runs`, `artifacts`) | Yes (`CommandCenter.test.tsx`) | No |
| `scripts/git/check_tdd_commit.sh` | Yes (commit-msg hook) | No |
| `commandCenterState.ts` / `routingState.ts` extractions | Yes | No |
| `docs/testing-anti-patterns.md`, `tdd-gate.md`, this `.tdd.md` | Yes | No |
| `docs/TDD.md` “gate closed” section | Yes (branch only) | No — `main` still lists RC-1 gap |
| oramasys-method Stage 4 TDD refs | Yes (branch) | Partial on `main` |

At snapshot time, `origin/main` had no Vitest deps, no `web-test` job, and zero `*.test.ts*` in `web/src/`.

### RC-1 minimum — branch checklist (pre-merge)

| Item | Branch status |
|------|---------------|
| One test per top-level page/route | Done — `command` (App + state), `routing`, `composer` / `runs` / `artifacts` (nav smokes) |
| `CommandCenter.test.tsx` | Done — nav smokes (fallback logic in `commandCenterState.test.ts`) |
| `client.ts:26` dead ternary | Fixed; covered by `client.test.ts` (#1–4) |
| `check_tdd_commit.sh` | Done — `.githooks/commit-msg` |

`CommandCenter` pages: `command`, `composer`, `runs`, `routing`, `artifacts` (`settings` / `docs` are footer nav placeholders).

### Post-merge checklist (`main` — not yet verified)

- [ ] `cd web && pnpm install && pnpm test` on `main` → 17 pass
- [ ] CI `web-test` green on `main`
- [ ] `docs/TDD.md` RC-1 gap section updated to “gate closed”
- [ ] Sync `docs/v2/26` + Perpetua-Tools ADR-004 pointer in tandem (zero-fragmentation)
- [ ] Close or fold [#117](https://github.com/diazMelgarejo/orama-system/pull/117) if redundant
- [ ] Delete stale `wip/vitest-scratch` / `feat/vitest-tdd-gate-scratch` locals

### Incremental backlog (post-merge)

| Item | Notes |
|------|-------|
| E2E / Playwright | Deferred until Vitest gate lands on `main` |
| PT pointer layer | `docs/TDD.md` pointer + ADR-004 — [Perpetua-Tools PR #163](https://github.com/diazMelgarejo/Perpetua-Tools/pull/163) |

### PR housekeeping (at snapshot time)

1. Land [PR #118](https://github.com/diazMelgarejo/orama-system/pull/118) as the integration PR; fold or close [#117](https://github.com/diazMelgarejo/orama-system/pull/117) if redundant.
2. Coordinate with [PR #116](https://github.com/diazMelgarejo/orama-system/pull/116) (Windows CRLF turf) — overlaps `platform/windows/gstack-brain-sync.cmd` with #118.

**Summary:** RC-1 gate verified on branch (17/17 PASS); `main` unmerged at snapshot date. Playwright deferred post-merge.

## Known gaps (incremental)

- E2E / Playwright — deferred until Vitest gate is merged to `main` (see post-merge backlog above)
