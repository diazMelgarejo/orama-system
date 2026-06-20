# Code Review: `feat/openclaw-codex-app-server`

**Date:** 2026-06-20  
**Reviewed range:** `main...04bac55`  
**Verdict:** **Do not merge or release this branch yet.**

The branch has useful groundwork: typed manifest structures, a Codex binding
path, focused tests, and a written control-plane direction. It also introduces
five concrete failures that can overwrite operator-owned files, lose active
OpenClaw configuration, accept raw credentials, publish an unusable wheel, or
generate instructions that contradict the implementation.

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

### R1: Profile generation writes to the wrong directory and destroys local edits

**Severity:** Critical  
**Evidence:**
[`generate_codex_openclaw_profile.py:46-52`](../bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/generate_codex_openclaw_profile.py#L46-L52),
[`58-60`](../bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/generate_codex_openclaw_profile.py#L58-L60),
[`250-256`](../bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/generate_codex_openclaw_profile.py#L250-L256)

`--openclaw-home` is used only to find and hash `openclaw.json`. The generated
`CODEX.md`, `AGENTS.md`, and `TOOLS.md` are instead written as relative paths in
the invoking process's current directory. `write_or_preview()` always calls
`Path.write_text()` and has no marker-based merge, backup, or explicit overwrite
confirmation.

**Concrete trigger:** run the generator from a repository that already has
`agents/codex-agent/AGENTS.md`, while passing another directory with
`--openclaw-home`. The existing repository file is replaced; the intended
OpenClaw home receives none of the generated directive files.

**Impact:** an installation command can silently replace operator-authored agent
instructions in an unrelated working tree. The profile is then absent from the
runtime it was supposed to configure.

**Minimum fix:** compute all output paths from an explicit runtime/profile root.
Use the approved generated-section markers to merge only generated content;
refuse an unmarked overwrite unless the operator passes an explicit force flag.
Add an integration test that proves a non-generated block survives regeneration
and that every output lands under `--openclaw-home`.

### R2: Independent configuration writers can erase each other's changes

**Severity:** Critical  
**Evidence:**
[`bind_codex_backend.sh:62-75`](../bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/bind_codex_backend.sh#L62-L75),
[`225-240`](../bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/bind_codex_backend.sh#L225-L240),
[`334-342`](../bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/bind_codex_backend.sh#L334-L342),
[`discover.py:353-387`](../scripts/discover.py#L353-L387)

The binder protects only itself with `.codex-bind.lockdir`. Discovery reads the
entire configuration, mutates selected providers, and rewrites the whole file
without acquiring that lock or checking whether its baseline changed. Other
writers follow similar independent read-modify-write patterns.

**Concrete trigger:** discovery reads an older `openclaw.json`; the binder then
adds the `codex` provider and `codex-agent`; discovery finishes and writes its
stale in-memory document. The newly bound provider and agent disappear. The
reverse ordering can likewise discard newly discovered endpoint data.

**Impact:** scheduled discovery and an operator binding action can silently lose
valid routing or agent configuration. Atomic `mv` protects against torn files,
not against stale full-document writes.

**Minimum fix:** before any further writer is added, establish one shared
configuration transaction boundary: a shared lock plus a baseline fingerprint
check as the short-term guard, followed by manifest/resource ownership and
conflict resolution in `orama-openclaw-control`. No path should retain a private
full-file writer after that migration.

### R3: Nested raw credentials pass manifest validation

**Severity:** Critical  
**Evidence:** [`schema.py:74-86`](../src/oramaclaw/schema.py#L74-L86)

`_check_no_raw_credentials()` iterates only the immediate keys of a resource's
`spec`. It does not inspect nested dictionaries or lists, despite the schema
contract prohibiting raw credentials in any spec value.

**Concrete trigger:** a valid resource with
`"spec": {"provider": {"apiKey": "test-secret"}}` parses successfully. The
same secret at the top level is rejected.

**Impact:** a raw credential can enter the manifest, result, or persisted state
through the newly introduced control-plane contract. That breaks the
auth-by-reference boundary before the execution engine even exists.

**Minimum fix:** recursively walk mappings and lists, rejecting forbidden keys at
every depth. Add parameterized tests for nested objects and arrays, including
case normalization if the public format permits variants.

### R4: The distributable wheel omits the new Oramaclaw package

**Severity:** Critical  
**Evidence:** [`pyproject.toml:55-56`](../pyproject.toml#L55-L56)

The Hatch wheel package list contains `bin`, `src/orama_system`, and
`src/utils`, but not `src/oramaclaw`. A wheel built from this branch succeeds,
yet inspection shows no `oramaclaw/` files.

**Concrete trigger:** install the wheel into a clean virtual environment and
attempt `import oramaclaw`. The import fails because the package was never
included in the distribution.

**Impact:** source-tree tests can pass while every released or installed control
plane fails at import time.

**Minimum fix:** add `src/oramaclaw` to the wheel package configuration and add a
CI smoke test that builds the wheel, installs it into an isolated environment,
and imports every supported public package.

### R5: Generated delegation instructions contradict the binding contract

**Severity:** Important  
**Evidence:**
[`generate_codex_openclaw_profile.py:174-181`](../bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/generate_codex_openclaw_profile.py#L174-L181),
[`bind_codex_backend.sh:331-342`](../bin/orama-system/skills/openclaw-skills/codex-openclaw-agent/scripts/bind_codex_backend.sh#L331-L342)

The generated `AGENTS.md` tells operators to configure
`agents.bindings.main.allowAgents`. The binder documents that the legacy
`agents.bindings.*.allowAgents` path is rejected and writes
`agents.defaults.subagents.allowAgents` instead.

**Concrete trigger:** an operator follows the generated `AGENTS.md` rather than
the binder implementation. The resulting delegation configuration uses a path
the new control-plane contract rejects.

**Impact:** the feature can appear configured while Codex-agent delegation is
non-functional or rejected at validation time.

**Minimum fix:** generate only the accepted path and introduce a single tested
constant or shared schema definition so the binder, profile generator, skill,
and control-plane manifest cannot drift independently.

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

This branch is ready for another review only when all of the following hold:

1. Profile generation writes to an explicit runtime root and merges marked
   generated sections without replacing operator content.
2. All active `openclaw.json` writers use one transaction/ownership boundary or
   prove they cannot overwrite a newer baseline.
3. Manifest validation rejects forbidden credential keys recursively.
4. The built wheel installs and imports `oramaclaw` in a clean environment.
5. Generated delegation documentation names only
   `agents.defaults.subagents.allowAgents`.
6. Tests demonstrate each requirement above, not merely the presence of source
   text.

## Related Design Work

- [V2 Oramaclaw lifecycle plugin](v2/40-oramaclaw-lifecycle-plugin.md) documents
  why lifecycle discovery must be separated from the canonical configuration
  control plane.
- [Oramaclaw control-plane implementation plan](superpowers/plans/2026-06-20-oramaclaw-control-plane-v1.md)
  contains the staged path toward transactional resource ownership.
- [Codex OpenClaw agent redesign](superpowers/specs/2026-06-19-codex-openclaw-agent-re-design-v2.md)
  defines the binding and generated-profile contracts that must be brought into
  alignment.

