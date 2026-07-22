# Eval Checklist — skillify

## 6Cs

- [ ] Clarity: intake questions and workflow steps have exactly one reading.
- [ ] Completeness: boundaries cover overwrite, registration, and
      publish-outside-repo cases.
- [ ] Conciseness: `SKILL.md` still reads as a table of contents, not an
      encyclopedia.
- [ ] Consistency: "canonical skill", "wrapper", "sub-skill" are used the
      same way every time they appear.
- [ ] Correctness: every command in the modular references has actually been
      run against this repo (not assumed).
- [ ] Context: a reader with no prior orama-system context can follow the
      Workflow section without opening a second file.

## Review Personas

- **Exec** — Is it obvious, from `SKILL.md` alone, what skillify produces
  and where it writes?
- **Builder** — Can the 12-step Workflow be executed without guessing a
  missing step (clobber guard, registration confirmation, validation)?
- **Critic** — What could skillify overreach on? Check specifically:
  writing to `.claude/skills/` (forbidden — canonical-source violation),
  touching `bin/orama-system/SKILL.md` or `CLAUDE.md` without confirmation,
  and proceeding past the `mcp-orchestration`/`hermes-harness` high-risk
  gate.

## Size Gate

- [ ] `SKILL.md` is <= 200 lines, or the overage has a written reason.
- [ ] `description` stays a single, complete, pushy sentence set — no
      truncation artifacts, no citation markers.
- [ ] Modular files stay one level from `SKILL.md` (no reference chains).

## Anthropic skill-creator Alignment

- [ ] `name` + `description` frontmatter present and third-person.
- [ ] Progressive disclosure: body is a table of contents, details live in
      `references/`, `instructions/`, `examples/`, `eval/`.
- [ ] At least one golden-path example exists (`examples/good/`).
- [ ] Description is appropriately "pushy" — lists concrete trigger phrases,
      not just an abstract capability statement.

## Dogfood Check

- [ ] Run skillify on itself: does `SKILL.md` still match the actual
      Workflow, Folder Shape, and Boundaries sections after the most recent
      edit? (This file exists so that check has a fixed rubric instead of
      relying on memory.)
