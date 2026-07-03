---
name: skillify
description: >-
  Interactive modular skill creator for orama-system, raw Claude Code, gstack,
  Codex wrappers, and ECC-style harnesses. Creates concise SKILL.md
  orchestrators with strong discovery metadata, one-level instructions,
  examples, references, scripts, templates, eval checklists, boundaries, and
  harness registration. Activates when asked to create a skill, new skill, add a
  sub-skill, /skillify, build a new tool as a skill, make a skill, install a
  skill, modularize a skill, or improve a SKILL.md.
version: 1.1.0
license: Apache 2.0
compatibility: claude-code, gstack, codex, cursor, gemini-cli, ecc
parent_skill: orama-system
triggers:
  - create a skill
  - new skill
  - /skillify
  - add sub-skill
  - build a skill
  - make a skill
  - install a skill
  - modularize a skill
  - improve a SKILL.md
allowed-tools: bash, file-operations, AskUserQuestion
---

# skillify - Interactive Modular Skill Creator

> Run from the repo root (`/path/to/orama-system/`) so relative sub-skill paths
> resolve correctly.

skillify creates production-grade skill folders. It does not make one giant
`SKILL.md`. It creates a concise orchestrator and routes deeper rules into
one-level modular files.

## Core Standard

Before creating or revising any skill, read:

- [`../../references/skill-architecture-guide.md`](../../references/skill-architecture-guide.md) - orama frontmatter, progressive disclosure, 6Cs, LINT rules, boundaries, and anti-patterns
- [`references/codex-thin-wrapper-installs.md`](references/codex-thin-wrapper-installs.md) - Codex wrapper policy
- [`references/ecc-cross-harness-authoring.md`](references/ecc-cross-harness-authoring.md) - ECC cross-harness authoring

External guidance to align with, without blindly copying:

- Anthropic Agent Skills overview: `https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview`
- Anthropic Skill authoring best practices: `https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices`
- Anthropic public skills examples: `https://github.com/anthropics/skills`
- Community directories and field examples may inform examples, eval rubrics, and naming, but repository policy wins over social-media trends.

## Relationship To `gstack-skillify`

This skill and gstack's `skillify` share `name: skillify` by design. They are
complementary:

| Skill | Role | When |
|---|---|---|
| `gstack-skillify` | Primary scrape-to-browser-skill codifier | Use when turning a scrape into a permanent browser skill |
| this orama skill | Modular authoring extension | Use when creating or improving a new skill folder across orama/raw Claude/gstack/Codex/ECC targets |

Defer to `gstack-skillify` for scrape codification. Use this skill for fresh
skill architecture, modularization, harness boundaries, and repo registration.

## When To Use

Use skillify when creating a new:

- orama-system sub-skill
- gstack global skill
- raw Claude Code skill
- Codex local thin wrapper
- ECC cross-harness skill
- modular replacement for an oversized or brittle `SKILL.md`

Do not use skillify for unrelated edits to existing skills. If improving an
existing skill, stay inside that skill's own directory unless the user explicitly
asks for registration or wrapper changes.

## Modern Skill Shape

Prefer this folder shape, trimming unused folders only when the task is truly
small:

```text
your-skill-name/
├── SKILL.md
├── instructions/
│   └── core-workflow.md
├── examples/
│   ├── good/
│   │   └── golden-path.md
│   └── bad/
│       └── anti-patterns.md
├── references/
│   └── architecture-notes.md
├── scripts/
│   └── validate_skill.py
├── templates/
│   └── output-template.md
└── eval/
    └── checklist.md
```

Rules:

- `SKILL.md` is the orchestrator, not the encyclopedia.
- Keep `SKILL.md` under 500 lines and preferably far shorter.
- Keep references one level deep from `SKILL.md`; avoid reference chains.
- Put fragile or repetitive logic in `scripts/`.
- Put output formats in `templates/`.
- Put reviewer personas and checklists in `eval/`.
- Put positive and negative examples in `examples/good/` and `examples/bad/`.
- Every fenced code block in markdown must have a language specifier.

## Codex Local Install Policy

When asked to install repo skills for Codex, install thin wrappers only:

1. Keep the canonical skill in the repo and update that source first.
2. Put only a small Codex-valid wrapper in `~/.agents/skills/<name>/SKILL.md` or repo `.agents/skills/<name>/SKILL.md`.
3. Write `~/.codex/skills/<name>/SKILL.md` only as a compatibility mirror.
4. Include the canonical repo root and canonical `SKILL.md` path in the wrapper.
5. Require `git fetch origin --prune` before reading the canonical card.
6. Run `git pull --ff-only` only when the repo is clean and on a tracking branch.
7. If dirty, use [`../git-history-surgery/references/safe-cross-host-sync-reference-card.md`](../git-history-surgery/references/safe-cross-host-sync-reference-card.md).
8. Do not cache upstream `SKILL.md`, references, scripts, or assets in the local Codex skill dir.
9. Validate the wrapper with Codex `quick_validate.py`, then run a compact local-model smoke test if requested.

For ECC/PT-orama skills consumed by multiple harnesses, read
[`references/ecc-cross-harness-authoring.md`](references/ecc-cross-harness-authoring.md).

## Step 0: Optional gstack Preamble

If gstack is installed, run its update check and analytics preamble:

```bash
if [ -x ~/.claude/skills/gstack/bin/gstack-update-check ]; then
  _UPD=$(~/.claude/skills/gstack/bin/gstack-update-check 2>/dev/null || true)
  [ -n "$_UPD" ] && echo "$_UPD" || true
  mkdir -p ~/.gstack/sessions
  touch ~/.gstack/sessions/"$PPID"
  _TEL=$(~/.claude/skills/gstack/bin/gstack-config get telemetry 2>/dev/null || echo "off")
  _SESSION_ID="$$-$(date +%s)"
  echo "GSTACK_AVAILABLE: true"
else
  echo "GSTACK_AVAILABLE: false"
fi
```

If `GSTACK_AVAILABLE: false`, skip all gstack-specific steps. All other steps
work identically without gstack.

## Step 1: D1 - Skill Identity

Ask via AskUserQuestion:

> D1 - What are we building?
>
> ELI10: A skill is a folder that turns a general AI into a specialist. The name
> becomes the directory and command. The description is the discovery hook that
> tells the agent when to load it.
>
> Recommendation: use a specific activity name and a third-person description.
> `generating-migrations` beats `database-helper`.

Collect:

1. Skill name: lowercase kebab-case, 1-64 chars, no reserved words, matches directory name.
2. One-sentence purpose: third-person, specific, includes activation contexts.

If invalid, re-prompt once with a corrected suggestion.

## Step 2: D2 - Target Context

Ask via AskUserQuestion:

> D2 - Where should this skill live?
>
> ELI10: The same skill idea can live in different harnesses. The target decides
> path, frontmatter, wrapper policy, and registration.

Options:

- A) orama-system sub-skill
- B) gstack global skill
- C) raw Claude Code skill
- D) Codex thin wrapper pointing to an in-repo canonical skill
- E) ECC cross-harness skill
- F) all applicable targets

## Step 3: D3 - Trigger Phrases

Ask for phrases the user would actually type. Include formal names, casual names,
file extensions, tool names, and workflow verbs.

Good triggers are specific. Bad triggers are generic.

```text
Good: generate migration, schema change, add column, rename table, create index
Bad: database, help, tools, stuff
```

Parse the answer into a YAML `triggers:` list.

## Step 4: D4 - Boundaries

Ask what the skill should always do, ask before doing, and never do.

Preset options:

- A) Conservative: ask before any write, delete, external call, install, deploy, or irreversible action.
- B) Standard: verify before done, ask before destructive/deploy/costly operations, never hardcode secrets or skip checks.
- C) Permissive: ask only for irreversible actions, still never hardcode secrets or skip verification.
- D) Custom: user specifies all three tiers.

## Step 5: D5 - Modularity Plan

Ask whether the generated skill needs modular folders.

Default recommendation: create the modular folder shape unless the skill is tiny.

Use this routing rule:

| Content | Destination |
|---|---|
| Discovery metadata and 5-10 step workflow | `SKILL.md` |
| Long rules and procedures | `instructions/*.md` |
| Golden paths and anti-patterns | `examples/good/*.md`, `examples/bad/*.md` |
| Architecture notes or external docs | `references/*.md` |
| Deterministic checks and generators | `scripts/*` |
| Reusable output formats | `templates/*.md` |
| Review checklist and personas | `eval/checklist.md` |

## Step 6: D6 - Preview And Confirm

Generate and show the full frontmatter before writing.

For orama-system targets:

```yaml
---
name: <name>
description: >-
  <purpose>. Use when the user asks for <trigger summary>.
version: 1.0.0
license: Apache 2.0
compatibility: claude-code
parent_skill: orama-system
triggers:
  - <trigger>
allowed-tools: bash, file-operations
---
```

For gstack targets, add:

```yaml
preamble-tier: 1
```

Ask:

> D6 - Does this look right?
>
> Options: A) Yes, create it. B) Edit description. C) Edit triggers. D) Edit modularity. E) Start over.

## Step 7: Write The Skill Folder

### Clobber guard

Always run first:

```bash
TARGET_DIR="bin/orama-system/skills/<name>"
if [ -d "$TARGET_DIR" ]; then
  echo "SKILL_EXISTS: $TARGET_DIR already exists"
  find "$TARGET_DIR" -maxdepth 2 -type f | sort
else
  echo "SKILL_EXISTS: false"
fi
```

If `SKILL_EXISTS: true`, ask whether to overwrite, merge missing files only, or
cancel. If cancelled, stop with `STATUS: BLOCKED - user cancelled, existing skill preserved`.

### SKILL.md body template

Write `SKILL.md` as a concise orchestrator:

```markdown
# <Name> - <one-line tagline>

## Purpose
<1-2 sentences>

## When To Use
- <specific scenario>
- <specific trigger phrase>

## Load Order
1. Read this `SKILL.md`.
2. Read `instructions/core-workflow.md` for the detailed workflow when needed.
3. Read `examples/good/` before generating examples.
4. Read `examples/bad/` when reviewing or refactoring.
5. Run `eval/checklist.md` before declaring done.

## Core Workflow
1. <step>
2. <step>
3. Verify against the eval checklist.

## Boundaries
### Always Do
<from D4>

### Ask First
<from D4>

### Never Do
<from D4>

## References
- [`instructions/core-workflow.md`](instructions/core-workflow.md)
- [`examples/good/golden-path.md`](examples/good/golden-path.md)
- [`examples/bad/anti-patterns.md`](examples/bad/anti-patterns.md)
- [`eval/checklist.md`](eval/checklist.md)
```

### Modular starter files

Create only files that help the skill avoid bloat. For a production skill, prefer:

- `instructions/core-workflow.md`
- `examples/good/golden-path.md`
- `examples/bad/anti-patterns.md`
- `eval/checklist.md`

Use `scripts/` and `templates/` only when there is actual deterministic logic or
output structure to place there.

### Eval checklist template

`eval/checklist.md` must include the 6Cs and reviewer personas:

```markdown
# Eval Checklist

## 6Cs
- [ ] Clarity: no ambiguous instructions
- [ ] Completeness: edge cases and failure modes are covered
- [ ] Conciseness: no repeated or low-value text
- [ ] Consistency: terms and paths are stable
- [ ] Correctness: steps are executable and verified
- [ ] Context: instructions make sense standalone

## Review Personas
- Exec: Is the skill purpose clear and bounded?
- Builder: Can the workflow be executed without guessing?
- Critic: What could go wrong, overreach, or silently fail?
```

### Path discipline

Use relative in-repo links and GitHub URLs only. Never write absolute workstation
paths such as `/Users/<name>/...`. For runtime locations, use `$REPO_ROOT`,
`$OPENCLAW_ROOT`, `$HOME`, or `~`.

## Step 8: Validate The Created Skill

After writing, validate before continuing:

```python
import pathlib
import re
import yaml

path = pathlib.Path("<target_dir>/SKILL.md")
content = path.read_text(encoding="utf-8")
assert content.startswith("---")
match = re.search(r"\n---\s*\n", content[3:])
assert match, "missing closing frontmatter fence"
frontmatter = yaml.safe_load(content[3:match.start() + 3])
assert "name" in frontmatter and "description" in frontmatter
assert re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", frontmatter["name"])
assert len(frontmatter["description"]) <= 1024
assert len(content.splitlines()) <= 500
for fence in re.findall(r"^```(.*)$", content, flags=re.MULTILINE):
    assert fence.strip(), "all fenced code blocks need language specifiers"
```

Fix any failure before moving on.

## Step 9: Register In Mother Skill (orama-system targets only)

Read `bin/orama-system/SKILL.md` and locate the `sub_skills:` block.

Check whether `<name>/SKILL.md` is already listed:

```bash
grep -n "skills/<name>/SKILL.md\|<name>/SKILL.md" bin/orama-system/SKILL.md
```

If already present, skip with note `already registered`.

If not present, ask before editing the mother skill. Append the smallest correct
entry using the repository's existing sub-skill path style.

## Step 10: CLAUDE.md Pointer (orama-system targets only)

Check whether `CLAUDE.md` already references the skill:

```bash
grep -n "<name>" CLAUDE.md
```

If found, skip. If not found, ask before writing. Keep the insertion to one line
and follow CIDF for exact placement.

## Step 11: 6Cs And Best-Practice Review

Read `../../references/skill-architecture-guide.md` again if it was not already
loaded in this session. Check the created files against:

| C | Check | Pass condition |
|---|---|---|
| Clarity | Instructions are unambiguous | No `it depends` without a decision rule |
| Completeness | Edge cases and failure modes addressed | Boundaries include all three tiers |
| Conciseness | Every sentence earns tokens | No repeated rule phrasing |
| Consistency | Same term for same concept | No synonym drift |
| Correctness | Steps are executable | Validation passes |
| Context | Skill stands alone | No unexplained jargon |

Also check modern skill hygiene:

- Strong third-person description with trigger contexts.
- One purpose per skill.
- Modular files are one level deep.
- Heavy logic is in scripts, not prose.
- Examples include at least one good path and one anti-pattern for non-trivial skills.
- Eval includes reviewer personas.
- Cross-tool assumptions are explicit.
- No secrets, workstation paths, or unlabeled code fences.

## Step 12: Summary

Report:

```text
STATUS: DONE

Created or updated:
  <target_dir>/SKILL.md
  <target_dir>/instructions/core-workflow.md
  <target_dir>/examples/good/golden-path.md
  <target_dir>/examples/bad/anti-patterns.md
  <target_dir>/eval/checklist.md

Registered:
  bin/orama-system/SKILL.md       <added/skipped/not applicable>
  CLAUDE.md                      <added/skipped/not applicable>

Validation:
  frontmatter: PASS/FAIL
  modularity: PASS/FAIL
  6Cs: PASS/PASS_WITH_NOTES/FAIL
  code fences: PASS/FAIL

To invoke:
  /skill bin/orama-system/skills/<name>/SKILL.md
```

## Telemetry (gstack only)

Skip if `GSTACK_AVAILABLE: false`.

```bash
if [ -x ~/.claude/skills/gstack/bin/gstack-timeline-log ]; then
  ~/.claude/skills/gstack/bin/gstack-timeline-log \
    '{"skill":"skillify","event":"completed","outcome":"success","session":"'"$_SESSION_ID"'"}' \
    2>/dev/null || true
fi
```

## Boundaries

### Always Do

- Read `../../references/skill-architecture-guide.md` before writing or validating a skill.
- Keep `SKILL.md` as a concise orchestrator.
- Use modular one-level references for detailed rules.
- Run the clobber guard before any write.
- Validate name, frontmatter, description length, line count, and code fences.
- Report 6Cs result before declaring done.

### Ask First

- Overwriting or deleting an existing skill directory.
- Writing to `bin/orama-system/SKILL.md`.
- Writing to `CLAUDE.md`.
- Installing or publishing a skill outside the repository.

### Never Do

- Source or execute any `.md` file as a shell script.
- Create a massive all-in-one `SKILL.md` when modular folders would fit better.
- Create nested reference chains that require reading references from references.
- Copy canonical repo skill bodies into Codex wrapper directories.
- Hardcode secrets, tokens, personal paths, LAN IPs, or workstation-specific paths.
- Skip verification or mark DONE with failing 6Cs.
