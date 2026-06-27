# TDD — Test-Driven Development Hints

> **Canonical path**: `orama-system/docs/TDD.md`
> **Companion**: parent-dir [`tdd.md`](../../tdd.md) — source-of-truth philosophy (SPECS → tests → code).
> **External skill**: `superpowers:test-driven-development` — install path: `~/.claude/plugins/cache/claude-plugins-official/superpowers/5.0.7/skills/test-driven-development/SKILL.md` — full methodology, anti-patterns. Do not duplicate here.
> **Anti-patterns reference**: same dir, [`testing-anti-patterns.md`](testing-anti-patterns.md).

This file is the **prescriptive gate**. Use them before every code change and every commit.

---

## source of truth

1. Create High level SPECS.md
2. The tests.
3. use [TDD](superpowers:test-driven-development), plan using gpt-5.5 and/or gemini-3.1-PRO

### TESTS

Agentic coding is the ideal mechanism for enforcing TDD and being strict with it.

Here is a summary of the workflow I coded as part of my implementation skill in Claude Code:

1. Before writing each code, write a test that fails for it
2. Run the test and ensure it fails
3. If you get an error, fix the test until it runs but fails
4. Once the test fails, write the code
5. Run the test and ensure it succeeds
6. If the test fails, go back to step 4
7. Once the test succeeds, verify that the task is complete (the original code's intent landed);
8. If the task is not complete, go back to step 1.

This loop forces the agent to write tests before writing any code, and tries to keep each test as simple as possible.

This is token-hungry upfront, so be frugal on turns (outsource: all code plans to GPT-5.5; all code reviews to Gemini 3.1 Thinking; if any of these models are unavailable, get the next best thing), but it has many advantages:

1. Simpler code
2. More modular code
3. Fewer bugs and regressions later
4. Easier to troubleshoot

---

### v2 instructions (oramasys org)

minimize kernel and ***MiniGraph*** as much as possible, it will call external modules and skills as necessary, it must still be extremely nimble and responsive even with the rich features by maximizing its adopted hybrid architecture?

---

Two short checklists:

## Pre-Code-Change Checklist

Before writing or modifying production code:

1. **Did I write a failing test first?**
   - YES → run it, confirm it fails for the right reason, then write code.
   - NO → STOP. Either write the test, OR document the reason for skipping in the commit message (one line: `tdd-skip: <reason>`). Acceptable skip reasons: pure refactor with no behavior change; doc-only change; experimental spike marked `WIP`. Everything else needs a test.

2. **Is the failing test the smallest one that would catch the bug if it regressed?**
   - One assertion if possible. One file boundary crossed at most.

3. **Does the test name describe the behavior, not the implementation?**
   - Good: `falls back to default model when env var is empty string`.
   - Bad: `test_command_center_line_33`.

---

## Pre-Commit Checklist

Before `git commit`:

1. **Did the test actually fail before the fix and pass after?** Re-run with the fix reverted if uncertain. A test that never failed is not a TDD test — it is theater.
2. **Did I run the full local suite?** `npm test` / `pytest` — green before commit.
3. **For Vite frontend changes:** did I add or extend a `*.test.ts` / `*.test.tsx` next to the changed file? (See gap section below.)
4. **For SQL / migrations:** did I include an idempotency test (run twice, second run is a no-op)?
5. **Commit message names the test file** if a non-trivial test was added. Reviewers should not have to grep for it.

---

## Vite Frontend Gate (RC-1 → closed 2026-06-26)

RC-1 flagged **zero `*.test.ts*` in `web/src/`**. The minimum gate is now landed on branch
`feat/vitest-tdd-gate-scratch` (evidence: [`docs/testing/2026-06-26-vite-frontend-tdd-gate.tdd.md`](testing/2026-06-26-vite-frontend-tdd-gate.tdd.md)):

- **Toolchain:** Vitest + React Testing Library + `@testing-library/jest-dom`; `pnpm test` in `web/`; CI job `web-test`.
- **13 tests / 4 files** covering `apiFetch`, command-center fallbacks (including empty-string job id), routing offline branch, and App smoke.
- **Production rule (unchanged):** no `web/src/` change without an accompanying `*.test.ts(x)` unless `tdd-skip:` is documented.

### Incremental backlog (post-gate)

- Per-route smoke tests beyond default `command` page.
- E2E / Playwright (out of RC-1 minimum scope).

---

## Canonical "Would-Have-Been-Caught-By-TDD" Examples

When teaching this workflow or reviewing a PR that skipped tests, point at these two RC-1 bugs:

| Bug | Why TDD would have caught it |
|-----|------------------------------|
| `CommandCenter.tsx:33` — fallback path silently swallowed an empty-string model id and used the wrong default | A test feeding `""` and asserting the resolved default would have failed before the bug shipped. |
| `client.ts:26` — ternary with an unreachable branch (dead code) | Writing the test for both sides of the ternary forces the author to either reach the dead branch (proving it isn't dead) or delete it. Either outcome is a win. |

If a PR is proposed that looks structurally similar to either of these (a fallback on falsy input, or a ternary on a value the author claims is "always defined"), reviewers should require a test before approving.

---

## Escape Hatches (use sparingly)

- **Pure refactor, no behavior change:** allowed without a new test if existing tests cover the refactored surface and stay green. If they don't, add coverage first, then refactor.
- **Exploratory spike:** allowed on a branch marked `spike/*`. Spike branches never merge to main as-is — they get rewritten with tests on a `feat/*` branch.
- **Doc-only / config-only changes:** no test required.

Anything else: write the test.

---

## References

- Parent philosophy doc: [`../../tdd.md`](../../tdd.md)
- Full TDD methodology + anti-patterns: `~/.claude/plugins/cache/claude-plugins-official/superpowers/5.0.7/skills/test-driven-development/`
- Session lessons: [`LESSONS.md`](LESSONS.md)
- Verifier gate (crystallization blocked without approved test result): [`2026-05-14--UNIFIED-ABSORPTION-PLAN.md`](2026-05-14--UNIFIED-ABSORPTION-PLAN.md) § 2
