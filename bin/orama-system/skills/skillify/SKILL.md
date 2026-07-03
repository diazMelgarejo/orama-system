---
name: skillify
description: >-
  Interactive modular skill creator for orama-system, raw Claude Code, gstack,
  Codex wrappers, and ECC-style harnesses. Creates concise SKILL.md
  orchestrators with strong discovery metadata, one-level modular references,
  examples, eval checklists, boundaries, and harness registration. Activates for
  create a skill, new skill, add a sub-skill, /skillify, build a skill, make a
  skill, install a skill, modularize a skill, or improve a SKILL.md.
version: 1.2.0
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

# skillify - Concise Skill Orchestrator

> Run from the repo root so relative skill paths resolve correctly.

skillify creates or improves skill folders. `SKILL.md` is the orchestrator, not
the encyclopedia. Put detailed procedures, examples, templates, and eval rubrics
in one-level reference files.

## Load First

Before writing or revising a skill, read:

- [`../../references/skill-architecture-guide.md`](../../references/skill-architecture-guide.md) - repo standard, frontmatter, progressive disclosure, 6Cs, lint rules

Read target-specific references **ONLY** when needed:

- [`references/codex-thin-wrapper-installs.md`](references/codex-thin-wrapper-installs.md) - Codex wrapper installs
- [`references/ecc-cross-harness-authoring.md`](references/ecc-cross-harness-authoring.md) - ECC cross-harness skills

## Non-Negotiables

- New generated `SKILL.md` files should be under 200 lines. Shorter is better.
- Existing or exceptional `SKILL.md` files must stay under 500 lines.
- Offload examples, full templates, long rules, and checklists to modular files.
- Keep modular files one level away from `SKILL.md`; avoid reference chains.
- Every fenced code block must include a language specifier.
- Never hardcode secrets, personal paths, raw LAN IPs, or workstation-specific paths.

## Workflow

1. Ask for skill name, purpose, target harness, trigger phrases, and boundaries.
2. Choose the smallest folder shape that satisfies the task.
3. Preview frontmatter and the concise `SKILL.md` outline before writing.
4. Run the clobber guard before any write.
5. Write `SKILL.md` plus only the needed modular files.
6. Register in `bin/orama-system/SKILL.md` only for orama sub-skills and only after confirmation.
7. Touch `CLAUDE.md` only after confirmation.
8. Validate frontmatter, line counts, code fences, relative links, and 6Cs.
9. Report created files, registration status, and validation result.

- [`references/modular-skill-authoring.md`](references/modular-skill-authoring.md) - skillify workflow and validation rules

## Folder Shape

Prefer this shape for non-trivial skills:

```text
your-skill-name/
├── SKILL.md
├── instructions/
├── examples/good/
├── examples/bad/
├── references/
├── scripts/
├── templates/
└── eval/
```

Trim unused folders for tiny skills. Do not create decorative empty structure.

- [`references/skill-folder-template.md`](references/skill-folder-template.md) - reusable folder layout, short `SKILL.md` template, examples, eval checklist

## Target Rules

- orama-system sub-skill: canonical path is under `bin/orama-system/skills/<name>/` unless the parent registry shows another current convention.
- gstack global skill: add gstack frontmatter fields and template source only when requested.
- raw Claude Code skill: keep platform-specific assumptions out unless requested.
- Codex install: create thin wrappers only; never copy canonical skill bodies into local wrapper dirs.
- ECC skill: use harness adapters only at the edge.

## Boundaries

### Always Do

- Read the architecture guide and skillify references before writing.
- Keep `SKILL.md` concise and move long material out.
- Validate generated `SKILL.md` line count: target <= 200, hard ceiling <= 500.
- Run the 6Cs review before declaring done.

### Ask First

- Overwriting or deleting an existing skill directory.
- Writing to `bin/orama-system/SKILL.md`.
- Writing to `CLAUDE.md`.
- Installing or publishing outside the repository.

### Never Do

- Source or execute markdown as shell.
- Create a massive all-in-one `SKILL.md`.
- Create nested reference chains.
- Copy canonical repo skill bodies into Codex wrapper directories.
- Mark done with failing validation.
