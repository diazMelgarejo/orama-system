# Fragment Synthesis — when one failure produces several partial fixes

**Companion to:** [integrative-merge.md](integrative-merge.md) (classification before resolution)
and [post-review-micro-remediation.md](../../references/post-review-micro-remediation.md).
**Trigger:** the same real failure has produced two or more partial fixes on different branches,
and a linear stack (base + fix A, then + fix B) would merely sequence the fragments instead of
harmonizing them.

## The method (seven steps)

1. **Classify the failure class first** — transient infrastructure, code defect, test drift, or
   configuration? The class dictates the response shape (retry vs repair vs expectation update)
   and immediately exposes which fragments are alternatives vs complements.
2. **Census every exposure point**, not just the site that happened to fail. A point fix protects
   one instance of the class; the census tells you the real blast radius of the synthesis
   (fragments covering 2 of 6 sites is the signal that neither side saw the whole problem).
3. **Classify each fragment per integrative-merge**: complementary capability, duplicated intent,
   or superseded (already merged elsewhere). Map every hunk to a disposition: keep / absorb /
   retire.
4. **Design the synthesis on the strengths table**, not on either fragment's shape: take each
   side's strongest idea, fold the other side's complementary idea into it, and extend the
   result across the full census. Keep the original failure-accounting semantics of the merged
   code — synthesis amalgamates strengths, it does not pick a winner.
5. **Build on a trial branch from main in a dedicated worktree.** Never stack linearly through
   the fragments; never touch main. Smoke-test the behavior with stubs before pushing.
6. **Retire superseded PRs with superseded-by comments** that name exactly which idea of theirs
   survived and where. The retired authors' work is absorbed, not discarded — say so.
7. **Crystallize the census** (the coverage table) as part of the PR description so the next
   agent auditing the failure class finds the exposure map, not just the fix.

## Worked example — orama-system PR #516 (the designated concrete exemplar)

One PyPI `IncompleteRead` failure on the agent-audit security-scan job produced three fragments:

| Fragment | Where | Idea | Disposition in the synthesis |
| --- | --- | --- | --- |
| Inline 3-attempt loop, linear backoff, explicit guarded failure + message | main `db536e15` (merged via #508) | failure accounting + backoff | **absorbed**: backoff folded into the helper; guarded failure kept verbatim |
| Reusable env-configurable `pip_install_retry()` | PR #509 | reusability + tunability | **absorbed**: the helper is the synthesis core |
| Test-expectation fix (port key) | PR #511 | correct assertions | **retired**: identical fix merged via #508 (`4b92735`) |

The census then found the coverage gap: the script had **6** `pip install` call sites and the
two fixes together protected **2** — the skill-scanner and mcp-scanner upgrade and package
installs carry the same blip exposure neither side touched. The synthesis applied the shared
helper to **6 of 6** sites, kept the guarded failure, and preserved the workflow pins, cache
keys and trigger scope.

**Verification:** `bash -n` clean; behavioral smoke test with a stubbed pip (recovery on the
third attempt; env-tunable attempt count honored; linear backoff logged); workflow-structure
suite 12 passed / 1 skipped. **Outcome:** PR #516 (head `8f8a0fb`), CI 31/31 checks green
(30 SUCCESS / 1 skipped / 1 neutral, 0 failures); PRs #509 and #511 closed as superseded with
absorption credit.

## Exhibit B — fix at the resolution layer (Mac default Python, 2026-11-17)

Operator earmark: the second designated example of elegance, beside Exhibit A (PR #516). It
applies the same method to an environment problem rather than a CI fragment.

- **Classify the failure.** It was a dependency migration hidden inside an interpreter change.
  Making uv CPython 3.13.18 (SQLite 3.53.1) the default `python3` dropped the old default's 229
  packages, and the board CLI failed on `aiosqlite`.
- **Census the exposure.** Every caller of bare `python3`: one launchd job (pinned to
  `/usr/bin/python3`, so unaffected), the Claude hooks (standard library only), and the many
  agent instructions that run `python3 scripts/...` (affected). There were also ten venvs whose
  `pyvenv.cfg` `home` pointed at removed uv patch directories.
- **Synthesize instead of picking a side.** Reverting would lose the SQLite fix. Reinstalling
  packages into a managed base would pollute it. Rewriting callers would touch dozens of
  instructions. The synthesis: `python3` becomes an `exec` wrapper into one venv built from the
  uv **minor-version link** (`home` survives 3.13.x patch upgrades), filled from one rebuild
  file.
- **Replace before remove, then verify.** The replacement env was built beside the old one and
  verified (version, SQLite floor, imports, board CLI). The wrappers were repointed by atomic
  rename, and only then was the old env deleted. Rollback is deleting two wrappers.

Mechanics and the failure table:
[wiki 02, Python venv resolution](../../../../../docs/wiki/02-idempotent-installs.md#addendum-2026-11-17---python-venv-resolution-and-the-default-environment)
and the Perpetua-Tools card
`.agent/memory/semantic/PYTHON_VENV_RESOLUTION_AND_DEFAULT_ENV_DOMAIN_KNOWLEDGE_2026-11-17.md`.

## Anti-patterns

- Stacking fragments linearly because each one "works" — the stack sequences partial coverage
  instead of closing the class.
- Resolving the synthesis conflict by picking one side wholesale (the integrative-merge
  never-delete violation in synthesis clothing).
- Retiring a PR without naming the absorbed idea — the retired author's contribution is part of
  the synthesis and the record must say where it went.
- Skipping the census because the failed site is now fixed — the next site fails on the next
  flaky runner day.
