# TDD-on-TDD — session reference (2026-06-26 dev recalib)

> Reference capture for the `2026-06-26--dev-recalib-cursor-agent` branch landing.
> Canonical gate: [`TDD.md`](TDD.md). Evidence: [`testing/2026-06-26-vite-frontend-tdd-gate.tdd.md`](testing/2026-06-26-vite-frontend-tdd-gate.tdd.md).

**AFRP:** Type C | Practitioner | Mode 2 — implement `docs/TDD.md` gate on orama-system + Perpetua-Tools via oramasys-method Stage 4 (TDD).

## orama-system

### Vite frontend gate (`web/`)

- **Toolchain:** Vitest 3 + jsdom + React Testing Library + `@testing-library/jest-dom`
- **Scripts:** `pnpm test`, `pnpm test:watch` in `web/package.json`
- **16 tests across 5 files** (RC-1 minimum gate from `TDD.md`):
  - `src/api/client.test.ts` — `apiFetch` success / error / POST body
  - `src/features/command-center/commandCenterState.test.ts` — mock-state fallback, empty job id
  - `src/features/command-center/CommandCenter.test.tsx` — composer / runs / artifacts nav smokes
  - `src/features/routing/RoutingView.test.tsx` — LM Studio online/offline branch
  - `src/App.test.tsx` — smoke render + API error banner
- **Pure helpers extracted** for testable fallbacks: `commandCenterState.ts`, `routingState.ts`
- **CI:** new `web-test` job in `.github/workflows/ci.yml` (`pnpm` + `pnpm test`)
- **Commit-msg:** `scripts/git/check_tdd_commit.sh` (paired `web/src` prod + test, or `tdd-skip:`)

### Docs & skill wiring

- `docs/testing-anti-patterns.md` — referenced from `TDD.md`
- `docs/testing/2026-06-26-vite-frontend-tdd-gate.tdd.md` — evidence report
- `bin/orama-system/skills/oramasys-method/references/tdd-gate.md` — Stage 4 gate
- `oramasys-method` SKILL + `5-stage-methodology.md` updated to require `docs/TDD.md` before commit

## Perpetua-Tools

- `docs/TDD.md` — thin pointer to orama canonical gate + local test commands
- `docs/adr/ADR-004-tdd-and-outsourced-review-doctrine.md` — generated pointer (v2/26)
- `scripts/git/sync-docs-v2-pointers.sh` — ADR-004 mapping added for ongoing sync (orama-side)

## Verify locally

```bash
cd orama-system/web && pnpm install && pnpm test
cd orama-system && python3 -m pytest tests/test_repo_hygiene.py -q
```

All 16 Vitest tests and repo hygiene checks pass. `check_tdd_commit.sh` is wired via `install-local-hooks.sh`. Playwright E2E deferred until after the Vitest gate merges to `main`.
