---
name: skillify
description: >-
  Interactive modular skill creator for orama-system, raw Claude Code, gstack,
  Codex wrappers, and ECC-style harnesses. Creates concise SKILL.md
  orchestrators with strong discovery metadata, one-level modular references,
  examples, eval checklists, boundaries, and harness registration. Activates for
  create a skill, new skill, add a sub-skill, /skillify, build a skill, make a
  skill, install a skill, modularize a skill, improve a SKILL.md, retiring fellow
  skill library, train smaller models with skills, or adapt .claude/skills
  runbooks into orama-system skills.
version: 1.6.0
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
  - retiring fellow skill library
  - train smaller models with skills
  - adapt .claude/skills runbook
allowed-tools: bash, file-operations, AskUserQuestion
---

# skillify - Concise Skill Orchestrator

> Run from the repo root so relative skill paths resolve correctly.

skillify creates or improves skill folders. `SKILL.md` is the orchestrator, not
the encyclopedia. Put detailed procedures, examples, templates, and eval rubrics
in one-level reference files.

## Related Tools (disambiguation)

Three different things can answer "make me a skill" or "/skillify" — pick
the right one instead of assuming this one, and see Workflow step 0 below
for when to interrupt and ask rather than guess:

| Tool | What it actually does | When it's the right one |
| --- | --- | --- |
| **This skill** (`oramasys-skillify`) | Creates/upgrades canonical `bin/orama-system/skills/<name>/` skills for this repo's own multi-harness stack (Claude Code, gstack, Codex, Cursor, gemini-cli, ECC) — SKILL.md orchestrator + modular references/examples/eval, plus packaging (see below) | Building or upgrading an **orama-system-owned** skill |
| gstack's own `/skillify` (`~/.claude/skills/gstack/skillify/SKILL.md`) | Codifies the most recent successful `/scrape` browser flow into a permanent, deterministic gstack `browser-skill` on disk | Turning a one-off browser scrape into a reusable script — nothing to do with authoring a general-purpose Claude skill |
| Anthropic's official `skill-creator` plugin (`anthropics/claude-plugins-official`, install via `/plugin install skill-creator@claude-plugins-official`) | The canonical Claude tool for creating/improving/benchmarking ANY Claude skill against the Agent Skills open standard — draft, eval loop, description-triggering optimizer | Building a **general-purpose, non-orama** skill, or when the user wants Anthropic's own eval-loop/benchmark workflow rather than this repo's conventions |

This skill's own standards are dogfooded against Anthropic's skill-creator
schema (see "Standards Conflict Note" below and `references/dogfood-upgrade-log.md`),
and its `Packaging` step (below) reimplements skill-creator's validate+zip
rules — so a skill built here is still installable the standard way. It
does not replace or wrap either of the other two tools; use whichever one
actually matches the task.

## Load First

Before writing or revising a skill, read:

- [`../../references/skill-architecture-guide.md`](../../references/skill-architecture-guide.md) - repo standard, frontmatter, progressive disclosure, 6Cs, lint rules
- [`references/modular-skill-authoring.md`](references/modular-skill-authoring.md) - workflow, validation, clobber guard, and report format
- [`references/skill-security-wording-reference-card.md`](references/skill-security-wording-reference-card.md) - aguara-safe wording; avoid literal-command prompt injection in skill docs
- [`examples/bad/security-wording-anti-patterns.md`](examples/bad/security-wording-anti-patterns.md) - literal bad/good curriculum (aguara-ignore quarantine; never copy into SKILL.md)
- [`references/skill-folder-template.md`](references/skill-folder-template.md) - reusable folder layout, short `SKILL.md` template, examples, eval checklist

Read target-specific references only when needed:

- [`references/retiring-fellow-skill-library.md`](references/retiring-fellow-skill-library.md) - adapt retiring-fellow `.claude/skills` library runbooks to `bin/orama-system/skills/`
- [`references/codex-thin-wrapper-installs.md`](references/codex-thin-wrapper-installs.md) - Codex wrapper installs
- [`references/ecc-cross-harness-authoring.md`](references/ecc-cross-harness-authoring.md) - ECC cross-harness skills

## Non-Negotiables

- Write canonical orama skills under `bin/orama-system/skills/<name>/`, never `.claude/skills/`.
- New generated `SKILL.md` files should be under 200 lines. Shorter is better.
- Existing or exceptional `SKILL.md` files must stay under 500 lines.
- Reuse or upgrade existing registered skills before creating siblings.
- Treat `mcp-orchestration` and `hermes-harness` as high-risk; verify Gate 3/HITL, audit-log, and MCP context-firewall checks before edits.
- Use imperative runbook voice; define each jargon term once and reuse it consistently.
- Offload examples, full templates, long rules, and checklists to modular files.
- Keep modular files one level away from `SKILL.md`; avoid reference chains.
- Every fenced code block must include a language specifier.
- Never hardcode secrets, personal paths, raw LAN IPs, or workstation-specific paths.
- **This skill's own `.claude/skills/skillify/SKILL.md` is permanently exempt from `scripts/consolidate-skills.sh`'s thin-wrapper conversion** (hardcoded `EXEMPT_SKILLS` in that script) — it must stay full standalone content, never a wrapper pointing at the canonical copy. Root cause: this repo's `skillify` shares its name with gstack's own bundled `skillify` (unrelated tool); see the collision incident in `references/dogfood-upgrade-log.md` and `docs/LESSONS.md` § 2026-07-24.
- Before naming a new skill or writing to any SHARED global namespace (`~/.claude/skills/`, `~/.codex/skills/`, `~/.agents/skills/`), run `scripts/check-skill-namespace-collision.sh <name>` (repo root) — the single shared check, same script the intake step below and `scripts/install-skills.sh` both call. See `references/modular-skill-authoring.md`'s "External Namespace Collision Check" for the full rule. gstack alone owns ~30 slugs directly under `~/.claude/skills/<name>/`; publishing this repo's skills there is `scripts/install-skills.sh`'s job (disambiguated slugs only, e.g. `oramasys-skillify`, `oramasys-method`) — never bolt a raw `~/.claude/skills` write target onto another script. This repo also owns a skill named `gstack-gbrain` (`bin/orama-system/gstack-gbrain/SKILL.md`, renamed 2026-07-22 from the collision-prone bare `gstack`); never add the bare `gstack` slug to any global-publish list.

## Workflow

0. **Disambiguate before doing anything** if the request could mean any of
   the three tools in "Related Tools" above and isn't already clearly
   scoped to this repo (e.g. bare "/skillify" or "make me a skill" with no
   orama-system context). Raise an `AskUserQuestion` interrupt — do not
   guess:
   - "codify the browser scrape I just ran" / mentions `/scrape` output →
     gstack's `/skillify`, hand off, stop.
   - explicitly orama-system-scoped (mentions this repo, `bin/orama-system/skills/`,
     a harness this repo targets, or an existing orama skill to upgrade) →
     proceed with this skill, no question needed.
   - anything else ambiguous → ask, offering: (a) this skill — an
     orama-system canonical skill, (b) Anthropic's official `skill-creator`
     plugin — a general-purpose Claude skill outside this repo's
     conventions, (c) gstack's `/skillify` — codify a browser scrape. If
     the user wants (b), tell them to install it
     (`/plugin install skill-creator@claude-plugins-official`) and hand off
     rather than imitating its workflow by hand.
1. Ask for skill name, purpose, target harness, trigger phrases, and boundaries. Run `scripts/check-skill-namespace-collision.sh <name>` against the proposed name before continuing — a collision means pick a disambiguated name now, not after writing anything.
2. Choose the smallest folder shape that satisfies the task.
3. Reuse or upgrade existing skills before creating a sibling.
4. If an upstream source is unreachable, continue only from cached/repo-verified material and mark the source `UNVERIFIED - retry required`.
5. For `mcp-orchestration` or `hermes-harness`, verify high-risk upgrade preconditions before proposing edits.
6. Preview frontmatter and the concise `SKILL.md` outline before writing.
7. Run the clobber guard before any write.
8. Write `SKILL.md` plus only the needed modular files.
9. Register in `bin/orama-system/SKILL.md` only for orama sub-skills and only after confirmation.
10. Touch `CLAUDE.md` only after confirmation.
11. Validate frontmatter, line counts, code fences, relative links, 6Cs, and audit notes.
12. Report created files, registration status, and validation result.

## High-Risk Upgrade Precondition

Before upgrading `mcp-orchestration` or `hermes-harness`, verify the checklist in
[`references/retiring-fellow-skill-library.md`](references/retiring-fellow-skill-library.md).
Do not proceed until Gate 3/HITL, audit-log, and MCP context-firewall checks are
explicitly satisfied or the operator acknowledges the block.

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

## Target Rules

- orama-system sub-skill: canonical path is under `bin/orama-system/skills/<name>/` unless the parent registry shows another current convention.
- retiring-fellow library build: read the dedicated reference and upgrade existing skills in place before adding new skills.
- gstack global skill: add gstack frontmatter fields and template source only when requested.
- raw Claude Code skill: keep platform-specific assumptions out unless requested.
- Codex install: create thin wrappers only; never copy canonical skill bodies into local wrapper dirs.
- ECC skill: use harness adapters only at the edge.

## Boundaries

### Always Do

- Read the architecture guide and relevant skillify references before writing.
- Keep `SKILL.md` concise and move long material out.
- Validate generated `SKILL.md` line count: target <= 200, hard ceiling <= 500.
- Run the 6Cs review before declaring done.

### Ask First

- Overwriting or deleting an existing skill directory.
- Writing to `bin/orama-system/SKILL.md`.
- Writing to `CLAUDE.md`.
- Installing or publishing outside the repository.
- Proceeding past a high-risk upgrade precondition that is not verified.

### Never Do

- Source or execute markdown as shell.
- Create a massive all-in-one `SKILL.md`.
- Create nested reference chains.
- Copy canonical repo skill bodies into Codex wrapper directories.
- Write canonical orama skills to `.claude/skills/`.
- Mark done with failing validation.


## Packaging

CLI install (Claude Code, Codex, other `.agents/skills`-style harnesses)
already works via `scripts/install-skills.sh` (repo root) — directory
copies, no packaging needed. For claude.ai / Claude Desktop's Settings ->
Capabilities, which install from an uploaded `.skill` file instead of a
local directory, package a canonical skill with:

```bash
python3 bin/orama-system/skills/skillify/scripts/package_skill.py \
  bin/orama-system/skills/<name> [output-dir]
```

This stages a copy (never edits the canonical files), bundles any
`../../references/*.md` or `bin/orama-system/references/*.md` cross-repo
citation — markdown link or plain backtick path, both forms — into the
staged copy's own `references/`, trims frontmatter to Anthropic's packaged
schema (moving `version`/`parent_skill`/`triggers`/etc. under `metadata:`,
truncating `description` to 1024 chars), validates against the same rules
as Anthropic's `skill-creator` plugin, then zips to `<name>.skill`. See
`references/dogfood-upgrade-log.md` for the full procedure, provenance,
and what's deliberately reimplemented rather than vendored.

## Examples

- Golden path (new skill + self-upgrade dogfood run): [`examples/good/skillify-golden-path.md`](examples/good/skillify-golden-path.md)
- Anti-patterns to avoid: [`examples/bad/anti-patterns.md`](examples/bad/anti-patterns.md)
- Eval rubric to run before declaring a skillify-produced skill done: [`eval/checklist.md`](eval/checklist.md)
- Test prompts for the skill-creator dogfood loop: [`eval/evals.json`](eval/evals.json)
- Audit trail + repeatable procedure for skillify upgrading itself (and oramasys-method) against both standards: [`references/dogfood-upgrade-log.md`](references/dogfood-upgrade-log.md)

## Standards Conflict Note

Anthropic's skill-creator keeps all "when to use" text in the frontmatter
`description` only ("All 'when to use' info goes here, not in the body").
This repo's own [`../../references/skill-architecture-guide.md`](../../references/skill-architecture-guide.md)
recommends a body-level `## When to Use` section too. Where a skill's
`description` already carries full trigger coverage (as this file's does),
prefer Anthropic's leaner rule and skip the redundant body section — but say
so, don't drop it silently. Re-add a body `## When to Use` if `description`
alone isn't carrying enough trigger signal for a given skill.

## Post-Review Micro-Remediation

When addressing review findings (CodeRabbit or human) on an open PR: cluster
findings by root cause, fix once at the abstraction level, keep every commit
mechanically attributable to its failure class, and never accumulate revert
chains — reset to a safety-ref-protected ancestor instead when policy allows.

Full doctrine: [`references/post-review-micro-remediation.md`](../../references/post-review-micro-remediation.md)
