# Anti-Patterns

## Giant SKILL.md

Problem: every rule, template, and example gets pasted directly into
`SKILL.md` until it creeps past the 200-line target and toward the 500-line
hard ceiling.

Fix: keep `SKILL.md` as the orchestrator; move long material into
`instructions/`, `references/`, `examples/`, or `eval/`.

## Skipping the Clobber Guard

Problem: writing straight into `bin/orama-system/skills/<name>/` without
first checking whether that directory already exists, silently overwriting
someone else's work-in-progress skill.

Fix: always run the clobber guard from
[`../modular-skill-authoring.md`](../modular-skill-authoring.md) first, and
ask before overwriting.

## Forking Instead of Reusing

Problem: creating `key-rotation-v2/` next to an existing, slightly-thin
`key-rotation/` skill instead of upgrading it in place.

Fix: check the reuse-before-create matrix in
[`../retiring-fellow-skill-library.md`](../retiring-fellow-skill-library.md)
first. Upgrade existing skills; only create a sibling when the gap is real.

## Copying Canonical Bodies Into Wrapper Directories

Problem: a Codex or `.agents/skills` install ends up with a full copy of the
skill body instead of a thin pointer, so the two copies drift the next time
the canonical skill changes.

Fix: follow
[`../codex-thin-wrapper-installs.md`](../codex-thin-wrapper-installs.md) —
wrappers carry only `name`, `description`, and a pointer back to the
canonical `SKILL.md`, never the body.

## Installing Outside the Repo Without Asking

Problem: silently writing skill files into `~/.claude/skills`,
`~/.codex/skills`, or any other path outside this repository because "the
user obviously wants it wired up."

Fix: this is explicitly an **Ask First** boundary. Confirm the target path
and scope before writing anything outside `bin/orama-system/`.

## Silently Resolving Standards Conflicts

Problem: Anthropic's skill-creator standard and this repo's own
`skill-architecture-guide.md` don't always agree (see the golden-path
example) — picking one without saying so hides a real design decision
inside what looks like a routine edit.

Fix: name the conflict, state which standard wins and why, and let the
operator override if they disagree.
