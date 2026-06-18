# Antigravity Adapter Map

This folder lets Antigravity CLI enter orama-system without copying the full
portable brain from another repo.

## Canonical Sources

- Repo contract: `AGENTS.md`
- User-facing method: `SKILL.md`
- Canonical mother skill: `bin/orama-system/SKILL.md`
- Lessons: `docs/LESSONS.md`
- Wiki index: `docs/wiki/README.md`
- Skill index: `.agent/skills/_index.md`
- Permissions: `.agent/protocols/permissions.md`

## Operating Rule

Read the canonical source first, then use `.agent/` only as a harness adapter.
If content belongs in every harness, put it in `bin/orama-system/skills/`,
`docs/LESSONS.md`, or `AGENTS.md`, not here.

## Antigravity Dispatch Shape

Use this bounded prompt pattern:

```text
ROLE: Antigravity coding partner for orama-system
GOAL: <specific outcome>
CONSTRAINTS:
- do not commit, delete, deploy, or change accounts
- do not reveal or request secrets
- cite files and tests used as evidence
- return proposed edits only unless explicitly asked to edit
OUTPUT: assumptions, findings, proposed_edits, tests, risks
```

## Skill Loading

Start with `.agent/skills/_index.md`, then load the matching canonical
`SKILL.md` from `bin/orama-system/skills/`.
