# Testing Anti-Patterns

> **Canonical path**: `orama-system/docs/testing-anti-patterns.md`
> **Companion gate**: [`TDD.md`](TDD.md) — pre-code and pre-commit checklists.
> **Executable skill**: `vendor/ecc-tools/skills/tdd-workflow/SKILL.md` (Perpetua-Tools submodule).

Reviewers and agents should block PRs that exhibit these patterns.

---

## Theater tests (never failed)

A test added **after** the fix, or copied from implementation without a RED run, provides false confidence. Revert the fix and confirm failure before approving.

**Signal:** reviewer cannot find evidence the test failed on the behavior under test.

---

## Implementation-coupled names

| Bad | Good |
|-----|------|
| `test_command_center_line_33` | `falls back to mock state when fetch returns undefined` |
| `apiFetch_works` | `throws ApiError with status and body on HTTP error` |

Test names describe **observable behavior**, not file locations or private helpers.

---

## Multi-assertion kitchen sinks

One test that asserts layout, API calls, routing, and error copy in a single `it()` block. Split by behavior boundary. One assertion per test when practical.

---

## Mocking the unit under test

Do not mock the function or component you are trying to prove. Mock **dependencies** (fetch, API modules, clock).

---

## Falsy-input fallbacks without branch coverage

Any `??`, `||`, or ternary on user/env input needs **both** sides exercised:

- `undefined` / missing key
- empty string `""` when the type allows it
- explicit empty collection when distinct from missing

RC-1 examples that motivated `docs/TDD.md`: empty-string model id swallowed by fallback; unreachable ternary branch in `client.ts`.

---

## Skipping RED for “simple” changes

Acceptable skips (document `tdd-skip: <reason>` in commit message):

- pure refactor with existing green coverage on the surface
- doc-only / config-only
- `spike/*` branches (never merge as-is)

Everything else: failing test first.

---

## Visual-only verification

“Looks fine in the browser” is not a gate. Run `pnpm test` (web), `pytest` (Python), or the project’s documented suite.

---

## References

- [`TDD.md`](TDD.md) — prescriptive gate
- [`docs/v2/26-tdd-and-outsourced-review-doctrine.md`](v2/26-tdd-and-outsourced-review-doctrine.md) — v2 policy
- `superpowers:test-driven-development` — full methodology (install via Claude superpowers plugin)
