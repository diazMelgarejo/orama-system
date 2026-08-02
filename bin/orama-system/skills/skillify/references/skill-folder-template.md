# Skill Folder Template Reference

Use this as the source for generated skill skeletons. Do not paste this entire file into a new `SKILL.md`.

## Recommended Folder Shape

```text
your-skill-name/
├── SKILL.md
├── instructions/
│   └── core-workflow.md
├── examples/
│   ├── good/
│   │   └── skillify-golden-path.md
│   └── bad/
│       └── anti-patterns.md
├── references/
│   └── architecture-notes.md
├── scripts/
├── templates/
└── eval/
    └── checklist.md
```

Trim unused folders for tiny skills. Do not create decorative empty folders.

## Concise SKILL.md Template

```markdown
---
name: <skill-name>
description: >-
  <third-person purpose>. Use when the user asks for <specific trigger contexts>.
version: 1.0.0
license: Apache 2.0
compatibility: claude-code
triggers:
  - <trigger>
allowed-tools: bash, file-operations
---

# <Skill Name> - <one-line tagline>

## Purpose

<1-2 sentences.>

## When To Use

- <specific scenario>
- <specific trigger phrase>

## Load Order

1. Read this `SKILL.md`.
2. Read `instructions/core-workflow.md` when the workflow needs detail.
3. Read examples only when generating or reviewing examples.
4. Run `eval/checklist.md` before declaring done.

## Workflow

1. <step>
2. <step>
3. Verify against the checklist.

## Boundaries

### Always Do

- <rule>

### Ask First

- <rule>

### Never Do

- <rule>

## References

- [`instructions/core-workflow.md`](instructions/core-workflow.md)
- [`eval/checklist.md`](eval/checklist.md)
```

## instructions/core-workflow.md Template

```markdown
# Core Workflow

## Steps

1. Gather required inputs.
2. Inspect existing repo patterns before inventing new ones.
3. Apply the smallest change that satisfies the request.
4. Verify with the cheapest reliable check.
5. Report result, files changed, and any skipped verification.

## Failure Handling

- If required inputs are missing, ask at most three focused questions.
- If a destructive action is needed, stop for explicit confirmation.
- If validation fails, fix once; if still failing, report the blocker.
```

## examples/good/skillify-golden-path.md Template

```markdown
# Golden Path Example

## Input

`<realistic user request>`

## Expected Behavior

- Activates the skill.
- Loads only necessary references.
- Produces a bounded, verified result.
- Reports exactly what changed.
```

## examples/bad/anti-patterns.md Template

```markdown
# Anti-Patterns

## Giant SKILL.md

Problem: all examples, templates, and long procedures are pasted into `SKILL.md`.

Fix: keep `SKILL.md` as the orchestrator and move details into modular files.

## Vague Trigger

Problem: description says `helps with tools`.

Fix: describe concrete user requests and trigger phrases.

## Hidden Side Effects

Problem: installs, deletes, deploys, or publishes without asking.

Fix: put one-way actions under Ask First.
```

## eval/checklist.md Template

```markdown
# Eval Checklist

## 6Cs

- [ ] Clarity: no ambiguous instructions.
- [ ] Completeness: edge cases and failure modes are covered.
- [ ] Conciseness: no repeated or low-value text.
- [ ] Consistency: terms and paths are stable.
- [ ] Correctness: steps are executable and verified.
- [ ] Context: instructions make sense standalone.

## Review Personas

- Exec: Is the purpose clear and bounded?
- Builder: Can the workflow be executed without guessing?
- Critic: What could overreach, silently fail, or violate boundaries?

## Size Gate

- [ ] New generated `SKILL.md` is <= 200 lines, or has a written reason.
- [ ] Any existing `SKILL.md` remains <= 500 lines.
```
