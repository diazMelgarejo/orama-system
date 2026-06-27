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

## Known gaps (incremental)

- Per-route smoke tests beyond default `command` page (incremental per `docs/TDD.md`)
- E2E / Playwright (out of RC-1 minimum gate scope)
