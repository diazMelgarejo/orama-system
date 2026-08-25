# Frequently Asked Questions

## General

### Q: What's the difference between this and other agent skill packages?

A: ultrathink is methodology-first, not tool-first. It encodes a complete problem-solving philosophy
(5 stages + 6 directives) rather than just API wrappers. It's designed to compound improvement over
time via the self-improvement loop.

### Q: Does this work with ECC Tools / everything-claude-code?

A: Yes. Drop `bin/orama-system/` into your ECC Tools skills directory. It follows the SKILL.md
standard and works alongside the 65+ skills in the ECC catalog.

### Q: How is this different from just using Claude normally?

A: Normal Claude is reactive. ultrathink makes Claude systematic: always plans first, always
verifies programmatically, always captures lessons, always demands elegance. The "amplifier
principle" — AI amplifies intent, and ultrathink gives that intent structure.

---

## Installation

### Q: Skill isn't activating. What's wrong?

1. Check SKILL.md is in the correct directory
2. Validate YAML frontmatter syntax (no tab characters, consistent indentation)
3. For Team/Enterprise Claude: verify Skills are enabled org-wide
4. Try manual trigger: "Apply The ὅραμα System to: [task]"

### Q: Do I need Redis for the multi-agent system?

A: No. The default in-memory backend works for development and single-machine setups. Redis is
recommended for production distributed deployments.

---

## Usage

### Q: When should I use the bin/orama-system vs multi-agent version?

A: Single-agent for most tasks — it's faster and simpler. Multi-agent for large parallel tasks
(refactoring many files, researching multiple approaches simultaneously, or when context window is a
bottleneck).

### Q: How do I add my own lessons?

A: Run `capture_lesson.py` with `PERPETUA_TOOLS_ROOT` configured; v1 delegates development lessons
to PT's tracked `.agent` memory. V1 does not start a new user/runtime lesson log. `--backend legacy`
preserves an already initialized compatibility log: it migrates an existing clone or installation
`tasks/lessons.md` to `~/tasks/lessons.md`, or reads an existing path supplied through
`--legacy-path` or `ORAMASYS_LEGACY_LESSONS_PATH`. Missing logs are never created. Runtime capture
starts after v2 Anamnesis provisioning.

### Q: Why do runtime `--review` and `--stats` sometimes work before v2?

A: They are compatibility reads only. They work when `~/tasks/lessons.md` already exists, or when an
explicitly configured legacy log exists. Otherwise runtime review and stats fail closed until
Anamnesis is provisioned. On successful v2 provisioning, the legacy log migrates automatically into
the private runtime store.

### Q: Can I customize the skill for my project?

A: Yes! Add a `## Project-Specific Rules` section to `bin/orama-system/SKILL.md`. Specify your
stack, patterns, and constraints. The skill architecture standard supports this in its "Degrees of
Freedom" section.

---

## Philosophy

### Q: Is this based on real research?

A: Yes. The methodology draws from the "Amplifier Principle" (AI amplifies intent, not replaces
judgment), DORA research on delivery performance, and the architectural optimization standard for
SKILL.md files. See `docs/api-reference.md` for citations.

### Q: What does "self-improving" actually mean?

A: After each mistake or correction, capture a structured lesson through the configured backend. In
v1, PT `.agent` preserves and renders development lessons; its recall and graduation workflow turns
verified patterns into reusable prevention rules.
