# PR 2 — Detailed Implementation Steps

Date: 2026-07-07
Branch: `skillify-pr2-low-risk-skills`
Base: `main` (after PR #141 squash merge)

## Overview

This document provides per-skill, per-file implementation steps for upgrading the three low-risk skills in PR 2. Each step includes the exact edit required, the validator rule it satisfies, and the acceptance criterion for verification.

## Pre-work: Validator KNOWN_FIELDS update

**File:** `scripts/review/check_orama_skills.py`
**Rationale:** The gstack skill uses legitimate gstack-specific frontmatter fields (`version`, `license`, `compatibility`, `parent_skill`, `gstack_version`, `gstack_install`) that are not in the Claude Code standard but are part of the orama-system skill ecosystem. Without adding these to `KNOWN_FIELDS`, the validator produces 7 false-positive `frontmatter.unknown-field` warnings for gstack alone, drowning real issues in noise.

**Edit:** Add gstack-specific fields to the `KNOWN_FIELDS` frozenset:

```python
KNOWN_FIELDS = {
    # Claude Code standard fields
    "name", "description", "when_to_use", "argument-hint", "arguments",
    "disable-model-invocation", "user-invocable", "allowed-tools",
    "disallowed-tools", "model", "effort", "context", "agent", "hooks",
    "paths", "shell", "version", "license", "compatibility",
    # orama-system / gstack ecosystem fields
    "parent_skill", "triggers", "canonical_path", "supersedes",
    "last_updated", "agent_compatibility", "layer", "upstream",
    "upstream_path", "origin",
    # gstack-specific fields (legitimate for gstack-originated skills)
    "gstack_version", "gstack_install",
}
```

**Note:** `triggers` is deprecated in favor of `when_to_use` but remains known for backward compatibility during migration. Skills using `triggers` should migrate to `when_to_use` in later PRs.

**Acceptance:** `python3 scripts/review/check_orama_skills.py --mode baseline` shows zero `frontmatter.unknown-field` warnings for gstack after this change.

---

## Skill 1: `gstack` (edit first — Planning Gstack priority)

**File:** `bin/orama-system/gstack/SKILL.md`

### Step 1.1: Refactor frontmatter — extract `when_to_use` from description

**Current description** embeds trigger phrases and is ~650 chars. Extract the activation triggers into a separate `when_to_use` field.

**Current:**
```yaml
description: >-
  gstack v1.58.3.0 integration sub-skill. Full routing table for web browsing,
  QA, shipping, planning reviews, design, DX audits, retros, and GBrain.
  Activates for: /browse, /qa, /ship, /review, /investigate, /design-review,
  /canary, /benchmark, /retro, gbrain, gstack skills, web browsing, QA testing,
  deploy, design review, canary monitoring, performance benchmarks.
  Also covers: gstack fork-patch upgrades, gbrain upgrades.
```

**Target:**
```yaml
description: >-
  gstack v1.58.3.0 integration sub-skill. Full routing table for web browsing,
  QA, shipping, planning reviews, design, DX audits, retros, and GBrain. Covers
  gstack fork-patch upgrades and gbrain upgrades.
when_to_use: >-
  Activates for: /browse, /qa, /ship, /review, /investigate, /design-review,
  /canary, /benchmark, /retro, gbrain, gstack skills, web browsing, QA testing,
  deploy, design review, canary monitoring, performance benchmarks.
```

**Validator rule satisfied:** `frontmatter.when_to_use` — activation contexts now in dedicated field.
**Constraint:** `description` + `when_to_use` combined must stay <= 1,536 chars. Current split keeps combined well under cap.

### Step 1.2: Add `effort: medium`

**Insert after `when_to_use`:**
```yaml
effort: medium
```

**Validator rule satisfied:** `frontmatter.effort` — EFFORT_RECOMMENDATIONS maps gstack to "medium".

### Step 1.3: Add `context: fork` + `agent`

**Insert after `effort`:**
```yaml
context: fork
agent: Explore
```

**Validator rule satisfied:** `frontmatter.context` — gstack is in FORK_RECOMMENDED_SKILLS (review/QA/harness skill should consider fork).
**Rationale:** gstack's `/review`, `/qa`, `/investigate`, `/autoplan` routes benefit from isolated subagent execution. `agent: Explore` matches the investigative nature of most gstack routes.

### Step 1.4: Add `paths` for monorepo-aware activation

**Insert after `agent`:**
```yaml
paths:
  - "bin/orama-system/gstack/**"
  - "bin/orama-system/scripts/**"
```

**Validator rule satisfied:** improves scoping; no validator rule directly requires this, but it satisfies the metadata strategy from the roadmap.

### Step 1.5: Deprecate `triggers` — migrate to `when_to_use`

**Current:** `triggers` list with 11 items.
**Action:** Remove the `triggers` field entirely. Its content is already represented in `when_to_use` (Step 1.1).

**Validator impact:** After KNOWN_FIELDS update (pre-work), `triggers` is still known (backward compat), so removing it is a net positive — one less non-standard field.

### Step 1.6: Add ADR-045 routing reference

**In the body, after the "## Rules" section opening, add a new sub-section:**

```markdown
## Resilience Routing

For gstack/gbrain/CRG error handling, timeouts, retries, and diagnostics, route
to the shared ADR-045 framework instead of inventing local variants:

- Canonical: `docs/adr/ADR-045-gstack-gbrain-crg-error-resilience.md`
- Implementation guide: `docs/how-to/hardening-gstack-gbrain-skills.md`
- Library: `bin/orama-system/scripts/lib/gstack-gbrain-crg-safe.sh`

Skills that call gstack/gbrain/CRG tools should source the safety library and
run pre-flight checks before first external calls.
```

**Rationale:** Satisfies the ADR-045 alignment requirement from the planning doc. gstack is the routing surface; it should point downstream skills to the shared resilience framework.

### Step 1.7: Verify body line count

After Step 1.6 additions, the body may exceed 500 lines. If so:
- Option A: Move the "## GBrain on Claude Desktop (MCP)" section to a new reference file `references/gbrain-claude-desktop-mcp.md` and link to it.
- Option B: Move "## GBrain Ops — Failure Modes and Fixes" to a new reference file `references/gbrain-ops-failure-modes.md` and link to it.
- Choose based on which section is less frequently needed at skill-load time.

**Acceptance:** `SKILL.md` body <= 500 lines after all edits.

### gstack edit summary

| Field | Before | After |
|---|---|---|
| `description` | 650 chars with embedded triggers | ~250 chars, core capability only |
| `when_to_use` | absent | New field with activation triggers |
| `effort` | absent | `medium` |
| `context` | absent | `fork` |
| `agent` | absent | `Explore` |
| `paths` | absent | `bin/orama-system/gstack/**`, `bin/orama-system/scripts/**` |
| `triggers` | 11-item list | Removed (content in `when_to_use`) |
| ADR-045 routing | absent | "## Resilience Routing" section added |

---

## Skill 2: `first-run-setup` (edit second)

**File:** `bin/orama-system/skills/first-run-setup/SKILL.md`

### Step 2.1: Refactor frontmatter — extract `when_to_use` from description

**Current description** contains activation triggers inline.

**Current:**
```yaml
description: |
  Idempotent first-run bootstrap for the orama-system toolchain: Node, Python 3.13,
  Ollama models, code-review-graph, gbrain, unified embeddings, Claude Code profiles,
  and PreCompact hook. Use when setting up a new machine, after fresh clone, or when
  the user asks for first-run install, bootstrap, or §0 checklist.
```

**Target:**
```yaml
description: >-
  Idempotent first-run bootstrap for the orama-system toolchain: Node, Python 3.13,
  Ollama models, code-review-graph, gbrain, unified embeddings, Claude Code profiles,
  and PreCompact hook.
when_to_use: >-
  Activates when setting up a new machine, after fresh clone, or when the user asks
  for first-run install, bootstrap, or §0 checklist.
```

**Validator rule satisfied:** `frontmatter.when_to_use`.
**Constraint:** Combined listing <= 1,536 chars. Well under.

### Step 2.2: Add `disable-model-invocation: true`

**Insert after `when_to_use`:**
```yaml
disable-model-invocation: true
```

**Validator rule satisfied:** `frontmatter.disable-model-invocation` — first-run-setup is in `SIDE_EFFECT_SKILLS` (installs, configures, mutates system state). Must require explicit user invocation.

### Step 2.3: Add `effort: medium`

**Insert after `disable-model-invocation`:**
```yaml
effort: medium
```

**Validator rule satisfied:** `frontmatter.effort`. Medium because bootstrap involves multiple toolchain components (Node, Python, Ollama, CRG, gbrain, embeddings, profiles).

### Step 2.4: Add `argument-hint` and `arguments`

**Insert after `effort`:**
```yaml
argument-hint: "[status|install|mcp]"
arguments: [action]
```

**Rationale:** The skill supports three workflow modes (`status`, `install`, `mcp`). Arguments make invocation reusable and explicit.

### Step 2.5: Add `paths` for activation scoping

**Insert after `arguments`:**
```yaml
paths:
  - "bin/orama-system/scripts/**"
  - "scripts/**"
```

### Step 2.6: Add ADR-045 bootstrap routing reference

**In the body, after "## Flags" section, add:**

```markdown
## Error Resilience

For gstack/gbrain/CRG error handling during bootstrap, source the shared
ADR-045 safety framework:

```bash
source bin/orama-system/scripts/lib/gstack-gbrain-crg-safe.sh
```

Run `_detect_errors` before first external gbrain or CRG call. Use
`_retry_with_backoff` for idempotent bootstrap steps. Report failures with
`_err_actionable` for clear diagnostics.

See: `docs/adr/ADR-045-gstack-gbrain-crg-error-resilience.md`
```

**Rationale:** first-run-setup is listed as an ADR-045 Phase 2 priority bootstrap skill. It should point to the shared framework rather than duplicating policy.

### first-run-setup edit summary

| Field | Before | After |
|---|---|---|
| `description` | ~350 chars with triggers | ~200 chars, core capability only |
| `when_to_use` | absent | New field with activation triggers |
| `disable-model-invocation` | absent | `true` (side-effect skill) |
| `effort` | absent | `medium` |
| `argument-hint` | absent | `[status\|install\|mcp]` |
| `arguments` | absent | `[action]` |
| `paths` | absent | `bin/orama-system/scripts/**`, `scripts/**` |
| ADR-045 routing | absent | "## Error Resilience" section added |

---

## Skill 3: `shell-hygiene` (edit third)

**File:** `bin/orama-system/skills/shell-hygiene/SKILL.md`

### Step 3.1: Refactor frontmatter — extract `when_to_use` from description

**Current description** is ~800 chars with embedded triggers.

**Current:**
```yaml
description: >
  Safe shell command execution for agents in this environment. Covers two enforced
  gotchas: (1) sleep N && <command> chains are blocked — wait on background processes,
  file growth, or conditions with Monitor until-loops / run_in_background instead;
  (2) the shell is zsh, which does NOT word-split unquoted $vars or `for x in $var`,
  so iterate multiline output with `while IFS= read -r` and pass lists as arrays.
  Invoke when waiting on long-running work (background tasks, npm install, claude
  update, port/health, PID exit) or when looping over command output / file lists.
```

**Target:**
```yaml
description: >-
  Safe shell command execution for agents. Covers enforced no-sleep-chain rules and
  zsh word-splitting behavior. Agents must use Monitor until-loops and
  run_in_background instead of sleep chains, and iterate command output with
  `while IFS= read -r` rather than unquoted `for x in $var`.
when_to_use: >-
  Activates when waiting on long-running work (background tasks, npm install,
  claude update, port/health checks, PID exit) or when looping over command output
  / file lists.
```

**Validator rule satisfied:** `frontmatter.when_to_use`.
**Constraint:** Combined listing <= 1,536 chars. Original description was ~800 chars; split keeps each half well under.

### Step 3.2: Add `effort: low`

**Insert after `when_to_use`:**
```yaml
effort: low
```

**Validator rule satisfied:** `frontmatter.effort` — EFFORT_RECOMMENDATIONS maps shell-hygiene to "low".

### Step 3.3: Add `paths` for shell-relevant file activation

**Insert after `effort`:**
```yaml
paths:
  - "bin/orama-system/scripts/**"
  - "bin/orama-system/gstack/**"
```

### Step 3.4: Verify portable script references

**Check body for non-portable patterns:**
- Body uses `Bash(command: "...", run_in_background: true)` — portable, correct.
- Body uses `~/.orama-system/first-run.done` reference in quick ref table — this is a home-dir path (`~`), not an absolute personal path. The validator's `has_personal_path` checks for common user-profile path patterns on Unix and Windows. Home-dir references (`~/...`) are NOT flagged.
- No raw LAN IPs detected.

**No body edits needed for this step.**

### shell-hygiene edit summary

| Field | Before | After |
|---|---|---|
| `description` | ~800 chars with triggers | ~350 chars, core rules only |
| `when_to_use` | absent | New field with activation triggers |
| `effort` | absent | `low` |
| `paths` | absent | `bin/orama-system/scripts/**`, `bin/orama-system/gstack/**` |

---

## Validation Pipeline

### Step 4.1: Run validator baseline on all three skills

```bash
python3 scripts/review/check_orama_skills.py --mode baseline --scan-root bin/orama-system/gstack --scan-root bin/orama-system/skills/first-run-setup --scan-root bin/orama-system/skills/shell-hygiene
```

**Expected result after all edits:**
- Zero `frontmatter.unknown-field` warnings (gstack fields now in KNOWN_FIELDS)
- Zero `frontmatter.when_to_use` warnings (all three skills have `when_to_use`)
- Zero `frontmatter.effort` warnings (all three skills have `effort`)
- Zero `frontmatter.disable-model-invocation` warnings (first-run-setup has it)
- Zero `frontmatter.context` warnings (gstack has `context: fork`)
- Any remaining warnings should be pre-existing (from other skills) or allowlisted with justification.

### Step 4.2: Run validator unit tests

```bash
python3 -m pytest tests/test_check_orama_skills.py -v
```

**Expected result:** All tests pass (no regressions from KNOWN_FIELDS change).

### Step 4.3: Run full repo baseline

```bash
python3 scripts/review/check_orama_skills.py --mode baseline
```

**Expected result:** Warning count for the three target roots is reduced vs. pre-PR baseline. No new errors introduced.

---

## PR Structure

### Files changed (expected)

| File | Action | Lines |
|---|---|---|
| `scripts/review/check_orama_skills.py` | Edit — add gstack fields to KNOWN_FIELDS | ~+3 |
| `bin/orama-system/gstack/SKILL.md` | Edit — refactor frontmatter, add ADR-045 section | ~+30, ~-15 |
| `bin/orama-system/skills/first-run-setup/SKILL.md` | Edit — refactor frontmatter, add ADR-045 section | ~+25, ~-5 |
| `bin/orama-system/skills/shell-hygiene/SKILL.md` | Edit — refactor frontmatter | ~+12, ~-8 |
| `docs/plans/2026-07-07-pr2-low-risk-skill-standardization.md` | Already on branch | — |

### Commit sequence

1. `scripts/review/check_orama_skills.py` — KNOWN_FIELDS update (isolated, testable)
2. `bin/orama-system/gstack/SKILL.md` — Planning Gstack + ADR-045 alignment
3. `bin/orama-system/skills/first-run-setup/SKILL.md` — explicit invocation + ADR-045 routing
4. `bin/orama-system/skills/shell-hygiene/SKILL.md` — metadata cleanup

### Acceptance criteria

- [ ] `python3 scripts/review/check_orama_skills.py --mode baseline` shows reduced warnings for all 3 target skills
- [ ] `python3 -m pytest tests/test_check_orama_skills.py -v` passes with no regressions
- [ ] No skill exceeds 500 lines
- [ ] All `description` + `when_to_use` combined <= 1,536 chars
- [ ] `first-run-setup` has `disable-model-invocation: true`
- [ ] `gstack` has `context: fork` + `agent`
- [ ] ADR-045 references use canonical paths (not Margined copies)
- [ ] No high-risk skills touched
- [ ] PR body preserves original purpose at top, appends execution notes below

---

## Risk Notes

1. **gstack body line count:** At ~500 lines, gstack is at the hard ceiling. The ADR-045 "## Resilience Routing" section adds ~8 lines. If this pushes over 500, move either "## GBrain on Claude Desktop (MCP)" or "## GBrain Ops — Failure Modes and Fixes" to a reference file.

2. **KNOWN_FIELDS scope creep:** Adding gstack-specific fields to the validator is a cross-cutting change. It affects validation for ALL skills, not just the 3 targets. Mitigation: the added fields are documented gstack conventions; they don't change validation behavior for non-gstack skills.

3. **ADR-045 path stability:** The ADR-045 document paths referenced in Steps 1.6 and 2.6 must exist on `main`. Verify before committing.
