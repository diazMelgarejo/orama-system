# Golden Path Example

## Input

> "/skillify — I need a skill that rotates API keys in our secrets manager.
> Target claude-code. Ask first before touching anything in prod."

## Expected Behavior

1. Ask the intake questions (name, purpose, target harness, trigger phrases,
   boundaries) only for facts not already given — here, trigger phrases and
   the exact folder shape still need confirming.
2. Run the clobber guard against `bin/orama-system/skills/key-rotation/`
   before proposing anything.
3. Choose the smallest folder shape that satisfies a side-effect-bearing
   skill: `SKILL.md`, `instructions/`, `references/`, `eval/`. Skip
   `examples/` and `templates/` if the skill has no golden-path variance
   worth documenting yet.
4. Preview frontmatter and the concise `SKILL.md` outline before writing —
   including `disable-model-invocation: true` (this skill mutates
   credentials) and an explicit `Ask First: any production key rotation`
   boundary.
5. Write `SKILL.md` plus the needed modular files only.
6. Validate: frontmatter, line count (<=200 target), code-fence language
   specifiers, relative links, 6Cs.
7. Report created files, registration status (not registered as an
   orama-system sub-skill unless asked), and the validation result — using
   the `STATUS: DONE` report format from
   [`../../references/modular-skill-authoring.md`](../../references/modular-skill-authoring.md).

## Second Input (upgrade path)

> "skillify feels stale — go check yourself against your own standards
> and Anthropic's skill-creator standards, and fix what's actually wrong."

## Expected Behavior

- Read `../../references/skill-architecture-guide.md`,
  `../modular-skill-authoring.md`, and `../skill-folder-template.md` before
  touching anything (skillify's own "Load First" rule applies to itself).
- Diff the current `SKILL.md` against both standards; only change what is
  genuinely missing (e.g. no `examples/`, no `eval/`) — do not rewrite
  sections that already comply, per the "reuse or upgrade" and "keep it
  lean" principles.
- Where the two standards disagree (for example: Anthropic's skill-creator
  keeps all "when to use" text in the frontmatter `description` only, while
  this repo's `skill-architecture-guide.md` recommended structure includes a
  body-level `## When to Use` section), state the conflict and the choice
  made instead of silently picking one — this is exactly the kind of thing
  `AskUserQuestion` exists for when it isn't obviously safe to decide alone.
