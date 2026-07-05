# Retiring Fellow Skill Library Runbook

Adapted from `tomicz/fable-5-train-opus-skills-after-it-retires` for orama-system.

## Goal

Build or upgrade a complete skill library under:

```text
bin/orama-system/skills/<skill-name>/
```

Do not write canonical orama skills to `.claude/skills/`.

The purpose is continuity: junior/mid-level engineers and smaller AI models must be able to debug, extend, validate, and advance this repo using verified skill runbooks.

## Hard Boundaries

- Write only under `bin/orama-system/skills/` unless the user explicitly approves registry or pointer updates.
- Prefer upgrading existing skills over creating duplicates.
- Do not mutate `.claude/skills/`; that path may be a consumer or wrapper location, not the canonical orama source.
- Ground every command, flag, path, and claim in the repo before writing it.
- Date-stamp volatile facts.
- End each skill or reference with provenance and re-verification commands for facts that may drift.
- Do not use private/user-specific paths as load-bearing sources.
- Keep new `SKILL.md` files <= 200 lines; hard ceiling <= 500 lines.

## Phase 1 - Discover Before Writing

Investigate like an incoming principal engineer before authoring any skill.

Read or inspect:

- `README.md`, `pyproject.toml`, `package.json`, manifests, and install docs.
- `bin/orama-system/SKILL.md` and registered sub-skills.
- `bin/orama-system/references/skill-architecture-guide.md`.
- `docs/v2/README.md`, `docs/LESSONS.md`, `docs/wiki/README.md`, and active plans.
- CI workflows and repo hygiene scripts.
- Existing tests and how they are actually run.
- Git history, reverted work, stalled branches, TODO/FIXME hotspots, and `.agent` memory when available.

Ask at most five questions only for facts the repo cannot reveal:

1. What is the hardest live problem now?
2. What unwritten discipline rule exists?
3. Who is the audience and what do they not know?
4. Which past failure cost the most time?
5. What does `beyond state of the art` mean for this repo?

## Phase 2 - Reuse Or Upgrade Existing Skills First

Existing registered skills already cover major parts of the taxonomy. Use this matrix before creating anything new.

| Source README need | Existing orama skill to reuse or upgrade |
|---|---|
| Change control and doctrine | `skills/code-review`, `cidf`, parent `orama-system` |
| Debugging playbook | `skills/code-review`, `skills/shell-hygiene` |
| Failure archaeology | `skills/git-history-surgery` |
| Architecture contract | parent `orama-system`, `docs/v2/*`, `afrp`, `cidf` |
| Domain reference | create only if no existing reference owns the domain |
| Config and flags | `skills/first-run-setup`, `skills/mcp-install`, `skills/openclaw-skills` |
| Build and environment | `skills/first-run-setup`, `skills/hermes-harness` |
| Run and operate | `skills/openclaw-skills`, `skills/mcp-orchestration` |
| Diagnostics and tooling | `skills/shell-hygiene`, `skills/code-review`, `gstack` |
| Validation and QA | `skills/code-review`, `gstack` QA/review routes |
| Docs and writing | `skills/skillify`, `../../references/skill-architecture-guide.md` |
| External positioning | add a reference or docs/v2 plan only if verified from public sources |
| Hardest-problem campaign | create a narrow campaign skill only after Phase 1 questions |
| Proof and analysis toolkit | create only if repo history has reusable proof patterns |
| Research frontier | create only with falsifiable milestones and no hype |
| Research methodology | create as a compact methodology skill or reference when not covered by existing docs |

If an existing skill is thin, upgrade it in place with a modular reference file. Do not create a sibling with overlapping ownership.

## Phase 3 - Author Missing Skills

If Phase 2 shows a real gap, create one skill per gap.

Required shape:

```text
bin/orama-system/skills/<name>/
├── SKILL.md
├── instructions/
├── examples/good/
├── examples/bad/
├── references/
├── scripts/
├── templates/
└── eval/
```

Trim unused folders. Do not create empty decorative structure.

Every new skill must include:

- trigger-rich YAML `description`,
- when to use and when not to use,
- sibling skill routing,
- copy-pasteable commands only after verification,
- acceptance checks,
- provenance and maintenance notes.

## Phase 4 - Review And Fix

After all planned skills or upgrades exist, run three reviews:

| Review | Checks |
|---|---|
| Factual | Paths, commands, flags, CI, tests, and citations are verified against repo state |
| Doctrine | No contradiction with parent `orama-system`, CIDF, AFRP, security, dry-run, or change-control rules |
| Usability | Trigger quality, scannability, duplication, self-containedness, and sibling routing |

Then apply blocking and important fixes.

## Output Report

Return:

```text
STATUS: DONE / BLOCKED

Inventory:
  <skill> - <one-line purpose>

Reused/upgraded:
  <existing skill> - <what changed>

Created:
  <new skill> - <why existing skills did not cover it>

Verified:
  <commands/files checked>

Uncertain:
  <facts requiring user answer or future verification>
```

## Provenance And Maintenance

Source adapted on 2026-07-06 from:

```text
https://github.com/tomicz/fable-5-train-opus-skills-after-it-retires/blob/main/README.md
```

Re-verify source and target path before rerunning:

```bash
git fetch origin --prune
git status --short --branch
find bin/orama-system/skills -maxdepth 2 -name SKILL.md | sort
sed -n '1,120p' bin/orama-system/SKILL.md
```
