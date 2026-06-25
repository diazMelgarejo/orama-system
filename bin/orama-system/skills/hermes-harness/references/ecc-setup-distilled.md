# ECC Setup — Distilled

Distilled from [`ecc-hermes-cross-harness.md`](ecc-hermes-cross-harness.md)
§ "ECC Setup Lessons" for fast-path onboarding. Full rationale is in the source.

## Core Model

Hermes is the operator shell. ECC/orama-system is the reusable substrate.
Do NOT ship raw `~/.hermes` exports — import only sanitized skill text or thin pointers.

| ECC concept | PT-orama adaptation |
|---|---|
| Hermes front door | Hermes operator shell (chat, CLI, cron, workspace state) |
| ECC reusable substrate | orama-system canonical skills + PT middleware |
| `~/.hermes/skills/ecc-imports/` | Sanitized imports from canonical orama skills only |
| `~/.hermes/config.yaml` | Local-only provider routing + MCP registration |
| `~/.hermes/cron/jobs.json` | Local operator automation; NOT repo source of truth |
| `~/.hermes/workspace/` | Private workspace memory — never publish |

## Bring-Up Order

1. Inventory any legacy Hermes/OpenClaw workspace before importing.
2. Plan and scaffold reusable artifacts before copying content.
3. Verify the canonical skill/harness repo tests first.
4. Install Hermes and point it at imported (sanitized) skills.
5. Register only the MCP servers used daily.
6. Authenticate providers locally — start with GitHub and document stores.
7. Start small (one recurring job) before heavier personal workflows.

## Import Safety Checklist

Before importing any Hermes artifact:

- [ ] Is it reusable across operators, or personal to one workspace?
- [ ] Is the asset mainly knowledge, procedure, or runtime behavior?
- [ ] Should it become a skill, command, hook, doc, or issue?
- [ ] Does publishing it leak secrets, private datasets, local paths, or personal state?

If any answer is "private / leaks," do not import — keep it local only.

## What Gets Imported vs. Kept Local

| Import (canonical, sanitized) | Keep local (never ship) |
|---|---|
| Skill text (`SKILL.md`) | Provider credentials |
| Command card (`SKILL.md`) | OAuth tokens |
| Workflow pattern | Raw `~/.hermes` export |
| Hook convention | Personal memory files |
| ECC vocabulary doc | Workspace state |
