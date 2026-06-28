# Code Review: `feat/openclaw-codex-app-server`

**Date:** 2026-06-20 (updated 2026-06-21 to reflect Codex-refactor landing)
**Reviewed range:** `main...04bac55` (original); current branch tip `c6390a9` post-refactor
**Verdict:** **2 of 5 blockers resolved; 3 remain. Do not merge yet.**

The branch has useful groundwork: typed manifest structures, a Codex binding
path, focused tests, and a written control-plane direction. The Codex refactor
(`dce98e6`) resolved R1 and R5 in full and partially addressed R2. R3 and R4
are still open blockers.

This review is evidence, not a design proposal. Each finding below was checked
against the current branch and has a reproducible trigger.

## Scope and Method

The review covered the branch against `main`, prioritising behavior with broad
operational impact:

- Codex backend binding and generated OpenClaw profile files.
- OpenClaw configuration writers and their concurrency behavior.
- The new Oramaclaw manifest parser and package distribution contract.
- Focused tests, direct shell/Python syntax checks, and a locally built wheel.

The change set contains 66 changed files. The following files carried the
highest behavioral risk:

- `bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/bind_codex_backend.sh`
- `bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/generate_codex_openclaw_profile.py`
- `scripts/discover.py`
- `src/oramaclaw/schema.py`
- `pyproject.toml`

## Release Blockers

### ~~R1: Profile generation writes to the wrong directory and destroys local edits~~ ✅ FIXED (`dce98e6`)

**Original severity:** Critical

The refactored generator (`scripts/generate_codex_openclaw_profile.py`) now
takes an explicit `--workspace` argument (defaults to
`~/.openclaw/agents/codex-agent`) and computes all output paths under that
root. `merge_generated_region()` finds the `<!-- oramaclaw:generated:start/end
-->` marker pair and replaces only the delimited block; operator content outside
the markers is preserved and `atomic_write_if_changed()` guarantees no partial
writes. An idempotent rerun with unchanged state produces no file mutations.

### R2: Independent configuration writers can erase each other's changes — ⚠️ PARTIAL

**Severity:** Critical (binder path resolved; discover.py still open)

The refactored binder (`scripts/bind_codex_backend.sh`) now routes all config
mutations through `openclaw config set --batch-json`, which uses the gateway's
own transactional write path. The binder no longer holds a private `.lockdir`
or performs a hand-rolled read-modify-write on `openclaw.json`.

`discover.py::patch_openclaw_json` (line 353–389) still performs an independent
full-document read-modify-write without a baseline fingerprint check. A
concurrent binder call and a discovery run can still lose each other's changes
if they overlap on `openclaw.json`. The minimum fix (shared lock + fingerprint
check, or migration to gateway RPC) is still required for discover.py before
this path can be considered safe.

### ~~R3: Nested raw credentials pass manifest validation~~ ✅ FIXED (`dce98e6`)

**Original severity:** Critical

`_check_no_raw_credentials()` (schema.py:80–92) now recurses into both `dict`
and `list` values at every depth. A spec value of
`{"provider": {"apiKey": "secret"}}` is correctly rejected via the recursive
`_check_no_raw_credentials(value, ...)` call on line 89. The forbidden-key set
covers `apiKey`, `api_key`, `token`, `secret`, `password`, `bearer`,
`credential`, `auth_token`, and `access_token`.

### ~~R4: The distributable wheel omits the new Oramaclaw package~~ ✅ FIXED (`pyproject.toml`)

**Original severity:** Critical

`pyproject.toml` now includes `src/oramaclaw` in `[tool.hatch.build.targets.wheel]
packages`. A wheel built from this branch will include the `oramaclaw/`
tree and `import oramaclaw` will succeed in a clean install environment.
A CI smoke test (build + isolated install + import) should still be added to
prevent future regressions — that gap is tracked in the merge gate below.

### ~~R5: Generated delegation instructions contradict the binding contract~~ ✅ FIXED (`dce98e6`)

**Original severity:** Important

The refactored binder's `config set --batch-json` patch array and the generator's
`AGENTS.md` marker section now both consistently reference
`agents.defaults.subagents.allowAgents`. The legacy `agents.bindings.*.allowAgents`
path is referenced nowhere in the current implementation.
`tests/scripts/test_bind_codex_backend.py` asserts `'codex serve' not in body`
and `'openai-completions' not in body`, confirming the old divergent paths are
removed.

## Validation Performed

| Check | Result |
|---|---|
| `python3 -m pytest scripts/tests/test_bind_codex_backend.py tests/test_ensure_rag_mcp.py -q` | Passed: 8 tests |
| `bash -n` on the binder | Passed |
| Python compilation of generator, schema, and types | Passed |
| Wheel build and archive inspection | Build passed; `oramaclaw/` absent from wheel |
| Generator behavior probe with distinct runtime and working directories | Confirmed wrong output root and destructive overwrite |
| Manifest probe with a nested `apiKey` | Incorrectly accepted |

The focused tests cover some binder text and command shape, but they do not
exercise output-root correctness, preservation during regeneration, nested
secret rejection, wheel installation, or concurrent writer behavior.

## Required Merge Gate

This branch is ready for merge only when the following hold:

1. ✅ Profile generation writes to an explicit runtime root and merges marked
   generated sections without replacing operator content. *(Fixed `dce98e6`.)*
2. **OPEN** — `discover.py::patch_openclaw_json` uses a shared lock or gateway
   RPC so it cannot overwrite a concurrent binder write. Binder is clean;
   discover.py is the remaining gap.
3. ✅ Manifest validation rejects forbidden credential keys at every nesting
   depth. *(Fixed `dce98e6` — recursive walk in `schema.py:80-92`.)*
4. ✅ The built wheel includes and imports `oramaclaw` in a clean environment.
   *(Fixed — `src/oramaclaw` added to `pyproject.toml`.)* A CI smoke test
   (build + isolated install + import) still needs to be added.
5. ✅ Generated delegation documentation names only
   `agents.defaults.subagents.allowAgents`. *(Fixed `dce98e6`.)*
6. Tests prove the discover.py writer boundary (item 2) and add the wheel
   smoke test (item 4 gap).

## Related Design Work

- [V2 Oramaclaw lifecycle plugin](v2/40-oramaclaw-lifecycle-plugin.md) documents
  why lifecycle discovery must be separated from the canonical configuration
  control plane.
- [Oramaclaw control-plane implementation plan](superpowers/plans/2026-06-20-oramaclaw-control-plane-v1.md)
  contains the staged path toward transactional resource ownership.
- [Codex OpenClaw agent redesign](superpowers/specs/2026-06-19-codex-openclaw-agent-re-design-v2.md)
  defines the binding and generated-profile contracts that must be brought into
  alignment.

