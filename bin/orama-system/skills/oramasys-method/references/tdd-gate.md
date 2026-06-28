# TDD Gate (oramasys-method Stage 4)

Canonical prescriptive checklists live in **`docs/TDD.md`** (orama-system repo).
Do not duplicate the full gate here — read and apply that file before production
code changes and before every commit.

## Mandatory loop (summary)

1. Write the **smallest** failing test for the target behavior.
2. Run it — confirm **FAIL** (not a test harness error).
3. Write minimal code to pass.
4. Run again — confirm **PASS**.
5. Verify intent (not just assertion) is satisfied.
6. Refactor with tests green.

Escape hatches and `tdd-skip:` reasons are defined in `docs/TDD.md` § Escape Hatches.

## Stage 4 integration

| Step | TDD requirement |
|------|-----------------|
| Plan | Convert each task to a testable guarantee before coding |
| Craft | RED → GREEN only; no production code before failing test |
| Verify | Full local suite green (`pytest`, `web/` → `pnpm test`) |

## Frontend (Vite operator console)

Path: `web/`. Toolchain: Vitest + React Testing Library + `@testing-library/jest-dom`.

Minimum gate (see `docs/TDD.md` § Vite Frontend Gap):

- `pnpm test` in `web/` must pass in CI
- Any `web/src/` production change needs an accompanying `*.test.ts(x)` unless `tdd-skip:`
- Enforced on commit: `scripts/git/check_tdd_commit.sh` (via `bash scripts/git/install-local-hooks.sh`)

### Bash 3.2 portability (macOS)

**Root cause:** macOS ships bash 3.2, which lacks `mapfile`. `check_tdd_commit.sh` uses a
`while read` loop instead — see
[`git-history-surgery/references/bash-32-git-script-portability.md`](../../git-history-surgery/references/bash-32-git-script-portability.md).

## Outsourced review (frugality)

For non-trivial features, after GREEN:

- **Plan** → GPT-5.5 (or next-best planner)
- **Review** → Gemini 3.1 Thinking (or next-best reviewer)
- **Harmonize** → executing agent applies CIDF

Full policy: `docs/v2/26-tdd-and-outsourced-review-doctrine.md`.

## Anti-patterns

`docs/testing-anti-patterns.md` — block PRs that match theater tests, falsy-input gaps, or visual-only verification.

## Executable skill

When the harness exposes it, prefer **`tdd-workflow`** (`vendor/ecc-tools/skills/tdd-workflow/SKILL.md`) for step-by-step agent instructions and evidence reports (`docs/testing/*.tdd.md`).
